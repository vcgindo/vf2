"""Read-only admission of a migrated release before a business trial is chosen.

No registration or source is minted here. Configured operational publications
continue through the existing publication admission instead of this path.
"""
import hashlib
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIRECTORIES = ('mta', 'vectorflow', 'baseline', 'parity', 'release')
SETUP_TABLES = ('django_migrations', 'fresh_mta_productioninitialization',
                'fresh_mta_mdmsource', 'fresh_mta_calculationrun')


def verify_export(root=None):
    root = Path(root) if root is not None else ROOT
    manifest_path = root / 'release-source.json'
    if manifest_path.is_symlink():
        raise ValueError('Installed source manifest cannot be a symlink')
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    if (manifest.get('schema') != 'vectorflow-release-source-v1'
            or manifest.get('default_data_import') is not False
            or not re.fullmatch('[0-9a-f]{40}', manifest.get('source_commit', ''))
            or not isinstance(manifest.get('files'), dict)):
        raise ValueError('Installed source manifest is invalid')
    expected = {name: value for name, value in manifest['files'].items()
                if name == 'manage.py' or name.startswith(tuple(d + '/' for d in SOURCE_DIRECTORIES))}
    actual = {'manage.py'}
    for directory in SOURCE_DIRECTORIES:
        for path in (root / directory).rglob('*'):
            if path.is_symlink():
                raise ValueError('Installed source cannot contain symlinks')
            if path.is_file() and '__pycache__' not in path.parts and path.suffix != '.pyc':
                actual.add(path.relative_to(root).as_posix())
    if actual != set(expected):
        raise ValueError('Installed release source roster differs')
    for name, expected_hash in expected.items():
        path = root / name
        if (path.is_symlink() or path.resolve().is_relative_to(root.resolve()) is False
                or hashlib.sha256(path.read_bytes()).hexdigest() != expected_hash):
            raise ValueError('Installed release source bytes differ')
    return manifest['source_commit']


def require_setup_grants(cursor, *, owner, runtime):
    """Before registration the runtime has only four SELECT grants in mta."""
    cursor.execute('SELECT current_user,session_user')
    if cursor.fetchone() != (runtime, runtime):
        raise ValueError('Setup must use the dedicated runtime session')
    cursor.execute('SELECT rolcanlogin,rolsuper,rolcreatedb,rolcreaterole,rolreplication,rolbypassrls '
                   'FROM pg_roles WHERE rolname=%s', [runtime])
    if cursor.fetchone() != (True, False, False, False, False, False):
        raise ValueError('Setup runtime role attributes differ')
    cursor.execute('SELECT 1 FROM pg_auth_members m JOIN pg_roles r ON r.oid=m.member WHERE r.rolname=%s', [runtime])
    if cursor.fetchone() is not None:
        raise ValueError('Setup runtime cannot inherit another role')
    cursor.execute('SELECT r.rolname,r.rolcanlogin,r.rolsuper,r.rolcreatedb,r.rolcreaterole,'
                   'r.rolreplication,r.rolbypassrls FROM pg_database d JOIN pg_roles r ON r.oid=d.datdba '
                   'WHERE d.datname=current_database()')
    if cursor.fetchone() != (owner, False, False, False, False, False, False):
        raise ValueError('Setup database owner differs')
    cursor.execute("SELECT r.rolname FROM pg_namespace n JOIN pg_roles r ON r.oid=n.nspowner WHERE n.nspname='mta'")
    if cursor.fetchone() != (owner,):
        raise ValueError('Setup schema owner differs')
    cursor.execute("SELECT has_database_privilege(current_user,current_database(),'CREATE'),"
                   "has_database_privilege(current_user,current_database(),'TEMP'),"
                   "has_schema_privilege(current_user,'mta','CREATE')")
    if cursor.fetchone() != (False, False, False):
        raise ValueError('Setup runtime has installation privileges')
    cursor.execute("SELECT n.nspname,a.privilege_type,a.is_grantable FROM pg_namespace n "
                   "CROSS JOIN LATERAL aclexplode(n.nspacl) a LEFT JOIN pg_roles r ON r.oid=a.grantee "
                   "WHERE n.nspname IN ('mta','mta_state','mta_opening','fresh_control','public') "
                   "AND (r.rolname=%s OR a.grantee=0)", [runtime])
    if set(cursor.fetchall()) != {('mta', 'USAGE', False)}:
        raise ValueError('Setup schema grants differ from the finite read profile')
    cursor.execute("SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
                   "JOIN pg_roles r ON r.oid=c.relowner WHERE r.rolname=%s "
                   "AND n.nspname NOT IN ('pg_catalog','information_schema') LIMIT 1", [runtime])
    if cursor.fetchone() is not None:
        raise ValueError('Setup runtime must not own database relations')
    cursor.execute("SELECT n.nspname,c.relname,a.privilege_type,a.is_grantable FROM pg_class c "
                   "JOIN pg_namespace n ON n.oid=c.relnamespace "
                   "CROSS JOIN LATERAL aclexplode(c.relacl) a LEFT JOIN pg_roles r ON r.oid=a.grantee "
                   "WHERE n.nspname IN ('mta','mta_state','mta_opening','fresh_control') "
                   "AND (r.rolname=%s OR a.grantee=0)",
                   [runtime])
    if set(cursor.fetchall()) != {('mta', name, 'SELECT', False) for name in SETUP_TABLES}:
        raise ValueError('Setup runtime grants differ from the finite read profile')
    cursor.execute("SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace "
                   "CROSS JOIN LATERAL aclexplode(COALESCE(p.proacl,acldefault('f',p.proowner))) a "
                   "LEFT JOIN pg_roles r ON r.oid=a.grantee "
                   "WHERE n.nspname IN ('mta','mta_state','mta_opening','fresh_control') "
                   "AND (r.rolname=%s OR a.grantee=0) LIMIT 1", [runtime])
    if cursor.fetchone() is not None:
        raise ValueError('Setup must not grant runtime or PUBLIC function execution')


def grant_setup():
    """Installer-only, before the existing artifact-bound registration."""
    import os
    import psycopg
    from psycopg import sql
    from release.configuration import database_options, secret
    from release.provision import plan
    config = plan()
    roles = config['roles']['MTA']
    with psycopg.connect(host=os.environ.get('DB_HOST', 'postgres'),
            port=os.environ.get('DB_PORT', '5432'), dbname=config['databases']['MTA'],
            user=os.environ.get('PG_ADMIN_USER', 'postgres'), password=secret('PG_ADMIN_PASSWORD'),
            **database_options()) as db, db.cursor() as cursor:
        cursor.execute('SELECT rolsuper FROM pg_roles WHERE rolname=current_user')
        if cursor.fetchone() != (True,):
            raise ValueError('Trusted provisioning session required')
        cursor.execute('SELECT current_database()')
        if cursor.fetchone() != (config['databases']['MTA'],):
            raise ValueError('Explicit installation database differs')
        cursor.execute("SELECT to_regclass('fresh_control.owned_namespace')")
        if cursor.fetchone()[0] is not None:
            raise ValueError('Existing namespace registration must not be modified')
        cursor.execute('SELECT (SELECT count(*) FROM mta.fresh_mta_productioninitialization),'
                       '(SELECT count(*) FROM mta.fresh_mta_mdmsource),'
                       '(SELECT count(*) FROM mta.fresh_mta_calculationrun)')
        if cursor.fetchone() != (0, 0, 0):
            raise ValueError('Setup grants require an empty business instance')
        for name in SETUP_TABLES:
            cursor.execute('SELECT r.rolname FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace '
                           'JOIN pg_roles r ON r.oid=c.relowner WHERE n.nspname=%s AND c.relname=%s',
                           ['mta', name])
            if cursor.fetchone() != (roles['OWNER'],):
                raise ValueError('Setup relation owner differs')
        for schema in ('mta', 'mta_state', 'mta_opening'):
            cursor.execute(sql.SQL('REVOKE ALL ON SCHEMA {} FROM PUBLIC').format(sql.Identifier(schema)))
            cursor.execute(sql.SQL('REVOKE EXECUTE ON ALL FUNCTIONS IN SCHEMA {} FROM PUBLIC').format(
                sql.Identifier(schema)))
        cursor.execute(sql.SQL('GRANT USAGE ON SCHEMA mta TO {}').format(sql.Identifier(roles['RUNTIME'])))
        for name in SETUP_TABLES:
            cursor.execute(sql.SQL('GRANT SELECT ON mta.{} TO {}').format(
                sql.Identifier(name), sql.Identifier(roles['RUNTIME'])))
        cursor.execute(sql.SQL('SET LOCAL ROLE {}').format(sql.Identifier(roles['RUNTIME'])))
        # session_user remains the provisioner in this maintenance transaction;
        # validate the exact table-grant roster here, then normal runtime startup
        # validates role/session identity and effective privileges independently.
        cursor.execute("SELECT n.nspname,c.relname,a.privilege_type,a.is_grantable FROM pg_class c "
                       "JOIN pg_namespace n ON n.oid=c.relnamespace "
                       "CROSS JOIN LATERAL aclexplode(c.relacl) a LEFT JOIN pg_roles r ON r.oid=a.grantee "
                       "WHERE n.nspname IN ('mta','mta_state','mta_opening','fresh_control') "
                       "AND (r.rolname=%s OR a.grantee=0)", [roles['RUNTIME']])
        if set(cursor.fetchall()) != {('mta', name, 'SELECT', False) for name in SETUP_TABLES}:
            raise ValueError('Setup grant profile differs; transaction rolled back')
    return dict(status='EMPTY_APPLICATION_SETUP_GRANTS_INSTALLED_NO_TRIAL_OR_REGISTRATION',
                database=config['databases']['MTA'], runtime_role=roles['RUNTIME'])


if __name__ == '__main__':
    print(json.dumps(grant_setup(), sort_keys=True))
