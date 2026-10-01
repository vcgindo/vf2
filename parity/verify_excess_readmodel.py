"""Deployed Excess grid/count/chart queries over OWN retained legacy facts.

Only temporary SQL tables. No calculation replay, input generation or production
publication. The unscoped projection check cannot certify authorization.
"""
import argparse
import gzip
import json
import os
from pathlib import Path
import re
from parity.legacy_isolation import connection,exclusive_replay
from parity.output_archive import file_sha,iter_rows
from parity.retained_consumer_input import terminal_inputs
from parity.temporal import differences
from parity.verify_rrr_consumer import temp_rows

SOURCE_ROOT=Path('F:/vflow_integrated/.local-stage7/deployed-planning')
PLAN=SOURCE_ROOT/'VectorFlowAPIs.VectorFlow.Processors.Replenishment.SCIH.PlanningProcessor.decompiled.cs'
CHART=SOURCE_ROOT/'VectorFlowAPIs.VectorFlow.Processors.Replenishment.InsightsAndTrends.ExcessInventoryProcessor.decompiled.cs'
PLAN_SHA='bf716c4f84e43920b5f2ab302e3d3c78ec685f5d714471c53047d377537d3486'
CHART_SHA='5eb90eb1746de5c87d00ee7ee16e31d2d29534183086477c1b0a073cc7321603'
EXCESS=Path('D:/freshvcf-build/evidence/f3-excess-comparison-001')
EXCESS_SHA='41498dec00989c834efe90b496e312dd9d92f52d5b8d8d0fe934cf60365894f4'
SECTIONS=(('location_count','topTenLocationsWithExcessInventorySkuCount','WHDescription','SKUCounts','ll'),
          ('location_value','topTenLocationsWithExcessInventoryValue','WHDescription','SumOfAmount','ll'),
          ('sku_count','topTenProductsWithExcessInventoryNumberOfLocations','SKUDescription','WHCount','sl'),
          ('sku_value','topTenProductsWithExcessInventoryInValue','SKUDescription','SumAmount','sl'))


def literals(source):
    return ''.join(json.loads(s) for s in re.findall(r'"(?:[^"\\]|\\.)*"',source))


def bindings(query):
    for old,new in (('.[dbo].[ExcessInventoryDetails]','#Excess '),('ExcessInventoryDetails','#Excess'),
                    ('LastBatchRunTbl','#LastDate'),('SKUDescriptionTbl','#SkuDesc'),('SiteDescriptionTbl','#LocDesc'),
                    ('SkuLocAttributeData','#Pair'),('SkuAttributeData','#Sku'),('LocationAttributeData','#Loc')):
        query=query.replace(old,new)
    return query


def selected_queries():
    if file_sha(PLAN)!=PLAN_SHA or file_sha(CHART)!=CHART_SHA:
        raise ValueError('Selected deployed consumer bytes changed')
    source=PLAN.read_text()
    method=source.split('public responseMessage ReviewExcessInventory(',1)[1].split('public responseMessage OrderFulfillment(',1)[0]
    grid=bindings(literals(method.split('string text = string.Concat(new string[6]',1)[1].split('if (sqlFilter !=',1)[0]))
    grid+=')a order by RN for json path,include_null_values) a'
    count=source.split('else if (masterRoot.category.ToLower() == "excessinventory")',1)[1]
    count=bindings(literals(count.split('text = text2 +',1)[1].split('if (sqlFilter3 !=',1)[0]))
    text=CHART.read_text().split('strSqlAuth = GenericFunction.getAuthQueryForReports',1)[1].split('ErrorLog.Logger(',1)[0]
    chart=''.join(literals(line) for line in text.splitlines() if line.strip().startswith('strSql '))
    queries=[bindings(query.strip()) for query in chart.split(';') if query.strip()]
    if len(queries)!=4 or not grid.lstrip().startswith('select(Select *') or not count.startswith('select count(1)'):
        raise ValueError('Unexpected deployed SQL extraction')
    config=[dict(header=h,colCode=c,colPosition=int(p)) for h,c,p in re.findall(
        r'header = "([^"]+)",\s*colCode = "([^"]+)",\s*colPosition = (\d+)',method)]
    return grid,count,queries,config


def expected_response(queries):
    """Independent transcription of GetResponse's four string dictionaries."""
    result={}
    for section,key,description,count,prefix in SECTIONS:
        config=[dict(header=f'{prefix.upper()}{i}',colCode=f'{prefix}{i}') for i in range(1,6)]
        rows=[]
        for row in queries[section]:
            values={description:row['Details'],count:row['counts'],
                    **{f'{prefix}{i}':row[f'{prefix}{i}'] for i in range(1,6)}}
            rows.append({k:'' if v is None else str(v) for k,v in values.items()})
        result[key]=dict(data=rows,uiconfig=config)
    return {'data':result}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('modern',type=Path)
    parser.add_argument('evidence',type=Path)
    args=parser.parse_args()
    if args.evidence.exists():
        raise ValueError('Preserve earlier receipt; use a new evidence directory')
    args.evidence.mkdir(parents=True)
    result=dict(status='FAILED',engine_replays=0,persistent_database_writes=False)
    try:
        receipt=json.loads((args.modern/'receipt.json').read_text())
        if receipt['status']!='READBACK_EXPORTED_COMPARISON_REQUIRED' or receipt['boundary']!='UNSCOPED_EXCESS_READ_MODEL':
            raise ValueError('Wrong selected read-model export')
        root=Path(__file__).resolve().parents[1]
        for name,sha in receipt['sources'].items():
            if file_sha(root/name)!=sha:
                raise ValueError('Modern source changed: '+name)
        if file_sha(args.modern/receipt['file'])!=receipt['sha256']:
            raise ValueError('Modern exported data changed')
        with gzip.open(args.modern/receipt['file'],'rt',encoding='utf-8') as stream:
            actual=json.load(stream)
        if not actual['grid'] or any(not rows for rows in actual['queries'].values()):
            raise ValueError('This unscoped full-estate proof requires nonempty grid and all charts')
        values,provenance=terminal_inputs()
        if (receipt['run']['id']!=provenance['modern_run'] or
            receipt['run']['output_digest']!=provenance['modern_output_digest'] or
            receipt['business_date']!=provenance['date']):
            raise ValueError('Legacy/modern pairing changed')
        if file_sha(EXCESS/'receipt.json')!=EXCESS_SHA:
            raise ValueError('Accepted canonical Excess projection receipt changed')
        excess=json.loads((EXCESS/'receipt.json').read_text())
        if excess['legacy_source']!=provenance or excess['status']!='PASS_CURRENT_DAY_EXCESS_REPORT':
            raise ValueError('Legacy Excess producer handoff differs')
        rows=list(iter_rows(EXCESS/'legacy-excess.jsonl.gz',excess['legacy_rows']))
        grid_sql,count_sql,charts_sql,config=selected_queries()
        cte=';WITH cte_SKUs AS (SELECT DISTINCT SKUCode FROM #Sku), cte_WhCodes AS (SELECT DISTINCT WHCode FROM #Loc) '
        expected,query_evidence={},{}
        os.environ['VFTEST_PROFILE']='fresh'
        with exclusive_replay():
            with connection('VFTEST_BPR') as db:
                # Selected deployed dynamic-column configuration is an explicit
                # precondition; never silently omit enabled custom columns.
                dynamic=db.execute("SELECT Col_Code FROM ui_ReportConfigurations WHERE reportname='adminbpr' AND Visible=1 AND (Col_Code LIKE 'SKUAttr%' OR Col_Code LIKE 'LocAttr%' OR Col_Code LIKE 'SKULocAttr%')").fetchall()
                if dynamic:
                    raise ValueError('Selected dynamic attributes need explicit consumer mapping: '+str(dynamic))
                temp_rows(db,'#Excess','dbo.ExcessInventoryDetails',rows)
                importer=values['closing']['importer']
                for name,table in (('#Sku','SkuAttributeData'),('#Loc','LocationAttributeData'),
                                   ('#Pair','SkuLocAttributeData'),('#SkuDesc','SKUDescriptionTbl'),('#LocDesc','SiteDescriptionTbl')):
                    temp_rows(db,name,'dbo.'+table,importer[table])
                temp_rows(db,'#LastDate','dbo.LastBatchRunTbl',values['late']['LastBatchRunTbl'])
                expected['grid']=json.loads(db.execute(cte+grid_sql).fetchone()[0])
                expected['count']=db.execute(cte+count_sql).fetchone()[0]
                expected['uiConfig']=config
                expected['queries']={}
                for (section,*_),query in zip(SECTIONS,charts_sql):
                    cursor=db.execute(cte+query)
                    # Identifier casing only; SQL declares WhCode whereas the
                    # already-portable read model spells its code WHCode.
                    fields=['WHCode' if col[0]=='WhCode' else col[0] for col in cursor.description]
                    expected['queries'][section]=[dict(zip(fields,row)) for row in cursor.fetchall()]
                    query_evidence[section]=cte+query
        expected['response']=expected_response(expected['queries'])
        delta=differences(expected,actual,'/unscoped-excess')
        # Validate only source-declared order, never a fabricated tied-row sort.
        order_matches={section:[r['counts'] for r in expected['queries'][section]]==
                        [r['counts'] for r in actual['queries'][section]] for section,*_ in SECTIONS}
        order_matches['grid']=[(r['wc'],r['sc']) for r in expected['grid']]==[(r['wc'],r['sc']) for r in actual['grid']]
        with gzip.open(args.evidence/'legacy-read-model.json.gz','wt',encoding='utf-8') as stream:
            json.dump(expected,stream,ensure_ascii=False)
        result.update(status='PASS_UNSCOPED_EXCESS_READ_MODEL_NOT_AUTH_ACCEPTANCE' if not delta and all(order_matches.values()) else 'FAIL',
            rows=len(expected['grid']),fields=len(expected['grid'][0]),chart_rows={k:len(v) for k,v in expected['queries'].items()},
            differences=delta,declared_order_matches=order_matches,legacy_source=provenance,
            modern_receipt_sha256=file_sha(args.modern/'receipt.json'),producer_receipt_sha256=EXCESS_SHA,
            source_hashes={str(PLAN):PLAN_SHA,str(CHART):CHART_SHA},selected_dynamic_columns=[],
            queries={'grid':cte+grid_sql,'count':cte+count_sql,**query_evidence},
            legacy_read_model_sha256=file_sha(args.evidence/'legacy-read-model.json.gz'),
            qualification='Unscoped current-day full projection, not nonempty authenticated/filter/historical or browser acceptance')
    except Exception as exc:
        result['error']=dict(type=type(exc).__name__,message=str(exc))
        raise
    finally:
        (args.evidence/'receipt.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({k:result[k] for k in ('status','rows','fields','chart_rows','declared_order_matches')}))
    if result['status']=='FAIL':
        raise SystemExit(1)


if __name__=='__main__':
    main()
