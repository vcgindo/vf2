"""Borrow validated input components only inside one complete view selection.

The canonical readers still authenticate the whole input before pruning. Live
request/remark owners, phase receipts and final selection checks are not lent.
Each independent selection owns and discards its own context.
"""
from contextlib import contextmanager
from contextvars import ContextVar
from copy import deepcopy
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from django.core.exceptions import ObjectDoesNotExist
from django.db import connections, DEFAULT_DB_ALIAS

from mta.presentation import request_scope

_active = ContextVar('complete_selection_inputs', default=None)
CURRENT = ('lineage', 'initialization_binding', 'profile', 'scope_request')
PREDECESSOR = ('initialization_binding', 'profile')


def _pass():
    value = request_scope._validation.get()
    return value if value is not None else request_scope._current.get()


@contextmanager
def selection(run_id):
    database = connections[DEFAULT_DB_ALIAS]
    lifetime = _pass()
    if (lifetime is None or _active.get() is not None or database.vendor != 'postgresql'
            or database.connection is None or database.connection.closed):
        value = None
    else:
        value = dict(run_id=str(run_id), parent_id=None, lifetime=lifetime,
            database=database, physical=database.connection, entries={}, disabled=False)
    token = _active.set(value)
    try:
        yield
    finally:
        _active.reset(token)


def _stamp(context):
    database = context['database']
    if (context['lifetime'] is not _pass() or database.connection is not context['physical']
            or database.connection.closed):
        return None
    with database.cursor() as cursor:
        cursor.execute("SELECT pg_current_snapshot()::text,pg_current_wal_insert_lsn()::text,"
            "pg_backend_pid(),current_database(),session_user,current_user,"
            "current_setting('transaction_isolation'),current_setting('transaction_read_only'),"
            "current_setting('search_path'),current_setting('row_security'),"
            "current_setting('session_replication_role'),current_setting('TimeZone'),"
            "current_setting('DateStyle'),current_setting('client_encoding')")
        value = cursor.fetchone()
    return value if value[6] == 'read committed' else None


def _finite(value):
    """Bound retained metadata; never iterate a streaming row source."""
    pending = [value]
    size = 0
    nodes = 0
    while pending:
        item = pending.pop()
        nodes += 1
        if nodes > 20000 or size > 1024 * 1024:
            return False
        if type(item) in (dict, list, tuple) and len(pending) + nodes + len(item) * 2 > 20000:
            return False
        if type(item) is dict:
            pending.extend(item.keys()); pending.extend(item.values())
        elif type(item) in (list, tuple):
            pending.extend(item)
        elif type(item) is str:
            size += len(item) * 4
        elif item is None or type(item) in (int, float, bool, date, datetime, Decimal, UUID):
            size += 32
        else:
            return False
    return size <= 1024 * 1024


def _same(left, right):
    # Canonical input bytes distinguish bool/int/float, signed zero and decimal
    # scale. Ordinary Python container equality does not preserve those types.
    if type(left) is not type(right):
        return False
    if type(left) is dict:
        return len(left) == len(right) and all(_same(a, b) and _same(left[a], right[b])
            for a, b in zip(left, right))
    if type(left) in (list, tuple):
        return len(left) == len(right) and all(_same(a, b) for a, b in zip(left, right))
    if type(left) is float:
        return left.hex() == right.hex()
    if type(left) is Decimal:
        return left.as_tuple() == right.as_tuple()
    if type(left) in (date, datetime):
        return left.isoformat() == right.isoformat()
    return left == right


def _physical_copy(entry):
    owner = entry['physical_model'](**deepcopy(entry['physical_metadata']))
    owner._state.db = entry['physical_database']
    owner._state.adding = entry['physical_adding']
    return owner


def _snapshot(run):
    return {field.attname: getattr(run, field.attname) for field in run._meta.concrete_fields}


def _entry(run):
    context = _active.get()
    if (context is None or context['disabled'] or run._meta.model_name != 'calculationrun'
            or run._state.db != DEFAULT_DB_ALIAS or run.kind != 'DAILY_CHAIN'):
        return None
    identity = str(run.pk)
    if identity == context['run_id']:
        components = CURRENT
        parent = str(run.predecessor_id) if run.predecessor_id else None
        if parent != context['parent_id']:
            context['entries'] = {key: value for key, value in context['entries'].items() if key == identity}
            context['parent_id'] = parent
    elif identity == context['parent_id']:
        components = PREDECESSOR
    else:
        return None
    before = _stamp(context)
    if before is None:
        context['entries'].clear()
        return None
    metadata = _snapshot(run)
    prior = context['entries'].get(identity)
    if prior is not None and prior['stamp'] == before and _same(prior['metadata'], metadata):
        return prior
    if not _finite(metadata):
        return None
    metadata = deepcopy(metadata)
    # Use the logical reader, including captured-wrapper authentication. An
    # invalid eager component must not change the caller's original failure
    # boundary: discard reuse and let each ordinary reader report its failure.
    from mta.runtime.input_reader import read_input as read
    from mta.runtime.captured_input import SCHEMAS, origin
    try:
        raw = read(run, components=components)
        physical = origin(run) if run.input_payload.get('schema') in SCHEMAS else run
    except (ValueError, KeyError, TypeError, AttributeError, ObjectDoesNotExist):
        context['disabled'] = True
        context['entries'].clear()
        return None
    physical_metadata = _snapshot(physical)
    if (not _finite(raw) or not _finite(physical_metadata) or _stamp(context) != before
            or not _same(_snapshot(run), metadata)):
        return None
    entry = dict(stamp=before, metadata=deepcopy(metadata), raw=deepcopy(raw),
                 physical_model=type(physical), physical_metadata=deepcopy(physical_metadata),
                 physical_database=physical._state.db, physical_adding=physical._state.adding,
                 components=components)
    context['entries'][identity] = entry
    return entry


def read_input(run, *, components):
    requested = tuple(components) if type(components) in (tuple, list) else None
    if requested is not None and all(type(name) is str and name in CURRENT for name in requested):
        entry = _entry(run)
        if entry is not None and set(requested) <= set(entry['components']):
            result = deepcopy({name: value for name, value in entry['raw'].items() if name in requested})
            if _stamp(_active.get()) == entry['stamp']:
                return result
    from mta.runtime.input_reader import read_input as read
    return read(run, components=components)


def physical(run):
    entry = _entry(run)
    if entry is not None:
        result = _physical_copy(entry)
        if _stamp(_active.get()) == entry['stamp']:
            return result
    from mta.runtime.captured_input import SCHEMAS, origin
    from mta.runtime import input_storage
    owner = origin(run) if run.input_payload.get('schema') in SCHEMAS else run
    input_storage.read_input(owner, components=())
    return owner
