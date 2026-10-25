"""Reuse successful native identity metadata only while the database is unchanged.

PostgreSQL snapshots invalidate conservatively on unrelated writes as well as
publication changes. No time-based freshness allowance, per-user permissions,
workflow or report rows are cached. Certified catalogue/grant/role admission is
reused only for an identical database/session. Offline/full verification always
uses the original path.
"""
from copy import deepcopy
from functools import wraps
import os
from uuid import UUID

from django.conf import settings
from django.db import connection

from mta.serialization import digest

_connection = None
_pid = None
_entries = {}


def clear():
    global _connection, _pid
    _entries.clear()
    _connection = None
    _pid = None
    from mta.presentation import schema_reuse
    schema_reuse.clear()


def stamp():
    global _connection, _pid
    if connection.vendor != 'postgresql' or connection.in_atomic_block or not connection.get_autocommit():
        return None
    with connection.cursor() as cursor:
        if _connection is not connection.connection or _pid != os.getpid():
            clear()
            _connection, _pid = connection.connection, os.getpid()
        cursor.execute("SELECT pg_current_snapshot()::text,current_database(),"
            "(SELECT oid FROM pg_database WHERE datname=current_database()),"
            "session_user,current_user,pg_backend_pid(),pg_postmaster_start_time(),"
            "current_setting('transaction_isolation'),current_setting('search_path'),"
            "current_setting('row_security'),current_setting('session_replication_role'),"
            "current_setting('TimeZone'),current_setting('DateStyle'),current_setting('client_encoding'),"
            "current_setting('quote_all_identifiers'),current_setting('standard_conforming_strings'),"
            "current_setting('extra_float_digits')")
        value = cursor.fetchone()
    if value[7] != 'read committed' or value[10] != 'origin':
        return None
    return value


def native_identity(function):
    def checked(run, *, verify_rows=False):
        from mta.presentation.request_scope import in_read_request
        from mta.presentation import admission
        # In particular, an already admitted process cannot lend a cached check
        # to offline publication preparation or a full serving/recovery audit.
        if verify_rows or not in_read_request() or admission._admitted is None:
            return function(run, verify_rows=verify_rows)
        from mta.presentation.native_mode import require_configuration
        require_configuration()
        if getattr(settings, 'VF_MTA_SYNTHETIC_ROSTER', ''):
            return function(run, verify_rows=verify_rows)
        try:
            before = stamp()
            if before is None:
                clear()
                return function(run, verify_rows=verify_rows)
            metadata = {field.attname: str(value) if isinstance(value, UUID) else value
                        for field in run._meta.concrete_fields
                        for value in (getattr(run, field.attname),)}
            key = (function, digest(metadata), before)
            if key in _entries:
                return deepcopy(_entries[key])
            value = function(run, verify_rows=verify_rows)
            if stamp() == before:
                # Never retain identity metadata for an older database snapshot.
                for old in list(_entries):
                    if old[-1] != before:
                        del _entries[old]
                if len(_entries) >= 8:
                    _entries.clear()
                _entries[key] = deepcopy(value)
            return value
        except Exception:
            clear()
            raise

    @wraps(function)
    def read(run, *, verify_rows=False):
        try:
            return checked(run, verify_rows=verify_rows)
        except Exception:
            clear()
            raise
    return read


def certified_readiness(function):
    """Reuse finite certified metadata only across an unchanged database.

    Each miss retains the original owned read-only transaction. Only read HTTP
    requests and their explicit pre-handler admission boundary may reuse it;
    preparation, action handlers and existing transactions retain full checks.
    """
    @wraps(function)
    def read(initialization_id):
        from mta.presentation.request_scope import in_read_request, in_admission_preflight
        from mta.presentation import admission
        try:
            if not (in_read_request() or in_admission_preflight()) or admission._admitted is None:
                return function(initialization_id)
            def fresh():
                from mta.presentation.schema_reuse import verification
                with verification():
                    return function(initialization_id)
            before = stamp()
            if before is None:
                clear()
                return function(initialization_id)
            key = (function, str(initialization_id),
                   os.environ.get('VF_NATIVE_RELEASE_COMMIT'),
                   os.environ.get('VF_NATIVE_RELEASE_SHA256'), before)
            if key in _entries:
                value = deepcopy(_entries[key])
                if stamp() == before:
                    return value
                clear()
                return fresh()
            value = fresh()
            if stamp() == before:
                for old in list(_entries):
                    if old[-1] != before:
                        del _entries[old]
                if len(_entries) >= 8:
                    _entries.clear()
                _entries[key] = deepcopy(value)
            return value
        except Exception:
            clear()
            raise
    return read
