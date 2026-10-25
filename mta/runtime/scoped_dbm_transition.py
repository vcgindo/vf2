"""Exact223->226 reader/action upgrade for the retained owned TEST namespace."""
from importlib import import_module
from mta.serialization import digest

INITIALIZATION='ed6ce944-372d-4038-aec4-89f91131648c'
PREVIOUS_COMMIT='a9b1c053f9988319f9aba8085978be8dd2479efa'
PREVIOUS_RELEASE='08dae80dde4ed37b035a9598f18853b055478ad503f7a4d795c0ca3e909f065c'
BEFORE_SCHEMA='e6b2e1d9a1b795970204a9f598561e0e712242923ff28559433027e3d94b4e38'
BEFORE_GUARD='82b04b126194d8bd433a323b9617ab1cabc39b02317702be396490b3df2eea29'
AFTER_SCHEMA='609f4e53e6839ccd26fe4c80d56538f169e220894952ebd7d973900f5a3ae912'
AFTER_GUARD='e2ac1e01f5dadd40b555cb5ab6965206953cd101dc4d87b9f9e965a328f829f2'
DELTA='78bde289a2c901a8f673f72174653a87d0696ac631a366f7e8d4333e4bc6ab1a'
PINS=(
    ('0224_uptodbm_bpr_read_configuration','4d875e1e9e2eee8ee7e908af59c5c51377bd30e41e4053c8459330b5fc238565'),
    ('0225_scope_read_configuration_alias','975cab9302d1ef24e2d700c46b1dbfacce6938d317a3a36e78c323fb25df317d'),
    ('0226_scoped_dbm_action_dependencies','558d01314a00a536ce4ba938e205354f22a940321ffdbbfb620f9eb31d4e5423'))
FUNCTIONS=frozenset(('functions:fresh_control.guard_application_write()',
    'functions:mta.guard_scope_read_reference()','functions:mta.guard_scoped_action_cache()',
    'functions:mta.guard_scoped_remark_cache_writer()',
    'functions:mta.scope_cache_command(reference uuid, actor text)'))


def migration_pins():return [list(pin) for pin in PINS]


def require_specification(spec):
    if (spec['initialization_id']!=INITIALIZATION or spec['migration_pins']!=migration_pins()
            or spec['previous_release']['source_commit']!=PREVIOUS_COMMIT
            or spec['previous_release']['manifest_sha256']!=PREVIOUS_RELEASE
            or set(spec['catalogue_delta'])!=FUNCTIONS or digest(spec['catalogue_delta'])!=DELTA):
        raise ValueError('Exact owned UptoDBM reader/action schema transition required')


def approved_receipt(value):
    return all(value.get(key)==expected for key,expected in dict(initialization_id=INITIALIZATION,
        migration_pins=migration_pins(),previous_release=PREVIOUS_RELEASE,
        before_schema_digest=BEFORE_SCHEMA,before_guard_digest=BEFORE_GUARD,
        schema_digest=AFTER_SCHEMA,guard_digest=AFTER_GUARD,catalogue_delta_digest=DELTA).items())


def upgrade_application_guard(cursor):
    """Registrar changes its own exact body; keep function identity/ACL intact."""
    from mta.mdm.owned_namespace import APPLICATION_WRITE_GUARD_BODY
    from mta.runtime.scoped_action_ownership import application_guard_body
    from mta.runtime.ingestion_authority import _provisioner
    _provisioner(cursor)
    old=application_guard_body(APPLICATION_WRITE_GUARD_BODY,
        frozen=import_module('mta.runtime.migrations.0221_scoped_action_cache_writer'))
    new=application_guard_body(APPLICATION_WRITE_GUARD_BODY)
    cursor.execute("SELECT P.prosrc,P.proconfig,P.prosecdef,pg_get_userbyid(P.proowner),"
        "L.lanname,pg_get_function_result(P.oid),P.proacl::text FROM pg_proc P "
        "JOIN pg_language L ON L.oid=P.prolang WHERE P.oid='fresh_control.guard_application_write()'::regprocedure")
    row=cursor.fetchone()
    if row is None or row[:6]!=(old,None,False,'fresh_namespace_registrar','plpgsql','trigger'):
        raise ValueError('Exact prior registrar application guard required')
    cursor.execute('SET LOCAL ROLE fresh_namespace_registrar')
    cursor.execute('CREATE OR REPLACE FUNCTION fresh_control.guard_application_write() RETURNS trigger '
        'LANGUAGE plpgsql AS $body$'+new+'$body$')
    cursor.execute('RESET ROLE')
    cursor.execute("SELECT proacl::text FROM pg_proc WHERE oid='fresh_control.guard_application_write()'::regprocedure")
    if cursor.fetchone()!=(row[6],):raise ValueError('Registrar guard ACL changed')
