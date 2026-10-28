"""Exact forward SQL-alias correction, retaining the accepted phase owners."""
import hashlib
from importlib import import_module
from pathlib import Path
from mta.serialization import digest
from mta.runtime import transit_settings_schema_transition as retained

MIGRATION_NAME = '0242_generic_read_sql_aliases'
PREVIOUS_COMMIT = '7cfc8c245e133e3ee1e623b2577649f87140e0ed'
PREVIOUS_RELEASE = '4c6bb681c2a00f852c71034d8117377730671ac845abae8bbed19132d54722df'
OWNER = retained.OWNER


def migration_pins():
    path = Path(__file__).parent / 'migrations' / (MIGRATION_NAME + '.py')
    return [[MIGRATION_NAME, hashlib.sha256(path.read_bytes()).hexdigest()]]


def catalogue_delta():
    migration = import_module('mta.runtime.migrations.' + MIGRATION_NAME)
    name = 'mta.guard_scope_read_reference()'
    before = dict(name=name, owner=OWNER, security_definer=False, body=migration.OLD,
        configuration=['search_path=pg_catalog, mta'], language='plpgsql', returns='trigger')
    return {'functions:' + name: dict(before=before, after=dict(before, body=migration.BODY))}


def require_specification(spec):
    previous = spec['previous_release']
    if (spec['migration_pins'] != migration_pins()
            or previous['source_commit'] != PREVIOUS_COMMIT
            or previous['manifest_sha256'] != PREVIOUS_RELEASE
            or spec['catalogue_delta'] != catalogue_delta()):
        raise ValueError('Exact generic read SQL-alias correction required')


def approved_receipt(value):
    return (value.get('migration_pins') == migration_pins()
        and value.get('previous_release') == PREVIOUS_RELEASE
        and value.get('catalogue_delta_digest') == digest(catalogue_delta()))


def require_start(cursor):
    from mta.runtime.ingestion_ownership import migration_history_guard
    migration = import_module('mta.runtime.migrations.' + MIGRATION_NAME)
    cursor.execute("SELECT max(name) FROM mta.django_migrations WHERE app='fresh_mta'")
    if cursor.fetchone() != ('0241_scope_transit_settings_owners',):
        raise ValueError('Generic alias correction requires exact0241 start')
    cursor.execute("SELECT prosrc,prosecdef,proconfig,pg_get_userbyid(proowner) FROM pg_proc "
                   "WHERE oid='mta.guard_scope_read_reference()'::regprocedure")
    if cursor.fetchone() != (migration.OLD, False, ['search_path=pg_catalog, mta'], OWNER):
        raise ValueError('Exact original generic read guard ownership required')
    if not migration_history_guard(cursor):raise ValueError('Original migration history guard required')
    cursor.execute("SELECT to_regclass('fresh_control.ingestion_schema_compatibility')")
    if cursor.fetchone()[0] is None:raise ValueError('Existing schema authority required')
    cursor.execute("SELECT EXISTS(SELECT 1 FROM mta.fresh_mta_runscopeattempt WHERE status='ACTIVE')")
    if cursor.fetchone() != (False,):raise ValueError('Alias correction refuses an active scoped worker')


def preservation(cursor, original):
    return retained.preservation(cursor, original, migration_name=MIGRATION_NAME)
