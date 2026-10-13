"""Typed initialization-owned images; no CalculationRun is created or borrowed."""
import hashlib
from django.db import connection

from mta.runtime.relational_state import (STORAGE_TABLES, quote, table_name, bulk,
    db_value, wire_type, wire_value)
from mta.serialization import rows_digest, canonical_parts


def table_sql(key):
    if key not in STORAGE_TABLES:
        raise ValueError('Unknown opening image schema')
    return 'mta_opening.'+quote(table_name(key))


def save_image(owner, image, binding, rows, *, table):
    if table not in STORAGE_TABLES or not image.startswith('input/'):
        raise ValueError('Unknown initialization image/schema')
    from mta.mdm.initialization_rows import select
    if image.endswith('/shape'):
        if table != 'input/row_shape' or any(set(row) != {'shape_id'} or type(row['shape_id']) is not int for row in rows):
            raise ValueError('Opening shape image differs')
    elif select(rows[0] if rows else (), image, rows) != table:
        raise ValueError('Opening population/table identity differs')
    columns = {name.casefold(): (name, kind) for name, kind in STORAGE_TABLES[table]}
    meta = dict(image=image, table=table, count=len(rows), digest=rows_digest(rows), fields=[])
    if not rows:
        return meta
    fields = list(rows[0])
    if any(set(row) != set(fields) for row in rows):
        raise ValueError('Mixed opening row fields: '+image)
    native = []
    for field in fields:
        if field.casefold() not in columns:
            raise ValueError('Unknown opening column: '+image+'/'+field)
        name, kind = columns[field.casefold()]
        kinds = {wire_type(row[field]) for row in rows if row[field] is not None}
        if len(kinds) > 1:
            raise ValueError('Mixed opening wire types: '+image+'/'+field)
        meta['fields'].append([field, name, next(iter(kinds), 'str')])
        native.append((name, kind))
    query = ('INSERT INTO '+table_sql(table)+' (vf_initialization_id,vf_image,vf_ordinal,'+
        ','.join(quote(name) for name, _ in native)+') VALUES ('+
        ','.join(['%s']*(len(native)+3))+')')
    bulk(query, ((owner.pk, image, ordinal, *[db_value(row[field], kind)
        for field, (_, kind) in zip(fields, native)]) for ordinal, row in enumerate(rows)))
    return meta


def load_image(owner, meta):
    fields = meta['fields']
    columns = {name: kind for name, kind in STORAGE_TABLES.get(meta['table'], ())}
    if any(name not in columns for _, name, _ in fields):
        raise ValueError('Opening image field/schema identity drift')
    checksum = hashlib.sha256(b'[')
    rows = []
    with connection.cursor() as cursor:
        cursor.execute('SELECT vf_ordinal'+(' ,'+','.join(quote(name) for _, name, _ in fields) if fields else '')+
            ' FROM '+table_sql(meta['table'])+' WHERE vf_initialization_id=%s AND vf_image=%s ORDER BY vf_ordinal',
            [owner.pk, meta['image']])
        while records := cursor.fetchmany(500):
            for record in records:
                if record[0] != len(rows):
                    raise ValueError('Opening ordinal/multiplicity drift')
                row = {field: wire_value(value, kind) for (field, _, kind), value in zip(fields, record[1:])}
                if rows:
                    checksum.update(b',')
                for part in canonical_parts(row):
                    checksum.update(part)
                rows.append(row)
    checksum.update(b']')
    if len(rows) != meta['count'] or checksum.hexdigest() != meta['digest']:
        raise ValueError('Opening typed value/order/count drift: '+meta['image'])
    return rows
