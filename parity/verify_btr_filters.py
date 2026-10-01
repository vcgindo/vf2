"""Compare deployed DLL BTR filters on retained canonical terminal facts.

Only SQL session-temp tables are written. No daily replay, regenerated facts,
modern output oracle, legacy repair or calculation acceptance substitution.
"""
import argparse
from datetime import date, datetime
import gzip
import json
import os
from pathlib import Path
import subprocess
from parity.btr_queries import SOURCE_SHA, REQ_FIELDS, grid_query, count_queries
from parity.legacy_isolation import connection, exclusive_replay
from parity.output_archive import file_sha
from parity.retained_consumer_input import terminal_inputs
from parity.temporal import differences
from parity.verify_btr_consumer import grid_rows
from parity.verify_rrr_consumer import (PERMISSION_SHA, auth_ctes, temp_rows, supplement_temp_hierarchy)


def bound(query):
    return query.replace('#SkuAttributeData','#Sku').replace('#LocationAttributeData','#Loc')


def source_sql_failure(exc):
    return exc.args and exc.args[0] in ('42S22','42000') and any(text in str(exc).lower()
        for text in ('invalid column name','could not be bound','incorrect syntax near','ambiguous column name'))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('modern',type=Path); parser.add_argument('evidence',type=Path)
    parser.add_argument('--hierarchy-supplement',type=Path,required=True)
    args=parser.parse_args()
    if args.evidence.exists(): raise ValueError('Preserve receipts; use a new evidence directory')
    args.evidence.mkdir(parents=True); root=Path(__file__).resolve().parents[1]
    result=dict(status='FAILED',engine_replays=0,persistent_sql_writes=False,cases=[])
    queries={}
    try:
        receipt=json.loads((args.modern/'receipt.json').read_text())
        if receipt['status']!='BTR_FILTER_READBACK_EXPORTED_COMPARISON_REQUIRED': raise ValueError('Wrong readback boundary')
        if any(file_sha(root/n)!=sha for n,sha in receipt['sources'].items()): raise ValueError('Modern source changed')
        if file_sha(args.modern/'cases.json')!=receipt['cases_sha256']: raise ValueError('Request roster changed')
        roster=json.loads((args.modern/'cases.json').read_text())['cases']
        supplement=receipt['hierarchy_supplement']; manifest=json.loads(args.hierarchy_supplement.read_text())
        binding=dict(run_id=receipt['run']['id'],business_date='2026-06-17',output_digest=receipt['run']['output_digest'])
        if (file_sha(args.hierarchy_supplement)!=supplement['sha256'] or binding not in manifest['publications'] or
            manifest['catalogue_sha256']!=PERMISSION_SHA or manifest['allowed_fields']!=
                {'products':['SL1','SL2','SL3'],'locations':['LL1','LL2','LL3']}): raise ValueError('Supplement binding changed')
        path=Path('D:/freshvcf-build/inputs/permission-input-v1.json')
        if file_sha(path)!=PERMISSION_SHA: raise ValueError('Retained catalogue changed')
        catalogue=json.loads(path.read_text())
        legacy,provenance=terminal_inputs(include_requirements=True); closing=legacy['closing']
        if provenance['modern_run']!=binding['run_id'] or provenance['modern_output_digest']!=binding['output_digest']:
            raise ValueError('Retained terminal pairing changed')
        req=[{f:r[f] for f in REQ_FIELDS} for r in legacy['requirements']]
        rationed=[{f:r[f] for f in REQ_FIELDS} for r in legacy['late']['vf_RationedReqReport']]
        if differences(req,rationed,'/native-five-fields'): raise ValueError('Five-field compatibility changed')
        observations={}
        for obs in receipt['observations']:
            path=args.modern/obs['payload']
            if file_sha(path)!=obs['sha256']: raise ValueError('Readback changed')
            with gzip.open(path,'rt') as stream: value=json.load(stream)
            key=(obs['case_id'],obs['path'])
            if key in observations: raise ValueError('Duplicate observation')
            observations[key]=value
        if len(observations)!=len(roster)*2: raise ValueError('Incomplete readback')
        request=args.evidence/'requests.json'; request.write_text(json.dumps(dict(cases=roster),indent=2))
        generated=args.evidence/'deployed-filters.json'
        call=subprocess.run(['pwsh','-NoProfile','-File',str(root/'parity/invoke_legacy_rrr_filters.ps1'),
            '-Report','BTR','-InputPath',str(request),'-OutputPath',str(generated)],capture_output=True,text=True)
        (args.evidence/'deployed-filter-builder.log').write_text(call.stdout+call.stderr)
        if call.returncode: raise RuntimeError('Canonical DLL invocation failed; retained log')
        built=json.loads(generated.read_text(encoding='utf-8-sig'))
        if built['input_sha256']!=file_sha(request) or built['report']!='BTR': raise ValueError('DLL request changed')
        query_by_id={r['id']:r for r in built['cases']}
        if set(query_by_id)!={r['id'] for r in roster}: raise ValueError('DLL roster changed')
        os.environ['VFTEST_PROFILE']='fresh'; failed=False
        with exclusive_replay():
            with connection('VFTEST_BTR') as db:
                for table in ('BPPTrendDispatch','BPPTrendPhysicalInv','BufferTrendDispatch','BufferTrendPhysicalInv',
                    'SkuLocAttributeData','SkuAttributeData','LocationAttributeData','BufferTrendDates'):
                    alias='#Sku' if table=='SkuAttributeData' else '#Loc' if table=='LocationAttributeData' else '#'+table
                    temp_rows(db,alias,'dbo.'+table,closing['btr'][table])
                supplement_temp_hierarchy(db,catalogue)
                temp_rows(db,'#Rationed','VFTEST_BPR.dbo.vf_RationedReqReport',legacy['late']['vf_RationedReqReport'])
                db.execute('SELECT TOP 0 '+','.join('['+f+']' for f in REQ_FIELDS)+' INTO #Req FROM VFTEST_BPR.dbo.vf_ReqCalculation')
                db.cursor().executemany('INSERT INTO #Req VALUES (?,?,?,?,?)',[tuple(r[f] for f in REQ_FIELDS) for r in req])
                temp_rows(db,'#Standard','VFTEST_Importer.dbo.SKULocStandardAttributes',closing['dbm']['SKULocStandardAttributes'])
                for table in ('SKUDescriptionTbl','SiteDescriptionTbl'):
                    temp_rows(db,'#'+table,'VFTEST_Importer.dbo.'+table,closing['importer'][table])
                temp_rows(db,'#CategoryColDescription','dbo.CategoryColDescription',closing['consumer_context']['CategoryColDescription'])
                cursor=db.execute('SELECT '+','.join(f'D{i}' for i in range(79,91))+' FROM #BufferTrendDates')
                fields=[c[0] for c in cursor.description]
                labels=[{n:v.strftime('%Y-%m-%d') if isinstance(v,(date,datetime)) else '' if v is None else str(v)
                    for n,v in zip(fields,row)} for row in cursor.fetchall()]
                for index,case in enumerate(roster):
                    payload=case['payload']; query=query_by_id[case['id']]
                    db.execute('DROP TABLE IF EXISTS #ProductPermissions; DROP TABLE IF EXISTS #LocationPermissions')
                    auth=auth_ctes(db,catalogue,payload)
                    kwargs=dict(sql_filter=query['sql_filter'],sql_join_filter=query['sql_join_filter'],auth_cte=auth)
                    counts={}; errors=[]
                    for name,q in count_queries(**kwargs).items():
                        queries[case['id']+'/count/'+name]=bound(q)
                        try: counts['TechCount' if name=='tech' else 'EcoCount']=str(db.execute(bound(q)).fetchone()[0])
                        except Exception as exc:
                            if not source_sql_failure(exc): raise
                            errors.append(dict(branch=name,error=str(exc),sql_state=exc.args[0]))
                    page=payload['paginationParameter']
                    q=bound(grid_query(payload['name'],page=page['pageNumber'],size=page['recordsPerPage'],start=79,end=90,**kwargs))
                    queries[case['id']+'/grid']=q
                    try:
                        rows=grid_rows(db.execute(q)); grid=dict(tech=[r for r in rows if r['Source']=='tech'],
                            eco=[r for r in rows if r['Source']=='eco'],labels=labels); grid_error=None
                        with gzip.open(args.evidence/('legacy-%02d.json.gz'%index),'wt') as stream: json.dump(grid,stream)
                    except Exception as exc:
                        if not source_sql_failure(exc): raise
                        grid_error=dict(error=str(exc),sql_state=exc.args[0])
                    for route,expected,error in (('GetBTRDataCount',counts,errors or None),('GetBTRData',None if grid_error else grid,grid_error)):
                        actual=observations[case['id'],route]
                        if actual['request']!=payload: raise ValueError('Request substitution')
                        row=dict(id=case['id'],route=route,modern_status=actual['status'])
                        if error:
                            row.update(status='LEGACY_FLAW_NOT_PARITY' if route in case['sql_errors'] and actual['status']==503 else 'FAIL',
                                legacy_error=error)
                        else:
                            delta=differences(expected,actual['response'].get('data'),'/'+route)
                            if route=='GetBTRData':
                                for branch in ('tech','eco'):
                                    keys=lambda values:[(r['SKUCode'],r['WhCode']) for r in values]
                                    delta+=differences(keys(expected[branch]),keys(actual['response']['data'][branch]),'/ordered/'+branch)
                            row.update(status='PASS' if not delta and actual['status']==200 and route not in case['sql_errors'] else 'FAIL',
                                differences=delta,counts=counts if route=='GetBTRDataCount' else {b:len(grid[b]) for b in ('tech','eco')})
                            if route=='GetBTRData':
                                row['legacy_response_file']='legacy-%02d.json.gz'%index
                                row['legacy_response_sha256']=file_sha(args.evidence/row['legacy_response_file'])
                        result['cases'].append(row); failed|=row['status']=='FAIL'
                    print(json.dumps(dict(case=case['id'],results=[r['status'] for r in result['cases'][-2:]])),flush=True)
        result.update(status='FAIL' if failed else 'PASS_SELECTED_BTR_FILTERS_WITH_DECLARED_LEGACY_FLAWS',
            strict_pass=sum(r['status']=='PASS' for r in result['cases']),
            legacy_flaws_not_parity=sum(r['status']=='LEGACY_FLAW_NOT_PARITY' for r in result['cases']),
            legacy_source=provenance,source_sha256=SOURCE_SHA,modern_receipt_sha256=file_sha(args.modern/'receipt.json'),
            hierarchy_supplement=supplement,query_builder_sha256=file_sha(generated),
            qualification='Finite read-only snapshot/private-identity consumer proof; cookie gateway/browser separate; invalid SQL NOT_PARITY')
    except Exception as exc:
        result['error']=dict(type=type(exc).__name__,message=str(exc)); raise
    finally:
        with gzip.open(args.evidence/'queries.json.gz','wt') as stream: json.dump(queries,stream)
        result['queries_sha256']=file_sha(args.evidence/'queries.json.gz')
        (args.evidence/'receipt.json').write_text(json.dumps(result,indent=2))
    print(json.dumps({k:result[k] for k in ('status','strict_pass','legacy_flaws_not_parity')}))
    if result['status']=='FAIL': raise SystemExit(1)


if __name__=='__main__': main()
