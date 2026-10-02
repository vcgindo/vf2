"""Observe deployed parent Expedite SQL using accepted independent legacy facts.

Writes session-local tables only. This is not modern or browser acceptance.
"""
import gzip
import json
import os
from pathlib import Path
import sys

from parity.expedite_grid_queries import parent_query, custom_query
from parity.git_queries import PLAN, PLAN_SHA
from parity.legacy_isolation import connection, exclusive_replay
from parity.output_archive import file_sha, iter_rows
from parity.retained_consumer_input import terminal_inputs
from parity.verify_expedite_consumer import PICK, PICK_SHA
from parity.verify_rrr_consumer import (
    PERMISSION_SHA, auth_ctes, supplement_temp_hierarchy, temp_rows,
)


def main():
    target = Path(sys.argv[1])
    target.mkdir(parents=True, exist_ok=False)
    custom = '--custom' in sys.argv[2:]
    filtered = '--filters' in sys.argv[2:]
    if custom and filtered:
        raise ValueError('Custom source ignores filters; use its existing proof')
    result = dict(status='FAILED', engine_replays=0, persistent_database_writes=False,
                  qualification='Independent parent SQL observations only; no API/browser/performance parity.')
    try:
        legacy, provenance = terminal_inputs()
        result['legacy_source'] = provenance
        result['consumer_sha256'] = PLAN_SHA
        assert file_sha(PLAN) == PLAN_SHA
        producer = Path('D:/freshvcf-build/evidence/f3-expedite-comparison-001')
        assert file_sha(producer/'receipt.json') == '24a68d58ca9c69ba73bf0c82e8b3576bd874a75ae3ed30d2268f45add34ff9e1'
        receipt = json.loads((producer/'receipt.json').read_text())
        assert receipt['legacy_source'] == provenance
        assert file_sha(producer/'legacy-expedite.json.gz') == receipt['legacy_readback_sha256']
        with gzip.open(producer/'legacy-expedite.json.gz', 'rt') as stream:
            expedite = json.load(stream)['rows']
        assert file_sha(PICK/'receipt.json') == PICK_SHA
        pick_receipt = json.loads((PICK/'receipt.json').read_text())
        assert pick_receipt['retained_source'] == provenance
        pick = list(iter_rows(PICK/'legacy-pick.jsonl.gz', pick_receipt['legacy']))
        manifest = Path('baseline/presentation-terminal-v1.json')
        assert file_sha(manifest) == 'bca78680e3fd2162c097ef0abcc5894e9177e77da5a3d75cb367742fbf97fdd5'
        supplement = json.loads(manifest.read_text())
        assert file_sha(Path(supplement['audit_receipt'])) == supplement['audit_receipt_sha256']
        assert supplement['publication']['run_id'] == provenance['modern_run']
        assert supplement['publication']['output_digest'] == provenance['modern_output_digest']
        catalogue_path = Path('D:/freshvcf-build/inputs/permission-input-v1.json')
        assert file_sha(catalogue_path) == PERMISSION_SHA
        catalogue = json.loads(catalogue_path.read_text())
        scopes = Path('D:/freshvcf-build/evidence/f3-bpr-terminal-003')
        assert file_sha(scopes/'receipt.json') == '89a9ba03575422174690183aaa1771340aa57d759c925a1c6ecb27ad11ec1693'
        scope_receipt = json.loads((scopes/'receipt.json').read_text())
        assert file_sha(scopes/'requests.json') == scope_receipt['file_hashes']['requests.json']
        cases = json.loads((scopes/'requests.json').read_text())['cases'][:4]
        compiled = {}
        if filtered:
            # Parent Expedite uses the identical PlanningGrid filter type,
            # Commons overload, aliases, call gate and replacements as GitGrid.
            # Reuse its actual-DLL expressions; execute the different SQL here.
            source = Path('D:/freshvcf-build/evidence/f3-stage2-git-filters-001')
            assert file_sha(source/'receipt.json') == 'ef961a530945a1be380a3be6267b2aefb2789beed0f62b0f11d1629c13385469'
            source_receipt = json.loads((source/'receipt.json').read_text())
            for name in ('requests.json', 'GitGrid.json'):
                assert file_sha(source/name) == source_receipt['file_hashes'][name]
            cases = json.loads((source/'requests.json').read_text())
            compiled = {r['id']:r for r in json.loads((source/'GitGrid.json').read_text(encoding='utf-8-sig'))['cases']}
            result['reused_filter_receipt_sha256'] = file_sha(source/'receipt.json')
        result['input_rows'] = dict(expedite=len(expedite), pick=len(pick),
                                    nms=len(legacy['closing']['consumer_context']['NMSAllItems']))
        observations, queries = {}, {}
        result['observations'] = observations
        os.environ['VFTEST_PROFILE'] = 'fresh'
        with exclusive_replay():
            with connection('VFTEST_BPR') as db:
                result['database'] = db.execute('SELECT DB_NAME()').fetchone()[0]
                tables = [
                    ('#Expedite', 'dbo.ExpediteDispatches', expedite),
                    ('#Pick', 'dbo.vf_PickListReport', pick),
                    ('#Master', 'dbo.BPRMaster', legacy['closing']['bpr']['BPRMaster']),
                    ('#Standard', 'VFTEST_Importer.dbo.SKULocStandardAttributes', legacy['closing']['dbm']['SKULocStandardAttributes']),
                    ('#Nms', 'VFTEST_Importer.dbo.NMSAllItems', legacy['closing']['consumer_context']['NMSAllItems']),
                    ('#Remarks', 'dbo.BPRReport_RemarkDetails', supplement['populations']['BPRReport_RemarkDetails']),
                ]
                if custom:
                    tables.append(('#Bpr', 'dbo.BPR_Table', legacy['late']['BPR_Table']))
                for name, table in (('#Sku', 'SkuAttributeData'), ('#Loc', 'LocationAttributeData'),
                                    ('#Pair', 'SkuLocAttributeData'), ('#SkuDesc', 'SKUDescriptionTbl'),
                                    ('#LocDesc', 'SiteDescriptionTbl')):
                    tables.append((name, 'dbo.'+table, legacy['closing']['importer'][table]))
                for name, table, rows in tables:
                    temp_rows(db, name, table, rows)
                supplement_temp_hierarchy(db, catalogue)
                for case in cases:
                    auth = auth_ctes(db, catalogue, case['payload'])
                    variants = (('full', 1, 5000),) if filtered else (('full', 1, 5000), ('page1', 1, 3), ('page2', 2, 3), ('unpaged', None, 5000))
                    for label, page, size in variants:
                        key = case['id']+'/'+label
                        query = (custom_query if custom else parent_query)(auth, page=page, size=size)
                        if filtered:
                            query = parent_query(auth, page=page, size=size, sql_filter=compiled[case['id']]['sql_filter'])
                        queries[key] = query
                        try:
                            cursor = db.execute(query)
                            observations[key] = dict(status='EXECUTED', columns=[c[0] for c in cursor.description],
                                                     rows=[list(r) for r in cursor.fetchall()])
                        except Exception as exc:
                            observations[key] = dict(status='SQL_ERROR', message=str(exc))
                    db.execute('DROP TABLE #ProductPermissions; DROP TABLE #LocationPermissions')
        (target/'queries.json').write_text(json.dumps(queries, indent=2))
        (target/'requests.json').write_text(json.dumps(cases, indent=2))
        result['status'] = 'CAPTURED_FILTERED_PARENT_SQL_REQUIRES_REVIEW' if filtered else 'CAPTURED_CUSTOM_SQL_REQUIRES_REVIEW' if custom else 'CAPTURED_PARENT_SQL_REQUIRES_REVIEW'
        result['file_hashes'] = {p.name: file_sha(p) for p in target.iterdir() if p.is_file()}
    except Exception as exc:
        result['error'] = dict(type=type(exc).__name__, message=str(exc))
        raise
    finally:
        result['proof_sources'] = {p: file_sha(Path(p)) for p in
                                  ('parity/expedite_grid_queries.py', 'parity/verify_expedite_parent_sql.py')}
        (target/'receipt.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(dict(status=result['status'], observations={k:v['status'] for k,v in observations.items()})))


if __name__ == '__main__':
    main()
