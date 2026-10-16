"""Export committed production sources only; never copy a workstation checkout or database."""
import argparse
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import subprocess
import tarfile

SCHEMA = 'vectorflow-release-source-v1'
NATIVE_SCHEMAS = frozenset(('complete-daily-state-schema-v3.json', 'daily-input-extra-schema-v2.json',
    'production-state-schema.json', 'cohort2-native-source-schema.json', 'cohort2-alert-source-schema.json',
    'cohort2-restore-cast-qualification.json', 'cohort2-runtime-restore-cast-qualification.json'))
EXCLUDED_COMMANDS = frozenset(('record_parity', 'run_temporal', 'run_daily', 'install_daily_input_source',
    'verify_current_day_receipts', 'export_pick_consumer', 'export_norm0_reports', 'export_insight_consumer',
    'export_history_consumers', 'export_daily_history', 'export_btr_consumer', 'export_excess_consumer',
    'export_expedite_charts', 'export_fulfillment_charts', 'publish_expedite_projection',
    'publish_fulfillment_projection', 'publish_excess_projection', 'prepare_guided_history_fixture',
    'prepare_guided_dbm_fixture', 'prepare_guided_chronic_fixture'))


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
        if path.suffix not in ('.py', '.json', '.sql'):
            return False
        # Historical migration names can contain "fixture" while defining
        # required tables/guards only. Keep the complete native schema chain.
        if name.startswith('mta/runtime/migrations/'):
            return path.suffix == '.py'
        if path.stem.endswith(('_probe', '_fixture')) or path.stem.startswith(('prove_', 'test_')):
            return False
        if '/management/commands/' in name and path.stem in EXCLUDED_COMMANDS:
            return False
        return True
    if name.startswith('baseline/'):
        return path.name in NATIVE_SCHEMAS
    # Required lossless compressed input/reference reader only; no oracle, replay,
    # comparison runner or validation fixtures from the rest of parity/.
    if name in ('parity/__init__.py', 'parity/output_archive.py'):
        return True
    if name.startswith('user-service/'):
        if path.name in ('bootstrap_stage7b.py', 'seed_local_demo_identities.py', 'seed_local_admin_permissions.py', 'seed_users_and_roles.py'):
            return False
        return (len(path.parts)>2 and path.parts[1] in ('api', 'api_gateway', 'apps', 'common', 'core', 'master_validation', 'templates') and path.suffix in ('.py', '.json', '.html')) or name in ('user-service/manage.py', 'user-service/logger_config.py')
    if name.startswith('mto/'):
        if path.name in ('bootstrap_stage7b.py',):
            return False
        return (len(path.parts)>2 and path.parts[1] in ('MTO_API', 'mto_app', 'poogi', 'procurement', 'production', 'import_export', 'scheduler') and path.suffix in ('.py', '.json', '.html')) or name in ('mto/manage.py', 'mto/Downloads/ReportPaths.json')
    if name.startswith('frontend/'):
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
    value = dict(schema=SCHEMA, source_commit=commit, files=dict(sorted(records.items())),
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
