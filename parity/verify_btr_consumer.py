"""Exact deployed BTR SQL on retained legacy rows; session-temp writes only."""
import argparse
from datetime import date, datetime
import gzip
import json
import os
from pathlib import Path
from parity.btr_queries import SOURCE,SOURCE_SHA,REQ_FIELDS,grid_query,count_queries
from parity.legacy_isolation import connection,exclusive_replay
from parity.output_archive import file_sha
from parity.retained_consumer_input import terminal_inputs
from parity.temporal import differences
from parity.verify_rrr_consumer import temp_rows


def grid_rows(cursor):
    names=[c[0] for c in cursor.description]
    return [{n:'' if v is None else str(v) for n,v in zip(names,row)} for row in cursor.fetchall()]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('modern',type=Path); parser.add_argument('evidence',type=Path)
    args=parser.parse_args()
    if args.evidence.exists(): raise ValueError('Preserve receipts; choose a new directory')
    args.evidence.mkdir(parents=True); result=dict(status='FAILED',engine_replays=0,persistent_sql_writes=False)
    try:
        receipt=json.loads((args.modern/'receipt.json').read_text()); root=Path(__file__).resolve().parents[1]
        if receipt['status']!='READBACK_EXPORTED_COMPARISON_REQUIRED' or receipt['boundary']!='UNSCOPED_TERMINAL_BTR':
            raise ValueError('Wrong export boundary')
        if any(file_sha(root/n)!=sha for n,sha in receipt['sources'].items()): raise ValueError('Modern source changed')
        if file_sha(args.modern/receipt['file'])!=receipt['sha256']: raise ValueError('Modern export changed')
        with gzip.open(args.modern/receipt['file'],'rt') as stream: actual=json.load(stream)
        legacy,provenance=terminal_inputs(include_requirements=True); closing=legacy['closing']
        if receipt['run']['id']!=provenance['modern_run'] or receipt['run']['output_digest']!=provenance['modern_output_digest']:
            raise ValueError('Independent run pairing changed')
        req=[{f:r[f] for f in REQ_FIELDS} for r in legacy['requirements']]
        rationed=[{f:r[f] for f in REQ_FIELDS} for r in legacy['late']['vf_RationedReqReport']]
        delta=differences(req,rationed,'/canonical-requirement-to-report-five-fields')
        delta+=differences(req,actual['requirements'],'/modern-native-requirement-projection')
        if delta: raise ValueError('Required source substitution not proved: '+json.dumps(delta[:3]))
        result.update(legacy_source=provenance,modern_receipt_sha256=file_sha(args.modern/'receipt.json'),
            source=str(SOURCE),source_sha256=SOURCE_SHA,requirement_projection_rows=len(req),
            requirement_projection_fields=list(REQ_FIELDS),requirement_projection_status='PASS')
        expected=dict(counts={},cases={}); queries={}; ordering=[]
        os.environ['VFTEST_PROFILE']='fresh'
        with exclusive_replay():
            with connection('VFTEST_BTR') as db:
                for table in ('BPPTrendDispatch','BPPTrendPhysicalInv','BufferTrendDispatch','BufferTrendPhysicalInv',
                    'SkuLocAttributeData','SkuAttributeData','LocationAttributeData','BufferTrendDates'):
                    temp_rows(db,'#'+table,'dbo.'+table,closing['btr'][table])
                temp_rows(db,'#Rationed','VFTEST_BPR.dbo.vf_RationedReqReport',legacy['late']['vf_RationedReqReport'])
                fields=','.join('['+f+']' for f in REQ_FIELDS)
                db.execute(f'SELECT TOP 0 {fields} INTO #Req FROM VFTEST_BPR.dbo.vf_ReqCalculation')
                db.cursor().executemany('INSERT INTO #Req VALUES (?,?,?,?,?)',[tuple(r[f] for f in REQ_FIELDS) for r in req])
                temp_rows(db,'#Standard','VFTEST_Importer.dbo.SKULocStandardAttributes',closing['dbm']['SKULocStandardAttributes'])
                for table in ('SKUDescriptionTbl','SiteDescriptionTbl'):
                    temp_rows(db,'#'+table,'VFTEST_Importer.dbo.'+table,closing['importer'][table])
                temp_rows(db,'#CategoryColDescription','dbo.CategoryColDescription',closing['consumer_context']['CategoryColDescription'])
                for name,query in count_queries().items():
                    queries['count/'+name]=query
                    expected['counts'][name]=str(db.execute(query).fetchone()[0])
                delta+=differences(expected['counts'],actual['counts'],'/counts')
                for case,selected in actual['cases'].items():
                    start,end=selected['start'],selected['end']
                    cursor=db.execute('SELECT '+','.join(f'D{i}' for i in range(start,end+1))+' FROM #BufferTrendDates')
                    names=[c[0] for c in cursor.description]
                    labels=[{n:v.strftime('%Y-%m-%d') if isinstance(v,(date,datetime)) else '' if v is None else str(v)
                             for n,v in zip(names,row)} for row in cursor.fetchall()]
                    expected['cases'][case]=dict(labels=labels)
                    delta+=differences(labels,selected['labels'],'/'+case+'/labels')
                    for branch in ('tech','eco'):
                        query=grid_query(branch,page=selected['page'],size=selected['size'],start=start,end=end)
                        queries[case+'/'+branch]=query; rows=grid_rows(db.execute(query))
                        expected['cases'][case][branch]=rows
                        delta+=differences(rows,selected[branch],'/'+case+'/'+branch)
                        keys=lambda values:[(r['SKUCode'],r['WhCode']) for r in values]
                        if keys(rows)!=keys(selected[branch]): ordering.append(case+'/'+branch)
                    query=grid_query('both',page=selected['page'],size=selected['size'],start=start,end=end)
                    queries[case+'/both']=query; combined=grid_rows(db.execute(query))
                    expected['cases'][case]['both']=combined
                    delta+=differences(combined,selected['eco']+selected['tech'],'/'+case+'/both')
                    for branch in ('tech','eco'):
                        if keys([r for r in combined if r['Source']==branch])!=keys(selected[branch]):
                            ordering.append(case+'/both/'+branch)
                    print('Compared BTR '+case,flush=True)
                query=grid_query('both'); queries['both']=query
                try:
                    combined=grid_rows(db.execute(query))
                    expected['combined']=dict(status='EXECUTED',rows=combined)
                except Exception as exc:
                    # Retain the exact exception, not a repaired SQL statement.
                    expected['combined']=dict(status='SOURCE_QUERY_FAILED',type=type(exc).__name__,error=str(exc))
                # Same exact Category metadata bag, reversed physical insertion.
                # Only session-temp rows change; canonical SQL is untouched.
                categories=closing['consumer_context']['CategoryColDescription']
                fields=list(categories[0]); db.execute('DELETE FROM #CategoryColDescription')
                db.cursor().executemany('INSERT INTO #CategoryColDescription ('+','.join('['+f+']' for f in fields)+') VALUES ('+
                    ','.join('?' for _ in fields)+')',[tuple(r[f] for f in fields) for r in reversed(categories)])
                reordered=grid_rows(db.execute(grid_query('tech')))
                expected['category_reordered']=reordered
                category_order_delta=differences(expected['cases']['full']['tech'],reordered,'/same-category-bag-reversed')
        for filename,value in (('legacy-btr.json.gz',expected),('queries.json.gz',queries)):
            with gzip.open(args.evidence/filename,'wt') as stream: json.dump(value,stream)
        result.update(status='PASS_SELECTED_SINGLE_BRANCHES' if not delta and not ordering else 'FAIL',
            differences=delta,declared_order_differences=ordering,counts=expected['counts'],
            row_counts={c:{b:len(v[b]) for b in ('tech','eco')} for c,v in expected['cases'].items()},
            combined=expected['combined'] if expected['combined']['status']=='SOURCE_QUERY_FAILED' else dict(status='EXECUTED'),
            category_order_probe=dict(changed=bool(category_order_delta),differences=category_order_delta),
            evidence_sha256={n:file_sha(args.evidence/n) for n in ('legacy-btr.json.gz','queries.json.gz')},
            qualification='Unscoped retained single-branch reports only; not authenticated filters/browser or general unordered Category alias parity')
    except Exception as exc:
        result['error']=dict(type=type(exc).__name__,message=str(exc)); raise
    finally:
        (args.evidence/'receipt.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({k:result[k] for k in ('status','counts','row_counts','combined')}))
    if delta or ordering: raise SystemExit(1)


if __name__=='__main__': main()
