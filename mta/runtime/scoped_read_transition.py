"""Exact226->228 transition for the approved three-day UptoDBM test.

The portable catalogue delta was exercised under PostgreSQL rollback before
release admission. New helper OIDs are allocated at application time: the
registrar records their actual security digest, and ordinary admission compares
that digest to the live catalogue. No old identity, role or ACL is replaced.
"""
from importlib import import_module
from mta.serialization import digest

INITIALIZATION='dcfa9a34-18d1-4b00-b1a6-973fade774b2'
PREVIOUS_COMMIT='fbb8abcc1ec0b3fe5177c028504ff20cc992f798'
PREVIOUS_RELEASE='4617b6c20db13fabbabe1d5e9f6157782e6e1afaa5bd0e142f0196d07f4e8d22'
BEFORE_SCHEMA='17212aa7d67ca1207a76f9d9830dccc7b653a08c660d020a06a2fa781cc537cb'
BEFORE_GUARD='9fd89a6e4c2dae0d118073c3e19118f761953e124bca57921565930156477ae0'
AFTER_SCHEMA='f04db0790784f0c1eb668da8de2c31ad7b7a1fcf487b436796a818f3751fe978'
DELTA='5cfa575eb7f1bd220514678a131532cd1c04529f171a419e496b6a9401083a07'
PINS=(
    ('0227_scope_read_action_reference','f772f40e9cdc3093ec91cd1e8ff93ddb79132076d53b086143e049247506f70b'),
    ('0228_scope_read_action_ownership','7a667cbc866d9e998f34248acd90c565443443145a421cc2ced81fbca5fc0956'))
EXECUTE=('mta.scope_read_action_revision(uuid)',
    'mta.scope_remark_parent_owner(uuid,bigint,bigint)')


def migration_pins():return [list(pin) for pin in PINS]


def require_specification(spec):
    if (spec['initialization_id']!=INITIALIZATION or spec['migration_pins']!=migration_pins()
            or spec['previous_release']['source_commit']!=PREVIOUS_COMMIT
            or spec['previous_release']['manifest_sha256']!=PREVIOUS_RELEASE
            or digest(spec['catalogue_delta'])!=DELTA):
        raise ValueError('Exact approved live-reference schema transition required')


def approved_receipt(value):
    return all(value.get(key)==expected for key,expected in dict(
        initialization_id=INITIALIZATION,migration_pins=migration_pins(),previous_release=PREVIOUS_RELEASE,
        before_schema_digest=BEFORE_SCHEMA,before_guard_digest=BEFORE_GUARD,
        schema_digest=AFTER_SCHEMA,catalogue_delta_digest=DELTA).items())


def upgrade_application_guard(cursor):
    """Preserve registrar ownership/ACL while installing the exact228 branch."""
    from mta.mdm.owned_namespace import APPLICATION_WRITE_GUARD_BODY
    from mta.runtime.scoped_action_ownership import application_guard_body
    from mta.runtime.ingestion_authority import _provisioner
    _provisioner(cursor)
    old=application_guard_body(APPLICATION_WRITE_GUARD_BODY,
        frozen=import_module('mta.runtime.migrations.0226_scoped_dbm_action_dependencies'))
    new=application_guard_body(APPLICATION_WRITE_GUARD_BODY,
        frozen=import_module('mta.runtime.migrations.0228_scope_read_action_ownership'))
    cursor.execute("SELECT P.prosrc,P.proconfig,P.prosecdef,pg_get_userbyid(P.proowner),"
        "L.lanname,pg_get_function_result(P.oid),P.proacl::text FROM pg_proc P "
        "JOIN pg_language L ON L.oid=P.prolang WHERE P.oid='fresh_control.guard_application_write()'::regprocedure")
    row=cursor.fetchone()
    if row is None or row[:6]!=(old,None,False,'fresh_namespace_registrar','plpgsql','trigger'):
        raise ValueError('Exact226 registrar application guard required')
    cursor.execute('SET LOCAL ROLE fresh_namespace_registrar')
    cursor.execute('CREATE OR REPLACE FUNCTION fresh_control.guard_application_write() RETURNS trigger '
        'LANGUAGE plpgsql AS $body$'+new+'$body$')
    cursor.execute('RESET ROLE')
    cursor.execute("SELECT proacl::text FROM pg_proc WHERE oid='fresh_control.guard_application_write()'::regprocedure")
    if cursor.fetchone()!=(row[6],):raise ValueError('Registrar guard ACL changed')
