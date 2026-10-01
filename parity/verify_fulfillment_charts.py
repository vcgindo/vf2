"""Exact SQL chart bags, then actual pinned API DLL GetResponse projection."""
import argparse
import gzip
import json
import os
from pathlib import Path
import subprocess
from parity.legacy_isolation import connection,exclusive_replay
from parity.output_archive import file_sha
from parity.retained_consumer_input import terminal_inputs
from parity.temporal import differences
from parity.verify_rrr_consumer import temp_rows
from parity.verify_excess_readmodel import literals

SOURCE=Path('F:/vflow_integrated/.local-stage7/deployed-planning/VectorFlowAPIs.VectorFlow.Processors.Replenishment.InsightsAndTrends.QuadrantProcessor.decompiled.cs')
SOURCE_SHA='9f084f3550ab5c6ca8193de71b70ee6d7341aa1647004776ff152dd9fd858d60'
PRODUCER=Path('D:/freshvcf-build/evidence/f3-fulfillment-comparison-002')
PRODUCER_SHA='7942b6bf84cda3c467970e89809aa45515c7570de681dacc4839d2dcfddea19f'
SECTIONS=('location_orders','sku_orders','location_gap','sku_gap')


def selected_queries():
    if file_sha(SOURCE)!=SOURCE_SHA: raise ValueError('Deployed chart source changed')
    text=SOURCE.read_text().split('strSqlAuth = GenericFunction.getAuthQueryForReports',1)[1].split('ErrorLog.Logger(',1)[0]
    query=''.join(literals(line) for line in text.splitlines() if line.strip().startswith('strSql '))
    for old,new in (('OrderFulfillmentDataDetails','#Details'),('OrderFulfillmentData','#Summary'),
                    ('SKUDescriptionTbl','#SkuDesc'),('SiteDescriptionTbl','#LocDesc'),
                    ('SkuAttributeData','#Sku'),('LocationAttributeData','#Loc')): query=query.replace(old,new)
    queries=[q for q in query.split(';') if q.strip()]
    if len(queries)!=4: raise ValueError('Unexpected chart SQL roster')
    return queries


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('modern',type=Path); parser.add_argument('evidence',type=Path)
    args=parser.parse_args()
    if args.evidence.exists(): raise ValueError('Preserve prior receipt; choose new evidence directory')
    args.evidence.mkdir(parents=True)
    result=dict(status='FAILED',engine_replays=0,persistent_database_writes=False)
    try:
        modern=json.loads((args.modern/'receipt.json').read_text())
        if modern['status']!='READBACK_EXPORTED_COMPARISON_REQUIRED' or modern['boundary']!='UNSCOPED_FULFILLMENT_CHARTS':
            raise ValueError('Wrong modern chart export')
        root=Path(__file__).resolve().parents[1]
        if any(file_sha(root/name)!=sha for name,sha in modern['sources'].items()): raise ValueError('Modern chart source changed')
        if file_sha(args.modern/modern['file'])!=modern['sha256']: raise ValueError('Modern exported charts changed')
        with gzip.open(args.modern/modern['file'],'rt') as stream: actual=json.load(stream)
        if any(not rows for rows in actual['queries'].values()): raise ValueError('This selected full-estate proof requires all chart populations')
        legacy,provenance=terminal_inputs()
        if modern['run']['id']!=provenance['modern_run'] or modern['run']['output_digest']!=provenance['modern_output_digest']:
            raise ValueError('Legacy/modern run pairing changed')
        if file_sha(PRODUCER/'receipt.json')!=PRODUCER_SHA: raise ValueError('Accepted canonical producer receipt changed')
        producer=json.loads((PRODUCER/'receipt.json').read_text())
        if producer['legacy_source']!=provenance or producer['status']!='PASS_PRODUCER_AND_UNSCOPED_FULFILLMENT_GRID':
            raise ValueError('Canonical producer handoff differs')
        if file_sha(PRODUCER/'legacy-fulfillment.json.gz')!=producer['legacy_readback_sha256']: raise ValueError('Retained canonical report rows changed')
        with gzip.open(PRODUCER/'legacy-fulfillment.json.gz','rt') as stream: reports=json.load(stream)
        cte=';WITH cte_SKUs AS (SELECT DISTINCT SKUCode FROM #Sku),cte_WhCodes AS (SELECT DISTINCT WHCode FROM #Loc) '
        queries=selected_queries(); expected={}; tables=[]
        os.environ['VFTEST_PROFILE']='fresh'
        with exclusive_replay():
            with connection('VFTEST_BPR') as db:
                for name,table,key in (('#Summary','OrderFulfillmentData','summary'),('#Details','OrderFulfillmentDataDetails','details')):
                    temp_rows(db,name,'dbo.'+table,reports[key])
                for name,table in (('#Sku','SkuAttributeData'),('#Loc','LocationAttributeData'),('#SkuDesc','SKUDescriptionTbl'),('#LocDesc','SiteDescriptionTbl')):
                    temp_rows(db,name,'dbo.'+table,legacy['closing']['importer'][table])
                dynamic=db.execute("SELECT Col_Code FROM ui_ReportConfigurations WHERE reportname='adminbpr' AND Visible=1 AND (Col_Code LIKE 'SKUAttr%' OR Col_Code LIKE 'LocAttr%')").fetchall()
                if dynamic: raise ValueError('Enabled dynamic chart configuration requires explicit mapping')
                for section,query in zip(SECTIONS,queries):
                    cursor=db.execute(cte+query)
                    names=[c[0] for c in cursor.description]
                    rows=[dict(zip(names,r)) for r in cursor.fetchall()]
                    expected[section]=rows
                    tables.append(dict(columns=[dict(name=n,type='int32' if n=='counts' else 'string') for n in names],rows=rows))
        path=args.evidence/'canonical-query-results.json'
        path.write_text(json.dumps(dict(tables=tables)),encoding='utf-8')
        dll_path=args.evidence/'deployed-method-response.json'
        harness=root/'parity/invoke_legacy_quadrant.ps1'
        completed=subprocess.run(['pwsh','-NoProfile','-File',str(harness),'-InputPath',str(path),'-OutputPath',str(dll_path)],
                                 text=True,capture_output=True)
        (args.evidence/'deployed-method.log').write_text(completed.stdout+completed.stderr,encoding='utf-8')
        if completed.returncode: raise RuntimeError('Canonical method invocation failed; see preserved log')
        binary=json.loads(dll_path.read_text(encoding='utf-8-sig'))
        if binary['input_sha256']!=file_sha(path): raise ValueError('Deployed method input changed')
        delta=differences(expected,actual['queries'],'/fulfillment-chart-queries')
        delta+=differences(binary['response'],actual['response'],'/deployed-GetResponse')
        order_match={name:[r['counts'] for r in expected[name]]==[r['counts'] for r in actual['queries'][name]] for name in SECTIONS}
        result.update(status='PASS_UNSCOPED_FULFILLMENT_CHARTS' if not delta and all(order_match.values()) else 'FAIL',
            rows={k:len(v) for k,v in expected.items()},differences=delta,declared_order_matches=order_match,
            modern_receipt_sha256=file_sha(args.modern/'receipt.json'),legacy_source=provenance,
            source_sha256=SOURCE_SHA,producer_receipt_sha256=PRODUCER_SHA,queries=[cte+q for q in queries],
            canonical_query_results_sha256=file_sha(path),deployed_method_response_sha256=file_sha(dll_path),
            invocation_source_sha256=file_sha(harness),runtime=binary['runtime'],serializer=binary['serializer'],
            qualification='Exact selected SQL bags and real deployed DLL pure-method response under recorded CLR; not legacy HTTP hosting, nonempty authenticated scopes/filters/browser acceptance, or unspecified tie ordering')
    except Exception as exc:
        result['error']=dict(type=type(exc).__name__,message=str(exc)); raise
    finally:
        (args.evidence/'receipt.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({k:result[k] for k in ('status','rows','declared_order_matches')}))
    if result['status']=='FAIL': raise SystemExit(1)


if __name__=='__main__': main()
