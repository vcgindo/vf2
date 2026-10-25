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
        versions = tuple(cursor.fetchall())
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
