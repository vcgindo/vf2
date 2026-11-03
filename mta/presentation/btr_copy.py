"""Write one fresh BTR display batch without constructing a wide INSERT.

The builder discards these objects: generated primary keys and Django object
state are deliberately not populated. This is not a bulk_create replacement.
COPY retains the table's constraints, row/statement guards and owning transaction.
"""
from django.db import connection

from mta.runtime.models import BtrPresentationRow
from mta.presentation.btr_snapshot_fields import DAILY_FIELDS, display_field


BATCH_SIZE = 64
_FIELDS = tuple(field for field in BtrPresentationRow._meta.local_concrete_fields
                if not field.primary_key and not field.generated)
_DATED_COLUMNS = frozenset(display_field(prefix+slot, variant) for slot in DAILY_FIELDS
                           for prefix in ('','C') for variant in ('number','text'))
SCALAR_FIELDS = tuple(field for field in _FIELDS if field.attname not in _DATED_COLUMNS)


def write_scalar_batch(generation, rows):
    """Write v3 scalar occurrences; omitted nullable day columns have no payload."""
    if not connection.in_atomic_block or generation.version != 3 or not 0 < len(rows) <= BATCH_SIZE:
        raise ValueError('BTR scalar COPY requires a private dated generation batch')
    quote = connection.ops.quote_name
    names = {field.attname for field in SCALAR_FIELDS if field.attname != 'generation_id'}
    sql = ('COPY '+quote('mta')+'.'+quote(BtrPresentationRow._meta.db_table)+' ('+
           ','.join(quote(field.column) for field in SCALAR_FIELDS)+') FROM STDIN')
    with connection.wrap_database_errors, connection.cursor() as cursor:
        with cursor.copy(sql) as writer:
            for row in rows:
                if row.keys() != names:
                    raise ValueError('BTR scalar occurrence columns differ')
                writer.write_row(tuple(field.get_db_prep_save(
                    generation.pk if field.attname=='generation_id' else row[field.attname], connection)
                    for field in SCALAR_FIELDS))


def write_batch(rows):
    """Store at most64 already mapped rows in their existing transaction."""
    if not 0 < len(rows) <= BATCH_SIZE:
        raise ValueError('BTR COPY requires one nonempty batch of at most64 rows')
    if not connection.in_atomic_block:
        raise ValueError('BTR COPY requires its owning transaction')
    for row in rows:
        if type(row) is not BtrPresentationRow or row.pk is not None:
            raise ValueError('BTR COPY accepts fresh presentation rows only')
        row._prepare_related_fields_for_save(operation_name='bulk_create')
    quote = connection.ops.quote_name
    sql = ('COPY ' + quote('mta') + '.' + quote(BtrPresentationRow._meta.db_table) +
           ' (' + ','.join(quote(field.column) for field in _FIELDS) + ') FROM STDIN')
    with connection.wrap_database_errors, connection.cursor() as cursor:
        with cursor.copy(sql) as writer:
            for row in rows:
                values = []
                for field in _FIELDS:
                    value = field.pre_save(row, add=True)
                    if hasattr(value, 'resolve_expression'):
                        raise ValueError('SQL expressions are outside the BTR mapped-row contract')
                    values.append(field.get_db_prep_save(value, connection))
                writer.write_row(tuple(values))
