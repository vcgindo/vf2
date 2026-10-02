"""Compile selected deployed GIT consumers against owned terminal temp tables.

This records the independent SQL contract only, not modern or browser parity.
"""
import json
import os
from pathlib import Path
import subprocess
import sys

from parity.git_queries import queries, PLAN, PLAN_SHA, CHART, CHART_SHA
from parity.legacy_isolation import connection, exclusive_replay
from parity.output_archive import file_sha
from parity.retained_consumer_input import terminal_inputs
from parity.verify_planning_overview import GIT_PRODUCERS
from parity.verify_rrr_consumer import auth_ctes, supplement_temp_hierarchy, temp_rows, PERMISSION_SHA


def main():
    target = Path(sys.argv[1])
    target.mkdir(parents=True, exist_ok=False)
    result = dict(status='FAILED', engine_replays=0, persistent_database_writes=False,
                  qualification='Unfiltered terminal SQL only; no modern/API/browser/performance acceptance.')
    try:
        root = Path(__file__).resolve().parents[1]
        result['base_commit'] = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
        result['proof_sources'] = {str(p.relative_to(root)): file_sha(p) for p in
                                  (Path(__file__), root/'parity/git_queries.py')}
        result['canonical_sources'] = {str(PLAN): PLAN_SHA, str(CHART): CHART_SHA}
        for name, sha in GIT_PRODUCERS.items():
            assert file_sha(Path('F:/VFlow_Local/local-runtime/mta-engine/Scripts/BPR')/name) == sha
        legacy, provenance = terminal_inputs()
        result['legacy_source'] = provenance
        manifest = root/'baseline/presentation-terminal-v1.json'
        assert file_sha(manifest) == 'bca78680e3fd2162c097ef0abcc5894e9177e77da5a3d75cb367742fbf97fdd5'
        supplement = json.loads(manifest.read_text())
        assert file_sha(Path(supplement['audit_receipt'])) == supplement['audit_receipt_sha256']
        assert supplement['publication']['run_id'] == provenance['modern_run']
        assert supplement['publication']['output_digest'] == provenance['modern_output_digest']
        assert supplement['populations']['InTransitData'] == []
        assert not any(r['GIT'] is not None and r['GIT'] > 0 for r in legacy['late']['vf_RationedReqReport'])
        nms = legacy['closing']['consumer_context']['NMSAllItems']
        assert nms == []
        result['native_nms_rows'] = len(nms)
        result['terminal_producer_sha256'] = GIT_PRODUCERS
        catalogue_path = Path('D:/freshvcf-build/inputs/permission-input-v1.json')
        assert file_sha(catalogue_path) == PERMISSION_SHA
        catalogue = json.loads(catalogue_path.read_text())
        parent = Path('D:/freshvcf-build/evidence/f3-bpr-terminal-003')
        assert file_sha(parent/'receipt.json') == '89a9ba03575422174690183aaa1771340aa57d759c925a1c6ecb27ad11ec1693'
        receipt = json.loads((parent/'receipt.json').read_text())
        assert file_sha(parent/'requests.json') == receipt['file_hashes']['requests.json']
        cases = json.loads((parent/'requests.json').read_text())['cases'][:4]
        (target/'requests.json').write_text(json.dumps(cases, indent=2))
        observations, sqls = {}, {}
        result['observations'] = observations
        os.environ['VFTEST_PROFILE'] = 'fresh'
        with exclusive_replay():
            with connection('VFTEST_BPR') as db:
                result['database'] = db.execute('SELECT DB_NAME()').fetchone()[0]
                for name, table, rows in (
                    ('#Git', 'dbo.GoodsInTransitMaster', []),
                    ('#Transporter', 'dbo.GoodsInTransitTransporterMaster', []),
                    ('#Transit', 'VFTEST_Importer.dbo.InTransitData', supplement['populations']['InTransitData']),
                    ('#Standard', 'VFTEST_Importer.dbo.SKULocStandardAttributes', legacy['closing']['dbm']['SKULocStandardAttributes']),
                    ('#Rationed', 'dbo.vf_RationedReqReport', legacy['late']['vf_RationedReqReport']),
                    ('#Nms', 'VFTEST_Importer.dbo.NMSAllItems', nms)):
                    temp_rows(db, name, table, rows)
                for name, table in (('#Sku', 'SkuAttributeData'), ('#Loc', 'LocationAttributeData'),
                                    ('#Pair', 'SkuLocAttributeData'), ('#SkuDesc', 'SKUDescriptionTbl'), ('#LocDesc', 'SiteDescriptionTbl')):
                    temp_rows(db, name, 'VFTEST_Importer.dbo.'+table, legacy['closing']['importer'][table])
                supplement_temp_hierarchy(db, catalogue)
                config = db.execute("select Col_Code, Header,Col_Position from ui_ReportConfigurations where reportname='adminbpr' and Col_Code like '%attr%' and Visible=1").fetchall()
                assert not config, 'Dynamic attributes require their actual source expression'
                result['visible_custom_attributes'] = []
                for case in cases:
                    selected = queries(auth_ctes(db, catalogue, case['payload']), case['payload'])
                    sqls[case['id']] = selected
                    observations[case['id']] = {}
                    for name, query in selected.items():
                        try:
                            cursor = db.execute(query)
                            description = cursor.description
                            rows = [list(row) for row in cursor.fetchall()]
                            observation = dict(status='EXECUTED', rows=rows,
                                columns=[dict(name=c[0], python_type=c[1].__name__, precision=c[4], scale=c[5], nullable=c[6]) for c in description])
                        except Exception as exc:
                            observation = dict(status='SQL_ERROR', error_type=type(exc).__name__, message=str(exc))
                        observations[case['id']][name] = observation
                        print(case['id']+'/'+name+': '+observation['status'], flush=True)
                    db.execute('DROP TABLE #ProductPermissions; DROP TABLE #LocationPermissions')
        (target/'queries.json').write_text(json.dumps(sqls, indent=2))
        expected_failures = {'child-transporter-grid'}
        for case in observations.values():
            for name, observation in case.items():
                if name in expected_failures:
                    assert observation['status'] == 'SQL_ERROR' and '207' in observation['message'], observation
                    for column in ('InTransitQty', 'TransporterCode', 'OrderNo'):
                        assert column in observation['message'], observation
                else:
                    assert observation['status'] == 'EXECUTED', (name, observation)
                    expected = [[0]] if name.endswith('-count') else [[None]] if name.endswith('-grid') or name.endswith('-custom') else []
                    assert observation['rows'] == expected, (name, observation)
        result['status'] = 'VERIFIED_UNFILTERED_TERMINAL_SQL_WITH_CHILD_SOURCE_FAILURE'
        result['file_hashes'] = {p.name: file_sha(p) for p in target.iterdir() if p.is_file()}
    except Exception as exc:
        result['error'] = dict(type=type(exc).__name__, message=str(exc))
        raise
    finally:
        (target/'receipt.json').write_text(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
