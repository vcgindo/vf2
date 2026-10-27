"""Finite consumed0237 ->0238 read-guard correction; original rows stay sealed.

Only the existing owned test roles and the reviewed18b9 predecessor are admitted.
This profile does not replay a producer or extend the unused0232 upgrade.
"""
import hashlib
from importlib import import_module
from pathlib import Path

from mta.serialization import digest

MIGRATION_NAME = '0238_registered_read_action_cut'
PREVIOUS_COMMIT = '18b9da4d5b1333d6f8409884e452bf12a7b0258f'
PREVIOUS_RELEASE = '3b14786e5e2ebbcd0d73c3cd954e6a8c67691f71725ddab0f11819fb7b599357'
OWNER = 'vftest_g2n_20261024_owner'
RUNTIME = 'vftest_g2n_20261024_runtime'
SCHEMAS = ('mta', 'mta_state', 'mta_opening')
# These are the only appended mta tables. Compatibility rows are separately
# checked by authority_history. Migration history below excludes ONLY the new
# approved row, preserving the complete older history including timestamps.


def migration_pins():
    path = Path(__file__).parent / 'migrations' / (MIGRATION_NAME + '.py')
    return [[MIGRATION_NAME, hashlib.sha256(path.read_bytes()).hexdigest()]]


def catalogue_delta(*, bootstrap=False):
    frozen = import_module('mta.runtime.migrations.' + MIGRATION_NAME)
    name = 'mta.guard_scope_read_reference()'
    before = dict(name=name, owner=OWNER, security_definer=False, body=frozen.OLD,
        configuration=['search_path=pg_catalog, mta'], language='plpgsql', returns='trigger')
    result = {'functions:' + name: dict(before=before, after=dict(before, body=frozen.BODY))}
    if bootstrap:
        # Reuse exactly the already-declared registrar bootstrap, not that
        # profile's unrelated action predicate or its predecessor authority.
        from mta.runtime.scoped_action_transition import catalogue_delta as original_delta
        result.update({key:value for key,value in original_delta(bootstrap=True).items()
                       if 'ingestion_schema_compatibility' in key})
    return result


def require_specification(spec):
    previous = spec['previous_release']
    if (spec['migration_pins'] != migration_pins()
            or previous['source_commit'] != PREVIOUS_COMMIT
            or previous['manifest_sha256'] != PREVIOUS_RELEASE
            or spec['catalogue_delta'] not in [catalogue_delta(bootstrap=value) for value in (False, True)]):
        raise ValueError('Exact consumed0237 registered-read correction required')


def approved_receipt(value):
    return (value.get('migration_pins') == migration_pins()
        and value.get('previous_release') == PREVIOUS_RELEASE
        and value.get('catalogue_delta_digest') in
            {digest(catalogue_delta(bootstrap=bootstrap)) for bootstrap in (False, True)})


def require_start(cursor):
    from mta.runtime.ingestion_ownership import migration_history_guard
    cursor.execute("SELECT max(name) FROM mta.django_migrations WHERE app='fresh_mta'")
    if cursor.fetchone() != ('0237_intake_diagnostic_guards',):
        raise ValueError('Registered-read correction requires exact0237 start')
    guards = import_module('mta.runtime.migrations.0235_registered_scope_read_attachment')
    watch = import_module('mta.runtime.migrations.0237_intake_diagnostic_guards')
    for name, body, definer in (('mta.guard_scope_read_reference()', guards.BODY, False),
                               ('mta.ingestion_watch()', watch.NEW, True)):
        cursor.execute('SELECT prosrc,prosecdef,proconfig,pg_get_userbyid(proowner) '
                       'FROM pg_proc WHERE oid=to_regprocedure(%s)', [name])
        if cursor.fetchone() != (body, definer, ['search_path=pg_catalog, mta'], OWNER):
            raise ValueError('Exact original0237 registered-read ownership required')
    if not migration_history_guard(cursor):
        raise ValueError('Registered-read correction requires original migration history guard')
    cursor.execute("SELECT EXISTS(SELECT 1 FROM mta.fresh_mta_runscopeattempt WHERE status='ACTIVE')")
    if cursor.fetchone() != (False,):
        raise ValueError('Registered-read correction refuses an active scoped worker')


def preservation(cursor, original):
    """Stream every typed table, including JSON/MDM runs and pending failures.

Binary COPY preserves database types, NULLs and duplicate ordinal rows without
materializing calculation graphs. A declared primary key supplies stable order;
an unkeyed/foreign/unexpected relation fails closed rather than being omitted.
The same repeatable-read maintenance transaction owns both observations.
"""
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
        "WHERE N.nspname=ANY(%s) AND C.relkind IN ('r','p','f') ORDER BY N.nspname,C.relname",
        [list(SCHEMAS)])
    tables = cursor.fetchall()
    if not tables or len({(schema,table) for schema,table,_keys in tables}) != len(tables):
        raise ValueError('Complete unambiguous typed-table roster required')
    result=[]
    for schema,table,keys in tables:
        if (schema,table) == ('mta','fresh_mta_ingestionreleasecompatibility'):
            continue
        if schema not in SCHEMAS or not keys or len(set(keys)) != len(keys):
            raise ValueError('Every preserved typed table requires its declared primary key')
        identifier=sql.Identifier(schema,table)
        where=(sql.SQL(' WHERE NOT (app={} AND name={})').format(
            sql.Literal('fresh_mta'),sql.Literal(MIGRATION_NAME))
            if (schema,table)==('mta','django_migrations') else sql.SQL(''))
        cursor.execute(sql.SQL('SELECT count(*) FROM {}{}').format(identifier,where))
        count=cursor.fetchone()[0]
        checksum=hashlib.sha256()
        statement=sql.SQL('COPY (SELECT * FROM {}{} ORDER BY {}) TO STDOUT (FORMAT BINARY)').format(
            identifier,where,sql.SQL(',').join(sql.Identifier(key) for key in keys))
        with cursor.copy(statement) as stream:
            for block in stream:
                checksum.update(block)
        result.append(dict(schema=schema,table=table,primary_key=list(keys),rows=count,
                           binary_sha256=checksum.hexdigest()))
    if not result:
        raise ValueError('Preserved typed-table roster cannot be empty')
    return dict(original=original,typed_tables=result)
