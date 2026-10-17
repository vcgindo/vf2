from mta.presentation.native_mode import removed_mode
"""Build sealed report rollups from prepared fixture or native published history."""
import hashlib
import json
import time
from uuid import UUID

from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction

from mta.presentation.context import permission_catalogue
from mta.presentation.guided_aggregates import (permission_classes, recipe_digest,
    source_binding, AGGREGATE_TABLE, MEMBER_TABLE)
from mta.presentation.selective import image_rows
from mta.runtime.models import ReportAggregateReceipt, ReportScopeMember
from mta.runtime.report_aggregate_schema import verify_guards
from mta.serialization import canonical_parts


def receipt_value(names, record):
    """Normalize only the report receipt's native UUID ownership field."""
    value = {name: item for name,item in zip(names,record) if name != 'id'}
    if isinstance(value.get('run_id'), UUID):
        value['run_id'] = str(value['run_id'])
    return value


def readback(run):
    results = []
    for table, order in ((AGGREGATE_TABLE, 'family,report_date,product_class,location_class,location_type NULLS FIRST,snapshot_age NULLS FIRST'),
                         (MEMBER_TABLE, 'family,dimension,class_key,permission_id')):
        checksum = hashlib.sha256(b'['); count = 0
        with connection.chunked_cursor() as cursor:
            cursor.execute('SELECT * FROM '+table+' WHERE run_id=%s ORDER BY '+order, [run.pk])
            names = [column[0] for column in cursor.description]
            while batch := cursor.fetchmany(2000):
                for record in batch:
                    value = receipt_value(names, record)
                    if count: checksum.update(b',')
                    for part in canonical_parts(value): checksum.update(part)
                    count += 1
        checksum.update(b']'); results.append((count, checksum.hexdigest()))
    return results


class Command(BaseCommand):
    help = __doc__

    def add_arguments(self, parser):
        parser.add_argument('--verify-only', action='store_true')
        parser.add_argument('--run-id')
        parser.add_argument('--output-digest')

    def handle(self, *args, **options):
        from mta.presentation.native_publication import require_mode
        require_mode()
        if connection.vendor != 'postgresql':
            raise CommandError('Existing PostgreSQL publication required')
        if options.get('run_id'):
            from mta.runtime.models import CalculationRun
            run = CalculationRun.objects.get(pk=options['run_id'])
            if run.kind != 'DAILY_CHAIN' or run.output_digest != options.get('output_digest'):
                raise CommandError('Explicit native run and output digest required')
        else:
            raise CommandError('Explicit native run or selected fixture required')
            run, _ = removed_mode('historical_fixture')
        source = source_binding(run)
        started = time.monotonic()
        from mta.runtime.guided_history_schema import verify_guards as verify_source_guards
        from mta.runtime.models import GuidedHistoryPreparedProjection
        verify_source_guards(connection)
        receipts = list(GuidedHistoryPreparedProjection.objects.filter(run=run))
        if {receipt.family for receipt in receipts} != {'availability', 'excess'}:
            raise CommandError('Complete source-bound history preparation required')
        with transaction.atomic():
            type(run).objects.select_for_update().get(pk=run.pk)
            verify_guards(connection)
            receipt = ReportAggregateReceipt.objects.filter(run=run).first()
            if receipt:
                counts = readback(run)
                if (receipt.source_digest, receipt.recipe_digest, receipt.row_count, receipt.rows_digest, receipt.member_count, receipt.members_digest) != (source, recipe_digest(), *counts[0], *counts[1]):
                    raise CommandError('Aggregate readback differs; no replacement permitted')
                self.stdout.write(json.dumps(dict(status='PASS', created=False, rows=receipt.row_count, members=receipt.member_count, seconds=time.monotonic() - started)))
                return
            if options['verify_only']:
                raise CommandError('Aggregate receipt absent')
            with connection.cursor() as cursor:
                cursor.execute('SELECT EXISTS(SELECT 1 FROM ' + AGGREGATE_TABLE + ' WHERE run_id=%s),EXISTS(SELECT 1 FROM ' + MEMBER_TABLE + ' WHERE run_id=%s)', [run.pk, run.pk])
                if any(cursor.fetchone()):
                    raise CommandError('Unsealed aggregate rows exist; refuse replacement')
                cursor.execute("SELECT set_config('fresh.report_aggregate_build',%s,true)", [str(run.pk)])
                catalogue = permission_catalogue()
                for family, owner in (('availability', 'closing/btr/'), ('excess', 'closing/importer/')):
                    for dimension, name, code, prefix, kind in (('product', 'SkuAttributeData', 'SKUCode', 'SL', 'products'), ('location', 'LocationAttributeData', 'WHCode', 'LL', 'locations')):
                        maps, classes = permission_classes(catalogue[kind]['records'], image_rows(run, owner + name), code, prefix)
                        temp = 'report_' + dimension
                        cursor.execute('CREATE TEMP TABLE ' + temp + ' (code text PRIMARY KEY,class_key text NOT NULL) ON COMMIT DROP')
                        cursor.executemany('INSERT INTO ' + temp + ' VALUES (%s,%s)', sorted(maps.items()))
                        cursor.execute('ANALYZE ' + temp)
                        ReportScopeMember.objects.bulk_create([ReportScopeMember(run=run, family=family, dimension=dimension, class_key=key, permission_id=identifier, weight=weight) for key, vector in sorted(classes.items()) for identifier, weight in vector], batch_size=2000)
                    self.populate(cursor, run, family)
                    cursor.execute('DROP TABLE report_product,report_location')
            counts = readback(run)
            if source_binding(run) != source:
                raise CommandError('Source changed during preparation')
            receipt = ReportAggregateReceipt.objects.create(run=run, source_digest=source, recipe_digest=recipe_digest(), row_count=counts[0][0], rows_digest=counts[0][1], member_count=counts[1][0], members_digest=counts[1][1])
        with connection.cursor() as cursor:
            cursor.execute('ANALYZE ' + AGGREGATE_TABLE)
            cursor.execute('ANALYZE ' + MEMBER_TABLE)
        self.stdout.write(json.dumps(dict(status='PASS', created=True, rows=receipt.row_count, members=receipt.member_count, rows_digest=receipt.rows_digest, members_digest=receipt.members_digest, seconds=time.monotonic() - started)))

    def populate(self, cursor, run, family):
        source = 'mta.fresh_mta_guided' + ('availability' if family == 'availability' else 'excess') + 'historyrow'
        variants = (family, 'ageing') if family == 'availability' else (family,)
        for variant in variants:
            age = 'SR.age_physical_inventory' if variant == 'ageing' else 'NULL::bigint'
            amount = 'sum(H.amount::numeric)' if family == 'excess' else 'NULL::numeric'
            colour = 'H.physical_inventory_color'
            selected = ['count(*)', 'count(' + colour + ')', 'count(*) FILTER (WHERE ' + colour + ' IS NOT NULL AND ' + colour + "<>'Black')"]
            selected += ['count(*) FILTER (WHERE ' + colour + "='" + value + "')" for value in ('Black', 'Red', 'White')]
            selected += ['count(*) FILTER (WHERE lower(rtrim(' + colour + ",' '))='white')", amount, 'min(H.ordinal)']
            sql = 'INSERT INTO ' + AGGREGATE_TABLE + ' (run_id,family,report_date,product_class,location_class,location_type,snapshot_age,occurrence_count,nonnull_count,nonblack_count,black_count,red_count,white_count,excess_white_count,amount,first_ordinal) SELECT %s,%s,H.report_date,P.class_key,L.class_key,H.location_type,' + age + ',' + ','.join(selected) + ' FROM ' + source + ' H JOIN report_product P ON H.sku_code=P.code JOIN report_location L ON H.location_code=L.code '
            if variant == 'ageing':
                sql += 'JOIN mta.fresh_mta_guidedavailabilitysnapshotreference SR ON SR.run_id=H.run_id AND SR.snapshot_anchor_ordinal=H.snapshot_anchor_ordinal '
            sql += 'WHERE H.run_id=%s GROUP BY H.report_date,P.class_key,L.class_key,H.location_type'
            if variant == 'ageing':
                sql += ',SR.age_physical_inventory'
            cursor.execute(sql, [run.pk, variant, run.pk])
