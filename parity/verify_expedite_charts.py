"""Canonical post-report SQL and actual deployed Expedite chart methods.

Only session-temporary writes; no accepted engine day is replayed.
"""
import argparse
import gzip
import json
import os
from pathlib import Path
import subprocess
from mta.serialization import storage
from parity.legacy_isolation import connection,exclusive_replay
from parity.output_archive import file_sha,iter_rows
from parity.retained_consumer_input import terminal_inputs
from parity.temporal import differences
from parity.verify_rrr_consumer import temp_rows
from parity.verify_excess_readmodel import literals
from parity.verify_expedite_consumer import PICK,PICK_SHA

SOURCE=Path('F:/vflow_integrated/.local-stage7/deployed-planning/VectorFlowAPIs.VectorFlow.Processors.Replenishment.InsightsAndTrends.ExpediteProcessor.decompiled.cs')
SOURCE_SHA='e78148cc38d5a802e014e6085111e79a40c2a6b462563e2bd412677505e654b4'
ENGINE=Path('F:/VFlow_Local/local-runtime/mta-engine/Scripts/BPR')
PRODUCERS={
    'Ration_Scripts/PostRationEcoAvailability.sql':'ad726c858dab068a86e567dfe814b99a5309b693ebee061aaa84f60d00b2e977',
    'CalculatePenetrationAndColor.sql':'e4a62d592b660fe08d46c45eecaf7a061e60eba7c8d86d3adec239023de5e251',
    'Ration_Scripts/UpdatePostRationPipelineInventoryPen.sql':'3881064e266422ceddfde472420c74b70d7799f01311afd8b650f55e0a80f554'}
EXPEDITE=Path('D:/freshvcf-build/evidence/f3-expedite-comparison-001')
EXPEDITE_SHA='24a68d58ca9c69ba73bf0c82e8b3576bd874a75ae3ed30d2268f45add34ff9e1'
SECTIONS=dict(parent=('critical','receiving','nil_stock','chronic','pre_post'),child=('critical','receiving','pre_post'))
CTE=';WITH cte_SKUs AS (SELECT DISTINCT SKUCode FROM #Sku),cte_WhCodes AS (SELECT DISTINCT WHCode FROM #Loc) '


def selected_sql():
    if file_sha(SOURCE)!=SOURCE_SHA or any(file_sha(ENGINE/p)!=s for p,s in PRODUCERS.items()):
        raise ValueError('Canonical selected source changed')
    sources=[(ENGINE/p).read_text() for p in PRODUCERS]
    producers=[
        'insert into PenetrationAndColor'+sources[0].split('insert into PenetrationAndColor',1)[1].split('END TRY',1)[0],
        'declare @LeastAllowedPen'+sources[1].split('declare @LeastAllowedPen',1)[1].split('END TRY',1)[0],
        'update A with(tablock)'+sources[2].split('update A with(tablock)',1)[1].split("print N'Delete records",1)[0]]
    for i,query in enumerate(producers):
        for old,new in (('[$(IntermediateDatabase)].dbo.PenetrationCalculation','#PenCalc'),
            ('$(RecordPenetrationExceptions)','0'),('BPRExceptions','#Exceptions'),
            ('PenetrationAndColor','#Pen'),('vf_PickListReport','#Pick')):
            query=query.replace(old,new)
        if '$(' in query or 'sp_MSForEachTable' in query: raise ValueError('Unsafe producer extraction')
        producers[i]=query
    charts={}
    for kind,name in (('parent','GetParentExpediteGraphDetails'),('child','GetChildExpediteGraphDetails')):
        body=SOURCE.read_text().split('public responseMessage '+name,1)[1].split('ErrorLog.Logger(',1)[0]
        query=''.join(literals(line) for line in body.splitlines() if line.strip().startswith('strSql '))
        for old,new in (('vf_PickListReport','#Pick'),('ExpediteDispatches','#Expedite'),('SiteDescriptionTbl','#LocDesc'),
                        ('LocationAttributeData','#Loc'),('BPRMaster','#Master')):
            query=query.replace(old,new)
        charts[kind]=[CTE+q for q in query.split(';') if q.strip()]
        if len(charts[kind])!=len(SECTIONS[kind]): raise ValueError('Unexpected canonical chart roster')
    return producers,charts


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('modern',type=Path); parser.add_argument('evidence',type=Path)
    args=parser.parse_args()
    if args.evidence.exists(): raise ValueError('Preserve prior receipt; choose new directory')
    args.evidence.mkdir(parents=True); result=dict(status='FAILED',engine_replays=0,persistent_sql_writes=False)
    try:
        modern=json.loads((args.modern/'receipt.json').read_text())
        if modern['status']!='READBACK_EXPORTED_COMPARISON_REQUIRED' or modern['boundary']!='UNSCOPED_EXPEDITE_CHARTS':
            raise ValueError('Wrong modern export boundary')
        root=Path(__file__).resolve().parents[1]
        if any(file_sha(root/n)!=sha for n,sha in modern['sources'].items()): raise ValueError('Modern source changed')
        if file_sha(args.modern/modern['file'])!=modern['sha256']: raise ValueError('Modern export changed')
        with gzip.open(args.modern/modern['file'],'rt') as stream: actual=json.load(stream)
        if not actual['pick']: raise ValueError('Selected acceptance requires nonempty Pick')
        legacy,provenance=terminal_inputs()
        if modern['run']['id']!=provenance['modern_run'] or modern['run']['output_digest']!=provenance['modern_output_digest']:
            raise ValueError('Legacy/modern accepted run pair changed')
        for directory,sha in ((PICK,PICK_SHA),(EXPEDITE,EXPEDITE_SHA)):
            if file_sha(directory/'receipt.json')!=sha: raise ValueError('Retained producer receipt changed')
        pr=json.loads((PICK/'receipt.json').read_text()); er=json.loads((EXPEDITE/'receipt.json').read_text())
        if pr['retained_source']!=provenance or er['legacy_source']!=provenance: raise ValueError('Retained producer provenance differs')
        pick=list(iter_rows(PICK/'legacy-pick.jsonl.gz',pr['legacy']))
        if file_sha(EXPEDITE/'legacy-expedite.json.gz')!=er['legacy_readback_sha256']: raise ValueError('Retained Expedite rows changed')
        with gzip.open(EXPEDITE/'legacy-expedite.json.gz','rt') as stream: reports=json.load(stream)
        producers,charts=selected_sql(); expected=dict(charts={}); dll_inputs={}
        result.update(modern_receipt_sha256=file_sha(args.modern/'receipt.json'),legacy_source=provenance,
            producer_sha256=PRODUCERS,consumer_sha256=SOURCE_SHA,queries=dict(producers=producers,charts=charts))
        os.environ['VFTEST_PROFILE']='fresh'
        with exclusive_replay():
            with connection('VFTEST_BPR') as db:
                for name,table,rows in (('#Pick','dbo.vf_PickListReport',pick),('#Pen','dbo.PenetrationAndColor',[]),
                    ('#PenCalc','VFTEST_Intermediate.dbo.PenetrationCalculation',[]),('#Exceptions','dbo.BPRExceptions',[]),
                    ('#Expedite','dbo.ExpediteDispatches',reports['rows']),('#Master','dbo.BPRMaster',legacy['closing']['bpr']['BPRMaster'])):
                    temp_rows(db,name,table,rows)
                for query in producers: db.execute(query)
                fields=list(pick[0])+['PostPipelineInventoryPen','PostPipelineInventoryColor']
                cursor=db.execute('SELECT '+','.join('['+f+']' for f in fields)+' FROM #Pick')
                expected['pick']=storage([dict(zip(fields,r)) for r in cursor.fetchall()])
                for name,table in (('#Sku','SkuAttributeData'),('#Loc','LocationAttributeData'),('#LocDesc','SiteDescriptionTbl')):
                    temp_rows(db,name,'dbo.'+table,legacy['closing']['importer'][table])
                if db.execute("SELECT Col_Code FROM ui_ReportConfigurations WHERE reportname='adminbpr' AND Visible=1 AND Col_Code LIKE 'LocAttr%'").fetchall():
                    raise ValueError('Dynamic chart configuration requires explicit mapping')
                for kind,queries in charts.items():
                    expected['charts'][kind]=dict(queries={}); tables=[]
                    for name,query in zip(SECTIONS[kind],queries):
                        cursor=db.execute(query); names=[c[0] for c in cursor.description]
                        rows=[dict(zip(names,r)) for r in cursor.fetchall()]
                        expected['charts'][kind]['queries'][name]=rows
                        tables.append(dict(columns=[dict(name=n,type='int32' if c[1] is int else 'string') for n,c in zip(names,cursor.description)],rows=rows))
                    dll_inputs[kind]=dict(tables=tables)
        invocation={}; method_differences=[]; flaws={}
        for kind,values in dll_inputs.items():
            path=args.evidence/(kind+'-canonical-query-results.json'); path.write_text(json.dumps(values),encoding='utf-8')
            dll_path=args.evidence/(kind+'-deployed-method-response.json'); harness=root/'parity/invoke_legacy_quadrant.ps1'
            completed=subprocess.run(['pwsh','-NoProfile','-File',str(harness),'-Processor','ExpediteProcessor','-Direction',kind,
                '-InputPath',str(path),'-OutputPath',str(dll_path)],text=True,capture_output=True)
            (args.evidence/(kind+'-deployed-method.log')).write_text(completed.stdout+completed.stderr,encoding='utf-8')
            if completed.returncode: raise RuntimeError('Canonical method invocation failed; see retained log')
            binary=json.loads(dll_path.read_text(encoding='utf-8-sig'))
            if binary['input_sha256']!=file_sha(path): raise ValueError('Deployed method input changed')
            expected['charts'][kind]['response']=binary['response']
            # A pure method contract takes an explicit ordered DataSet. Use the
            # SAME method input for both implementations, separately from the
            # independently generated query-bag comparisons. Never publish it.
            from mta.presentation.expedite_charts import response_from_dataset
            method_actual=response_from_dataset(expected['charts'][kind]['queries'],kind)
            method_differences+=differences(binary['response'],method_actual,'/explicit-dataset-method/'+kind)
            if actual['charts'][kind].get('source_flaw'):
                # Reproduce the canonical order flaw with the same full query
                # bag, reversed only at the otherwise unordered critical table.
                from copy import deepcopy
                reversed_values=deepcopy(values); reversed_values['tables'][0]['rows'].reverse()
                reverse_path=args.evidence/(kind+'-reversed-query-results.json')
                reverse_path.write_text(json.dumps(reversed_values),encoding='utf-8')
                reverse_dll=args.evidence/(kind+'-reversed-deployed-response.json')
                reverse_call=subprocess.run(['pwsh','-NoProfile','-File',str(harness),'-Processor','ExpediteProcessor','-Direction',kind,
                    '-InputPath',str(reverse_path),'-OutputPath',str(reverse_dll)],text=True,capture_output=True)
                (args.evidence/(kind+'-reversed-method.log')).write_text(reverse_call.stdout+reverse_call.stderr,encoding='utf-8')
                if reverse_call.returncode: raise RuntimeError('Flaw reproduction failed; see retained log')
                reverse_binary=json.loads(reverse_dll.read_text(encoding='utf-8-sig'))
                table_bags={n:t['rows'] for n,t in zip(SECTIONS[kind],reversed_values['tables'])}
                method_differences+=differences(reverse_binary['response'],response_from_dataset(table_bags,kind),'/reversed-explicit-dataset/'+kind)
                section='maxPipelineInvBlackRedSKUWithRationedQuantityAvailableAtParentuiconfig'
                labels=lambda r:[v['LogisticsLocation'] for v in r['data']['expediteDispatches'][section]['data']]
                before_labels,after_labels=labels(binary['response']),labels(reverse_binary['response'])
                if before_labels==after_labels: raise ValueError('Selected permutation did not reproduce the source flaw')
                flaws[kind]=dict(contract='receiving LogisticsLocation from unordered last critical row',status='NOT_PARITY',
                    original_labels=before_labels,reordered_labels=after_labels,
                    reordered_input_sha256=file_sha(reverse_path),reordered_response_sha256=file_sha(reverse_dll))
            invocation[kind]=dict(query_results_sha256=file_sha(path),response_sha256=file_sha(dll_path),runtime=binary['runtime'],method=binary['method'])
        delta=differences(expected['pick'],actual['pick'],'/post-producer')+method_differences
        for kind in SECTIONS:
            delta+=differences(expected['charts'][kind]['queries'],actual['charts'][kind]['queries'],'/chart-queries/'+kind)
            if kind not in flaws:
                delta+=differences(expected['charts'][kind]['response'],actual['charts'][kind]['response'],'/chart-response/'+kind)
        order={}
        for kind in SECTIONS:
            for name,keys in (('receiving',('ParentwiseCount','MaxPipelineInv')),('nil_stock',('counts',)),('chronic',('counts',))):
                if name not in expected['charts'][kind]['queries']: continue
                a,b=(v['charts'][kind]['queries'][name] for v in (expected,actual))
                order[kind+'/'+name]=[tuple(r[k] for k in keys) for r in a]==[tuple(r[k] for k in keys) for r in b]
        with gzip.open(args.evidence/'legacy-post-charts.json.gz','wt') as stream: json.dump(expected,stream)
        result.update(status=('PASS_POST_AND_CHART_QUERIES_WITH_LEGACY_RESPONSE_FLAW' if flaws else 'PASS_POST_PRODUCER_AND_UNSCOPED_EXPEDITE_CHARTS') if not delta and all(order.values()) else 'FAIL',
            pick_rows=len(expected['pick']),pick_fields=len(expected['pick'][0]),differences=delta,declared_order_matches=order,
            chart_rows={k:{n:len(r) for n,r in v['queries'].items()} for k,v in expected['charts'].items()},invocation=invocation,
            invocation_source_sha256=file_sha(harness),legacy_readback_sha256=file_sha(args.evidence/'legacy-post-charts.json.gz'),legacy_response_flaws=flaws,
            qualification='Exact selected producer/query bags and deployed DLL response under recorded CLR; not native legacy HTTP host, nonempty authenticated scopes, filters, detail grids, or UI acceptance; unordered ties are not an ordering claim')
    except Exception as exc:
        result['error']=dict(type=type(exc).__name__,message=str(exc)); raise
    finally:
        (args.evidence/'receipt.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({k:result[k] for k in ('status','pick_rows','chart_rows','declared_order_matches')}))
    if result['status']=='FAIL': raise SystemExit(1)


if __name__=='__main__': main()
