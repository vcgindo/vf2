"""Reuse a schema digest, never an admission decision or mutable readiness.

The ticket is captured before readiness opens its read-only snapshot. Live WAL
bracketing prevents a snapshot-old catalogue stamp from hiding newer DDL seen
by PostgreSQL's deparser caches. Any intervening write takes the original path.
"""
from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps
import os
import threading

from django.db import DatabaseError, connections, DEFAULT_DB_ALIAS

_active = ContextVar('schema_catalogue_ticket', default=None)
_local = threading.local()
_action = ContextVar('action_schema_admission', default=None)

# Include deparser dependencies outside the application's four namespaces.
# Versions of whole catalogues also detect new/deleted objects and restores.
CATALOGUES = (
    'pg_namespace', 'pg_class', 'pg_attribute', 'pg_proc', 'pg_type',
    'pg_attrdef', 'pg_constraint', 'pg_index', 'pg_trigger', 'pg_rewrite',
    'pg_operator', 'pg_collation', 'pg_language', 'pg_am', 'pg_opclass',
    'pg_opfamily', 'pg_amop', 'pg_amproc', 'pg_enum', 'pg_depend',
    'pg_extension', 'pg_cast', 'pg_sequence', 'pg_range', 'pg_database',
    'pg_auth_members', 'pg_ts_config', 'pg_ts_config_map', 'pg_ts_dict',
    'pg_ts_parser', 'pg_ts_template',
    'pg_default_acl', 'pg_policy',
)
VERSION_SQL = ' UNION ALL '.join(
    "SELECT '" + name + "',encode(sha256(convert_to(coalesce("
    "string_agg(ctid::text||':'||xmin::text,',' ORDER BY ctid),''),'UTF8')),'hex') "
    'FROM pg_catalog.' + name for name in CATALOGUES)


def clear():
    _local.owner = None
    _local.entries = {}


def _session(cursor):
    cursor.execute("SELECT pg_current_wal_insert_lsn()::text,current_database(),"
        "(SELECT oid FROM pg_database WHERE datname=current_database()),"
        "session_user,current_user,pg_backend_pid(),pg_postmaster_start_time(),"
        "floor(pg_snapshot_xmax(pg_current_snapshot())::text::numeric/4294967296)::text,"
        "current_setting('transaction_isolation'),current_setting('transaction_read_only')")
    row = cursor.fetchone()
    cursor.execute('SELECT name,setting FROM pg_settings ORDER BY name')
    settings = tuple((name, value) for name, value in cursor.fetchall()
                     if name not in ('transaction_isolation', 'transaction_read_only'))
    return row[0], (tuple(row[1:8]), settings), tuple(row[8:])


def _stock_outputs(cursor):
    # Const deparsing must not invoke user code that could read arbitrary data.
    # Internal symbol dispatch is part of the pinned PostgreSQL binary. A C
    # library, changed symbol/language, shell type or custom function falls back.
    # txid_snapshot_out is PostgreSQL's compatibility alias for pg_snapshot_out.
    cursor.execute("SELECT NOT EXISTS (SELECT 1 FROM pg_type t "
        "LEFT JOIN pg_proc p ON p.oid=t.typoutput "
        "LEFT JOIN pg_namespace n ON n.oid=p.pronamespace "
        "LEFT JOIN pg_language l ON l.oid=p.prolang "
        "WHERE NOT t.typisdefined OR NOT coalesce((p.oid<16384 "
        "AND n.nspname='pg_catalog' AND l.lanname='internal' "
        "AND p.probin IS NULL AND (p.prosrc=p.proname OR "
        "(p.proname='txid_snapshot_out' AND p.prosrc='pg_snapshot_out')) "
        "AND p.proname LIKE '%out' "
        "AND p.prorettype='cstring'::regtype AND p.pronargs=1),false))")
    return cursor.fetchone() == (True,)


def _ticket(database):
    physical = database.connection
    with database.cursor() as cursor:
        wal, session, mode = _session(cursor)
        if mode != ('read committed', 'off') or not _stock_outputs(cursor):
            return None
        cursor.execute(VERSION_SQL)
        versions = tuple(sorted(cursor.fetchall()))
        cursor.execute('SELECT oid,rolname,rolsuper,rolinherit,rolcreaterole,rolcreatedb,'
            'rolcanlogin,rolreplication,rolbypassrls,rolconfig FROM pg_roles ORDER BY oid')
        roles = tuple((tuple(row[:-1]), None if row[-1] is None else tuple(row[-1]))
                      for row in cursor.fetchall())
        cursor.execute('SELECT app,name FROM mta.django_migrations ORDER BY app,name')
        migrations = tuple(cursor.fetchall())
        after, current, current_mode = _session(cursor)
    if (after != wal or current != session or current_mode != mode
            or database.connection is not physical):
        return None
    owner = (os.getpid(), database, physical)
    if getattr(_local, 'owner', None) != owner:
        clear()
        _local.owner = owner
    return dict(database=database, physical=physical, pid=os.getpid(), wal=wal,
                session=session, key=(session, versions, roles, migrations))


@contextmanager
def verification():
    """Only the existing serving readiness wrapper may lend this short ticket."""
    from mta.presentation import admission
    from mta.presentation.request_scope import in_read_request, in_admission_preflight
    database = connections[DEFAULT_DB_ALIAS]
    if (_active.get() is not None or admission._admitted is None
            or not (in_read_request() or in_admission_preflight())
            or database.vendor != 'postgresql' or database.in_atomic_block
            or database.connection is None or database.connection.closed
            or not database.get_autocommit()):
        yield
        return
    try:
        ticket = _ticket(database)
    except DatabaseError:
        # Unsupported WAL functions/recovery modes do not disable admission.
        clear()
        ticket = None
    token = _active.set(ticket)
    try:
        yield
    except Exception:
        clear()
        raise
    finally:
        _active.reset(token)


def _valid(cursor, ticket):
    database = getattr(cursor, 'db', None)
    if (database is not ticket['database'] or database.connection is not ticket['physical']
            or os.getpid() != ticket['pid'] or not database.in_atomic_block
            or database.get_autocommit()):
        return False
    wal, session, mode = _session(cursor)
    return (wal == ticket['wal'] and session == ticket['session']
            and mode == ('repeatable read', 'on'))


def schema_read(function):
    @wraps(function)
    def read(cursor):
        ticket = _active.get()
        if ticket is None:
            return function(cursor)
        try:
            if not _valid(cursor, ticket):
                return function(cursor)
            entries = _local.entries
            key = (function, ticket['key'])
            if key in entries:
                value = entries[key]
                if _valid(cursor, ticket):
                    return value
                return function(cursor)
            value = function(cursor)
            if _valid(cursor, ticket):
                if len(entries) >= 4:
                    entries.clear()
                entries[key] = value
            return value
        except Exception:
            clear()
            raise
    return read


def action_contract(cursor=None):
    """The action's static admission; never a publication or data-read cache."""
    value = _action.get()
    if value is None:
        return None
    database = connections[DEFAULT_DB_ALIAS]
    if (cursor is not None and getattr(cursor, 'db', None) is not database):
        return None
    if (database.connection is not value['physical'] or value['physical'].closed
            or os.getpid() != value['pid'] or not database.in_atomic_block
            or database.atomic_blocks[0] is not value['transaction']):
        raise ValueError('Action schema admission lifetime changed')
    return value


def action_guard(name, cursor=None):
    value = action_contract(cursor)
    return value is not None and name in value['guards']


def action_migrations(cursor):
    value = action_contract(cursor)
    return None if value is None else value['migrations']


def _action_stamp(database):
    # Application DML may advance WAL and planner statistics. Neither changes
    # a guard. Catalogue tuple generations detect replacement/restoration;
    # pg_class uses its structural fields so autoanalyze does not reject a click.
    with database.cursor() as cursor:
        _wal, session, mode = _session(cursor)
        if mode != ('read committed', 'off'):
            raise ValueError('Action admission requires READ COMMITTED writes')
        query = ' UNION ALL '.join(
            "SELECT '" + name + "',encode(sha256(convert_to(coalesce("
            "string_agg(ctid::text||':'||xmin::text,',' ORDER BY ctid),''),'UTF8')),'hex') "
            'FROM pg_catalog.' + name for name in CATALOGUES if name != 'pg_class')
        cursor.execute(query)
        # UNION ALL can use Parallel Append; result order is not contractual.
        versions = tuple(sorted(cursor.fetchall()))
        cursor.execute("SELECT oid,relname,relnamespace,reltype,reloftype,relowner,relam,"
            "relfilenode,reltablespace,relhasindex,relisshared,relpersistence,relkind,relnatts,"
            "relchecks,relhasrules,relhastriggers,relhassubclass,relrowsecurity,relforcerowsecurity,"
            "relispopulated,relreplident,relispartition,relrewrite,relacl::text,reloptions::text,"
            "relpartbound::text FROM pg_class ORDER BY oid")
        relations = tuple(cursor.fetchall())
        cursor.execute('SELECT oid,rolname,rolsuper,rolinherit,rolcreaterole,rolcreatedb,'
            'rolcanlogin,rolreplication,rolbypassrls,rolconfig::text FROM pg_roles ORDER BY oid')
        roles = tuple(cursor.fetchall())
        cursor.execute('SELECT app,name FROM mta.django_migrations ORDER BY app,name')
        migrations = tuple(cursor.fetchall())
        cursor.execute('SELECT ctid::text,xmin::text FROM fresh_control.owned_namespace ORDER BY ctid')
        registration = tuple(cursor.fetchall())
    return session, versions, relations, roles, registration, migrations


@contextmanager
def action_verification(run_id):
    """Admit infrastructure once under the existing action/upgrade locks.

    Every listed verifier runs in full before its result can be shared. Only
    catalogue facts survive derived-row writes; live owner/revision/permission
    and business validation remain with their existing consumers. Nothing is
    retained after this action or exposed to an independently admitted request.
    """
    from django.db import connection
    from mta.runtime.models import CalculationRun, RemarkOwner
    from mta.runtime.scope_execution import _source_lock
    if not connection.in_atomic_block or _action.get() is not None:
        raise ValueError('Action admission requires its own transaction scope')
    # Same key as the normal upgrade's exclusive lock, acquired before source
    # locks to keep the existing maintenance lock order.
    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_advisory_xact_lock_shared(hashtextextended('fresh.production.initialization',0))")
    _source_lock(run_id)
    run = CalculationRun.objects.select_for_update().get(pk=run_id)
    RemarkOwner.objects.select_for_update().get(pk='BPRReport_RemarkDetails')
    database = connections[DEFAULT_DB_ALIAS]
    # PostgreSQL exposes PL/pgSQL GUCs only after loading the language in this
    # backend. The action's triggers necessarily use it. Initialize it before
    # taking the settings stamp; do not ignore later changes to those settings.
    with connection.cursor() as cursor:
        cursor.execute('DO LANGUAGE plpgsql $$ BEGIN NULL; END $$')
    before = _action_stamp(database)
    value = dict(physical=database.connection, transaction=database.atomic_blocks[0],
        pid=os.getpid(), guards=set(), migrations=frozenset(name for app, name in before[-1]
            if app == 'fresh_mta'))
    token = _action.set(value)
    try:
        from mta.runtime import accepted_state_ownership, scoped_action_ownership, scoped_remark_ownership, ingestion_ownership
        from mta.mdm import owned_namespace as owned
        from mta.runtime import input_v3, ingestion_admission, scoped_pick_files, scope_consumers
        from mta.presentation import (scoped_report_storage, scoped_prepared, scoped_planning,
            scoped_transit_storage, scoped_pick_storage, scoped_expedite_storage,
            scoped_expedite_parent, scoped_git, scoped_remarks, scoped_requests, scoped_view)
        with connection.cursor() as cursor:
            # An admitted optional guard is present, not merely skipped because
            # its migration was absent on an older installation.
            accepted_state_ownership.verify_guards(cursor)
            value['guards'].add('accepted')
            scoped_action_ownership.verify_guards(cursor)
            value['guards'].add('action')
            scoped_remark_ownership.verify_guards(cursor)
            value['guards'].add('remark')
            ingestion_ownership.require_guard_coverage(cursor)
            value['guards'].add('ingestion')
            actual = owned._database_identity(cursor)
            registered = owned._registered_identity(cursor)
            evidence = owned._catalogue_evidence(cursor, actual, registered)
            owned._validate_identity(actual, registered, evidence)
            if (actual['current_user_oid'] != registered['consumer_oid']
                    or actual['session_user_oid'] != registered['consumer_oid']):
                raise ValueError('Actions require the registered runtime session')
            value['database'], value['registration'] = actual, registered
            value['namespace_evidence'] = evidence
            initial = input_v3._run_initialization_id(run, None)
            release = ingestion_admission._process_release(os.environ.get('VF_NATIVE_RELEASE_COMMIT'),
                os.environ.get('VF_NATIVE_RELEASE_SHA256'))
            ingestion_admission._admit(cursor, initial, release, pending=True)
            value['guards'].add('ingestion_function')
        for module in (scoped_report_storage, scoped_prepared, scoped_planning, scoped_transit_storage,
                scoped_pick_storage, scoped_expedite_storage, scoped_expedite_parent,
                scoped_git, scoped_remarks, scoped_requests, scoped_pick_files, scope_consumers):
            module.verify_guards()
            value['guards'].add(module.__name__)
        scoped_view.verify_guards(registered=True)
        value['guards'].add(scoped_view.__name__)
        if _action_stamp(database) != before:
            raise ValueError('Action schema changed during admission')
        yield
        if _action_stamp(database) != before:
            raise ValueError('Action schema, migration or security state changed')
    finally:
        _action.reset(token)
