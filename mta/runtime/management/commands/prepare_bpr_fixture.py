"""Atomically prepare one native BPR candidate relation in the owned fixture."""
import hashlib
import json

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction

from mta.presentation import fixture
from mta.presentation.bpr_prepared_fields import SOURCES, FIELDS, field_name, schema_digest
from mta.presentation.rrr_sql import equal, key
from mta.presentation.selective import image_metadata, image_query
from mta.runtime.models import CalculationRun, BprPreparedProjection, BprPreparedRow
from mta.runtime.bpr_prepared_schema import verify_guards
from mta.runtime.relational_state import CATALOG, PG_TYPES, quote
from mta.serialization import canonical_parts


ORDINALS = ('a_ordinal', 'v_ordinal', 's_ordinal', 'c_ordinal', 'd_ordinal', 'b_ordinal')
ROW_FIELDS = ('ordinal', 'sku_key', 'location_key') + ORDINALS + tuple(
    field_name(owner, name) for owner, fields in FIELDS.items() for name in fields)


def insert_query(run):
    """Same six native candidate left joins as BPR; never auth or projection."""
    ctes, values = [], []
    for owner, path in SOURCES.items():
        item = image_metadata(run, path)
        native = dict(CATALOG['tables'][item['table']])
        published = {name: PG_TYPES[native[column]] for name, column, wire_kind in item['fields']}
        for name, kind in FIELDS[owner].items():
            if published.get(name) != kind:
                raise CommandError('BPR prepared source field/type differs: ' + owner + '.' + name)
        sql, params = image_query(run, path)
        ctes.append(owner + ' AS NOT MATERIALIZED (' + sql + ')')
        values.extend(params)
    source_order = ','.join(owner + '.vf_ordinal' for owner in SOURCES)
    selected = [
        '%s', 'row_number() OVER (ORDER BY ' + source_order + ')-1',
        key('A."SKUCode"'), key('A."WhCode"'),
    ] + [owner + '.vf_ordinal' for owner in SOURCES]
    selected += [owner + '.' + quote(name) for owner, fields in FIELDS.items() for name in fields]
    joins = ' FROM A'
    for owner, sku, location in (('V', 'SKUCode', 'WhCode'), ('S', 'SKUCode', 'WhCode'),
                                 ('C', 'SKUCode', None), ('D', None, 'WHCode'),
                                 ('B', 'SKUCode', 'LocCode')):
        conditions = []
        if sku:
            conditions.append(equal('A."SKUCode"', owner + '.' + quote(sku)))
        if location:
            conditions.append(equal('A."WhCode"', owner + '.' + quote(location)))
        joins += ' LEFT JOIN ' + owner + ' ON ' + ' AND '.join(conditions)
    columns = ','.join(quote(name) for name in ('run_id',) + ROW_FIELDS)
    # WITH source bindings precede the INSERT SELECT run value.
    query = ('WITH ' + ','.join(ctes) + ' INSERT INTO ' + quote(BprPreparedRow._meta.db_table) +
             ' (' + columns + ') SELECT ' + ','.join(selected) + joins)
    return query, values + [run.pk]


def rows_receipt(run):
    """Stream complete typed native values in stable ordinal order, bounded RAM."""
    checksum = hashlib.sha256(b'[')
    count = 0
    columns = ','.join(quote(name) for name in ROW_FIELDS)
    # A server-side cursor prevents fetchmany from hiding a full client buffer.
    with connection.chunked_cursor() as cursor:
        cursor.execute('SELECT ' + columns + ' FROM ' + quote(BprPreparedRow._meta.db_table) +
                       ' WHERE run_id=%s ORDER BY ordinal', [run.pk])
        while True:
            batch = cursor.fetchmany(1000)
            if not batch:
                break
            for row in batch:
                if row[0] != count:
                    raise CommandError('BPR prepared ordinal population differs')
                if count:
                    checksum.update(b',')
                for part in canonical_parts(dict(zip(ROW_FIELDS, row))):
                    checksum.update(part)
                count += 1
    checksum.update(b']')
    return count, checksum.hexdigest()


def prepare(*, run=None, verify_only=False):
    if connection.vendor != 'postgresql':
        raise CommandError('BPR prepared relation requires PostgreSQL')
    if getattr(settings, 'VF_MTA_HIERARCHY_FILE', '') or getattr(settings, 'VF_MTA_HIERARCHY_SHA256', ''):
        raise CommandError('BPR preparation requires native hierarchy; supplement is read-time only')
    with transaction.atomic():
        verify_guards(connection)
        fixture_run = run is None
        if fixture_run:
            run, source = fixture.binding()
        else:
            from mta.presentation.daily_preparation import source_digest
            source = source_digest(run)
        # Serialize builds and insert guards against the same retained identity.
        CalculationRun.objects.select_for_update().get(pk=run.pk)
        if fixture_run:
            run_after_lock, source_after_lock = fixture.binding()
            if run.pk != run_after_lock.pk or source != source_after_lock:
                raise CommandError('BPR prepared source changed before preparation')
        else:
            from mta.presentation.daily_preparation import source_digest
            if source_digest(run) != source:
                raise CommandError('BPR prepared source changed before preparation')
        schema = schema_digest()
        receipt = BprPreparedProjection.objects.filter(run=run).first()
        if receipt:
            if (receipt.source_digest, receipt.schema_digest) != (source, schema):
                raise CommandError('Existing BPR prepared binding/schema differs; no replacement allowed')
            count, rows_digest = rows_receipt(run)
            if (receipt.row_count, receipt.rows_digest) != (count, rows_digest):
                raise CommandError('Existing BPR prepared complete row receipt differs')
            created = False
        else:
            if verify_only:
                raise CommandError('BPR prepared receipt does not exist')
            if BprPreparedRow.objects.filter(run=run).exists():
                raise CommandError('Unsealed BPR prepared rows exist; no replacement allowed')
            query, params = insert_query(run)
            with connection.cursor() as cursor:
                cursor.execute(query, params)
                inserted = cursor.rowcount
            count, rows_digest = rows_receipt(run)
            if inserted != count:
                raise CommandError('BPR prepared insert/readback population differs')
            receipt = BprPreparedProjection.objects.create(run=run, source_digest=source,
                schema_digest=schema, rows_digest=rows_digest, row_count=count)
            created = True
        if fixture_run:
            final_run, final_source = fixture.binding()
            if final_run.pk != run.pk or final_source != source:
                raise CommandError('BPR prepared source changed before commit')
        else:
            from mta.presentation.daily_preparation import source_digest
            if source_digest(run) != source:
                raise CommandError('BPR prepared source changed before commit')
        verify_guards(connection)
        return dict(run_id=str(run.pk), source_digest=source, schema_digest=schema,
                    rows_digest=receipt.rows_digest, row_count=receipt.row_count,
                    created=created, status='PASS')


class Command(BaseCommand):
    help = 'Prepare or verify the selected isolated fixture native BPR candidate relation.'

    def add_arguments(self, parser):
        parser.add_argument('--verify-only', action='store_true',
                            help='Verify the complete existing receipt; never insert rows.')
        parser.add_argument('--run-id')

    def handle(self, *args, **options):
        run = None
        if options.get('run_id'):
            run = CalculationRun.objects.get(pk=options['run_id'])
        result = prepare(run=run, verify_only=options['verify_only'])
        self.stdout.write(json.dumps(result, sort_keys=True))
