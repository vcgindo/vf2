"""Retained independent SQL overview vs modern relational reader; no day replay."""
from copy import deepcopy
import gzip
import json
import os
from pathlib import Path
import subprocess
import sys
from parity.planning_overview_queries import queries, response, SOURCE, SOURCE_SHA
from parity.legacy_isolation import exclusive_replay, connection
from parity.output_archive import file_sha, iter_rows
from parity.retained_consumer_input import terminal_inputs
from parity.verify_rrr_consumer import auth_ctes, supplement_temp_hierarchy, temp_rows, PERMISSION_SHA
from parity.temporal import differences

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = Path('D:/freshvcf-build/evidence')
SOURCES = ('mta/presentation/planning_overview.py','mta/presentation/planning_read.py',
           'mta/presentation/views.py','mta/presentation/urls.py','tools/planning_overview_probe.py')
GIT_PRODUCERS = {
    'GenerateGoodsInTransitMaster.sql':'de8367e704206c9031bbec32fa2f5cb83b4656eca79ba0e1c8161f84786ac379',
    'GoodsInTransitTransporterMaster.sql':'79a3a80bd45d989b37ae59d08259c7a39aeda8ef51e2261a722d241cc689a79d'}


def main():
    target=Path(sys.argv[1]); target.mkdir(parents=True,exist_ok=False)
    result=dict(status='FAILED',engine_replays=0,persistent_database_writes=False)
    try:
        for name,sha in GIT_PRODUCERS.items():
            assert file_sha(Path('F:/VFlow_Local/local-runtime/mta-engine/Scripts/BPR')/name)==sha
        parent=EVIDENCE/'f3-bpr-terminal-003'
        assert file_sha(parent/'receipt.json')=='89a9ba03575422174690183aaa1771340aa57d759c925a1c6ecb27ad11ec1693'
        pr=json.loads((parent/'receipt.json').read_text())
        assert file_sha(parent/'requests.json')==pr['file_hashes']['requests.json']
        cases=json.loads((parent/'requests.json').read_text())['cases'][:4]
        for key in ('product_permissions','location_permissions'):
            c=deepcopy(cases[0]); c['id']='denied-'+key; c['payload'][key]=[]; cases.append(c)
        (target/'requests.json').write_text(json.dumps(dict(cases=cases),indent=2))
        runtime=json.loads(subprocess.check_output(['docker','inspect','freshvcf-preview-mta-1'],text=True))[0]
        args=['docker','run','--rm','--name','freshvcf-planning-overview-proof','--network','freshvcf-test_default',
            '--memory','4g','--memory-swap','4g','--cpus','2','-v',ROOT.as_posix()+':/app:ro',
            '-v',EVIDENCE.as_posix()+':/evidence:ro','-e','PYTHONPATH=/app']
        for value in runtime['Config']['Env']:
            if value.startswith(('VF_','MTA_')): args+=['-e',value]
        for mount in runtime['Mounts']:
            if mount['Destination']!='/app': args+=['-v',mount['Source']+':'+mount['Destination']+':ro']
        process=subprocess.run(args+[runtime['Image'],'python','tools/planning_overview_probe.py',
            '/evidence/'+target.name+'/requests.json'],text=True,capture_output=True)
        (target/'modern.log').write_text(process.stderr)
        if process.returncode: raise RuntimeError('Modern reader failed; see modern.log')
        modern=json.loads(process.stdout)
        with gzip.open(target/'modern.json.gz','wt') as stream: json.dump(modern,stream)
        result.update(base_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
            dependency_image=runtime['Image'],source_hashes={p:file_sha(ROOT/p) for p in SOURCES})
        legacy,provenance=terminal_inputs()
        assert modern['run_id']==provenance['modern_run'] and modern['output_digest']==provenance['modern_output_digest']
        parents={}
        for name,sha in (('f3-excess-comparison-001','41498dec00989c834efe90b496e312dd9d92f52d5b8d8d0fe934cf60365894f4'),
                         ('f3-expedite-comparison-001','24a68d58ca9c69ba73bf0c82e8b3576bd874a75ae3ed30d2268f45add34ff9e1'),
                         ('f3-fulfillment-comparison-002','7942b6bf84cda3c467970e89809aa45515c7570de681dacc4839d2dcfddea19f')):
            path=EVIDENCE/name; assert file_sha(path/'receipt.json')==sha
            receipt=json.loads((path/'receipt.json').read_text()); assert receipt['legacy_source']==provenance
            parents[name]=receipt
        e=parents['f3-excess-comparison-001']
        excess=list(iter_rows(EVIDENCE/'f3-excess-comparison-001/legacy-excess.jsonl.gz',e['legacy_rows']))
        def retained(name,file):
            path=EVIDENCE/name/file
            assert file_sha(path)==parents[name]['legacy_readback_sha256']
            with gzip.open(path,'rt') as stream: return json.load(stream)
        expedite=retained('f3-expedite-comparison-001','legacy-expedite.json.gz')['rows']
        fulfillment=retained('f3-fulfillment-comparison-002','legacy-fulfillment.json.gz')['summary']
        manifest=ROOT/'baseline/presentation-terminal-v1.json'
        assert file_sha(manifest)=='bca78680e3fd2162c097ef0abcc5894e9177e77da5a3d75cb367742fbf97fdd5'
        supplement=json.loads(manifest.read_text()); assert supplement['populations']['InTransitData']==[]
        assert supplement['publication']['run_id']==provenance['modern_run']
        assert not any(r['GIT'] is not None and r['GIT']>0 for r in legacy['late']['vf_RationedReqReport'])
        catalogue_path=Path('D:/freshvcf-build/inputs/permission-input-v1.json')
        assert file_sha(catalogue_path)==PERMISSION_SHA
        catalogue=json.loads(catalogue_path.read_text())
        expected=[]; sqls={}; delta=[]; denied_guards=[]
        os.environ['VFTEST_PROFILE']='fresh'
        with exclusive_replay():
            with connection('VFTEST_BPR') as db:
                for name,table,rows in (
                    ('#Git','dbo.GoodsInTransitMaster',[]),('#Transporter','dbo.GoodsInTransitTransporterMaster',[]),
                    ('#Transit','VFTEST_Importer.dbo.InTransitData',supplement['populations']['InTransitData']),
                    ('#Expedite','dbo.ExpediteDispatches',expedite),('#Excess','dbo.ExcessInventoryDetails',excess),
                    ('#Fulfillment','dbo.OrderFulfillmentData',fulfillment),
                    ('#Standard','VFTEST_Importer.dbo.SKULocStandardAttributes',legacy['closing']['dbm']['SKULocStandardAttributes']),
                    ('#LastDate','dbo.LastBatchRunTbl',legacy['late']['LastBatchRunTbl'])):
                    temp_rows(db,name,table,rows)
                for name,table in (('#Sku','SkuAttributeData'),('#Loc','LocationAttributeData'),
                                   ('#Pair','SkuLocAttributeData'),('#SkuDesc','SKUDescriptionTbl'),('#LocDesc','SiteDescriptionTbl')):
                    temp_rows(db,name,'VFTEST_Importer.dbo.'+table,legacy['closing']['importer'][table])
                supplement_temp_hierarchy(db,catalogue)
                for case,actual in zip(cases,modern['observations']):
                    assert case['id']==actual['id']
                    if case['id'].startswith('denied-'):
                        # Deployed SCIH quotes the empty list, then GenericFunction
                        # quotes that again on empty expansion. Its INT permission
                        # comparison receives a literal apostrophe, not valid IDs.
                        # Preserve this source-invalid branch, never label the
                        # modern safe zero-membership response as legacy parity.
                        flaw_query="SELECT CONVERT(int,value) FROM string_split('''',',')"
                        try:
                            db.execute(flaw_query).fetchall()
                        except Exception as exc:
                            if '245' not in str(exc): raise
                            failure=str(exc)
                        else:
                            raise AssertionError('Expected deployed empty-ID conversion failure')
                        assert all(v=='0' for r in actual['data'] for k,v in r.items() if k!='category')
                        denied_guards.append(dict(id=case['id'],status='SAFE_DENIAL_NOT_PARITY',
                            source_failure=failure,source_conversion_query=flaw_query,data=actual['data']))
                        continue
                    selected=queries(auth_ctes(db,catalogue,case['payload']))
                    values=[db.execute(q).fetchone()[0] for q in selected]
                    data=response(values); expected.append(dict(id=case['id'],data=data))
                    sqls[case['id']]=selected
                    delta+=differences(data,actual['data'],'/'+case['id'])
                    (target/'completed-comparisons.json').write_text(json.dumps(dict(expected=expected,differences=delta),indent=2))
                    db.execute('DROP TABLE #ProductPermissions; DROP TABLE #LocationPermissions')
                    print('Compared '+case['id']+': '+str(values),flush=True)
        for name,value in (('legacy.json.gz',expected),('queries.json.gz',sqls)):
            with gzip.open(target/name,'wt') as stream: json.dump(value,stream)
        result.update(status='PASS_TEN_PLANNING_OVERVIEW_COUNTS' if not delta else 'FAIL',
            legacy=provenance,source=str(SOURCE),source_sha256=SOURCE_SHA,comparisons=len(expected)*10,
            terminal_git_producer_hashes=GIT_PRODUCERS,
            cases=expected,differences=delta,denied_guards=denied_guards,report_counts=modern['report_counts'],
            file_hashes={n:file_sha(target/n) for n in ('requests.json','modern.json.gz','legacy.json.gz','queries.json.gz')},
            qualification='Exact overview string counts/permission bags on retained terminal inputs. Not full grids/charts/filters/nonempty logistics parity.')
        if delta: raise ValueError('Overview mismatch; retained receipt')
    except Exception as exc:
        result['error']=dict(type=type(exc).__name__,message=str(exc)); raise
    finally:
        (target/'receipt.json').write_text(json.dumps(result,indent=2))


if __name__=='__main__': main()
