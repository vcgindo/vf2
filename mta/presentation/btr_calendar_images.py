"""Persist the scalar roster and verify the complete dated BTR image."""
import hashlib
import os

from django.db import connection

from mta.domain.btr_finalization import DAYS
from mta.presentation.btr_calendar_sources import TRENDS, _trend_query
from mta.row_sequences import RecordRows
from mta.runtime import relational_state as typed
from mta.serialization import canonical_parts


FORMAT = 'btr-dated-roster-v1'


def owns(item):
    return item.get('storage_format') == FORMAT


def published_directory(run, item):
    from mta.presentation.operational_reports import generation
    owner = generation(run)
    if owner.version != 2 or owner.metadata['images'].get(item['image']) != item or not owns(item):
        raise ValueError('Dated BTR image does not belong to the sealed report generation')
    return owner.metadata['btr_calendar']


def published_query(run, item):
    directory = published_directory(run, item)
    return _trend_query(run, directory, item['image'].removeprefix('closing/btr/'))


def verified_rows(run, directory, item):
    name = item['image'].removeprefix('closing/btr/')
    if name not in TRENDS or item['image'] != 'closing/btr/' + name or item['table'] != 'BTR/' + name:
        raise ValueError('Unexpected dated BTR image')
    relation, bindings = _trend_query(run, directory, name)
    fields = item['fields']
    columns = ['vf_ordinal', *(typed.quote(column) for _, column, _ in fields)]
    checksum = hashlib.sha256(b'[')
    count = 0
    with connection.chunked_cursor() as cursor:
        cursor.execute('SELECT ' + ','.join(columns) + ' FROM (' + relation + ') image ORDER BY vf_ordinal', bindings)
        while batch := cursor.fetchmany(256):
            for ordinal, *values in batch:
                if ordinal != count:
                    raise ValueError('Dated BTR roster ordinal differs')
                row = {field: typed.wire_value(value, kind)
                       for (field, _, kind), value in zip(fields, values, strict=True)}
                if count:
                    checksum.update(b',')
                for part in canonical_parts(row):
                    checksum.update(part)
                count += 1
                yield row
    checksum.update(b']')
    if count != item['count'] or checksum.hexdigest() != item['digest']:
        raise ValueError('Dated BTR logical image differs: ' + name)


def load(run, directory, item):
    def records():
        return verified_rows(run, directory, item)
    if item['count'] <= 10000:
        return list(records())
    if os.environ.get('VF_WORK_ROOT'):
        return RecordRows.from_rows(records())
    for _ in records():
        pass
    return RecordRows(item['count'], records)


def save(run, directory, name, rows):
    if name not in TRENDS or not connection.in_atomic_block:
        raise ValueError('Dated BTR storage requires the owning report transaction')
    table, path = 'BTR/' + name, 'closing/btr/' + name
    columns = {col.casefold(): (col, kind) for col, kind in typed.STORAGE_TABLES[table]}
    item, fields, _ = typed.describe_rows(rows, columns, path)
    item['table'] = table
    item['storage_format'] = FORMAT
    scalars = tuple(field for field in fields if field not in DAYS)
    roster = RecordRows(len(rows), lambda: ({key: row[key] for key in scalars} for row in rows))
    typed.save_image(run, path, path, roster)
    # Compare the independently reconstructed SQL result with the complete
    # original producer output, including duplicate order and wire types.
    for _ in verified_rows(run, directory, item):
        pass
    return item
