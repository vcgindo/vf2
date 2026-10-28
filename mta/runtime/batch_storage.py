"""Immutable attempt-owned typed daily-feed staging.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend
presentation and behavior. No frontend redesign, substitute screens, refactoring
or MTO changes. Any future exception requires explicit human authorization.

This module stores only already-parsed daily facts.  CSV parsing, availability
policy, business algorithms, attempt sealing and transaction ownership remain
with their callers.
"""
from collections.abc import Mapping, Sequence
import hashlib
import json
from pathlib import Path
from uuid import UUID
from datetime import datetime

from django.db import connection

from mta.application.production_csv_contract import feeds
from mta.row_sequences import RecordRows
from mta.runtime.relational_state import bulk, db_value, describe_rows, quote, wire_value
from mta.serialization import canonical_parts
from mta.application.stage_observation import stage, summary
from time import perf_counter, process_time


DECLARATION = json.loads((Path(__file__).resolve().parents[1] /
    'config/daily_batch_storage_v1.json').read_text())
CONTRACT = DECLARATION['contract']
TABLES = DECLARATION['feeds']
TEMPORAL_KINDS = frozenset(('datetime', 'datetimetz'))


def table_sql(filename):
    try:
        name = TABLES[filename]['table']
    except KeyError as error:
        raise ValueError('Unknown daily feed storage table') from error
    return 'mta_state.' + quote(name)


def _uuid(value, label):
    try:
        normalized = str(UUID(str(value)))
    except (TypeError, ValueError, AttributeError) as error:
        raise ValueError(label + ' UUID differs') from error
    if normalized != str(value).lower():
        raise ValueError(label + ' UUID differs')
    return normalized


def _database_identity():
    with connection.cursor() as cursor:
        cursor.execute('SELECT current_database(),oid::bigint FROM pg_database '
                       'WHERE datname=current_database()')
        value = cursor.fetchone()
    if (not value or not isinstance(value[0], str) or not value[0]
            or type(value[1]) is not int or value[1] <= 0):
        raise ValueError('Daily batch database identity unavailable')
    return value


def _live_identity(attempt, *, reading=False, manifest=None,
                   allow_owned_failed=False):
    current = type(attempt).objects.select_related('initialization__source').get(
        attempt_id=attempt.attempt_id)
    mutable = (current.status == 'RUNNING' and current.phase == 'VALIDATE'
               and current.accepted_facts == {})
    readable = current.status in ('RUNNING', 'COMMITTED', 'PREPARED', 'PUBLISHED')
    if allow_owned_failed and current.status == 'FAILED':
        readable = True
    sealed = (reading and readable
              and isinstance(manifest, dict)
              and current.accepted_facts == manifest)
    if (current.pk != attempt.pk or not (mutable or sealed)
            or current.initialization_id != attempt.initialization_id):
        raise ValueError('Daily feed attempt is not a current writable or sealed readable owner')
    source = current.initialization.source
    database_name, database_oid = _database_identity()
    return dict(database_name=database_name, database_oid=database_oid,
        source_id=source.pk, source_digest=source.digest,
        initialization_id=str(current.initialization_id),
        attempt_id=str(current.attempt_id))


def _identity(attempt, resolver, *, reading=False, manifest=None,
              allow_owned_failed=False):
    value = (resolver(attempt) if resolver is not None else
             _live_identity(attempt, reading=reading, manifest=manifest,
                            allow_owned_failed=allow_owned_failed))
    required = {'database_name', 'database_oid', 'source_id', 'source_digest',
                'initialization_id', 'attempt_id'}
    if not isinstance(value, dict) or set(value) != required:
        raise ValueError('Daily batch owner identity fields differ')
    if (not isinstance(value['database_name'], str) or not value['database_name']
            or type(value['database_oid']) is not int or value['database_oid'] <= 0
            or not isinstance(value['source_digest'], str)
            or len(value['source_digest']) != 64
            or any(c not in '0123456789abcdef' for c in value['source_digest'])):
        raise ValueError('Daily batch owner identity values differ')
    value = dict(value)
    value['initialization_id'] = _uuid(value['initialization_id'], 'Initialization')
    value['attempt_id'] = _uuid(value['attempt_id'], 'Attempt')
    if value['attempt_id'] != _uuid(attempt.attempt_id, 'Attempt'):
        raise ValueError('Foreign daily feed attempt')
    return value


def _schema(intake):
    if intake not in DECLARATION['intakes']:
        raise ValueError('Unsupported daily intake storage schema')
    live = feeds(intake)
    expected = DECLARATION['intakes'][intake]
    if list(live) != expected:
        raise ValueError('Daily intake feed roster differs')
    for filename in expected:
        declared = TABLES[filename]
        actual = live[filename]
        if (actual['path'] != declared['path'] or
                [[c['name'], c['type']] for c in actual['columns']] != declared['columns']):
            raise ValueError('Daily feed schema differs: ' + filename)
    return expected


def _rows(value, filename):
    if (not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray, dict))
            or len(value) > 10000 and not isinstance(value, RecordRows)):
        raise ValueError('Daily feed requires bounded reiterable typed rows: ' + filename)
    return value


def _wire_text(value, kind):
    if value is None:
        return None
    if kind not in TEMPORAL_KINDS:
        raise ValueError('Daily batch wire text is limited to timestamp fields')
    return value if isinstance(value, str) else value.isoformat() if isinstance(value, datetime) else str(value)


def save_populations(attempt, intake, populations, *, _identity_resolver=None):
    """Insert a complete declared roster; caller owns transaction and sealing."""
    roster = _schema(intake)
    internal = DECLARATION['internal_roster']
    if (not isinstance(populations, Mapping)
            or set(populations) not in (set(roster), set(roster) | set(internal))):
        raise ValueError('Complete daily feed population roster required')
    selected = roster + (internal if set(internal).issubset(populations) else [])
    owner = _identity(attempt, _identity_resolver)
    entries = []
    for filename in selected:
        rows = _rows(populations[filename], filename)
        declaration = TABLES[filename]
        declared_fields = [name for name, _ in declaration['columns']]
        if any(not isinstance(row, dict) or set(row) != set(declared_fields) for row in rows):
            raise ValueError('Complete ordered daily feed fields required: ' + filename)
        columns = {name.casefold(): (name, kind) for name, kind in declaration['columns']}
        with stage('batch_describe', feed=filename, rows=len(rows)):
            meta, fields, native = describe_rows(rows, columns, declaration['path'])
        if rows:
            temporal = [(field, name, kind) for field, (name, kind) in zip(fields, native)
                        if kind in TEMPORAL_KINDS]
            insert_names = [name for name, _ in native] + ['vf_wire_' + name for _, name, _ in temporal]
            sql = ('INSERT INTO ' + table_sql(filename) + ' (vf_attempt_id,vf_ordinal,' +
                ','.join(quote(name) for name in insert_names) + ') VALUES (' +
                ','.join(['%s'] * (len(insert_names) + 2)) + ')')
            with stage('batch_insert', feed=filename, rows=len(rows)):
                bulk(sql, ((owner['attempt_id'], ordinal, *[
                    db_value(row[field], kind) for field, (_, kind) in zip(fields, native)],
                    *[_wire_text(row[field], kind) for field, _, kind in temporal])
                    for ordinal, row in enumerate(rows)))
        entries.append(dict(filename=filename, path=declaration['path'],
            table=declaration['table'], columns=declaration['columns'],
            fields=meta['fields'], count=meta['count'], digest=meta['digest']))
    return dict(contract=CONTRACT, intake=intake, **owner, feeds=entries)


def _validate_manifest(attempt, manifest, resolver, *, allow_owned_failed=False):
    owner = _identity(attempt, resolver, reading=True, manifest=manifest,
        allow_owned_failed=allow_owned_failed)
    if not isinstance(manifest, dict) or manifest.get('contract') != CONTRACT:
        raise ValueError('Daily batch manifest contract differs')
    roster = _schema(manifest.get('intake'))
    for key, value in owner.items():
        if manifest.get(key) != value:
            raise ValueError('Daily batch manifest owner identity differs')
    entries = manifest.get('feeds')
    names = [e.get('filename') for e in entries] if isinstance(entries, list) else []
    if names not in (roster, roster + DECLARATION['internal_roster']):
        raise ValueError('Daily batch manifest roster differs')
    for entry in entries:
        declared = TABLES[entry['filename']]
        if (entry.get('path') != declared['path'] or entry.get('table') != declared['table']
                or entry.get('columns') != declared['columns'] or type(entry.get('count')) is not int
                or entry['count'] < 0 or not isinstance(entry.get('digest'), str)
                or len(entry['digest']) != 64 or not isinstance(entry.get('fields'), list)):
            raise ValueError('Daily batch manifest feed identity differs')
        native = {name: kind for name, kind in declared['columns']}
        seen = set()
        for field in entry['fields']:
            if (not isinstance(field, list) or len(field) != 3 or field[1] not in native
                    or field[0] in seen or field[2] not in ('str', 'int', 'float', 'bool')):
                raise ValueError('Daily batch manifest field identity differs')
            seen.add(field[0])
        if entry['count'] and (seen != set(native) or
                any(field != native_name for field, native_name, _ in entry['fields'])):
            raise ValueError('Daily batch manifest fixed field roster differs')
    return entries


def _iter_population(attempt, entry):
    fields = entry['fields']
    declared = TABLES[entry['filename']]
    kinds = {name: kind for name, kind in declared['columns']}
    temporal = [(field, native, kinds[native]) for field, native, _ in fields
                if kinds[native] in TEMPORAL_KINDS]
    count = 0
    checksum = hashlib.sha256(b'[')
    fetch_seconds=fetch_cpu_seconds=0.0;fetch_calls=0
    with connection.chunked_cursor() as cursor:
        selected = [f[1] for f in fields] + ['vf_wire_' + native for _, native, _ in temporal]
        wall,cpu=perf_counter(),process_time()
        cursor.execute('SELECT vf_ordinal' + (',' + ','.join(quote(name) for name in selected)
            if selected else '') + ' FROM ' + table_sql(entry['filename']) +
            ' WHERE vf_attempt_id=%s ORDER BY vf_ordinal', [str(attempt.attempt_id)])
        query_seconds=perf_counter()-wall;query_cpu_seconds=process_time()-cpu
        while True:
            wall,cpu=perf_counter(),process_time()
            records=cursor.fetchmany(500)
            fetch_seconds+=perf_counter()-wall;fetch_cpu_seconds+=process_time()-cpu;fetch_calls+=1
            if not records:break
            for record in records:
                if record[0] != count:
                    raise ValueError('Daily batch ordinal/multiplicity drift')
                values = record[1:1 + len(fields)]
                wires = record[1 + len(fields):]
                wire_by_field = {field: (wire, kind)
                    for (field, _, kind), wire in zip(temporal, wires)}
                row = {}
                for (field, native, wire_kind), value in zip(fields, values):
                    if field in wire_by_field:
                        wire, kind = wire_by_field[field]
                        if ((wire is None) != (value is None)
                                or wire is not None and db_value(wire, kind) != value):
                            raise ValueError('Daily batch timestamp wire/typed drift: ' + field)
                        row[field] = wire
                    else:
                        row[field] = wire_value(value, wire_kind)
                if count:
                    checksum.update(b',')
                for part in canonical_parts(row):
                    checksum.update(part)
                count += 1
                yield row
    checksum.update(b']')
    if count != entry['count'] or checksum.hexdigest() != entry['digest']:
        raise ValueError('Daily batch typed value/order/count drift: ' + entry['filename'])
    # A timer held across yield would also charge caller work and leak its phase
    # into the consumer. Aggregate only actual cursor calls; parent phases own
    # conversion/hash/consumer costs. No extra row pass or per-row timer/log.
    summary('batch_readback',feed=entry['filename'],rows=count,fetch_calls=fetch_calls,
        query_seconds=query_seconds,query_cpu_seconds=query_cpu_seconds,
        fetch_seconds=fetch_seconds,fetch_cpu_seconds=fetch_cpu_seconds)


def iter_population(attempt, filename, manifest=None, *, _identity_resolver=None,
                    _allow_owned_failed=False):
    """Stream one population after validating its complete sealed manifest."""
    if manifest is None:
        manifest = getattr(attempt, 'accepted_facts', None)
    entries = _validate_manifest(attempt, manifest, _identity_resolver,
        allow_owned_failed=_allow_owned_failed)
    try:
        entry = next(item for item in entries if item['filename'] == filename)
    except StopIteration as error:
        raise ValueError('Daily batch population is outside the manifest') from error
    yield from _iter_population(attempt, entry)


def read_populations(attempt, manifest=None, *, _identity_resolver=None):
    if manifest is None:
        manifest = getattr(attempt, 'accepted_facts', None)
    entries = _validate_manifest(attempt, manifest, _identity_resolver)
    result = {}
    for entry in entries:
        factory = lambda item=entry: _iter_population(attempt, item)
        result[entry['filename']] = (RecordRows(entry['count'], factory)
            if entry['count'] > 10000 else list(factory()))
    return result
