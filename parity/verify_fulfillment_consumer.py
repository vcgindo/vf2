"""Canonical Fulfilment producer and deployed grid over retained OWN facts."""
import argparse
import gzip
import json
import os
from pathlib import Path
import re
from mta.serialization import storage
from parity.legacy_isolation import connection,exclusive_replay
from parity.output_archive import file_sha
from parity.retained_consumer_input import terminal_inputs
from parity.temporal import differences
from parity.verify_rrr_consumer import temp_rows
from parity.verify_excess_readmodel import PLAN,PLAN_SHA,literals

SOURCE=Path('F:/VFlow_Local/local-runtime/mta-engine/Scripts/BPR/CollectOrderFulfillmentData.sql')
SOURCE_SHA='b6ae768bd632c831050453f7702a2016bf8db11bc69a2a05088f31c030d3d3b1'


def temp_orders(db,rows):
    # A plain SQL SELECT INTO can propagate OrderKey's IDENTITY property even
    # with the constant CROSS JOIN used by other schema-only temp copies. A
    # typed INT expression removes only that generator, not the supplied key.
    fields=('OrderKey','CustomerOrderId','PartId','IsSpike','IsElephant','OriginalQty','Qty','SKUCode',
            'WhCode','CustomerExpectedDate','FirstServicingWhCode','DueDate','IntroDate')
    if any(set(r)!=set(fields) for r in rows): raise ValueError('Retained order schema differs')
    columns=','.join('CONVERT(int,OrderKey+0) AS OrderKey' if f=='OrderKey' else '['+f+']' for f in fields)
    db.execute('SELECT TOP 0 '+columns+' INTO #Orders FROM dbo.SpikeOrderData')
    if rows:
        db.cursor().executemany('INSERT INTO #Orders VALUES ('+','.join('?' for _ in fields)+')',
                               [tuple(r[f] for f in fields) for r in rows])


def selected_queries():
    if file_sha(SOURCE)!=SOURCE_SHA or file_sha(PLAN)!=PLAN_SHA:
        raise ValueError('Selected canonical producer/consumer source changed')
    producer=SOURCE.read_text().split('\n\tTruncate table OrderFulfillmentDataDetails',1)[1].split('END TRY',1)[0]
    for old,new in (('OrderFulfillmentDataDetails','#Details'),('OrderFulfillmentData','#Summary'),
                    ('[$(ImporterDatabase)].dbo.SKULocStandardAttributes','#Standard'),
                    ('vf_RationedReqReport','#Rationed'),('SpikeOrderRouteOriginal','#Routes'),('SpikeOrderData','#Orders')):
        producer=producer.replace(old,new)
    producer='DECLARE @today date=?;\n'+producer
    source=PLAN.read_text()
    method=source.split('public responseMessage OrderFulfillment(',1)[1].split('public void GetUIConfigAttributeForCustom(',1)[0]
    grid=literals(method.split('string text = string.Concat(new string[6]',1)[1].split('if (sqlFilter !=',1)[0])
    grid+=')a order by RN for json path,include_null_values) a'
    count=source.split('else if (masterRoot.category.ToLower() == "orderfulfillment")',1)[1]
    count=literals(count.split('text = text2 +',1)[1].split('if (sqlFilter4 !=',1)[0])
    def bind(query):
        for old,new in (('[OrderFulfillmentDataDetails]','#Details'),('[OrderFulfillmentData]','#Summary'),
                        ('SKUDescriptionTbl','#SkuDesc'),('SiteDescriptionTbl','#LocDesc'),
                        ('SkuLocAttributeData','#Pair'),('SkuAttributeData','#Sku'),('LocationAttributeData','#Loc')):
            query=query.replace(old,new)
        return query
    config=[dict(header=h,colCode=c,colPosition=int(p)) for h,c,p in re.findall(
        r'header = "([^"]+)",\s*colCode = "([^"]+)",\s*colPosition = (\d+)',method)]
    return producer,bind(grid),bind(count),config


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('modern',type=Path); parser.add_argument('evidence',type=Path)
    args=parser.parse_args()
    if args.evidence.exists(): raise ValueError('Preserve earlier evidence; select a new directory')
    args.evidence.mkdir(parents=True)
    result=dict(status='FAILED',engine_replays=0,persistent_database_writes=False)
    try:
        receipt=json.loads((args.modern/'receipt.json').read_text())
        if receipt['status']!='PERSISTED_READBACK_PASS_COMPARISON_REQUIRED' or receipt['producer_sha256']!=SOURCE_SHA:
            raise ValueError('Modern Fulfilment publication identity differs')
        root=Path(__file__).resolve().parents[1]
        if any(file_sha(root/name)!=sha for name,sha in receipt['sources'].items()):
            raise ValueError('Modern source changed')
        if file_sha(args.modern/receipt['file'])!=receipt['sha256']: raise ValueError('Modern export changed')
        with gzip.open(args.modern/receipt['file'],'rt') as stream: actual=json.load(stream)
        if not actual['summary'] or not actual['details'] or not actual['grid']:
            raise ValueError('This sizeable selected proof requires positive summary, details and grid')
        legacy,provenance=terminal_inputs(include_routes=True)
        if (receipt['run']['id']!=provenance['modern_run'] or receipt['run']['output_digest']!=provenance['modern_output_digest'] or
            receipt['business_date']!=provenance['date']): raise ValueError('Modern/legacy pairing changed')
        producer,grid,count,config=selected_queries()
        result.update(legacy_source=provenance,modern_receipt_sha256=file_sha(args.modern/'receipt.json'),
                      producer_sha256=SOURCE_SHA,consumer_sha256=PLAN_SHA,verifier_sha256=file_sha(Path(__file__)))
        expected={}
        cte=';WITH cte_SKUs AS (SELECT DISTINCT SKUCode FROM #Sku),cte_WhCodes AS (SELECT DISTINCT WHCode FROM #Loc) '
        os.environ['VFTEST_PROFILE']='fresh'
        with exclusive_replay():
            with connection('VFTEST_BPR') as db:
                temp_orders(db,legacy['closing']['orders']['SpikeOrderData'])
                temp_rows(db,'#Rationed','dbo.vf_RationedReqReport',legacy['late']['vf_RationedReqReport'])
                temp_rows(db,'#Standard','VFTEST_Importer.dbo.SKULocStandardAttributes',legacy['closing']['dbm']['SKULocStandardAttributes'])
                temp_rows(db,'#Summary','dbo.OrderFulfillmentData',[])
                temp_rows(db,'#Details','dbo.OrderFulfillmentDataDetails',[])
                # The accepted route capture is the original table joined to
                # its order. Recover only the required four columns; reject
                # nonunique IDs rather than inventing a part allocation.
                db.execute('CREATE TABLE #CapturedRoutes (OrderId nvarchar(50),OrderKey int NULL,SrcWhCode nvarchar(50),DestWhCode nvarchar(50),DueDate date)')
                if legacy['routes']:
                    db.cursor().executemany('INSERT INTO #CapturedRoutes VALUES (?,?,?,?,?)',[
                        (r['order_id'],r.get('order_key'),r['location_code'],r['child_location_code'],r['due_date']) for r in legacy['routes']])
                ambiguous=db.execute('SELECT R.OrderId FROM #CapturedRoutes R WHERE (SELECT COUNT(*) FROM #Orders O WHERE O.CustomerOrderId=R.OrderId AND (R.OrderKey IS NULL OR O.OrderKey=R.OrderKey))<>1').fetchall()
                if ambiguous: raise ValueError('Legacy captured route has ambiguous OrderKey mapping')
                db.execute('SELECT O.OrderKey,R.SrcWhCode,R.DestWhCode,R.DueDate INTO #Routes FROM #CapturedRoutes R JOIN #Orders O ON O.CustomerOrderId=R.OrderId AND (R.OrderKey IS NULL OR O.OrderKey=R.OrderKey)')
                db.execute(producer,provenance['date'])
                for key,table in (('summary','#Summary'),('details','#Details')):
                    cursor=db.execute('SELECT * FROM '+table)
                    fields=[c[0] for c in cursor.description]
                    expected[key]=storage([dict(zip(fields,r)) for r in cursor.fetchall()])
                dynamic=db.execute("SELECT Col_Code FROM ui_ReportConfigurations WHERE reportname='adminbpr' AND Visible=1 AND (Col_Code LIKE 'SKUAttr%' OR Col_Code LIKE 'LocAttr%' OR Col_Code LIKE 'SKULocAttr%')").fetchall()
                if dynamic: raise ValueError('Selected dynamic attributes require explicit mapping')
                for name,table in (('#Sku','SkuAttributeData'),('#Loc','LocationAttributeData'),('#Pair','SkuLocAttributeData'),
                                   ('#SkuDesc','SKUDescriptionTbl'),('#LocDesc','SiteDescriptionTbl')):
                    temp_rows(db,name,'dbo.'+table,legacy['closing']['importer'][table])
                expected['grid']=json.loads(db.execute(cte+grid).fetchone()[0])
                expected['count']=db.execute(cte+count).fetchone()[0]
                expected['uiConfig']=config
        delta=differences(expected,actual,'/fulfillment-producer-and-unscoped-grid')
        order_match=[(r['g'],r['sc'],r['wc']) for r in expected['grid']]==[(r['g'],r['sc'],r['wc']) for r in actual['grid']]
        with gzip.open(args.evidence/'legacy-fulfillment.json.gz','wt') as stream: json.dump(expected,stream)
        result.update(status='PASS_PRODUCER_AND_UNSCOPED_FULFILLMENT_GRID' if not delta and order_match else 'FAIL',
            summary_rows=len(expected['summary']),detail_rows=len(expected['details']),grid_rows=len(expected['grid']),
            summary_fields=len(expected['summary'][0]),detail_fields=len(expected['details'][0]),grid_fields=len(expected['grid'][0]),
            differences=delta,declared_order_matches=order_match,legacy_source=provenance,
            modern_receipt_sha256=file_sha(args.modern/'receipt.json'),producer_sha256=SOURCE_SHA,consumer_sha256=PLAN_SHA,
            legacy_readback_sha256=file_sha(args.evidence/'legacy-fulfillment.json.gz'),
            queries=dict(producer=producer,grid=cte+grid,count=cte+count),selected_dynamic_columns=[],
            qualification='Full retained current-day producer/grid only, not charts, authenticated scopes/filters or browser acceptance')
    except Exception as exc:
        result['error']=dict(type=type(exc).__name__,message=str(exc)); raise
    finally:
        (args.evidence/'receipt.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({k:result[k] for k in ('status','summary_rows','detail_rows','grid_rows','summary_fields','detail_fields','grid_fields','declared_order_matches')}))
    if result['status']=='FAIL': raise SystemExit(1)


if __name__=='__main__': main()
