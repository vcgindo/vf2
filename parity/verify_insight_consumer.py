"""Deployed insight SQL over independent terminal legacy populations."""
import argparse
import gzip
import json
import os
from pathlib import Path
from parity.insight_queries import SOURCE,SOURCE_SHA,TABLES,query
from parity.legacy_isolation import connection,exclusive_replay
from parity.output_archive import file_sha
from parity.retained_consumer_input import terminal_inputs
from parity.temporal import differences
from parity.verify_rrr_consumer import temp_rows


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('modern',type=Path); parser.add_argument('evidence',type=Path)
    args=parser.parse_args()
    if args.evidence.exists(): raise ValueError('Preserve receipts; choose a new directory')
    args.evidence.mkdir(parents=True); result=dict(status='FAILED',engine_replays=0,persistent_sql_writes=False)
    try:
        receipt=json.loads((args.modern/'receipt.json').read_text()); root=Path(__file__).resolve().parents[1]
        if receipt['status']!='READBACK_EXPORTED_COMPARISON_REQUIRED' or receipt['boundary']!='UNSCOPED_TERMINAL_INSIGHTS':
            raise ValueError('Wrong export boundary')
        if any(file_sha(root/n)!=sha for n,sha in receipt['sources'].items()): raise ValueError('Modern source changed')
        if file_sha(args.modern/receipt['file'])!=receipt['sha256']: raise ValueError('Modern export changed')
        with gzip.open(args.modern/receipt['file'],'rt') as stream: actual=json.load(stream)
        legacy,provenance=terminal_inputs(); closing=legacy['closing']
        if receipt['run']['id']!=provenance['modern_run'] or receipt['run']['output_digest']!=provenance['modern_output_digest']:
            raise ValueError('Independent run pairing changed')
        result.update(legacy_source=provenance,modern_receipt_sha256=file_sha(args.modern/'receipt.json'),
            source=str(SOURCE),source_sha256=SOURCE_SHA)
        expected={}; queries={}; delta=[]; order=[]
        os.environ['VFTEST_PROFILE']='fresh'
        with exclusive_replay():
            with connection('VFTEST_BTR') as db:
                for table in TABLES: temp_rows(db,'#'+table,'dbo.'+table,closing['btr'][table])
                temp_rows(db,'#DBMMaster','VFTEST_DBM.dbo.DBMMaster',closing['dbm']['DBMMaster'])
                temp_rows(db,'#NMSAllItems','VFTEST_Importer.dbo.NMSAllItems',closing['consumer_context']['NMSAllItems'])
                for case,rows in actual.items():
                    parts=case.split('/'); kind=parts[0]
                    sql=query(kind,horizon=int(parts[1]) if len(parts)>1 else 90,ageing=int(parts[2]) if len(parts)>2 else 1)
                    queries[case]=sql; scalar=db.execute(sql).fetchone()[0]
                    expected[case]=json.loads(scalar) if scalar else None
                    delta+=differences(expected[case],rows,'/'+case)
                    if expected[case] is not None and rows:
                        field=('week' if kind=='availability-trend' else 'date' if kind=='availability-ageing'
                            else 'countSku' if kind=='chronic-loc' else 'countloc' if kind=='chronic-sku' else 'age' if kind=='ageing' else None)
                        order_key=(lambda r:r['NormInc']+r['NormDec']) if kind=='loc' else (lambda r:r[field]) if field else None
                        if order_key and list(map(order_key,expected[case]))!=list(map(order_key,rows)): order.append(case)
                    print('Compared '+case,flush=True)
        for filename,value in (('legacy-insights.json.gz',expected),('queries.json.gz',queries)):
            with gzip.open(args.evidence/filename,'wt') as stream: json.dump(value,stream)
        result.update(status='PASS_RETAINED_INSIGHTS' if not delta and not order else 'FAIL',differences=delta,
            declared_order_differences=order,populations={k:None if v is None else len(v) for k,v in expected.items()},
            evidence_sha256={n:file_sha(args.evidence/n) for n in ('legacy-insights.json.gz','queries.json.gz')},
            qualification='Selected unscoped terminal query results only; no authenticated filters/browser or nonempty claims for empty populations')
    except Exception as exc:
        result['error']=dict(type=type(exc).__name__,message=str(exc)); raise
    finally:
        (args.evidence/'receipt.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({k:result[k] for k in ('status','populations','differences','declared_order_differences')}))
    if delta or order: raise SystemExit(1)


if __name__=='__main__': main()
