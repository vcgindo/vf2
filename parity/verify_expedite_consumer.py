"""Exact canonical Expedite report SQL and count queries on retained own facts."""
import argparse
import gzip
import json
import os
from pathlib import Path
import re
from mta.serialization import storage
from parity.legacy_isolation import connection,exclusive_replay
from parity.output_archive import file_sha,iter_rows
from parity.retained_consumer_input import terminal_inputs
from parity.temporal import differences
from parity.verify_rrr_consumer import temp_rows
from parity.verify_excess_readmodel import PLAN,PLAN_SHA,literals

SOURCE=Path('F:/VFlow_Local/local-runtime/mta-engine/Scripts/BPR/CollectDataToExpediteDispatches.sql')
SOURCE_SHA='894ba52512be0bb39ec4e97aff603ed1da572c4463d6c319b9a2ae20a54f753d'
PICK=Path('D:/freshvcf-build/evidence/f3-pick-native-comparison-003')
PICK_SHA='d06e30cc8d203d78ec7ade158ddc2402b0134e30e268217ade1be2fb84beb19a'


def selected_queries():
    if file_sha(SOURCE)!=SOURCE_SHA or file_sha(PLAN)!=PLAN_SHA: raise ValueError('Canonical source differs')
    producer='Insert into ExpediteDispatches'+SOURCE.read_text().split('Insert into ExpediteDispatches',1)[1].split('END TRY',1)[0]
    for old,new in (('[$(ImporterDatabase)].dbo.SKULocStandardAttributes','#Standard'),
            ('[$(ImporterDatabase)].dbo.MasterData','#Master'),('ExpediteDispatches','#Expedite'),
            ('vf_PickListReport','#Pick'),('vf_RationedReqReport','#Rationed')):
        producer=producer.replace(old,new)
    body=PLAN.read_text().split('else if (masterRoot.category.ToLower() == "expedite")',1)[1].split('else if (masterRoot.category.ToLower() == "excessinventory")',1)[0]
    blocks=re.findall(r'text = string.Concat\(new string\[9\]\s*\{([\s\S]+?)\}\);',body)
    predicates=re.findall(r'text \+= "( where  a.RationedQty[^"\n]+)";',body)
    if len(blocks)!=2 or len(predicates)!=2: raise ValueError('Canonical count extraction changed')
    queries={}
    for direction,column in (('parent','WhCode'),('child','ParentWhCode')):
        queries[direction]={}
        for name,block,predicate in zip(('expediteDispatches','createAvailabilityAtParent'),blocks,predicates):
            query=literals(block)+' inner Join cte_SKUs skucodes on a.SKUCode=skucodes.SKUCode '
            query+=' inner join cte_WhCodes whcodes on a.'+column+'=whcodes.WHCode '+predicate+')) '+name
            for old,new in (('.[dbo].[ExpediteDispatches]a','#Expedite a'),('.dbo.[ExpediteDispatches]a','#Expedite a'),
                ('.dbo.[SKULocStandardAttributes]','#Standard'),('SKUDescriptionTbl','#SkuDesc'),('SiteDescriptionTbl','#LocDesc'),
                ('SkuLocAttributeData','#Pair'),('SkuAttributeData','#Sku'),('LocationAttributeData','#Loc')):
                query=query.replace(old,new)
            queries[direction][name]=query
    return producer,queries


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('modern',type=Path); parser.add_argument('evidence',type=Path)
    args=parser.parse_args()
    if args.evidence.exists(): raise ValueError('Preserve receipts; choose new directory')
    args.evidence.mkdir(parents=True); result=dict(status='FAILED',engine_replays=0,persistent_sql_writes=False)
    try:
        receipt=json.loads((args.modern/'receipt.json').read_text())
        if receipt['status']!='PERSISTED_READBACK_PASS_COMPARISON_REQUIRED' or receipt['producer_sha256']!=SOURCE_SHA:
            raise ValueError('Modern Expedite identity differs')
        root=Path(__file__).resolve().parents[1]
        if any(file_sha(root/n)!=sha for n,sha in receipt['sources'].items()): raise ValueError('Modern source differs')
        if file_sha(args.modern/receipt['file'])!=receipt['sha256']: raise ValueError('Modern readback differs')
        with gzip.open(args.modern/receipt['file'],'rt') as stream: actual=json.load(stream)
        if not actual['rows']: raise ValueError('This selected full-estate check requires nonempty Expedite')
        legacy,provenance=terminal_inputs()
        if receipt['run']['id']!=provenance['modern_run'] or receipt['run']['output_digest']!=provenance['modern_output_digest']:
            raise ValueError('Modern/legacy run pairing changed')
        if file_sha(PICK/'receipt.json')!=PICK_SHA: raise ValueError('Retained Pick receipt changed')
        pick_receipt=json.loads((PICK/'receipt.json').read_text())
        if pick_receipt['retained_source']!=provenance: raise ValueError('Retained Pick provenance differs')
        pick=list(iter_rows(PICK/'legacy-pick.jsonl.gz',pick_receipt['legacy']))
        producer,queries=selected_queries(); expected=dict(counts={})
        result.update(legacy_source=provenance,producer_sha256=SOURCE_SHA,consumer_sha256=PLAN_SHA,
            retained_pick_receipt_sha256=PICK_SHA,modern_receipt_sha256=file_sha(args.modern/'receipt.json'),queries=dict(producer=producer,counts=queries))
        os.environ['VFTEST_PROFILE']='fresh'
        with exclusive_replay():
            with connection('VFTEST_BPR') as db:
                temp_rows(db,'#Pick','dbo.vf_PickListReport',pick)
                temp_rows(db,'#Rationed','dbo.vf_RationedReqReport',legacy['late']['vf_RationedReqReport'])
                temp_rows(db,'#Master','VFTEST_Importer.dbo.MasterData',legacy['closing']['importer']['MasterData'])
                temp_rows(db,'#Standard','VFTEST_Importer.dbo.SKULocStandardAttributes',legacy['closing']['dbm']['SKULocStandardAttributes'])
                temp_rows(db,'#Expedite','dbo.ExpediteDispatches',[])
                db.execute(producer)
                # Accepted BTR already computed these three fields; transfer only
                # its own retained legacy values, never modern state or answers.
                db.execute('CREATE TABLE #Age (SKUCode nvarchar(50),WhCode nvarchar(50),BRAge int,BRAgeRedCount int,BRAgeBlackCount int)')
                ages=legacy['closing']['btr']['ExpediteDispatches']
                if ages: db.cursor().executemany('INSERT INTO #Age VALUES (?,?,?,?,?)',[
                    tuple(r[f] for f in ('SKUCode','WhCode','BRAge','BRAgeRedCount','BRAgeBlackCount')) for r in ages])
                db.execute('UPDATE E SET BRAge=A.BRAge,BRAgeRedCount=A.BRAgeRedCount,BRAgeBlackCount=A.BRAgeBlackCount FROM #Expedite E JOIN #Age A ON E.SKUCode=A.SKUCode AND E.WhCode=A.WhCode')
                cursor=db.execute('SELECT * FROM #Expedite'); fields=[c[0] for c in cursor.description]
                expected['rows']=storage([dict(zip(fields,r)) for r in cursor.fetchall()])
                for name,table in (('#Sku','SkuAttributeData'),('#Loc','LocationAttributeData'),('#Pair','SkuLocAttributeData'),
                                   ('#SkuDesc','SKUDescriptionTbl'),('#LocDesc','SiteDescriptionTbl')):
                    temp_rows(db,name,'dbo.'+table,legacy['closing']['importer'][table])
                cte=';WITH cte_SKUs AS (SELECT DISTINCT SKUCode FROM #Sku),cte_WhCodes AS (SELECT DISTINCT WHCode FROM #Loc) '
                for direction,counts in queries.items():
                    expected['counts'][direction]={name:db.execute(cte+query).fetchone()[0] for name,query in counts.items()}
                # Focused arithmetic probes cover nonzero/half-tie report values;
                # they are not new engine/synthetic acceptance fixtures.
                from mta.presentation.expedite import potential_loss
                probes=[]
                for norm,rlt,price in ((2,1,'1.000'),(6,1,'3.000'),(3,1,'4.500'),(220,4,'110.000'),(0,4,'9.000'),(-1,4,'9.000'),(220,4,None)):
                    row=db.execute('DECLARE @N int=?,@R int=?,@P decimal(18,3)=?; SELECT CONVERT(bigint,CASE WHEN @N>0 THEN ROUND((@R/(@N*1.0))*ISNULL(@P,0),0) WHEN @N=0 THEN 0 END)',norm,rlt,price).fetchone()[0]
                    probes.append(dict(norm=norm,rlt=rlt,price=price,legacy=row,modern=potential_loss(norm,rlt,price)))
        delta=differences(expected,actual,'/expedite-producer-and-unscoped-counts')
        for i,probe in enumerate(probes):
            delta+=differences(probe['legacy'],probe['modern'],f'/potential-loss-unit-probes/{i}')
        with gzip.open(args.evidence/'legacy-expedite.json.gz','wt') as stream: json.dump(expected,stream)
        result.update(status='PASS_EXPEDITE_PRODUCER_AND_UNSCOPED_COUNTS' if not delta else 'FAIL',rows=len(expected['rows']),
            fields=len(fields),counts=expected['counts'],differences=delta,potential_loss_unit_probes=probes,
            legacy_readback_sha256=file_sha(args.evidence/'legacy-expedite.json.gz'),
            qualification='Complete report and normal unfiltered counts; not detail/remark/transit grids, charts, authenticated nonempty scope or browser acceptance')
    except Exception as exc:
        result['error']=dict(type=type(exc).__name__,message=str(exc)); raise
    finally:
        (args.evidence/'receipt.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({k:result[k] for k in ('status','rows','fields','counts')}))
    if delta: raise SystemExit(1)


if __name__=='__main__': main()
