"""Read-only source/evidence inventory for the complete-day assessment.

Writes only the explicitly selected JSON report. Does not import engine modules,
read credentials, provision resources or execute business calculations.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KEY_SOURCES = (
    'mta/runtime/temporal.py', 'mta/runtime/services.py',
    'mta/runtime/receipt_integrity.py', 'mta/runtime/relational_state.py',
    'mta/runtime/validation_storage.py', 'mta/runtime/temporal_continuation.py',
    'mta/runtime/management/commands/run_temporal.py',
    'mta/runtime/management/commands/run_daily.py',
    'mta/runtime/management/commands/record_parity.py',
    'mta/temporal/chain.py', 'mta/evidence.py',
    'parity/offline_temporal.py', 'parity/replay_temporal.py',
    'parity/accepted_prefix.py', 'parity/temporal_policy.py',
    'parity/adapters/legacy/temporal_day.py',
    'parity/adapters/legacy/temporal_delivery.py',
    'tools/offline_temporal_validation.py',
)
CANONICAL_SUFFIXES = (
    '/Engine/VectorFLOWv4.bat', '/Engine/GenericFinalProcessing.bat',
    '/Engine/SiteSpecific/GulfOil/PostBPRProcessing.bat',
    '/Engine/SiteSpecific/GulfOil/PostDBMProcessing.bat',
    '/Engine/SiteSpecific/GulfOil/FinalProcessing.bat',
    '/Scripts/SiteSpecific/GulfOil/BPR/CalculatedAttributes.sql',
    '/Scripts/Importer/ValidateBatchExecutionFlags.sql',
    '/Scripts/BPR/ValidateBPRBatchExecutionFlags.sql',
    '/Scripts/BPR/ClearTableForBPRBatchExecutionFailure.sql',
    '/Engine/RunCoreBPR.bat', '/Engine/Planning.bat',
    '/Engine/GenerateBPRExceptionReport.bat',
    '/Engine/PickListReports.bat', '/Engine/OrderAllocBasedReports.bat',
    '/Scripts/BPR/ProdOrderSuggestions.sql',
    '/Scripts/BPR/ClearHistoryData_BPR.sql',
    '/Scripts/BPR/CollectOrderFulfillmentData.sql',
    '/Engine/StdSettingsPre.bat', '/Engine/StdSettingsPost.bat',
    '/Engine/SiteSpecific/GulfOil/Settings.bat',
    '/Engine/SiteSpecific/GulfOil/PostBTRProcessing.bat',
    '/Scripts/SiteSpecific/GulfOil/BTR/CalculateAttributeBasedonBTR.sql',
    '/Scripts/Importer/ResetBatchExecutionFlag.sql',
    '/Scripts/Importer/ValidationForParentNorm.sql',
    '/Scripts/Importer/NMSTaskStatusUpdate.sql',
)
REUSE = (
    'D:/freshvcf-build/refinement/dbm-joins-001/identities.json',
    'D:/freshvcf-build/refinement/dbm-joins-001/final-proof.json',
    'D:/freshvcf-build/refinement/dbm-joins-001/mode-equivalence-resolved.json',
    'D:/freshvcf-build/daily-3006/runtime/offline-temporal-full-001/readiness-dbm-v1/readiness-result.json',
)


def identity(path):
    raw = path.read_bytes()
    return dict(path=path.as_posix(), sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))


def inventory():
    manifest_path = ROOT/'baseline/manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    canonical = []
    for row in manifest['engine_sources']:
        if any(row['path'].replace('\\', '/').endswith(s) for s in CANONICAL_SUFFIXES):
            observed = identity(Path(row['path']))
            observed.update(expected_sha256=row['sha256'], matches_pin=observed['sha256']==row['sha256'])
            canonical.append(observed)
    found = {s for s in CANONICAL_SUFFIXES if any(r['path'].endswith(s) for r in canonical)}
    api = []
    for row in manifest['canonical_api']:
        value = identity(Path(row['path']))
        value.update(expected_sha256=row['sha256'], matches_pin=value['sha256']==row['sha256'])
        api.append(value)
    paths = sorted(set((ROOT/'mta/presentation').rglob('*.py')) | {ROOT/p for p in KEY_SOURCES})
    modules = []
    for path in paths:
        value = identity(path)
        value['path'] = path.relative_to(ROOT).as_posix()
        tree = ast.parse(path.read_text(encoding='utf-8-sig'))
        value['top_level_symbols'] = [n.name for n in tree.body
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))]
        modules.append(value)
    proof = [identity(Path(p)) for p in REUSE]
    old = json.loads(Path(REUSE[0]).read_text(encoding='utf-8'))
    refinements = []
    for name, expected in old['changed_sources'].items():
        value = identity(ROOT/name.replace('\\', '/'))
        value.update(expected_sha256=expected, matches_pin=value['sha256']==expected)
        refinements.append(value)
    site_python = [identity(Path(p)) for p in (
        'F:/VFlow_Local/local-runtime/mta-engine/Scripts/SiteSpecific/GulfOil/BTR/GulfOil_BTRReports.py',
        'F:/VFlow_Source_Backup/deployed-demo/MTA/V6/Scripts/SiteSpecific/GulfOil/BTR/GulfOil_BTRReports.py')]
    return dict(schema='fresh-complete-daily-assessment-inventory-v1',
        status_tracker='docs/MIGRATION.md',
        inventory_is_not_execution_or_equivalence_proof=True,
        baseline=identity(manifest_path),
        navigation=[identity(ROOT/p) for p in (
            'docs/batch-atlas/inventory.json','docs/batch-atlas/diagrams-v2.json')],
        frozen_input=identity(Path('D:/freshvcf-build/synthetic/rlt-4-7-v1/scenario-004/full-input.json')),
        canonical=canonical, missing_canonical_suffixes=sorted(set(CANONICAL_SUFFIXES)-found),
        deployed_api=api, retained_dbm_refinement=refinements,
        newly_observed_site_python=dict(files=site_python,
            copies_identical=site_python[0]['sha256']==site_python[1]['sha256'],
            baseline_registered=False,
            qualification='Called by pinned PostBTR BAT; observed bytes only, not accepted producer proof or a new baseline registration.'),
        evidence=proof, modules=modules,
        limitation='Hashes bind inspected sources, not full BAT activation or new daily acceptance. '
                   'All timings remain historical until a separately authorized complete exercise.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    value = inventory()
    failures = [r['path'] for group in ('canonical','deployed_api','retained_dbm_refinement')
                for r in value[group] if not r['matches_pin']]
    if failures or value['missing_canonical_suffixes']:
        raise ValueError('Assessment source reconciliation failed: '+repr(
            (failures,value['missing_canonical_suffixes'])))
    args.output.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(source_pins='MATCH', modules=len(value['modules']),
                          canonical=len(value['canonical']), report=str(args.output))))


if __name__ == '__main__':
    main()
