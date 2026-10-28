"""Typed initialization-owned images; no CalculationRun is created or borrowed."""
import hashlib
import os
import json
from pathlib import Path
from django.db import connection

from mta.runtime.relational_state import (quote, table_name, bulk, copy_rows, INGESTION_COPY_MIN_ROWS,
    db_value, wire_type, wire_value, describe_rows)
from mta.serialization import rows_digest, canonical_parts
from mta.row_sequences import RecordRows
from mta.application.stage_observation import stage

# Initialization v1 owns the exact table set created by0118, independently of
# later run-input families. A later daily table is never an opening namespace.
STORAGE_TABLES = json.loads((Path(__file__).resolve().parents[1]/
    'config/initialization_storage_v1.json').read_text())['tables']
from mta.runtime.dbm_phase_storage import TABLES as PHASE_TABLES
from mta.runtime.btr_history_storage import TABLES as BTR_TABLES
STORAGE_TABLES = {**STORAGE_TABLES, **PHASE_TABLES, **BTR_TABLES}


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
    with stage('opening_describe', image=image, rows=len(rows)):
        meta,fields,native=describe_rows(rows,columns,image)
    meta['table']=table
    if not rows:return meta
    query = ('INSERT INTO '+table_sql(table)+' (vf_initialization_id,vf_image,vf_ordinal,'+
        ','.join(quote(name) for name, _ in native)+') VALUES ('+
        ','.join(['%s']*(len(native)+3))+')')
    records = ((owner.pk, image, ordinal, *[db_value(row[field], kind)
        for field, (_, kind) in zip(fields, native)]) for ordinal, row in enumerate(rows))
    with stage('opening_insert', image=image, rows=len(rows)):
        if len(rows) >= INGESTION_COPY_MIN_ROWS and connection.vendor == 'postgresql':
            copy_rows(table_sql(table), ['vf_initialization_id', 'vf_image', 'vf_ordinal',
                *[name for name, _ in native]], records)
        else:
            bulk(query, records)
    return meta


def iter_image(owner, meta):
    fields = meta['fields']
    columns = {name: kind for name, kind in STORAGE_TABLES.get(meta['table'], ())}
    if any(name not in columns for _, name, _ in fields):
        raise ValueError('Opening image field/schema identity drift')
    checksum = hashlib.sha256(b'[')
    count = 0
    with connection.chunked_cursor() as cursor:
        cursor.execute('SELECT vf_ordinal'+(' ,'+','.join(quote(name) for _, name, _ in fields) if fields else '')+
            ' FROM '+table_sql(meta['table'])+' WHERE vf_initialization_id=%s AND vf_image=%s ORDER BY vf_ordinal',
            [owner.pk, meta['image']])
        while records := cursor.fetchmany(500):
            for record in records:
                if record[0] != count:
                    raise ValueError('Opening ordinal/multiplicity drift')
                row = {field: wire_value(value, kind) for (field, _, kind), value in zip(fields, record[1:])}
                if count:
                    checksum.update(b',')
                for part in canonical_parts(row):
                    checksum.update(part)
                count += 1
                yield row
    checksum.update(b']')
    if count != meta['count'] or checksum.hexdigest() != meta['digest']:
        raise ValueError('Opening typed value/order/count drift: '+meta['image'])



def load_image(owner, meta):
    with stage('opening_fetch_verify_spool', image=meta['image'], rows=meta['count']):
        if meta['count'] > 10000:
            if os.environ.get('VF_WORK_ROOT'):
                return RecordRows.from_rows(iter_image(owner,meta))
            # Serving roots are read-only. Certify the complete immutable typed
            # image before returning, then rescan without an application spool.
            # Installer/daily workers use the existing writable disk cache above.
            for _ in iter_image(owner,meta):pass
            return RecordRows(meta['count'],lambda:iter_image(owner,meta))
        return list(iter_image(owner, meta))
