"""Independent retained Fulfilment normal/custom consumer proof, no calculation replay."""
from copy import deepcopy
import gzip
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import pyodbc

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from parity.legacy_isolation import connection,exclusive_replay
from parity.output_archive import file_sha
from parity.temporal import differences
from parity.verify_fulfillment_consumer import selected_queries
from parity.verify_fulfillment_charts import PRODUCER,PRODUCER_SHA
from parity.verify_excess_readmodel import PLAN,PLAN_SHA,literals
from parity.verify_rrr_consumer import auth_ctes,supplement_temp_hierarchy,temp_rows,PERMISSION_SHA
from parity.verify_rrr_export import call
from tools.excess_receipt import roster as excess_roster


def roster():
    cases=excess_roster()
    for case in cases:
        case['payload']['category']='orderFulfillment'
    base=cases[0]['payload']
    for i,label in enumerate(('Gap < 33%','33% <= Gap <= 67%','Gap > 67%')):
        for kind,route in (('grid','GetPlanningDataGrid'),('count','GetPlanningDataGridCount')):
            payload=deepcopy(base)
            payload['filters']={'coverageFilter':{'filters':[dict(attributeName='coverage',value=label)]}}
            cases.append(dict(id=f'coverage-{i}-{kind}',kind=kind,route=route,payload=payload))
    for name,kind,route in (('custom-outside','custom','GetPlanningDataCustom'),('grid-outside','grid','GetPlanningDataGrid')):
        payload=deepcopy(base);payload['paginationParameter']=dict(pageNumber=9999,recordsPerPage=5000)
        cases.append(dict(id=name,kind=kind,route=route,payload=payload))
    for kind,route in (('grid','GetPlanningDataGrid'),('count','GetPlanningDataGridCount'),('custom','GetPlanningDataCustom')):
        payload=deepcopy(base);payload['product_permissions']=[]
        cases.append(dict(id='empty-scope-'+kind,kind=kind,route=route,payload=payload))
    return cases


def custom_query():
    assert file_sha(PLAN)==PLAN_SHA
    method=PLAN.read_text().split('public responseMessage GetCustomGridData(',1)[1]
    branch=method.split('if (category == "orderFulfillment")',1)[1].split('text = ((sCIHModels.paginationParameter',1)[0]
    query=literals(branch)+' for json path) data'
    for old,new in (('.dbo.NMSAllItems','#NMS'),('OrderFulfillmentData','#Summary'),('SiteDescriptionTbl','#LocDesc')):
        query=query.replace(old,new)
    config=[dict(header=h,colCode=c,colPosition=int(p)) for h,c,p in re.findall(
        r'header = "([^"]+)",\s*colCode = "([^"]+)",\s*colPosition = (\d+)',method)]
    assert len(config)==46
    return query,config


def source_failure(name,message):
    name,kind=name.removeprefix('filter-').rsplit('-',1)
    columns={'missing-category':'category','category-code':'category','missing-availability':'availability',
        'missing-color-count':'redCount','red-positive-count':'redCount','invalid-hierarchy-column':'sl9',
        'green-count-zero':'greenCount','black-red-positive-count':'BlackCount'}
    if name in ('missing-category','category-code'):
        code,detail='4104','"b.category" could not be bound'
    elif name in columns:
        code,detail='207',"Invalid column name '"+columns[name]+"'"
    elif name in ('missing-color-age','black-red-age','green-age'):
        code,detail='4104','"btd.D90" could not be bound'
    elif name=='invalid-operator':
        code,detail='102',"Incorrect syntax near ')'"
    elif name=='black-red-invalid-multi-column':
        code,detail=('102',"Incorrect syntax near '('") if kind=='grid' else ('156',"Incorrect syntax near the keyword 'NULLIF'")
    else:
        raise AssertionError('Unexpected source failure: '+name+' '+message)
    assert '('+code+')' in message and detail in message,(name,message)
    return dict(code=code,detail=detail)


def main():
    target=Path(sys.argv[1]).resolve()
    assert target.parent==Path('D:/freshvcf-build/evidence').resolve()
    target.mkdir(exist_ok=False)
    result=dict(status='FAILED',engine_replays=0,persistent_writes=False,serving_changes=False,checks=[])
    try:
        cases=roster()
        (target/'requests.json').write_text(json.dumps(dict(cases=cases),indent=2))
        runtime=json.loads(subprocess.check_output(['docker','inspect','freshvcf-preview-mta-1'],text=True))[0]
        command=['docker','run','--rm','--name','freshvcf-stage2-fulfillment','--network','freshvcf-test_default',
            '--memory','4g','--memory-swap','4g','--cpus','2','-v','F:/freshvcf:/app:ro',
            '-v','D:/freshvcf-build/evidence:/evidence:ro','-e','PYTHONPATH=/app']
        for value in runtime['Config']['Env']:
            if value.startswith(('VF_','MTA_')):command+=['-e',value]
        for mount in runtime['Mounts']:
            if mount['Destination']!='/app':command+=['-v',mount['Source']+':'+mount['Destination']+':ro']
        # The existing read-only consumer probe is route-neutral and forbids full publication().
        command += [runtime['Image'],'python','tools/excess_probe.py','/evidence/'+target.name+'/requests.json']
        if len(sys.argv)>2:
            parent=Path(sys.argv[2]).resolve()
            receipt=json.loads((parent/'receipt.json').read_text())
            assert file_sha(parent/'modern.log')==receipt['files']['modern.log']
            assert (parent/'requests.json').read_bytes()==(target/'requests.json').read_bytes()
            assert all(file_sha(ROOT/name)==sha for name,sha in receipt['sources'].items() if name!='tools/fulfillment_receipt.py')
            (target/'modern.log').write_bytes((parent/'modern.log').read_bytes())
            modern=json.loads((parent/'modern.log').read_text())
            result['modern_reused_from']=dict(path=str(parent),receipt_sha256=file_sha(parent/'receipt.json'))
        else:
            modern=json.loads(call(command,target/'modern.log'))
        observed={row['id']:row for row in modern['observations']}
        assert all(row['status'] in (200,503) for row in observed.values()),[(n,r) for n,r in observed.items() if r['status'] not in (200,503)]
        (target/'filter-requests.json').write_text(json.dumps(dict(cases=[c for c in cases if c['kind']!='custom'])))
        filters={}
        for kind,report in (('grid','FulfillmentGrid'),('count','FulfillmentCount')):
            call(['pwsh','-NoProfile','-File',str(ROOT/'parity/invoke_legacy_rrr_filters.ps1'),
                '-InputPath',str(target/'filter-requests.json'),'-OutputPath',str(target/(kind+'-filters.json')),
                '-Report',report],target/(kind+'-filters.log'))
            filters[kind]={r['id']:r for r in json.loads((target/(kind+'-filters.json')).read_text())['cases']}
        permission=Path('D:/freshvcf-build/inputs/permission-input-v1.json')
        assert file_sha(permission)==PERMISSION_SHA
        catalogue=json.loads(permission.read_text())
        handoff=Path('D:/freshvcf-build/evidence/f3-stage2-excess-004')
        handoff_receipt=json.loads((handoff/'receipt.json').read_text())
        assert file_sha(handoff/'legacy-input-handoff.json.gz')==handoff_receipt['files']['legacy-input-handoff.json.gz']
        with gzip.open(handoff/'legacy-input-handoff.json.gz','rt',encoding='utf-8') as stream:retained=json.load(stream)
        legacy,provenance=retained['values'],retained['provenance']
        assert modern['run']==provenance['modern_run'] and modern['output_digest']==provenance['modern_output_digest']
        assert file_sha(PRODUCER/'receipt.json')==PRODUCER_SHA
        producer=json.loads((PRODUCER/'receipt.json').read_text())
        assert producer['legacy_source']==provenance
        assert file_sha(PRODUCER/'legacy-fulfillment.json.gz')==producer['legacy_readback_sha256']
        with gzip.open(PRODUCER/'legacy-fulfillment.json.gz','rt') as stream:reports=json.load(stream)
        _,normal_sql,count_sql,normal_config=selected_queries()
        custom_sql,custom_config=custom_query()
        expected={}
        os.environ['VFTEST_PROFILE']='fresh'
        print('Modern observations complete; independent SQL consumer comparisons starting',flush=True)
        with exclusive_replay(),connection('VFTEST_BPR') as db:
            dynamic=db.execute("SELECT Col_Code FROM ui_ReportConfigurations WHERE reportname='adminbpr' AND Visible=1 AND (Col_Code LIKE 'SKUAttr%' OR Col_Code LIKE 'LocAttr%' OR Col_Code LIKE 'SKULocAttr%')").fetchall()
            assert not dynamic
            for name,table,key in (('#Summary','OrderFulfillmentData','summary'),('#Details','OrderFulfillmentDataDetails','details')):
                temp_rows(db,name,'dbo.'+table,reports[key])
            for name,table in (('#Sku','SkuAttributeData'),('#Loc','LocationAttributeData'),('#Pair','SkuLocAttributeData'),('#SkuDesc','SKUDescriptionTbl'),('#LocDesc','SiteDescriptionTbl')):
                temp_rows(db,name,'dbo.'+table,legacy['closing']['importer'][table])
            temp_rows(db,'#NMS','VFTEST_Importer.dbo.NMSAllItems',legacy['closing']['consumer_context']['NMSAllItems'])
            result['native_nms_rows']=len(legacy['closing']['consumer_context']['NMSAllItems'])
            supplement_temp_hierarchy(db,catalogue)
            for case in cases:
                db.execute('DROP TABLE IF EXISTS #ProductPermissions; DROP TABLE IF EXISTS #LocationPermissions')
                payload,kind=case['payload'],case['kind']
                query=count_sql if kind=='count' else custom_sql if kind=='custom' else normal_sql
                if kind!='custom':
                    f=filters[kind][case['id']]
                    query=query.replace('#Summary a ','#Summary a '+f['sql_join_filter'].replace('LocationAttributeData','#Loc')+' ')
                    if f['sql_filter']:
                        query=query.replace(')a order by RN',' where '+f['sql_filter']+')a order by RN') if kind=='grid' else query+' where '+f['sql_filter']
                paging=payload.get('paginationParameter')
                bounds=''
                if paging is not None:
                    page,size=(paging[k] for k in ('pageNumber','recordsPerPage'))
                    bounds=f' where RN between ({page}-1)*{size}+1 and ({page}*{size}) '
                if kind=='grid':query=query.replace(')a order by RN',')a '+bounds+' order by RN')
                if kind=='custom':query=query.replace(' for json path) data',bounds+' for json path) data')
                if case['id'].startswith('empty-scope-'):
                    # Planning passes quoted empty IDs. GenericFunction's failed
                    # expansion wraps them again, yielding SQL literal ''''.
                    # Retain its varchar-to-int failure; modern NULL-denial is
                    # a safety boundary, not legacy result parity.
                    auth=auth_ctes(db,catalogue,{**payload,'product_permissions':[71001]})
                    assert 'WHERE t1.id IN (71001)' in auth
                    auth=auth.replace('WHERE t1.id IN (71001)',"WHERE t1.id IN (SELECT value FROM string_split('''', ','))")
                else:
                    auth=auth_ctes(db,catalogue,payload)
                query=auth+query
                (target/(case['id']+'.sql')).write_text(query)
                try:value=db.execute(query).fetchone()[0]
                except pyodbc.Error as exc:
                    if case['id'].startswith('empty-scope-'):
                        assert '(245)' in str(exc) and "varchar value ''' to data type int" in str(exc)
                        actual=observed[case['id']]['body']['data']
                        assert observed[case['id']]['status']==200 and (actual==0 if kind=='count' else actual['data']==[])
                        result['checks'].append(dict(id=case['id'],status='SCOPE_DENIAL_NOT_PARITY',legacy_error=str(exc),modern_denial=actual))
                        continue
                    failure=source_failure(case['id'],str(exc))
                    assert observed[case['id']]['status']==503,(case['id'],observed[case['id']])
                    result['checks'].append(dict(id=case['id'],status='LEGACY_FLAW_NOT_PARITY',legacy_error=str(exc),exact_failure=failure,modern_error=observed[case['id']]['body']))
                    continue
                if kind!='count':value=dict(data=json.loads(value) if value else [],uiConfig=custom_config if kind=='custom' else normal_config)
                expected[case['id']]=value
                if kind=='custom' and value['data']:
                    assert result['native_nms_rows']==0
                    assert all('sc' not in r and 'wc' not in r for r in value['data'])
                    assert len({json.dumps({k:v for k,v in r.items() if k!='RN'},sort_keys=True) for r in value['data']})>1
                    assert observed[case['id']]['status']==503 and 'LEG-FULFILLMENT-CUSTOM-UNORDERED-NMS' in str(observed[case['id']]['body'])
                    result['checks'].append(dict(id=case['id'],status='LEGACY_FLAW_NOT_PARITY',rows=len(value['data']),
                        source_defect='Distinct payloads assigned RN from identical NULL NMS keys; sc/wc omitted; exact rows retained, no claimed parity',modern_error=observed[case['id']]['body']))
                    continue
                actual=observed[case['id']]['body'].get('data')
                delta=differences(value,actual,'/'+case['id'])
                result['checks'].append(dict(id=case['id'],status='PASS' if observed[case['id']]['status']==200 and value==actual and not delta else 'FAIL',
                    complete_ordered_body_equal=value==actual,differences=delta,rows=value if kind=='count' else len(value['data']),
                    query_count=observed[case['id']]['query_count'],modern_seconds=observed[case['id']]['seconds']))
        (target/'legacy-responses.json').write_text(json.dumps(expected,indent=2))
        failed=[r for r in result['checks'] if r['status']=='FAIL']
        assert not failed,failed
        result.update(status='PASS_SELECTED_FULFILLMENT_CONSUMERS_WITH_DECLARED_FLAWS_NOT_JOURNEY_ACCEPTANCE',provenance=provenance,
            producer_receipt_sha256=PRODUCER_SHA,legacy_handoff_receipt_sha256=file_sha(handoff/'receipt.json'),consumer_sha256=PLAN_SHA,
            qualification='Complete retained SQL body/order/config and actual DLL filter generator; custom missing identity/RN flaw explicitly unavailable, no parity claim. Private bounded read-only PostgreSQL worker, not serving/browser or matched performance.')
    except Exception as exc:
        result['error']=repr(exc)
        raise
    finally:
        result['sources']={name:file_sha(ROOT/name) for name in ('mta/presentation/fulfillment_read.py','mta/presentation/fulfillment_filters.py',
            'mta/presentation/fulfillment_views.py','mta/presentation/fulfillment_grid.py','mta/presentation/views.py',
            'parity/invoke_legacy_rrr_filters.ps1','tools/excess_probe.py','tools/fulfillment_receipt.py')}
        result['files']={p.name:file_sha(p) for p in target.iterdir() if p.is_file() and p.name!='receipt.json'}
        (target/'receipt.json').write_text(json.dumps(result,indent=2))
        print(json.dumps(dict(status=result['status'],error=result.get('error'))),flush=True)


if __name__=='__main__':main()
