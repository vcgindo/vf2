"""Retained RRR SQL + deployed header builder/CsvHelper vs candidate export.

Session-temp SQL only; no calculation replay, serving action or fixture replacement.
"""
import base64
from copy import deepcopy
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

from parity.output_archive import file_sha, iter_rows
from parity.retained_consumer_input import terminal_inputs
from parity.legacy_isolation import connection, exclusive_replay
from parity.verify_rrr_consumer import (EVIDENCE, PICK_RECEIPT_SHA, PERMISSION_SHA,
    auth_ctes, selected_sql, supplement_temp_hierarchy, temp_rows)

ROOT=Path(__file__).resolve().parents[1]
CONFIG=Path('F:/VFlow_Local/local-runtime/mta-engine/Scripts/DBCreation/UI_ReportConfiguration_2.0.sql')


def typed(value):
    kind=('null' if value is None else 'bool' if isinstance(value,bool) else
          'decimal' if isinstance(value,Decimal) else 'int' if isinstance(value,int) else
          'float' if isinstance(value,float) else 'str')
    return dict(type=kind,value=str(value) if kind in ('decimal','float') else value)


def call(args,target):
    result=subprocess.run(args,text=True,capture_output=True)
    target.write_text(result.stdout+'\n'+result.stderr,encoding='utf-8')
    if result.returncode: raise RuntimeError('Failed command; see '+str(target))
    return result.stdout


def main():
    target=Path(sys.argv[1]);target.mkdir(parents=True,exist_ok=False)
    result=dict(status='FAILED',engine_replays=0,persistent_database_writes=False)
    try:
        parent=EVIDENCE/'f3-rrr-filters-modern-001'
        assert file_sha(parent/'receipt.json')=='f96cc963afce16ce3342ab49b7448ecea047159e71efe745bf81b568049c0dff'
        old=json.loads((parent/'cases.json').read_text())['cases']
        selected=('root-regression','selected-leaf','parent-leaf-empty','overlapping-permission-ids','location-type')
        cases=[dict(id=c['id'],payload=deepcopy(c['payload']),layout='') for c in old if c['id'] in selected]
        for case in cases:
            case['payload'].update(reportName='RRR',user={'id':'rrr-export-proof'},stream=1,ISExport='1')
        root=deepcopy(cases[0])
        root['id']='pagination-ignored';root['payload']['paginationParameter']={'recordsPerPage':1}
        cases.append(root)
        for name,layout in (
            ('saved-layout',{'columns':[{'colId':'SKUName'},{'colId':'SKUCode','pinned':'left'},
                {'colId':'Norm','hide':True},{'colId':'WhCode','pinned':'right'},
                {'colId':'IsNormed'},{'colId':'not-returned'},{'colId':'SKUName'}]}),
            ('empty-layout',{'columns':[]}),('invalid-json','not-json'),
            ('all-raw-columns',{'columns':[{'colId':k} for k in (
                'SpikeThreshold','PSOThreshold','TPen','EPen','ParentNorm','IsNormed','SKULocAttr9','SKUName')]})):
            case=deepcopy(cases[0]);case['id']=name
            case['layout']=layout if isinstance(layout,str) else json.dumps(layout)
            cases.append(case)
        (target/'requests.json').write_text(json.dumps(dict(cases=cases),indent=2))
        result['requests_sha256']=file_sha(target/'requests.json')
        runtime=json.loads(subprocess.check_output(['docker','inspect','freshvcf-preview-mta-1'],text=True))[0]
        args=['docker','run','--rm','--name','freshvcf-rrr-export-proof','--network','freshvcf-test_default',
            '--memory','4g','--memory-swap','4g','--cpus','2','-v',str(ROOT).replace('\\','/')+':/app:ro',
            '-v','D:/freshvcf-build/evidence:/evidence:ro','-e','PYTHONPATH=/app']
        for value in runtime['Config']['Env']:
            if value.startswith(('VF_','MTA_')): args+=['-e',value]
        for mount in runtime['Mounts']:
            if mount['Destination']!='/app': args+=['-v',mount['Source']+':'+mount['Destination']+':ro']
        args += [runtime['Image'],'python','tools/rrr_export_probe.py','/evidence/'+target.name+'/requests.json']
        modern=json.loads(call(args,target/'modern.log'))
        (target/'modern.json').write_text(json.dumps(modern,indent=2))
        result['candidate_sources']={str(p.relative_to(ROOT)).replace('\\','/'):file_sha(p)
            for p in [*(ROOT/'mta/presentation').glob('*.py'),ROOT/'tools/rrr_export_probe.py']}
        result['dependency_image']=runtime['Image']
        observed={c['id']:c for c in modern['observations']}
        for mode,script,output in (('filters','invoke_legacy_rrr_filters.ps1','filters.json'),
                                    ('headers','invoke_legacy_rrr_export.ps1','headers.json')):
            command=['pwsh','-NoProfile','-File',str(ROOT/'parity'/script),'-InputPath',str(target/'requests.json'),
                '-OutputPath',str(target/output)]
            if mode=='headers': command+=['-Mode','headers']
            call(command,target/(mode+'.log'))
        generated=json.loads((target/'filters.json').read_text())
        filters={c['id']:c for c in generated['cases']}
        headers={c['id']:c['query'] for c in json.loads((target/'headers.json').read_text())['cases']}
        assert file_sha(CONFIG)=='4b248637cd659bdf05730964513bf555103d83521a268e93cddb24bc8c6f34da'
        permission=Path('D:/freshvcf-build/inputs/permission-input-v1.json')
        assert file_sha(permission)==PERMISSION_SHA
        assert file_sha(ROOT/'baseline/presentation-hierarchy-v1.json')=='d69c63804798b3cf31f98849341d7a61d38a37fe73c05e627aef1237e5ecfc6a'
        catalogue=json.loads(permission.read_text())
        values,provenance=terminal_inputs()
        assert provenance['modern_run']==modern['run'] and provenance['modern_output_digest']==modern['output_digest']
        pick_dir=EVIDENCE/'f3-pick-native-comparison-003'
        assert file_sha(pick_dir/'receipt.json')==PICK_RECEIPT_SHA
        pick=json.loads((pick_dir/'receipt.json').read_text())
        assert pick['retained_source']==provenance
        picks=list(iter_rows(pick_dir/'legacy-pick.jsonl.gz',pick['legacy']))
        os.environ['VFTEST_PROFILE']='fresh'
        oracle=[];checks=[]
        with exclusive_replay():
            with connection('VFTEST_BPR') as db:
                temp_rows(db,'#Pick','dbo.vf_PickListReport',picks)
                closing=values['closing']
                temp_rows(db,'#Standard','VFTEST_Importer.dbo.SKULocStandardAttributes',closing['dbm']['SKULocStandardAttributes'])
                for name,table in (('#Sku','SkuAttributeData'),('#Loc','LocationAttributeData'),('#Pair','SkuLocAttributeData')):
                    temp_rows(db,name,'dbo.'+table,closing['importer'][table])
                supplement_temp_hierarchy(db,catalogue)
                db.execute('SELECT TOP 0 * INTO #Config FROM dbo.ui_ReportConfigurations; '
                    'SELECT TOP 0 * INTO #Layouts FROM dbo.Userwise_UiReportConfiguration; '
                    'SELECT TOP 0 * INTO #Dates FROM VFTEST_BTR.dbo.BufferTrendDates')
                lines=[line.strip().replace('[dbo].[ui_ReportConfigurations]','#Config')
                    for line in CONFIG.read_text(encoding='utf-8-sig').splitlines()
                    if line.startswith('INSERT') and "VALUES (N'RationRequirementReport'," in line]
                assert len(lines)==118
                db.execute('\n'.join(lines))
                for case in cases:
                    db.execute('DROP TABLE IF EXISTS #ProductPermissions; DROP TABLE IF EXISTS #LocationPermissions; DELETE FROM #Layouts')
                    if case['layout']:
                        db.execute('INSERT INTO #Layouts (username,reportname,state) VALUES (?,?,?)','rrr-export-proof','RRR',case['layout'])
                    cte=auth_ctes(db,catalogue,case['payload']); f=filters[case['id']]
                    query=cte+selected_sql(f['sql_filter'],f['sql_join_filter'])+' ORDER BY DispatchColorSequence, DispatchPen DESC, WhCode, SKUCode'
                    cursor=db.execute(query);fields=[c[0] for c in cursor.description]
                    rows=[dict(zip(fields,row)) for row in cursor.fetchall()]
                    header_query=headers[case['id']].replace('VFTEST_BINDING.dbo.[Userwise_UiReportConfiguration]','#Layouts').replace('VFTEST_BINDING.dbo.ui_ReportConfigurations','#Config').replace('VFTEST_BINDING.dbo.BufferTrendDates','#Dates')
                    cursor=db.execute(header_query)
                    while cursor.description is None:
                        if not cursor.nextset(): raise ValueError('No canonical header result')
                    mapping=[(r[0] or '',r[1],r[2]) for r in cursor.fetchall()]
                    ordered=sorted(mapping,key=lambda r:r[2])
                    effective=[(h,c) for h,c,_ in ordered if c and c.strip() and c in fields]
                    expected_rows=[{k:typed(v) for k,v in row.items()} for row in rows]
                    raw_equal=expected_rows==observed[case['id']]['rows']
                    check=dict(id=case['id'],rows=len(rows),raw_typed_equal=raw_equal,
                        headers_equal=[list(h) for h in effective]==observed[case['id']]['headers'],headers=effective)
                    if not raw_equal:
                        check['raw_differences']=[(i,k,v,observed[case['id']]['rows'][i].get(k))
                            for i,row in enumerate(expected_rows) for k,v in row.items()
                            if i<len(observed[case['id']]['rows']) and v!=observed[case['id']]['rows'][i].get(k)][:20]
                    checks.append(check)
                    oracle.append(dict(id=case['id'],records=[[typed(h) for h,_ in effective]]+
                        [[typed(row[c]) for _,c in effective] for row in rows]))
                    (target/(case['id']+'-query.sql')).write_text(query+';\n'+header_query)
        (target/'oracle-cells.json').write_text(json.dumps(dict(cases=oracle),indent=2))
        call(['pwsh','-NoProfile','-File',str(ROOT/'parity/invoke_legacy_rrr_export.ps1'),
            '-InputPath',str(target/'oracle-cells.json'),'-OutputPath',str(target/'legacy-csv.json'),'-Mode','csv'],target/'csv.log')
        legacy=json.loads((target/'legacy-csv.json').read_text())
        assert legacy['csvhelper_sha256']=='20101c398654a14bfd42bd78d7281f43197d19b7b3cf41c7aae93f1eaba65a61'
        for c in legacy['cases']:
            raw=base64.b64decode(c['base64']); actual=base64.b64decode(observed[c['id']]['base64'])
            (target/(c['id']+'-legacy.csv')).write_bytes(raw)
            (target/(c['id']+'-modern.csv')).write_bytes(actual)
            item=next(i for i in checks if i['id']==c['id'])
            item.update(csv_bytes_equal=raw==actual,legacy_sha256=hashlib.sha256(raw).hexdigest(),modern_sha256=hashlib.sha256(actual).hexdigest())
        result.update(checks=checks,retained_source=provenance,source_dll_sha256=generated['assembly_sha256'],
            csvhelper_sha256=legacy['csvhelper_sha256'],modern_readback_sha256=file_sha(target/'modern.json'))
        assert all(c['raw_typed_equal'] and c['headers_equal'] and c['csv_bytes_equal'] for c in checks),'Export mismatch; inspect preserved checks'
        result['status']='PASS_RETAINED_EXPORT_SQL_HEADERS_TYPED_ROWS_AND_CSV_BYTES'
    except Exception as exc:
        result['error']=repr(exc)
        raise
    finally:
        (target/'receipt.json').write_text(json.dumps(result,indent=2))
        print(json.dumps(dict(status=result['status'],receipt=str(target/'receipt.json'))))


if __name__=='__main__': main()
