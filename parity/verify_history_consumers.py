"""Independent terminal DBM/history readback, with deployed research SQL."""
import argparse,gzip,json,os,subprocess
from datetime import date,datetime
from pathlib import Path
from parity.history_queries import SOURCES,CTE,bind,buffer_query,availability_query,dbm_query
from parity.legacy_isolation import connection,exclusive_replay
from parity.output_archive import file_sha
from parity.retained_consumer_input import terminal_inputs
from parity.temporal import differences
from parity.verify_rrr_consumer import temp_rows

BTR=('BufferTrendPhysicalInv','BufferTrendDispatch','BufferTrendDates','SkuAttributeData','LocationAttributeData','SkuLocAttributeData')
DBM=('DBMMaster','Suggestions','NormAcceptanceTbl','SKUDescriptionTbl','SiteDescriptionTbl','ReasonCodes','SkuAttributeData','LocationAttributeData','SkuLocAttributeData')


def rows(cursor):
    names=[c[0] for c in cursor.description]
    return [{n:v.isoformat() if isinstance(v,(date,datetime)) else v for n,v in zip(names,row)} for row in cursor.fetchall()]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('modern',type=Path);parser.add_argument('evidence',type=Path);args=parser.parse_args()
    if args.evidence.exists(): raise ValueError('Preserve receipts; choose new directory')
    args.evidence.mkdir(parents=True); result=dict(status='FAILED',engine_replays=0,persistent_sql_writes=False)
    try:
        root=Path(__file__).resolve().parents[1]; receipt=json.loads((args.modern/'receipt.json').read_text())
        if receipt['status']!='READBACK_EXPORTED_COMPARISON_REQUIRED' or receipt['boundary']!='UNSCOPED_NATIVE_HISTORY_DBM':
            raise ValueError('Wrong modern export')
        if file_sha(args.modern/receipt['file'])!=receipt['sha256']: raise ValueError('Modern export changed')
        if any(file_sha(root/n)!=sha for n,sha in receipt['sources'].items()): raise ValueError('Modern source changed')
        with gzip.open(args.modern/receipt['file'],'rt') as stream: actual=json.load(stream)
        legacy,provenance=terminal_inputs(include_master=True); closing=legacy['closing']
        if receipt['run']['id']!=provenance['modern_run'] or receipt['run']['output_digest']!=provenance['modern_output_digest']:
            raise ValueError('Run pairing changed')
        fields=('SKUCode','WhCode','ParentWhCode')
        # BPRMaster owns WHCode; the report projection spells it WhCode.
        master=[dict(SKUCode=r['SKUCode'],WhCode=r['WHCode'],ParentWhCode=r['ParentWhCode']) for r in legacy['bpr_master']]
        delta=differences(master,actual['master'],'/BPRMaster-key-parent-projection')
        delta+=differences([{f:r[f] for f in fields[:2]} for r in master],actual['selected'],'/selected-retained-estate')
        if delta: raise ValueError('Parent projection/selection substitution not proved: '+json.dumps(delta[:1]))
        result.update(legacy_source=provenance,modern_receipt_sha256=file_sha(args.modern/'receipt.json'),
            source_sha256={k:v[1] for k,v in SOURCES.items()},master_rows=len(master),master_projection_status='PASS')
        expected={}; querylog={}; formatter_input=dict(selected=actual['selected'],auth=CTE,graphs={})
        os.environ['VFTEST_PROFILE']='fresh'
        with exclusive_replay():
            with connection('VFTEST_BTR') as db:
                for table in BTR: temp_rows(db,'#'+table,'dbo.'+table,closing['btr'][table])
                db.execute('SELECT TOP 0 SKUCode,WhCode,ParentWhCode INTO #BPRMaster FROM VFTEST_BPR.dbo.BPRMaster')
                db.cursor().executemany('INSERT INTO #BPRMaster VALUES (?,?,?)',[tuple(r[f] for f in fields) for r in master])
                for case in actual['graphs']:
                    name,days=case.split('/'); querylog[case]=buffer_query(name,int(days))
                    cursor=db.execute(querylog[case]); counts=rows(cursor)
                    if not cursor.nextset(): raise ValueError('Missing source graph date result')
                    labels=rows(cursor);formatter_input['graphs'][case]=dict(counts=counts,labels=labels)
                querylog['availability']=availability_query();formatter_input['availability']=rows(db.execute(querylog['availability']))
                path=args.evidence/'sql-response-input.json';path.write_text(json.dumps(formatter_input),encoding='utf-8')
                formatter=args.evidence/'deployed-query-dotnet-format.json'
                harness=root/'parity/invoke_legacy_history.ps1'
                call=subprocess.run(['pwsh','-NoProfile','-File',str(harness),'-InputPath',str(path),'-OutputPath',str(formatter)],capture_output=True,text=True)
                (args.evidence/'deployed-query-dotnet-format.log').write_text(call.stdout+call.stderr,encoding='utf-8')
                if call.returncode: raise RuntimeError('Canonical query/.NET formatter failed; see retained log')
                formatted=json.loads(formatter.read_text(encoding='utf-8-sig'))
                if formatted['input_sha256']!=file_sha(path): raise ValueError('Formatter input identity changed')
                querylog['research']=bind(formatted['research_query'])
                scalar=db.execute(querylog['research']).fetchone()[0]; expected['research']=json.loads(scalar) if scalar else None
                expected.update(graphs=formatted['graphs'],availability=formatted['availability'])
                for table in DBM: temp_rows(db,'#DBM_'+table,'VFTEST_DBM.dbo.'+table,closing['dbm'][table])
                for kind in ('grid','count'):
                    sql=dbm_query(count=kind=='count')
                    for table in sorted(DBM,key=len,reverse=True): sql=sql.replace('#'+table,'#DBM_'+table)
                    querylog['dbm/'+kind]=sql;scalar=db.execute(sql).fetchone()[0]
                    expected.setdefault('dbm',{})[kind]=str(scalar) if kind=='count' else json.loads(scalar) if scalar else None
        for name in ('graphs','availability','research','dbm'): delta+=differences(expected[name],actual[name],'/'+name)
        ordering=[]
        for case,graph in expected['graphs'].items():
            for series in ('absolute','percentage'):
                if [r['dt'] for r in graph[series]]!=[r['dt'] for r in actual['graphs'][case][series]]: ordering.append(case+'/'+series)
        for filename,value in (('legacy-history.json.gz',expected),('queries.json.gz',querylog)):
            with gzip.open(args.evidence/filename,'wt') as stream: json.dump(value,stream)
        result.update(status='PASS_RETAINED_HISTORY_DBM' if not delta and not ordering else 'FAIL',differences=delta,
            declared_order_differences=ordering,research_rows=len(expected['research'] or []),dbm_count=expected['dbm']['count'],
            graph_days={c:len(v['absolute']) for c,v in expected['graphs'].items()},runtime=formatted['runtime'],culture=formatted['culture'],
            evidence_sha256={n:file_sha(args.evidence/n) for n in ('legacy-history.json.gz','queries.json.gz','sql-response-input.json','deployed-query-dotnet-format.json')},
            qualification='Retained unscoped consumer proof; actual DLL research query, source-extracted remaining SQL and independent .NET response transcription. Not HTTP-host or nonempty scoped/UI proof; empty DBM is not positive pending-suggestion coverage')
    except Exception as exc:
        result['error']=dict(type=type(exc).__name__,message=str(exc));raise
    finally: (args.evidence/'receipt.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({k:result[k] for k in ('status','research_rows','dbm_count','graph_days','declared_order_differences')}))
    print('difference_count',len(delta))
    if delta or ordering: raise SystemExit(1)


if __name__=='__main__': main()
