"""Actual DLL-generated RRR filters against unchanged retained terminal SQL facts.

Consumer comparison only: session-temp writes, no engine replay or output seed.
Every valid selected request compares typed rows, duplicates, count and order.
Invalid canonical SQL is retained as flaw evidence, never scored as parity.
"""
import argparse
import gzip
import json
import os
from pathlib import Path
import re
import subprocess

from parity.legacy_isolation import connection, exclusive_replay
from parity.output_archive import file_sha, iter_rows, write_rows
from parity.retained_consumer_input import terminal_inputs
from parity.temporal import differences
from parity.verify_rrr_consumer import (EVIDENCE, PICK_RECEIPT_SHA, PERMISSION_SHA, TYPE_SHA,
    RRR_SHA, AUTH_SHA, auth_ctes, selected_sql, supplement_temp_hierarchy, temp_rows, wire_rows)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('modern',type=Path);parser.add_argument('evidence',type=Path)
    parser.add_argument('--hierarchy-supplement',type=Path,required=True)
    args=parser.parse_args()
    if args.evidence.exists(): raise ValueError('Preserve receipts; select a new directory')
    args.evidence.mkdir(parents=True)
    result=dict(status='FAILED',persistent_sql_writes=False,engine_replays=0,cases=[])
    root=Path(__file__).resolve().parents[1]
    try:
        receipt=json.loads((args.modern/'receipt.json').read_text())
        if receipt['status']!='RRR_FILTER_READBACK_EXPORTED_COMPARISON_REQUIRED': raise ValueError('Wrong readback boundary')
        if any(file_sha(root/n)!=sha for n,sha in receipt['sources'].items()): raise ValueError('Readback source changed')
        if file_sha(args.modern/'cases.json')!=receipt['cases_sha256']: raise ValueError('Request roster changed')
        roster=json.loads((args.modern/'cases.json').read_text())['cases']
        supplement=receipt['hierarchy_supplement']
        manifest=json.loads(args.hierarchy_supplement.read_text())
        binding=dict(run_id=receipt['run']['id'],business_date='2026-06-17',output_digest=receipt['run']['output_digest'])
        if (file_sha(args.hierarchy_supplement)!=supplement['sha256'] or binding not in manifest['publications'] or
            manifest['catalogue_sha256']!=PERMISSION_SHA or
            manifest['allowed_fields']!={'products':['SL1','SL2','SL3'],'locations':['LL1','LL2','LL3']}):
            raise ValueError('Approved supplement binding changed')
        permission=Path('D:/freshvcf-build/inputs/permission-input-v1.json')
        if file_sha(permission)!=PERMISSION_SHA: raise ValueError('Retained permission catalogue changed')
        catalogue=json.loads(permission.read_text())
        values,provenance=terminal_inputs()
        if provenance['modern_run']!=binding['run_id'] or provenance['modern_output_digest']!=binding['output_digest']:
            raise ValueError('Terminal pair differs')
        pick_dir=EVIDENCE/'f3-pick-native-comparison-003'
        if file_sha(pick_dir/'receipt.json')!=PICK_RECEIPT_SHA: raise ValueError('Accepted Pick consumer handoff changed')
        pick=json.loads((pick_dir/'receipt.json').read_text())
        if pick['retained_source']!=provenance: raise ValueError('Pick source differs')
        picks=list(iter_rows(pick_dir/'legacy-pick.jsonl.gz',pick['legacy']))
        type_source=Path('F:/VFlow_Local/local-runtime/mta-engine/Scripts/DBCreation/UI_ReportColumnTypes_2.0.sql')
        if file_sha(type_source)!=TYPE_SHA: raise ValueError('Type source differs')
        types={n.casefold():t for n,t in re.findall(r"VALUES \(N'RationRequirementReport', N'([^']+)', N'([^']+)'\)",type_source.read_text())}
        if len(types)!=118: raise ValueError('Type roster differs')
        observed={}
        for obs in receipt['observations']:
            path=args.modern/obs['payload']
            if file_sha(path)!=obs['sha256']: raise ValueError('Readback response changed')
            with gzip.open(path,'rt') as stream: value=json.load(stream)
            key=(obs['case_id'],obs['path'])
            if key in observed: raise ValueError('Duplicate readback observation')
            observed[key]=value
        if len(observed)!=len(roster)*2: raise ValueError('Incomplete count/grid roster')
        # Invoke the actual deployed method, rather than sharing modern predicates.
        request=args.evidence/'requests.json'
        request.write_text(json.dumps(dict(cases=roster),indent=2))
        generated=args.evidence/'deployed-filters.json'
        call=subprocess.run(['pwsh','-NoProfile','-File',str(root/'parity/invoke_legacy_rrr_filters.ps1'),
            '-InputPath',str(request),'-OutputPath',str(generated)],capture_output=True,text=True)
        (args.evidence/'deployed-filter-builder.log').write_text(call.stdout+call.stderr)
        if call.returncode: raise RuntimeError('Pinned DLL invocation failed; see preserved log')
        queries=json.loads(generated.read_text(encoding='utf-8-sig'))
        if queries['input_sha256']!=file_sha(request): raise ValueError('DLL input differs')
        built={item['id']:item for item in queries['cases']}
        if set(built)!={item['id'] for item in roster}: raise ValueError('DLL query roster differs')
        os.environ['VFTEST_PROFILE']='fresh'
        failed=False
        with exclusive_replay():
            with connection('VFTEST_BPR') as db:
                temp_rows(db,'#Pick','dbo.vf_PickListReport',picks)
                closing=values['closing']
                temp_rows(db,'#Standard','VFTEST_Importer.dbo.SKULocStandardAttributes',closing['dbm']['SKULocStandardAttributes'])
                for name,table in (('#Sku','SkuAttributeData'),('#Loc','LocationAttributeData'),('#Pair','SkuLocAttributeData')):
                    temp_rows(db,name,'dbo.'+table,closing['importer'][table])
                supplement_temp_hierarchy(db,catalogue)
                for index,case in enumerate(roster):
                    payload=case['payload']; item=built[case['id']]
                    for route in ('RRRDataCount','RRRData'):
                        if observed[case['id'],route]['request']!=payload: raise ValueError('Modern request substitution')
                    db.execute('DROP TABLE IF EXISTS #ProductPermissions; DROP TABLE IF EXISTS #LocationPermissions')
                    cte=auth_ctes(db,catalogue,payload)
                    sql=selected_sql(item['sql_filter'],item['sql_join_filter'])
                    page=payload['paginationParameter'];size=page['recordsPerPage'];offset=(page['pageNumber']-1)*size
                    query=cte+sql+f' ORDER BY DispatchColorSequence, DispatchPen DESC, WhCode, SKUCode OFFSET {offset} ROWS FETCH NEXT {size} ROWS ONLY'
                    row=dict(id=case['id'],query=query,sql_filter=item['sql_filter'],sql_join_filter=item['sql_join_filter'])
                    try:
                        count=db.execute(cte+', cte_finaldata AS ('+sql+') SELECT COUNT(1) FROM cte_finaldata').fetchone()[0]
                        cursor=db.execute(query);fields=[v[0] for v in cursor.description]
                        expected=wire_rows([dict(zip(fields,r)) for r in cursor.fetchall()],types)
                    except Exception as exc:
                        sql_state=exc.args[0] if exc.args else None
                        row.update(status='LEGACY_FLAW_NOT_PARITY',legacy_error=str(exc),sql_state=sql_state,modern_statuses={
                            p:observed[case['id'],p]['status'] for p in ('RRRDataCount','RRRData')})
                        source_sql_failure=sql_state in ('42S22','42000') and any(text in str(exc).lower()
                            for text in ('invalid column name','could not be bound','incorrect syntax near'))
                        if (not case['canonical_sql_error'] or not source_sql_failure or
                            any(s!=503 for s in row['modern_statuses'].values())):
                            row['status']='FAIL_UNEXPECTED_SQL_OR_MODERN_BOUNDARY'; failed=True
                    else:
                        actual=observed[case['id'],'RRRData']['response']['data']
                        actual_count=observed[case['id'],'RRRDataCount']['response']['recordCount']
                        delta=differences(expected,actual,'/RRRData')+differences(str(count),actual_count,'/RRRDataCount')
                        order=('DispatchColorSequence','DispatchPen','WhCode','SKUCode')
                        delta+=differences([tuple(r[f] for f in order) for r in expected],
                            [tuple(r[f] for f in order) for r in actual],'/ordered-keys')
                        row.update(status='PASS' if not delta and not case['canonical_sql_error'] else 'FAIL',
                            count=count,rows=len(expected),fields=len(fields),differences=delta,
                            legacy_rows=write_rows(args.evidence/('legacy-%02d.jsonl.gz'%index),expected))
                        failed|=row['status']!='PASS'
                    result['cases'].append(row)
                    print(json.dumps(dict(case=case['id'],status=row['status'],count=row.get('count'))),flush=True)
        result.update(status='FAIL' if failed else 'PASS_SELECTED_RRR_FILTERS_WITH_DECLARED_LEGACY_FLAWS',
            strict_pass=sum(x['status']=='PASS' for x in result['cases']),
            legacy_flaws_not_parity=sum(x['status']=='LEGACY_FLAW_NOT_PARITY' for x in result['cases']),
            modern_receipt_sha256=file_sha(args.modern/'receipt.json'),legacy_source=provenance,
            hierarchy_supplement=supplement,query_builder_sha256=file_sha(generated),runtime=queries['runtime'],
            consumer_source_sha256=RRR_SHA,permission_source_sha256=AUTH_SHA,
            qualification='Django/private identity count/grid proof; actual cookie gateway/browser variants remain separate; source-invalid SQL is NOT_PARITY')
    except Exception as exc:
        result['error']=dict(type=type(exc).__name__,message=str(exc)); raise
    finally:
        (args.evidence/'receipt.json').write_text(json.dumps(result,indent=2))
    print(json.dumps({k:result[k] for k in ('status','strict_pass','legacy_flaws_not_parity')}))
    if result['status']=='FAIL': raise SystemExit(1)


if __name__=='__main__': main()
