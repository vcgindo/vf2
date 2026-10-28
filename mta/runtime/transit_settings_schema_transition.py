"""Finite forward admission of the native transit-owner seal correction.

Fresh installations use the complete migration graph. This maintenance profile
preserves an already certified opening, captures and accepted scoped prefix.
"""
import hashlib
from importlib import import_module
from pathlib import Path
from mta.serialization import digest

MIGRATION_NAME = '0241_scope_transit_settings_owners'
PREVIOUS_COMMIT = '64327dd53afb687c3b98726b7f1741f095977501'
PREVIOUS_RELEASE = 'c902fc0ea4a84043259ffb4d633dfcc4842c08428e055ec3a3bc090830fee2ae'
OWNER = 'vectorflow_mta_owner'


def migration_pins():
    path = Path(__file__).parent / 'migrations' / (MIGRATION_NAME + '.py')
    return [[MIGRATION_NAME, hashlib.sha256(path.read_bytes()).hexdigest()]]


def catalogue_delta(*, bootstrap=False):
    migration = import_module('mta.runtime.migrations.' + MIGRATION_NAME)
    name = 'mta.guard_scope_transit_generation()'
    before = dict(name=name, owner=OWNER, security_definer=False,
        body=migration.body(migration.prior.SQL), configuration=['search_path=pg_catalog, mta'],
        language='plpgsql', returns='trigger')
    result = {'functions:' + name: dict(before=before,
        after=dict(before, body=migration.body(migration.SQL)))}
    if bootstrap:
        from mta.runtime import scoped_action_transition as original
        roles = {original.OWNER: OWNER, original.RUNTIME: 'vectorflow_mta_runtime'}
        def mapped(value):
            if isinstance(value, dict):return {mapped(k): mapped(v) for k,v in value.items()}
            if isinstance(value, list):return [mapped(v) for v in value]
            if isinstance(value, str):
                if value in roles:return roles[value]
                if value.startswith('grants:'):
                    return ':'.join(roles.get(part,part) for part in value.split(':'))
            return value
        result.update(mapped({key:value for key,value in original.catalogue_delta(bootstrap=True).items()
                              if 'ingestion_schema_compatibility' in key}))
    return result


def require_specification(spec):
    previous = spec['previous_release']
    if (spec['migration_pins'] != migration_pins()
            or previous['source_commit'] != PREVIOUS_COMMIT
            or previous['manifest_sha256'] != PREVIOUS_RELEASE
            or spec['catalogue_delta'] not in [catalogue_delta(bootstrap=v) for v in (False,True)]):
        raise ValueError('Exact native transit-owner schema correction required')


def approved_receipt(value):
    return (value.get('migration_pins') == migration_pins()
        and value.get('previous_release') == PREVIOUS_RELEASE
        and value.get('catalogue_delta_digest') in {digest(catalogue_delta(bootstrap=v)) for v in (False,True)})


def require_start(cursor):
    from mta.runtime.ingestion_ownership import migration_history_guard
    migration = import_module('mta.runtime.migrations.' + MIGRATION_NAME)
    cursor.execute("SELECT max(name) FROM mta.django_migrations WHERE app='fresh_mta'")
    if cursor.fetchone() != ('0240_framework_metadata_writer_guards',):
        raise ValueError('Transit-owner correction requires exact0240 start')
    cursor.execute("SELECT prosrc,prosecdef,proconfig,pg_get_userbyid(proowner) FROM pg_proc "
                   "WHERE oid='mta.guard_scope_transit_generation()'::regprocedure")
    if cursor.fetchone() != (migration.body(migration.prior.SQL), False,
                            ['search_path=pg_catalog, mta'], OWNER):
        raise ValueError('Exact original transit guard ownership required')
    if not migration_history_guard(cursor):
        raise ValueError('Transit-owner correction requires original migration history guard')
    cursor.execute("SELECT EXISTS(SELECT 1 FROM mta.fresh_mta_runscopeattempt WHERE status='ACTIVE')")
    if cursor.fetchone() != (False,):
        raise ValueError('Transit-owner correction refuses an active scoped worker')


def preservation(cursor, original):
    """Hash every typed row; exclude only the new history/authority appends."""
    from django.db import connection
    from psycopg import sql
    if not connection.in_atomic_block:
        raise ValueError('Typed preservation requires its maintenance transaction')
    cursor.execute('SHOW transaction_isolation')
    if cursor.fetchone() != ('repeatable read',):
        raise ValueError('Typed preservation requires repeatable-read isolation')
    cursor.execute("SELECT N.nspname,C.relname,ARRAY(SELECT A.attname FROM pg_index I "
        "CROSS JOIN LATERAL unnest(I.indkey) WITH ORDINALITY K(attnum,ordinal) "
        "JOIN pg_attribute A ON A.attrelid=C.oid AND A.attnum=K.attnum "
        "WHERE I.indrelid=C.oid AND I.indisprimary AND I.indisvalid ORDER BY K.ordinal) "
        "FROM pg_class C JOIN pg_namespace N ON N.oid=C.relnamespace "
        "WHERE N.nspname IN ('mta','mta_state','mta_opening') AND C.relkind IN ('r','p','f') "
        "ORDER BY N.nspname,C.relname")
    tables = cursor.fetchall()
    result = []
    for schema, table, keys in tables:
        if (schema, table) == ('mta', 'fresh_mta_ingestionreleasecompatibility'):
            continue
        if not keys or len(set(keys)) != len(keys):
            raise ValueError('Every preserved typed table requires its declared primary key')
        where = (sql.SQL(' WHERE NOT (app={} AND name={})').format(
            sql.Literal('fresh_mta'), sql.Literal(MIGRATION_NAME))
            if (schema, table) == ('mta', 'django_migrations') else sql.SQL(''))
        checksum = hashlib.sha256()
        statement = sql.SQL('COPY (SELECT * FROM {}{} ORDER BY {}) TO STDOUT (FORMAT BINARY)').format(
            sql.Identifier(schema, table), where, sql.SQL(',').join(map(sql.Identifier, keys)))
        with cursor.copy(statement) as stream:
            for block in stream:checksum.update(block)
        result.append(dict(schema=schema, table=table, primary_key=keys,
                           binary_sha256=checksum.hexdigest()))
    if not result:raise ValueError('Preserved typed-table roster cannot be empty')
    return dict(original=original, typed_tables=result)
