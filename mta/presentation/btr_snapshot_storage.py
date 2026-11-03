"""Exact XML tuples shared by ordinals of one immutable BTR snapshot."""
import hashlib
import os

from django.db import connection

from mta.runtime import relational_state as typed
from mta.row_sequences import RecordRows
from mta.serialization import canonical_parts


TABLE = 'BTR/BTRSnapshotForUI'
PATH = 'closing/btr/BTRSnapshotForUI'
FORMAT = 'btr-snapshot-xml-ordinal-v1'
XML = tuple(prefix + branch for prefix in ('BPP', 'Colors')
            for branch in ('Tech', 'Econ', 'Dispatch', 'PhysicalInv'))
MAX_ENTRIES = 8192
MAX_BYTES = 4 * 1024 * 1024


def owns(item):
    return item.get('storage_format') == FORMAT


def require(item):
    if (not owns(item) or item['table'] != TABLE or item['image'] != PATH or
            not 0 <= item['reuse_before'] <= item['count']):
        raise ValueError('Invalid BTR snapshot representation')
    if item['count'] and not set(XML).issubset({field for field, _, _ in item['fields']}):
        raise ValueError('BTR snapshot XML fields missing')


class Representatives:
    """After the budget fills, new patterns stay inline. Prior patterns still share."""

    def __init__(self):
        self.ordinals = {}
        self.size = 0
        self.cutoff = None

    def assign(self, ordinal, values):
        existing = self.ordinals.get(values)
        if existing is not None:
            return existing
        if self.cutoff is None:
            size = sum(len(value.encode('utf-8')) for value in values)
            if len(self.ordinals) < MAX_ENTRIES and self.size + size <= MAX_BYTES:
                self.ordinals[values] = ordinal
                self.size += size
            else:
                self.cutoff = ordinal
        return ordinal


def save(run, rows):
    if not connection.in_atomic_block:
        raise ValueError('Snapshot XML requires the owning report transaction')
    columns = {name.casefold(): (name, kind) for name, kind in typed.STORAGE_TABLES[TABLE]}
    item, fields, native = typed.describe_rows(rows, columns, PATH)
    item.update(table=TABLE, storage_format=FORMAT, reuse_before=len(rows))
    require(item)
    if not rows:
        return item
    sql_columns = ['vf_run_id', 'vf_image', 'vf_ordinal', 'vf_xml_ordinal', *(n for n, _ in native)]
    query = 'COPY '+typed.table_sql(TABLE)+' ('+','.join(map(typed.quote, sql_columns))+') FROM STDIN'
    reps = Representatives()
    with connection.cursor() as cursor, cursor.copy(query) as writer:
        for ordinal, row in enumerate(rows):
            representative = reps.assign(ordinal, tuple(row[name] for name in XML))
            values = (None if representative != ordinal and field in XML else typed.db_value(row[field], kind)
                      for field, (_, kind) in zip(fields, native, strict=True))
            writer.write_row((run.pk, PATH, ordinal, representative, *values))
    if reps.cutoff is not None:
        item['reuse_before'] = reps.cutoff
    return item


def relation(run, item):
    require(item)
    table = typed.table_sql(TABLE)
    projections = [('owner.' if name in XML else 's.')+typed.quote(name)
                   for name, _ in typed.STORAGE_TABLES[TABLE]]
    return ('SELECT s.vf_run_id,s.vf_image,s.vf_ordinal,'+','.join(projections)+
            ' FROM '+table+' s JOIN '+table+' owner ON owner.vf_run_id=s.vf_run_id'
            ' AND owner.vf_image=s.vf_image AND owner.vf_ordinal=s.vf_xml_ordinal'
            ' AND owner.vf_xml_ordinal=owner.vf_ordinal WHERE s.vf_run_id=%s AND s.vf_image=%s',
            [run.pk, PATH])


def verified_rows(run, item):
    require(item)
    fields = item['fields']
    columns = ['vf_ordinal', 'vf_xml_ordinal', *(typed.quote(name) for _, name, _ in fields)]
    query = ('SELECT '+','.join(columns)+' FROM '+typed.table_sql(TABLE)+
             ' WHERE vf_run_id=%s AND vf_image=%s ORDER BY vf_ordinal')
    cache = {}
    retained_bytes = count = 0
    checksum = hashlib.sha256(b'[')
    with connection.chunked_cursor() as cursor:
        cursor.execute(query, [run.pk, PATH])
        while batch := cursor.fetchmany(256):
            for ordinal, representative, *values in batch:
                if ordinal != count:
                    raise ValueError('BTR snapshot ordinal differs')
                row = {field: typed.wire_value(value, kind)
                       for (field, _, kind), value in zip(fields, values, strict=True)}
                if representative == ordinal:
                    xml = tuple(row[name] for name in XML)
                    if not all(isinstance(value, str) for value in xml):
                        raise ValueError('Incomplete BTR snapshot XML owner')
                    if ordinal < item['reuse_before']:
                        retained_bytes += sum(len(value.encode('utf-8')) for value in xml)
                        if len(cache) >= MAX_ENTRIES or retained_bytes > MAX_BYTES:
                            raise ValueError('BTR snapshot XML lookup budget exceeded')
                        cache[ordinal] = xml
                else:
                    if representative not in cache or any(row[name] is not None for name in XML):
                        raise ValueError('Invalid BTR snapshot XML reference')
                    row.update(zip(XML, cache[representative], strict=True))
                if count:
                    checksum.update(b',')
                for part in canonical_parts(row):
                    checksum.update(part)
                count += 1
                yield row
    checksum.update(b']')
    if count != item['count'] or checksum.hexdigest() != item['digest']:
        raise ValueError('BTR snapshot logical image differs')


def load(run, item):
    def records():
        return verified_rows(run, item)
    if item['count'] <= 10000:
        return list(records())
    if os.environ.get('VF_WORK_ROOT'):
        return RecordRows.from_rows(records())
    for _ in records():
        pass
    return RecordRows(item['count'], records)
