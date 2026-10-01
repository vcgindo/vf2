"""Exact deployed BPR SQL vs native modern reports, approved terminal supplement.

Independent retained legacy facts; session-temp SQL only. Never engine replay.
"""
from copy import deepcopy
import gzip
import json
import os
from pathlib import Path
import subprocess
import sys
from parity.bpr_queries import queries, SOURCE, SOURCE_SHA
from parity.legacy_isolation import exclusive_replay, connection
from parity.output_archive import file_sha
from parity.retained_consumer_input import terminal_inputs
from parity.verify_rrr_consumer import auth_ctes, supplement_temp_hierarchy, temp_rows, PERMISSION_SHA
from parity.verify_rrr_export import typed
from parity.temporal import differences

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = Path('D:/freshvcf-build/evidence')
MANIFEST_SHA = 'bca78680e3fd2162c097ef0abcc5894e9177e77da5a3d75cb367742fbf97fdd5'


def main():
    target = Path(sys.argv[1])
    target.mkdir(parents=True, exist_ok=False)
    result = dict(status='FAILED', engine_replays=0, persistent_database_writes=False)
    try:
        manifest_path = ROOT/'baseline/presentation-terminal-v1.json'
        assert file_sha(manifest_path) == MANIFEST_SHA
        manifest = json.loads(manifest_path.read_text())
        assert file_sha(Path(manifest['audit_receipt'])) == manifest['audit_receipt_sha256']
        parent = EVIDENCE/'f3-rrr-filters-modern-001'
        assert file_sha(parent/'receipt.json') == 'f96cc963afce16ce3342ab49b7448ecea047159e71efe745bf81b568049c0dff'
        old = json.loads((parent/'cases.json').read_text())['cases']
        selected = ('root-regression', 'selected-leaf', 'parent-leaf-empty', 'overlapping-permission-ids')
        cases = [deepcopy(c) for c in old if c['id'] in selected]
        assert len(cases) == 4
        for c in cases:
            assert not c['payload'].get('filters') or not any(c['payload']['filters'].values())
            c['payload']['paginationParameter'] = dict(pageNumber=1, recordsPerPage=5000)
        for page in (1,2,249):
            case = deepcopy(cases[0]); case['id'] = 'root-page-'+str(page)
            case['payload']['paginationParameter'] = dict(pageNumber=page, recordsPerPage=5)
            cases.append(case)
        (target/'requests.json').write_text(json.dumps(dict(cases=cases),indent=2))
        runtime = json.loads(subprocess.check_output(['docker','inspect','freshvcf-preview-mta-1'],text=True))[0]
        args = ['docker','run','--rm','--name','freshvcf-bpr-terminal-proof','--network','freshvcf-test_default',
            '--memory','4g','--memory-swap','4g','--cpus','2','-v',ROOT.as_posix()+':/app:ro',
            '-v',EVIDENCE.as_posix()+':/evidence:ro','-e','PYTHONPATH=/app']
        for value in runtime['Config']['Env']:
            if value.startswith(('VF_', 'MTA_')): args += ['-e', value]
        args += ['-e','VF_MTA_TERMINAL_FILE=/app/baseline/presentation-terminal-v1.json',
                 '-e','VF_MTA_TERMINAL_SHA256='+MANIFEST_SHA]
        for mount in runtime['Mounts']:
            if mount['Destination'] != '/app': args += ['-v',mount['Source']+':'+mount['Destination']+':ro']
        process = subprocess.run(args + [runtime['Image'],'python','tools/bpr_terminal_probe.py',
            '/evidence/'+target.name+'/requests.json'],text=True,capture_output=True)
        (target/'modern.log').write_text(process.stderr)
        if process.returncode: raise RuntimeError('Modern reader failed; see modern.log')
        actual = json.loads(process.stdout)
        with gzip.open(target/'modern.json.gz','wt') as stream: json.dump(actual,stream)
        result.update(base_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
            dependency_image=runtime['Image'], supplement_sha256=MANIFEST_SHA,
            candidate_sources={p:file_sha(ROOT/p) for p in ('mta/presentation/bpr.py','mta/presentation/bpr_read.py',
                'mta/presentation/terminal_supplement.py','tools/bpr_terminal_probe.py')})
        legacy, provenance = terminal_inputs()
        closing = legacy['closing']
        assert actual['run_id'] == provenance['modern_run'] == manifest['publication']['run_id']
        assert actual['output_digest'] == provenance['modern_output_digest'] == manifest['publication']['output_digest']
        assert actual['ancillary'] == manifest['populations'] == {'InTransitData':[], 'BPRReport_RemarkDetails':[]}
        catalogue_path = Path('D:/freshvcf-build/inputs/permission-input-v1.json')
        assert file_sha(catalogue_path) == PERMISSION_SHA
        catalogue = json.loads(catalogue_path.read_text())
        observed = {row['id']:row for row in actual['observations']}
        expected = []; sqls = {}; delta = []; order_delta = []
        os.environ['VFTEST_PROFILE'] = 'fresh'
        with exclusive_replay():
            with connection('VFTEST_BPR') as db:
                for name,table,rows in (
                    ('#Bpr','dbo.BPR_Table',legacy['late']['BPR_Table']),
                    ('#Rationed','dbo.vf_RationedReqReport',legacy['late']['vf_RationedReqReport']),
                    ('#Standard','VFTEST_Importer.dbo.SKULocStandardAttributes',closing['dbm']['SKULocStandardAttributes']),
                    ('#Sku','VFTEST_Importer.dbo.SkuAttributeData',closing['importer']['SkuAttributeData']),
                    ('#Loc','VFTEST_Importer.dbo.LocationAttributeData',closing['importer']['LocationAttributeData']),
                    ('#Pair','VFTEST_Importer.dbo.SkuLocAttributeData',closing['importer']['SkuLocAttributeData']),
                    ('#Trend','VFTEST_BTR.dbo.BufferTrendPhysicalInv',closing['btr']['BufferTrendPhysicalInv']),
                    ('#Transit','VFTEST_Importer.dbo.InTransitData',manifest['populations']['InTransitData']),
                    ('#Remarks','dbo.BPRReport_RemarkDetails',manifest['populations']['BPRReport_RemarkDetails'])):
                    temp_rows(db,name,table,rows)
                supplement_temp_hierarchy(db,catalogue)
                for case in cases:
                    payload = case['payload']
                    auth = auth_ctes(db,catalogue,payload)
                    query = queries(auth, payload['paginationParameter']['pageNumber'],payload['paginationParameter']['recordsPerPage'])
                    sqls[case['id']] = query
                    count = db.execute(query['count']).fetchone()[0]
                    cursor = db.execute(query['grid']); fields = [c[0] for c in cursor.description]
                    assert len(fields) == len(set(fields))
                    rows = [{name:typed(value) for name,value in zip(fields,row)} for row in cursor.fetchall()]
                    value = dict(id=case['id'],count=count,rows=rows)
                    expected.append(value)
                    delta += differences(value, observed[case['id']], '/'+case['id'])
                    order = lambda items:[(r['WHCode'],r['SKUCode']) for r in items]
                    if order(rows) != order(observed[case['id']]['rows']): order_delta.append(case['id'])
                    db.execute('DROP TABLE #ProductPermissions; DROP TABLE #LocationPermissions')
                    print('Compared BPR '+case['id']+': '+str(len(rows))+' rows',flush=True)
        for name,value in (('legacy.json.gz',expected),('queries.json.gz',sqls)):
            with gzip.open(target/name,'wt') as stream: json.dump(value,stream)
        result.update(status='PASS_TERMINAL_BPR_RAW_TYPED_SCOPED_CONSUMER' if not delta and not order_delta else 'FAIL',
            legacy=provenance, source=str(SOURCE),source_sha256=SOURCE_SHA,
            cases=[dict(id=c['id'],count=c['count'],rows=len(c['rows'])) for c in expected],
            differences=delta, declared_order_differences=order_delta,
            file_hashes={n:file_sha(target/n) for n in ('requests.json','modern.json.gz','legacy.json.gz','queries.json.gz')},
            qualification='Selected unfiltered count/key-page/grid and permission bags; no nonempty transit, HTTP wire/filter/export/action acceptance')
        if delta or order_delta: raise ValueError('BPR raw consumer mismatch; retain receipt')
    except Exception as exc:
        result['error'] = dict(type=type(exc).__name__, message=str(exc))
        raise
    finally:
        (target/'receipt.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(dict(status=result['status'],cases=result['cases'])))


if __name__ == '__main__': main()
