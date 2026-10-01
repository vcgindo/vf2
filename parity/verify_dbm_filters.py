"""Independent DBM pre-action consumer comparison using retained legacy capture.

The modern trial owns its calculation/state/actions. SQL reads the earlier
canonical capture; only session-temp consumer metadata tables are written.
"""
import argparse
import gzip
import json
import os
from pathlib import Path
import subprocess
from parity.history_queries import SOURCES, dbm_query
from parity.legacy_isolation import connection, exclusive_replay
from parity.output_archive import file_sha
from parity.temporal import differences
from mta.serialization import digest
from parity.verify_rrr_consumer import PERMISSION_SHA, auth_ctes, temp_rows, supplement_temp_hierarchy

TABLES=('DBMMaster','Suggestions','NormAcceptanceTbl','SKUDescriptionTbl','SiteDescriptionTbl',
        'ReasonCodes','SkuAttributeData','SkuLocAttributeData','LocationAttributeData')
ARTIFACT_SHA='458c7c661cc2e6b2e65f30415042b98ab889c6e151aeaf086c00029c6528c92f'
REPLAY_SHA='316070183c5be144042736e314dfb0eb95a83e4833ae4882457a5bf4ac55dfd5'


def bound(query):
    return query.replace('#SkuAttributeData','#Sku').replace('#LocationAttributeData','#Loc')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('trial',type=Path);parser.add_argument('evidence',type=Path)
    args=parser.parse_args()
    if args.evidence.exists():raise ValueError('Preserve receipts; use a new evidence directory')
    args.evidence.mkdir(parents=True);root=Path(__file__).resolve().parents[1]
    result=dict(status='FAILED',legacy_engine_replays=0,persistent_sql_writes=False,cases=[]);queries={}
    try:
        outer=json.loads((args.trial/'receipt.json').read_text());modern=args.trial/'proof'
        if outer['status']!='DBM_GATEWAY_READBACK_EXPORTED_COMPARISON_REQUIRED':raise ValueError('Wrong actual gateway boundary')
        if file_sha(modern/'receipt.json')!=outer['proof_sha256']:raise ValueError('Modern proof changed')
        receipt=json.loads((modern/'receipt.json').read_text())
        if (receipt['status']!='RETAINED_DBM_GATEWAY_READBACK_EXPORTED_COMPARISON_REQUIRED' or
            receipt['artifact_sha256']!=ARTIFACT_SHA or receipt['retained_replay_sha256']!=REPLAY_SHA or
            receipt['comparisons']!=31 or len(receipt['days'])!=1 or not receipt['existing_runs_and_commands_unchanged']):
            raise ValueError('Wrong retained pre-action/current-day proof')
        if any(file_sha(root/n)!=sha for n,sha in receipt['sources'].items()):raise ValueError('Modern affected source changed')
        selected=receipt['dbm_filters'];day=receipt['days'][0]
        if (selected['run']['id']!=day['run_id'] or selected['run']['output_digest']!=day['output_digest'] or
            selected['boundary']!='RETAINED_DAY_ZERO_PRE_ACTION_DBM_FILTERS' or selected['unauthenticated_status']!=401):
            raise ValueError('Wrong run/date/read boundary')
        path=Path(selected['retained_capture_path'])
        if not path.resolve().is_relative_to(Path('D:/freshvcf-build/evidence').resolve()):raise ValueError('Unregistered source root')
        if file_sha(path)!=selected['retained_capture_sha256']:raise ValueError('Retained legacy capture changed')
        with gzip.open(path,'rt') as stream:legacy=json.load(stream)
        if digest(legacy['closing'])!=selected['legacy_closing_digest']:raise ValueError('Closing-state lineage differs')
        state=legacy['closing']['dbm']
        catalogue_path=Path('D:/freshvcf-build/inputs/permission-input-v1.json')
        if file_sha(catalogue_path)!=PERMISSION_SHA:raise ValueError('Retained catalogue changed')
        catalogue=json.loads(catalogue_path.read_text())
        supplement=modern/selected['hierarchy_file'];manifest=json.loads(supplement.read_text())
        if (file_sha(supplement)!=selected['hierarchy_supplement']['sha256'] or manifest['catalogue_sha256']!=PERMISSION_SHA or
            manifest['allowed_fields']!={'products':['SL1','SL2','SL3'],'locations':['LL1','LL2','LL3']} or
            manifest['publications']!=[dict(run_id=day['run_id'],business_date=day['date'],output_digest=day['output_digest'])]):
            raise ValueError('Identical run-bound supplement required')
        request=modern/'dbm-cases.json'
        if file_sha(request)!=selected['cases_sha256']:raise ValueError('Frozen request roster changed')
        roster=json.loads(request.read_text())['cases'];observed={}
        for obs in selected['observations']:
            path=modern/obs['file']
            if file_sha(path)!=obs['sha256']:raise ValueError('Readback changed')
            with gzip.open(path,'rt') as stream:value=json.load(stream)
            key=obs['case_id'],obs['route']
            if key in observed:raise ValueError('Duplicate readback')
            observed[key]=value
        if len(observed)!=2*len(roster):raise ValueError('Incomplete count/grid roster')
        generated=args.evidence/'deployed-filters.json'
        call=subprocess.run(['pwsh','-NoProfile','-File',str(root/'parity/invoke_legacy_rrr_filters.ps1'),
            '-Report','DBM','-InputPath',str(request),'-OutputPath',str(generated)],capture_output=True,text=True)
        (args.evidence/'deployed-builder.log').write_text(call.stdout+call.stderr)
        if call.returncode:raise RuntimeError('Canonical DLL method failed; see retained log')
        generated_values=json.loads(generated.read_text(encoding='utf-8-sig'))
        if generated_values['input_sha256']!=file_sha(request) or generated_values['report']!='DBM':raise ValueError('DLL input differs')
        built={r['id']:r for r in generated_values['cases']}
        if set(built)!={r['id'] for r in roster}:raise ValueError('DLL roster differs')
        os.environ['VFTEST_PROFILE']='fresh';failed=False
        with exclusive_replay():
            with connection('VFTEST_DBM') as db:
                for table in TABLES:
                    alias='#Sku' if table=='SkuAttributeData' else '#Loc' if table=='LocationAttributeData' else '#'+table
                    temp_rows(db,alias,'dbo.'+table,state[table])
                supplement_temp_hierarchy(db,catalogue)
                for index,case in enumerate(roster):
                    payload=case['payload'];parts=built[case['id']]
                    db.execute('DROP TABLE IF EXISTS #ProductPermissions;DROP TABLE IF EXISTS #LocationPermissions')
                    auth=auth_ctes(db,catalogue,payload);page=payload['paginationParameter']
                    for route in ('DBMDataCount','DBMData'):
                        actual=observed[case['id'],route]
                        if actual['request']!=payload:raise ValueError('Request substitution')
                        query=bound(dbm_query(count=route=='DBMDataCount',page=page['pageNumber'],size=page['recordsPerPage'],
                            sql_filter=parts['sql_filter'],sql_join_filter=parts['sql_join_filter'],auth_cte=auth))
                        queries[case['id']+'/'+route]=query
                        row=dict(id=case['id'],route=route,transport=actual['transport'],modern_status=actual['status'])
                        try:
                            scalar=db.execute(query).fetchone()[0]
                            expected=str(scalar) if route=='DBMDataCount' else json.loads(scalar) if scalar else None
                        except Exception as exc:
                            source_error=exc.args and exc.args[0] in ('42S22','42000') and any(x in str(exc).lower()
                                for x in ('invalid column name','could not be bound','incorrect syntax near','ambiguous column name'))
                            if not source_error:raise
                            row.update(status='LEGACY_FLAW_NOT_PARITY' if case['sql_error'] and actual['status']==503 else 'FAIL',
                                legacy_error=str(exc),sql_state=exc.args[0])
                        else:
                            data=actual['response'];value=data.get('recordCount') if route=='DBMDataCount' else data.get('data')
                            delta=differences(expected,value,'/'+route)
                            if route=='DBMData':
                                keys=lambda rows:[(r['RN'],r['SKUCode'],r['LocCode']) for r in rows or []]
                                delta+=differences(keys(expected),keys(value),'/ordered/RN-SKU-location')
                            row.update(status='PASS' if not delta and actual['status']==200 and not case['sql_error'] else 'FAIL',
                                differences=delta,count=expected if route=='DBMDataCount' else len(expected or []))
                            filename='legacy-%02d-%s.json.gz'%(index,route)
                            with gzip.open(args.evidence/filename,'wt') as stream:json.dump(expected,stream)
                            row.update(legacy_response=filename,legacy_response_sha256=file_sha(args.evidence/filename))
                        result['cases'].append(row);failed|=row['status']=='FAIL'
                    print(json.dumps(dict(case=case['id'],results=[r['status'] for r in result['cases'][-2:]])),flush=True)
        result.update(status='FAIL' if failed else 'PASS_RETAINED_DBM_PRE_ACTION_FILTERS_WITH_DECLARED_LEGACY_FLAWS',
            strict_pass=sum(r['status']=='PASS' for r in result['cases']),legacy_flaws_not_parity=sum(r['status']=='LEGACY_FLAW_NOT_PARITY' for r in result['cases']),
            modern_trial_receipt_sha256=file_sha(args.trial/'receipt.json'),modern_proof_sha256=outer['proof_sha256'],
            source_sha256=SOURCES['dbm'][1],retained_capture_sha256=selected['retained_capture_sha256'],
            current_day_contracts=31,modern_trial_run_id=day['run_id'],hierarchy_supplement=selected['hierarchy_supplement'],
            actual_gateway_requests=selected['real_gateway_requests'],
            qualification='One retained pre-action shallow trial; source-invalid SQL NOT_PARITY; leaf scopes are private asserted cases, not new leaf login; terminal publication unchanged')
    except Exception as exc:
        result['error']=dict(type=type(exc).__name__,message=str(exc));raise
    finally:
        with gzip.open(args.evidence/'queries.json.gz','wt') as stream:json.dump(queries,stream)
        result['queries_sha256']=file_sha(args.evidence/'queries.json.gz')
        (args.evidence/'receipt.json').write_text(json.dumps(result,indent=2))
    print(json.dumps({k:result[k] for k in ('status','strict_pass','legacy_flaws_not_parity')}))
    if result['status']=='FAIL':raise SystemExit(1)


if __name__=='__main__':main()
