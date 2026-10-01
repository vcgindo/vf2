"""All terminal DBM daily-history graphs against actual DLL-generated SQL."""
import argparse
import gzip
import json
import os
from pathlib import Path
import re
import subprocess
from parity.legacy_isolation import connection,exclusive_replay
from parity.output_archive import file_sha
from parity.retained_consumer_input import terminal_inputs
from parity.temporal import differences
from parity.verify_rrr_consumer import temp_rows

TABLES=('DBMMaster','DailyConsumption','SuspendHistory','NormChangeLogTbl',
        'SuspendStockType','SuspendConsumptionType','SuggestionsLog','ReasonCodes','LastBatchRunTbl')
ORDERED=dict(StockData='dt',NormData='Ndt',NormChangeHistoryData='nCD',SuggestionHistoryData='sdate')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('modern',type=Path); parser.add_argument('evidence',type=Path)
    args=parser.parse_args()
    if args.evidence.exists(): raise ValueError('Preserve receipts; choose new directory')
    args.evidence.mkdir(parents=True); result=dict(status='FAILED',engine_replays=0,persistent_sql_writes=False)
    try:
        receipt=json.loads((args.modern/'receipt.json').read_text())
        if receipt['status']!='READBACK_EXPORTED_COMPARISON_REQUIRED' or receipt['boundary']!='UNSCOPED_ALL_TERMINAL_DAILY_HISTORY':
            raise ValueError('Wrong modern export boundary')
        root=Path(__file__).resolve().parents[1]
        if any(file_sha(root/n)!=sha for n,sha in receipt['sources'].items()): raise ValueError('Modern source changed')
        if file_sha(args.modern/receipt['file'])!=receipt['sha256']: raise ValueError('Modern export changed')
        with gzip.open(args.modern/receipt['file'],'rt') as stream: actual=json.load(stream)
        legacy,provenance=terminal_inputs(); state=legacy['closing']['dbm']
        if receipt['run']['id']!=provenance['modern_run'] or receipt['run']['output_digest']!=provenance['modern_output_digest']:
            raise ValueError('Independent run pairing changed')
        actual_map={(r['SKUCode'],r['WhCode']):r['graph'] for r in actual}
        pairs=sorted({(r['SKUCode'],r['WhCode']) for r in state['DBMMaster']})
        if len(pairs)!=1240 or set(pairs)!=set(actual_map) or len(actual)!=len(pairs):
            raise ValueError('Required whole-terminal population differs')
        path=args.evidence/'deployed-query-builders.json'; harness=root/'parity/invoke_legacy_daily_history.ps1'
        call=subprocess.run(['pwsh','-NoProfile','-File',str(harness),'-OutputPath',str(path)],text=True,capture_output=True)
        (args.evidence/'deployed-query-builders.log').write_text(call.stdout+call.stderr,encoding='utf-8')
        if call.returncode: raise RuntimeError('Canonical DLL query invocation failed; see retained log')
        methods=json.loads(path.read_text(encoding='utf-8-sig'))
        if len(methods['fragments'])!=7: raise ValueError('Canonical method count changed')
        # Exact outer wrapper in deployed GetDailyDataGraphData; inner SQL is
        # returned by the DLL itself. Only data bindings are replaced below.
        query='select(select '+', '.join(r['sql'] for r in methods['fragments'])+', (select 90)horizonValue for json path, INCLUDE_NULL_VALUES)a'
        for table in sorted(TABLES,key=len,reverse=True): query=re.sub(r'\b'+table+r'\b','#'+table,query)
        tokens=re.findall(r"'(__FRESH_SKU__|__FRESH_LOC__)'",query)
        query=re.sub(r"'(__FRESH_SKU__|__FRESH_LOC__)'",'?',query)
        if not tokens or '__FRESH_' in query: raise ValueError('Unexpected query parameterization')
        result.update(legacy_source=provenance,modern_receipt_sha256=file_sha(args.modern/'receipt.json'),
            deployed_queries_sha256=file_sha(path),invocation_source_sha256=file_sha(harness),runtime=methods['runtime'],query=query)
        expected=[]; delta=[]; ordering=[]; counts={n:0 for n in (
            'StockData','NormData','MasterData','MonitoringData','NormChangeHistoryData','SuggestionHistoryData')}
        os.environ['VFTEST_PROFILE']='fresh'
        with exclusive_replay():
            with connection('VFTEST_DBM') as db:
                for table in TABLES:
                    temp_rows(db,'#'+table,'dbo.'+table,state[table])
                    if table not in ('ReasonCodes','LastBatchRunTbl'):
                        db.execute(f'CREATE INDEX idx_{table}_pair ON #{table} (SKUCode,WhCode)')
                for ordinal,(sku,loc) in enumerate(pairs):
                    parameters=[sku if t=='__FRESH_SKU__' else loc for t in tokens]
                    graph=json.loads(db.execute(query,*parameters).fetchone()[0])
                    if len(graph)!=1: raise ValueError('Unexpected canonical root population')
                    expected.append(dict(SKUCode=sku,WhCode=loc,graph=graph))
                    modern_graph=actual_map[(sku,loc)]
                    if len(modern_graph)!=1: raise ValueError('Modern graph root population differs')
                    # Compare each nested population as a typed bag; check the
                    # explicitly ordered dates separately below. No ordering is
                    # invented for records tied on the source ORDER BY fields.
                    delta+=differences(graph[0],modern_graph[0],f'/daily-history/{sku}/{loc}')
                    for name,date_field in ORDERED.items():
                        # NULL vs [] remains a strict difference above. Ordering
                        # is defined only when both actual populations are lists.
                        a,b=graph[0][name],actual_map[(sku,loc)][0][name]
                        if a is None or b is None: continue
                        if [r[date_field] for r in a] != [r[date_field] for r in b]:
                            ordering.append(dict(SKUCode=sku,WhCode=loc,population=name))
                    for name in counts: counts[name]+=len(graph[0][name] or [])
                    if (ordinal+1)%200==0: print(f'Compared {ordinal+1}/{len(pairs)} retained graphs',flush=True)
        with gzip.open(args.evidence/'legacy-daily-history.json.gz','wt') as stream: json.dump(expected,stream)
        result.update(status='PASS_ALL_TERMINAL_DAILY_HISTORY' if not delta and not ordering else 'FAIL',pairs=len(pairs),rows=counts,
            differences=delta,declared_order_differences=ordering,legacy_readback_sha256=file_sha(args.evidence/'legacy-daily-history.json.gz'),
            qualification='All retained terminal graph populations/typed values/duplicates and temporal sorting; not raw-ingestion coverage, authenticated scopes/browser or unordered tie-order acceptance')
    except Exception as exc:
        result['error']=dict(type=type(exc).__name__,message=str(exc)); raise
    finally:
        (args.evidence/'receipt.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({k:result[k] for k in ('status','pairs','rows')}))
    if result['status']=='FAIL': raise SystemExit(1)


if __name__=='__main__': main()
