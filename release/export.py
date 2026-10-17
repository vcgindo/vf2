# **DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.**
"""Export committed production sources only; never copy a workstation checkout or database."""
import argparse
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import subprocess
import tarfile

SCHEMA = 'vectorflow-release-source-v1'
NATIVE_SCHEMAS = frozenset(('operational-alert-source-pins.json', 'complete-daily-state-schema-v3.json', 'daily-input-extra-schema-v2.json',
    'production-state-schema.json', 'cohort2-native-source-schema.json', 'cohort2-alert-source-schema.json',
    'cohort2-restore-cast-qualification.json', 'cohort2-runtime-restore-cast-qualification.json'))
EXCLUDED_COMMANDS = frozenset(('record_parity', 'run_temporal', 'run_daily', 'install_daily_input_source',
    'verify_current_day_receipts', 'export_pick_consumer', 'export_norm0_reports', 'export_insight_consumer',
    'export_history_consumers', 'export_daily_history', 'export_btr_consumer', 'export_excess_consumer',
    'export_expedite_charts', 'export_fulfillment_charts', 'publish_expedite_projection',
    'publish_fulfillment_projection', 'publish_excess_projection', 'prepare_guided_history_fixture',
    'prepare_guided_dbm_fixture', 'prepare_guided_chronic_fixture',
    'verify_application_reads', 'verify_offline_terminal', 'publish_pick_projection'))


SUPPORTED_MTA_COMMANDS = frozenset(('initialize_production', 'run_production_day', 'prepare_daily_ui', 'activate_daily_ui', 'check_daily_selection', 'prepare_guided_aggregates', 'prepare_history_reports', 'prepare_planning_charts', 'prepare_planning_custom', 'prepare_planning_expedite_charts', 'prepare_planning_expedite_custom', 'prepare_planning_expedite_grids', 'prepare_planning_expedite_transit', 'prepare_planning_git', 'prepare_planning_grids', 'prepare_planning_sources', 'prepare_research_availability', 'prepare_rrr', 'build_btr_reporting', 'build_btr_snapshot', 'prepare_bor_membership', 'prepare_boroa_membership', 'cohort2_operational', 'register_operational_configuration'))

def included(name):
    path = PurePosixPath(name)
    if path.is_absolute() or '..' in path.parts:
        return False
    if any(part in ('.git', '__pycache__', 'node_modules', 'tests', '__tests__', 'secrets') for part in path.parts):
        return False
    if (path.name.startswith(('test_', '.env')) or '.test.' in path.name or '.spec.' in path.name
            or path.suffix.lower() in ('.dll', '.bat', '.exe', '.ps1', '.pem', '.key', '.dump', '.bak', '.zip')
            or path.name in ('tests.py', 'web.config', 'setupTests.ts')):
        return name == 'release/.env.example'
    if name in ('manage.py', 'requirements.txt'):
        return True
    if name.startswith('release/'):
        return path.suffix in ('.py', '.md', '.json', '.yaml', '.sh', '.sql', '.lock') or path.name.endswith('Dockerfile') or path.suffix == '.template' or path.name == '.dockerignore'
    if name.startswith('vectorflow/'):
        return path.suffix == '.py'
    if name.startswith('mta/'):
        if '/management/commands/' in name and path.suffix == '.py' and path.stem != '__init__':
            return path.stem in SUPPORTED_MTA_COMMANDS
        if name in (
                'mta/presentation/fixture.py', 'mta/presentation/dbm_fixture_read.py',
                'mta/presentation/fixture_count_plan.py', 'mta/presentation/qualified_consumption.py',
                'mta/presentation/daily_planning_extension.py', 'mta/presentation/operational_admission.py'):
            return False
        if name.startswith('mta/presentation/daily_planning/'):
            return False
        if name.startswith('mta/fixtures/'):
            return False
        if path.suffix not in ('.py', '.json', '.sql'):
            return False
        # Historical migration names can contain "fixture" while defining
        # required tables/guards only. Keep the complete native schema chain.
        if name.startswith('mta/runtime/migrations/'):
            return path.suffix == '.py'
        # target_fixture is an imported fail-closed provenance guard, not a
        # fixture population/installer. Native MDM modules import it even when
        # the historical fixture mode is inactive.
        if name == 'mta/mdm/target_fixture.py':
            return True
        if path.stem.endswith(('_probe', '_fixture')) or path.stem.startswith(('prove_', 'test_')):
            return False
        if '/management/commands/' in name and path.stem in EXCLUDED_COMMANDS:
            return False
        return True
    if name.startswith('baseline/'):
        return path.name in NATIVE_SCHEMAS
    if name.startswith('user-service/'):
        if path.name in ('bootstrap_stage7b.py', 'seed_local_demo_identities.py', 'seed_local_admin_permissions.py', 'seed_users_and_roles.py'):
            return False
        return (len(path.parts)>2 and path.parts[1] in ('api', 'api_gateway', 'apps', 'common', 'core', 'master_validation', 'templates') and path.suffix in ('.py', '.json', '.html')) or name in ('user-service/manage.py', 'user-service/logger_config.py')
    if name.startswith('mto/'):
        if path.name in ('bootstrap_stage7b.py',):
            return False
        return (len(path.parts)>2 and path.parts[1] in ('MTO_API', 'mto_app', 'poogi', 'procurement', 'production', 'import_export', 'scheduler') and path.suffix in ('.py', '.json', '.html')) or name in ('mto/manage.py', 'mto/Downloads/ReportPaths.json')
    if name.startswith('frontend/'):
        # Keep only the two existing imports used by runtime UI modules. Other
        # mock payloads are used exclusively by excluded frontend tests.
        if name.startswith('frontend/src/mock-data/'):
            return name in ('frontend/src/mock-data/MCGrid.ts',
                            'frontend/src/mock-data/RRR-Color-Bandwise.ts')
        if name in ('frontend/package.json', 'frontend/package-lock.json', 'frontend/tsconfig.json', 'frontend/.eslintrc.json'):
            return True
        return (name.startswith('frontend/src/') and path.suffix in ('.ts', '.tsx', '.js', '.jsx', '.mjs', '.css', '.scss', '.json', '.svg', '.png', '.jpg', '.jpeg', '.gif', '.webp', '.ico', '.woff', '.woff2', '.ttf')) or name.startswith('frontend/public/')
    return False


def export(repository, revision, destination):
    repository, destination = Path(repository).resolve(), Path(destination).resolve()
    if destination.exists() or destination == repository or repository in destination.parents:
        raise ValueError('Choose a new external export directory; existing targets are never replaced')
    commit = subprocess.check_output(['git', '-C', str(repository), 'rev-parse', revision + '^{commit}']).decode().strip()
    archive = subprocess.check_output(['git', '-C', str(repository), 'archive', '--format=tar', commit])
    records = {}
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        for member in tar.getmembers():
            if not included(member.name) or not member.isfile():
                continue
            raw = tar.extractfile(member).read()
            target = destination / member.name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
            if member.name.endswith('.sh'):
                target.chmod(0o755)
            records[member.name] = hashlib.sha256(raw).hexdigest()
    ignore = destination/'release/.dockerignore'
    if ignore.is_file():
        (destination/'.dockerignore').write_bytes(ignore.read_bytes())
        records['.dockerignore'] = hashlib.sha256(ignore.read_bytes()).hexdigest()
    value = dict(restriction='**DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.**', schema=SCHEMA, source_commit=commit, files=dict(sorted(records.items())),
        default_data_import=False, qualification='Source export only; image/platform/install/UI proof is separate. Required native SQL/migrations/security/source-integrity libraries retained; no customer/test DB, computed output seed or secret copied.')
    destination.mkdir(parents=True, exist_ok=True)
    (destination/'release-source.json').write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
    return value


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--revision', required=True)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    result = export(args.repository,args.revision,args.output)
    print(json.dumps(dict(source_commit=result['source_commit'],files=len(result['files']),output=str(args.output))))
