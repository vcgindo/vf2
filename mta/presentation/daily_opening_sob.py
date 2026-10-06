"""Exact opening SOB scalars with a separate canonical float projection."""
import inspect
import math

from mta.runtime.models import DailyOpeningSob
from mta.runtime.relational_state import wire_type, wire_value, quote
from mta.serialization import digest

PATH = 'opening/supplier/SOBData'
FIELDS = ('SKUCode', 'WHCode', 'SupplierCode', 'SOB')


def recipe_digest():
    return digest(inspect.getsource(inspect.getmodule(save)))


def save(run, rows):
    fields = list(rows[0]) if rows else []
    if rows and (set(fields) != set(FIELDS) or any(set(row) != set(FIELDS) for row in rows)):
        raise ValueError('Opening SOB source shape differs')
    kinds = {}
    for field in fields:
        types = {wire_type(row[field]) for row in rows if row[field] is not None}
        if len(types) > 1 or types - ({'str', 'int', 'float'} if field == 'SOB' else {'str'}):
            raise ValueError('Opening SOB source wire type differs: ' + field)
        kinds[field] = next(iter(types), 'str')
    records = []
    for ordinal, row in enumerate(rows):
        value = row['SOB']
        number = None if value is None else float(value)
        if number is not None and not math.isfinite(number):
            raise ValueError('Opening SOB must have finite canonical numeric value')
        records.append(DailyOpeningSob(run=run, ordinal=ordinal,
            **{name: row[name] for name in FIELDS if name != 'SOB'}, SOB=number,
            sob_wire=None if value is None else str(value)))
    DailyOpeningSob.objects.bulk_create(records)
    item = dict(image=PATH, table=DailyOpeningSob._meta.db_table, count=len(rows),
                digest=digest(rows), fields=[[field, field, kinds[field]] for field in fields])
    if read(run, item) != rows:
        raise ValueError('Opening SOB exact source readback differs')
    return item


def read(run, item):
    if item['image'] != PATH or item['table'] != DailyOpeningSob._meta.db_table:
        raise ValueError('Opening SOB source identity differs')
    fields = item['fields']
    if (item['count'] == 0 and fields) or (item['count'] != 0 and
            (len(fields) != len(FIELDS) or {f for f, _, _ in fields} != set(FIELDS))):
        raise ValueError('Opening SOB source fields differ')
    if (
            any(f != column or kind not in ({'str', 'int', 'float'} if f == 'SOB' else {'str'})
                   for f, column, kind in fields)):
        raise ValueError('Opening SOB source fields differ')
    records = list(DailyOpeningSob.objects.filter(run=run).order_by('ordinal').values(
        'ordinal', *FIELDS, 'sob_wire'))
    if [row['ordinal'] for row in records] != list(range(item['count'])):
        raise ValueError('Opening SOB source count/order differs')
    rows = []
    for record in records:
        wire, number = record['sob_wire'], record['SOB']
        if (wire is None) != (number is None) or (wire is not None and float(wire) != number):
            raise ValueError('Opening SOB canonical numeric projection differs')
        rows.append({field: wire_value(wire if field == 'SOB' else record[field], kind)
                     for field, _, kind in fields})
    if digest(rows) != item['digest']:
        raise ValueError('Opening SOB source value/type/multiplicity drift')
    return rows


def query(run):
    return ('SELECT ordinal AS vf_ordinal,' + ','.join(quote(f) for f in FIELDS)
            + ' FROM mta.' + quote(DailyOpeningSob._meta.db_table) + ' WHERE run_id=%s'), [run.pk]
