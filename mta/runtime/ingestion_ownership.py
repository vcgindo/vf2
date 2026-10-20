"""Ownership catalogue for revision guards, independent of business algorithms.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
from mta.runtime.ingestion_context import DataOwner

METADATA = frozenset(('fresh_mta_initializationcertification',
    'fresh_mta_masterinputrevision', 'fresh_mta_ingestionreleasecompatibility',
    'fresh_mta_ingestionrevisionstate'))
IMMUTABLE = frozenset(('fresh_mta_productioninitialization', 'fresh_mta_mdmsource',
    'fresh_mta_mdmfamilysource', 'fresh_mta_mdmsourceintegration'))
MASTER = frozenset('fresh_mta_' + name for name in (
    'mdmskuattributes', 'mdmskudescription', 'mdmlocationattributes',
    'mdmlocationdescription', 'mdmskulocpair', 'mdmskulocmasterpair',
    'mdmskuloccurrent', 'mdmskuuse', 'mdmlocationuse'))
FACT = frozenset(('fresh_mta_dailyfeedattempt', 'fresh_mta_mdmdailyinputcapture',
    'fresh_mta_mdmdailyinputoccurrence', 'fresh_mta_mdmdailypairexclusion',
    'fresh_mta_mdmdailyinputtask', 'fresh_mta_mdmdailyinputhistory',
    'fresh_mta_mdmdailyskuarchive', 'fresh_mta_mdmdailylocationarchive',
    'fresh_mta_mdmdailyskulocaddarchive', 'fresh_mta_mdmdailyskulocmodifyarchive',
    'fresh_mta_mdmdailyskulocremovearchive'))
CONFIGURATION = frozenset('fresh_mta_'+name for name in (
    'mdmsupplierconfiguration', 'mdmsobraw', 'mdmmoqraw1', 'mdmmoqraw2',
    'mdmpairexclusionsource', 'mdmpairexclusion', 'mdmseasoneligibility'))
ACTION = frozenset('fresh_mta_'+name for name in (
    'mdmskuapproved', 'mdmlocationapproved', 'mdmskulocaddapproved',
    'mdmskulocmodifyapproved', 'mdmskulocremoveapproved', 'mdmsobapproved',
    'mdmmoqwithdestinationapproved', 'mdmmoqwithoutdestinationapproved',
    'mdmskuhistory', 'mdmlocationhistory', 'mdmskulochistory', 'mdmsobhistory',
    'mdmmoqhistory', 'mdmforcehistory', 'mdmseasonhistory', 'mdmseasonstatushistory',
    'mdmstoppipohistory', 'mdmphaseouthistory', 'mdmphaseinnormhistory',
    'mdmskuuploadlog', 'mdmlocationuploadlog', 'mdmskulocadduploadlog',
    'mdmskulocmodifyuploadlog', 'mdmskulocremoveuploadlog', 'mdmsobuploadlog',
    'mdmmoquploadlog', 'mdmforceuploadlog'))
SCHEMAS = ('mta', 'mta_state', 'mta_opening')
GUARD_VERSION = 'ingestion-revision-guards-v1'


def is_revision_guard(function):
    """The sole admitted definer is this frozen, fixed-search-path trigger.

    No general definer permission is introduced. Applied migrations, rather than
    mutable database metadata, define the expected function body.
    """
    from importlib import import_module
    frozen = import_module('mta.runtime.migrations.0145_ingestion_revision_guards').SQL
    body = frozen.split('CREATE FUNCTION mta.ingestion_watch()', 1)[1].split('AS $$', 1)[1].split('$$;', 1)[0]
    body = body.replace('UPDATE mta.fresh_mta_initializationcertification SET',
        'UPDATE mta.fresh_mta_ingestionrevisionstate SET')
    body = body.replace("WHERE status='CERTIFIED';", "WHERE initialization_id IN "
        "(SELECT initialization_id FROM mta.fresh_mta_initializationcertification WHERE status='CERTIFIED');")
    return (function['name'] == 'mta.ingestion_watch()' and function['security_definer'] is True
        and function['body'] == body and function['configuration'] == ['search_path=pg_catalog, mta']
        and function['returns'] == 'trigger')


def domain(schema, table):
    if schema not in SCHEMAS:
        raise ValueError('Outside the ingestion database boundary')
    if schema == 'mta_opening' or table in IMMUTABLE:
        return 'immutable'
    if table in METADATA:
        return 'authority'
    if table in MASTER:
        return 'mixed' if table in ('fresh_mta_mdmskuloccurrent', 'fresh_mta_mdmskulocmasterpair') else DataOwner.MASTER.value
    if table in FACT or schema == 'mta_state' and table.startswith('input_'):
        return DataOwner.FACT.value
    if table in CONFIGURATION or any(part in table for part in ('configuration', 'setting')):
        return DataOwner.CONFIGURATION.value
    if table in ACTION or any(part in table for part in ('draft', 'request', 'task', 'queue', 'liveremark', 'annotation')):
        return DataOwner.ACTION.value
    # All other existing typed histories, results and owner/projection receipts
    # are operating state. New tables cannot enter silently: guard coverage
    # checks reject any table not installed by a declared migration.
    return DataOwner.OPERATIONAL.value


def tables(cursor):
    cursor.execute("SELECT n.nspname,c.relname FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
        "WHERE n.nspname=ANY(%s) AND c.relkind IN ('r','p') ORDER BY 1,2", [list(SCHEMAS)])
    return [(s, t, domain(s, t)) for s, t in cursor.fetchall()]


def require_guard_coverage(cursor):
    expected = {(s, t): owner for s, t, owner in tables(cursor) if owner != 'authority'}
    cursor.execute("SELECT n.nspname,c.relname,t.tgname,t.tgenabled,"
        "pn.nspname,p.proname,encode(t.tgargs,'escape'),t.tgtype,t.tgnargs,t.tgqual::text,"
        "t.tgattr::text,t.tgoldtable,t.tgnewtable "
        "FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid "
        "JOIN pg_namespace n ON n.oid=c.relnamespace JOIN pg_proc p ON p.oid=t.tgfoid "
        "JOIN pg_namespace pn ON pn.oid=p.pronamespace "
        "WHERE n.nspname=ANY(%s) AND t.tgname LIKE 'ingestion_watch_%%'", [list(SCHEMAS)])
    actual = {}
    specs = {'insert': (4,None,'new_rows'), 'update': (16,'old_rows','new_rows'),
             'delete': (8,'old_rows',None), 'truncate': (32,None,None)}
    for schema, table, trigger, enabled, fn_schema, function, args, kind, nargs, qual, attr, old, new in cursor.fetchall():
        if enabled != 'O' or fn_schema != 'mta' or function != 'ingestion_watch':
            raise ValueError('Ingestion revision guard disabled or replaced')
        if (specs.get(trigger.removeprefix('ingestion_watch_')) != (kind,old,new)
                or nargs != 1 or qual is not None or attr != ''):
            raise ValueError('Ingestion revision trigger statement/transition contract differs')
        actual.setdefault((schema, table), {})[trigger] = args.removesuffix('\\000')
    for table, owner in expected.items():
        if actual.get(table) != {'ingestion_watch_' + op: owner for op in ('insert', 'update', 'delete', 'truncate')}:
            raise ValueError('Missing or incorrectly classified ingestion writer: ' + '.'.join(table))
    if set(actual) != set(expected):
        raise ValueError('Unexpected ingestion revision participant')
