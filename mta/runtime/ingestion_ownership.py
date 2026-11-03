"""Ownership catalogue for revision guards, independent of business algorithms.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
from mta.runtime.ingestion_context import DataOwner
from mta.presentation.request_scope import once_per_request

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
    revised=import_module('mta.runtime.migrations.0157_report_revision_ownership').current_body()
    references=import_module('mta.runtime.migrations.0159_report_reference_ownership').current_body()
    consumers=import_module('mta.runtime.migrations.0160_report_consumer_source_ownership').current_body()
    trends=import_module('mta.runtime.migrations.0162_derived_trend_ownership').current_body()
    owner_sets=import_module('mta.runtime.migrations.0168_report_guard_owner_sets').NEW_INGESTION
    scope_files=import_module('mta.runtime.migrations.0195_scope_pick_revision_ownership').NEW
    scope_capture=import_module('mta.runtime.migrations.0196_scope_pick_capture_key').NEW
    scope_reports=import_module('mta.runtime.migrations.0198_scope_report_guards').NEW
    scope_sources=import_module('mta.runtime.migrations.0200_scope_source_guards').NEW
    scope_planning=import_module('mta.runtime.migrations.0202_scope_planning_guards').NEW
    scope_consumers=import_module('mta.runtime.migrations.0204_scoped_bpr_consumer_ownership').NEW
    scope_transit=import_module('mta.runtime.migrations.0207_scope_transit_guards').NEW
    scope_git=import_module('mta.runtime.migrations.0210_scope_git_guards').NEW
    scope_pick_view=import_module('mta.runtime.migrations.0212_scope_pick_guards').NEW
    scope_expedite=import_module('mta.runtime.migrations.0214_scope_expedite_guards').NEW
    scope_expedite_parent=import_module('mta.runtime.migrations.0216_scope_expedite_parent_guards').NEW
    scope_read=import_module('mta.runtime.migrations.0218_scope_read_reference_guards').NEW
    bpr_history=import_module('mta.runtime.migrations.0223_bpr_history_completion').NEW
    scope_live_read=import_module('mta.runtime.migrations.0228_scope_read_action_ownership').NEW
    runtime_reports=import_module('mta.runtime.migrations.0230_runtime_report_publication_guards').NEW
    placement_reports=import_module('mta.runtime.migrations.0231_runtime_report_placement_guards').NEW
    registered_reports=import_module('mta.runtime.migrations.0234_report_definition_guards').NEW
    intake_diagnostics=import_module('mta.runtime.migrations.0237_intake_diagnostic_guards').NEW
    btr_scope_dimensions=import_module('mta.runtime.migrations.0246_btr_scope_dimension_ingestion_ownership').NEW
    rationing_anchor=import_module('mta.runtime.migrations.0254_rationing_anchor_revision_ownership').NEW
    dated_anchor=import_module('mta.runtime.migrations.0268_dated_history_anchor_revision').NEW
    bpr_anchor=import_module('mta.runtime.migrations.0270_bpr_history_storage').NEW
    closure_anchor=import_module('mta.runtime.migrations.0272_order_closure_history_storage').NEW
    remark_anchor=import_module('mta.runtime.migrations.0274_complete_remark_history_storage').NEW
    return (function['name'] == 'mta.ingestion_watch()' and function['security_definer'] is True
        and function['body'] in (body,revised,references,consumers,trends,owner_sets,scope_files,scope_capture,scope_reports,scope_sources,scope_planning,scope_consumers,scope_transit,scope_git,scope_pick_view,scope_expedite,scope_expedite_parent,scope_read,bpr_history,scope_live_read,runtime_reports,placement_reports,registered_reports,intake_diagnostics,btr_scope_dimensions,rationing_anchor,dated_anchor,bpr_anchor,closure_anchor,remark_anchor) and function['configuration'] == ['search_path=pg_catalog, mta']
        and function['returns'] == 'trigger')


def scoped_derived_body(cursor,*,minimum):
    """Exact applied scoped-watch version, separate from producer recipes."""
    from importlib import import_module
    versions=('0274_complete_remark_history_storage','0272_order_closure_history_storage','0270_bpr_history_storage','0268_dated_history_anchor_revision','0254_rationing_anchor_revision_ownership','0246_btr_scope_dimension_ingestion_ownership','0237_intake_diagnostic_guards','0234_report_definition_guards','0231_runtime_report_placement_guards','0230_runtime_report_publication_guards','0228_scope_read_action_ownership','0223_bpr_history_completion','0218_scope_read_reference_guards','0216_scope_expedite_parent_guards','0214_scope_expedite_guards','0212_scope_pick_guards','0210_scope_git_guards','0207_scope_transit_guards','0204_scoped_bpr_consumer_ownership','0202_scope_planning_guards','0200_scope_source_guards','0198_scope_report_guards','0196_scope_pick_capture_key')
    if minimum not in versions:raise ValueError('Unknown scoped derived guard minimum')
    cursor.execute("SELECT name FROM mta.django_migrations WHERE app='fresh_mta' AND name=ANY(%s)",[list(versions)])
    installed={name for name, in cursor.fetchall()}
    if minimum not in installed:raise ValueError('Required scoped derived guard migration missing')
    return import_module('mta.runtime.migrations.'+next(name for name in versions if name in installed)).NEW


def domain(schema, table):
    if schema not in SCHEMAS:
        raise ValueError('Outside the ingestion database boundary')
    if schema == 'mta_opening' or table in IMMUTABLE:
        return 'immutable'
    if table in METADATA:
        return 'authority'
    if table in MASTER:
        return 'mixed' if table in ('fresh_mta_mdmskuloccurrent', 'fresh_mta_mdmskulocmasterpair') else DataOwner.MASTER.value
    if table in FACT or schema == 'mta_state' and table.startswith(('input_', 'batch_')):
        return DataOwner.FACT.value
    if table in CONFIGURATION or any(part in table for part in ('configuration', 'setting')):
        return DataOwner.CONFIGURATION.value
    # These are immutable terminal occurrences, not the similarly named live
    # request/action owners. Keep that distinction ahead of substring rules.
    if schema == 'mta_state' and table in (
            'history_complete_bpr_bprreport_remarkdetails',
            'history_complete_bpr_openexpeditrequestremarkshistory',
            'history_complete_bpr_intransitwhereaboutsremarks'):
        return DataOwner.OPERATIONAL.value
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
    from mta.presentation.request_scope import in_read_request, in_validation_reads
    database = getattr(cursor, 'db', None)
    physical = getattr(database, 'connection', None)
    if (in_read_request() or in_validation_reads()) and physical is not None and not physical.closed:
        return _request_guard_coverage(database, physical)
    from mta.presentation.request_scope import metadata_guard_check
    return metadata_guard_check(_verify_guard_coverage, cursor)


@once_per_request
def _request_guard_coverage(database, physical):
    # The physical connection is part of the key. Reopening an alias or using
    # another database cannot inherit this request's successful verification.
    with database.cursor() as cursor:
        return _verify_guard_coverage(cursor)


def _verify_guard_coverage(cursor):
    from mta.runtime.accepted_state_ownership import verify_guards
    verify_guards(cursor, required=False)
    from mta.runtime import scoped_action_ownership
    scoped_action_ownership.available(cursor)
    expected = {(s, t): owner for s, t, owner in tables(cursor) if owner != 'authority'}
    if migration_history_guard(cursor):
        expected.pop(('mta','django_migrations'))
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


def migration_history_guard(cursor):
    """Qualify only the exact additive metadata guard; old watches stay strict."""
    cursor.execute("SELECT t.tgname,t.tgenabled,t.tgtype,t.tgnargs,t.tgqual::text,"
        "n.nspname,p.proname,p.prosrc,p.prosecdef,p.proconfig,p.proowner=c.relowner "
        "FROM pg_trigger t JOIN pg_proc p ON p.oid=t.tgfoid JOIN pg_namespace n ON n.oid=p.pronamespace "
        "JOIN pg_class c ON c.oid=t.tgrelid WHERE t.tgrelid=to_regclass('mta.django_migrations') "
        "AND t.tgname IN ('migration_history_append','migration_history_immutable') ORDER BY t.tgname")
    rows=cursor.fetchall()
    if not rows:return False
    from importlib import import_module
    body=import_module('mta.runtime.migrations.0164_migration_history_ownership').BODY
    expected=[('migration_history_append','O',7,0,None),('migration_history_immutable','O',58,0,None)]
    if (len(rows)!=2 or [r[:5] for r in rows]!=expected
            or any(r[5:]!=('mta','guard_migration_history',body,False,['search_path=pg_catalog, mta'],True) for r in rows)):
        raise ValueError('Migration history authority guard differs')
    return True


def business_trigger_rows(cursor, rows):
    """Separate only independently verified ingestion watches from old guards.

    Existing report guards still require their exact roster and SQL bodies.
    An extra/disabled/rebound watch is an error, never ignored by its prefix.
    """
    from mta.runtime.accepted_state_ownership import business_trigger_rows as accepted_rows
    rows = accepted_rows(cursor, rows)
    if not any(row[0].startswith('ingestion_watch_') for row in rows):
        return rows
    require_guard_coverage(cursor)
    cursor.execute("SELECT p.prosrc,p.prosecdef,p.proconfig,pg_get_function_result(p.oid) "
        "FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace "
        "WHERE n.nspname='mta' AND p.proname='ingestion_watch' AND p.pronargs=0")
    observed=cursor.fetchall()
    if len(observed)!=1 or not is_revision_guard(dict(name='mta.ingestion_watch()',
            body=observed[0][0],security_definer=observed[0][1],
            configuration=observed[0][2],returns=observed[0][3])):
        raise ValueError('Ingestion watch function contract differs')
    return [row for row in rows if not row[0].startswith('ingestion_watch_')]
