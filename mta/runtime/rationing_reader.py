"""Indexed logical rationing images over immutable occurrence facts and deltas.

This reader is not activated by importing it. Admission remains with the existing
run/publication owners. A cut is bounded metadata; no ancestor-list expansion,
per-row query, or current-table fallback is used to read a historical image.
"""
from dataclasses import dataclass
import json
from uuid import UUID

from django.db import connection

from mta.serialization import digest
from mta.row_sequences import RecordRows
from mta.runtime.rationing_delta import Occurrence
from mta.runtime.rationing_shape import require_fields
from mta.runtime.relational_state import quote, wire_value
from mta.runtime.state_cut_models import OperationalStateCut


FORMAT = 'rationing-occurrences-v1'
IMAGE = 'closing/btr/RationingHistory'
TABLE = 'BTR/RationingHistory'
FAMILY = 'rationing_history'
IMAGE_KEYS = frozenset(('image', 'table', 'count', 'digest', 'fields', 'storage_format', 'cut_id'))
CUT_FIELDS = ('id', 'initialization_id', 'run_id', 'position', 'family', 'parent_id',
              'input_digest', 'settings_digest', 'root_body', 'root_digest', 'run__status')


@dataclass(frozen=True)
class Cut:
    identity: UUID
    initialization: UUID
    run: UUID | None
    position: int
    root_digest: str
    body: dict


def read_cut(identity):
    """Authenticate one sealed header. Normal reads do not walk its ancestry."""
    return authenticate_cut(OperationalStateCut.objects.values(*CUT_FIELDS).get(pk=identity))


def authenticate_cut(row):
    """Validate an already fetched header; also used by the explicit audit."""
    if not row['root_body'] or not row['root_digest'] or row['run_id'] is not None and row['run__status'] != 'SUCCEEDED':
        raise ValueError('Rationing image requires its accepted sealed cut')
    body = json.loads(row['root_body'])
    if (type(body) is not dict or digest(body) != row['root_digest']
            or body.get('format') != FORMAT or row['family'] != FAMILY
            or body.get('cut') != str(row['id'])
            or body.get('initialization') != str(row['initialization_id'])
            or body.get('run') != (str(row['run_id']) if row['run_id'] else None)
            or body.get('parent') != (str(row['parent_id']) if row['parent_id'] else None)
            or type(body.get('position')) is not int or body['position'] != row['position']
            or body.get('family') != row['family'] or body.get('input_digest') != row['input_digest']
            or body.get('settings_digest') != row['settings_digest']):
        raise ValueError('Rationing cut commitment differs')
    require_fields(body.get('fields'), body.get('count'))
    return Cut(row['id'], row['initialization_id'], row['run_id'], row['position'], row['root_digest'], body)


def image_metadata(cut):
    return dict(image=IMAGE, table=TABLE, count=cut.body['count'], digest=cut.root_digest,
                fields=cut.body['fields'], storage_format=FORMAT, cut_id=str(cut.identity))


def uses_occurrences(item):
    """An unrecognized explicit format must never fall back to legacy rows."""
    if 'storage_format' not in item and 'cut_id' not in item:
        return False
    if item.get('storage_format') != FORMAT or item.get('table') != TABLE or item.get('image') != IMAGE:
        raise ValueError('Unknown operational image storage format')
    return True


def require_image(run, item):
    if type(item) is not dict or set(item) != IMAGE_KEYS or item.get('storage_format') != FORMAT:
        raise ValueError('Unknown rationing image storage format or metadata')
    cut = read_cut(item['cut_id'])
    if cut.run != run.pk or image_metadata(cut) != item:
        raise ValueError('Rationing image differs from its exact accepted run/cut')
    return cut


def occurrence_query(cut):
    """One range-bounded relation, ordered by immutable producer occurrence.

    A NULL Dispatch revision is a value; it must not fall back to the fact.
    No revision newer than this cut may affect a historical read.
    """
    fields = cut.body['fields']
    require_fields(fields, cut.body['count'])
    columns = [
        '(CASE WHEN D.cut_id IS NULL THEN F."Dispatch" ELSE D.dispatch END) AS "Dispatch"'
        if name == 'Dispatch' else 'F.'+quote(name)
        for _, name, _ in fields]
    sql = ('SELECT L.born_position,L.original_ordinal' + (','+','.join(columns) if columns else '') +
        ' FROM mta_state.rationing_lifetime L'
        ' JOIN mta_state.rationing_fact F ON F.cut_id=L.fact_cut_id AND F.vf_ordinal=L.original_ordinal'
        ' LEFT JOIN LATERAL (SELECT V.cut_id,V.dispatch FROM mta_state.rationing_dispatch V'
        ' WHERE V.original_cut_id=L.fact_cut_id AND V.original_ordinal=L.original_ordinal'
        ' AND V.position<=%s ORDER BY V.position DESC LIMIT 1) D ON true'
        " WHERE L.initialization_id=%s AND int8range(L.born_position,L.end_position,'[)') @> %s::bigint"
        ' ORDER BY L.born_position,L.original_ordinal')
    return sql, [cut.position, cut.initialization, cut.position]


def iter_occurrences(cut):
    """Accepted reader: no payload rehash; full physical audit is separate."""
    sql, params = occurrence_query(cut)
    count = 0
    previous = None
    fields = cut.body['fields']
    with connection.chunked_cursor() as cursor:
        cursor.execute(sql, params)
        while batch := cursor.fetchmany(500):
            for record in batch:
                occurrence = Occurrence(record[0], record[1])
                if occurrence.position > cut.position or previous is not None and occurrence <= previous:
                    raise ValueError('Rationing logical occurrence order differs')
                previous = occurrence
                row = {field: wire_value(value, kind)
                       for (field, _, kind), value in zip(fields, record[2:])}
                count += 1
                yield occurrence, row
    if count != cut.body['count']:
        raise ValueError('Rationing logical membership count differs')


def iter_image(run, item):
    cut = require_image(run, item)
    for _, row in iter_occurrences(cut):
        yield row


def load_image(run, item):
    return load_cut(require_image(run, item))


def load_cut(cut):
    def records():
        return (row for _, row in iter_occurrences(cut))
    count = cut.body['count']
    return RecordRows(count, records) if count > 10000 else list(records())
