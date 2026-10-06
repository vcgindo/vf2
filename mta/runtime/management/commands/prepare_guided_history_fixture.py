"""Build the two sealed fixture Guided history occurrence grains once."""
import hashlib
import json
import time

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import DatabaseError, connection, transaction

from mta.presentation import fixture
from mta.presentation.guided_history_fields import ROW_FIELDS, schema_digest
from mta.presentation.selective import image_query
from mta.runtime.models import (
    ExcessInventoryRow, GuidedAvailabilityHistoryRow,
    GuidedAvailabilitySnapshotReference, GuidedExcessHistoryRow,
    GuidedHistoryPreparedProjection,
)
from mta.runtime.guided_history_schema import verify_guards
from mta.runtime.relational_state import quote, table_sql
from mta.serialization import canonical_parts


def exact(left, right):
    # The accepted SQL history readers use ordinary equality: NULL keys do not
    # join and must not gain prepared eligibility.
    return left + ' = ' + right


def rows_receipt(run, family):
    models = ((GuidedAvailabilityHistoryRow, ROW_FIELDS['availability']),
              (GuidedAvailabilitySnapshotReference, ROW_FIELDS['snapshot'])) \
             if family == 'availability' else ((GuidedExcessHistoryRow, ROW_FIELDS['excess']),)
    checksum = hashlib.sha256(b'['); total = 0; references = 0
    for model, fields in models:
        table = 'mta.' + quote(model._meta.db_table)
        order = 'snapshot_anchor_ordinal,snapshot_ordinal' if model is GuidedAvailabilitySnapshotReference else 'ordinal'
        with connection.chunked_cursor() as cursor:
            cursor.execute('SELECT '+','.join(quote(field) for field in fields)+' FROM '+table+
                           ' WHERE run_id=%s ORDER BY '+order, [run.pk])
            while True:
                batch = cursor.fetchmany(2000)
                if not batch: break
                for row in batch:
                    if total: checksum.update(b',')
                    for part in canonical_parts(dict(zip(fields, row))): checksum.update(part)
                    total += 1
                    if model is GuidedAvailabilitySnapshotReference: references += 1
    checksum.update(b']')
    return total - references, references, checksum.hexdigest()


class Command(BaseCommand):
    help = __doc__

    def add_arguments(self, parser):
        parser.add_argument('--verify-only', action='store_true')
        parser.add_argument('--run-id')

    def handle(self, *args, **options):
        if connection.vendor != 'postgresql': raise CommandError('Guided history preparation requires PostgreSQL')
        if not getattr(settings, 'VF_GUIDED_PREPARED', False): raise CommandError('Guided prepared trial switch is disabled')
        from mta.presentation.daily_preparation import command_binding, assert_unchanged
        run, admission = command_binding(options.get('run_id'))
        if run.kind not in ('LEGACY_UI_FIXTURE','DAILY_CHAIN') or (run.kind == 'LEGACY_UI_FIXTURE' and run.status != 'FIXTURE_BLOCKED'):
            raise CommandError('Guided history preparation requires the blocked fixture')
        started = time.monotonic()
        with transaction.atomic():
            verify_guards(connection)
            type(run).objects.select_for_update().get(pk=run.pk)
            assert_unchanged(run, admission)
            receipts = {item.family:item for item in GuidedHistoryPreparedProjection.objects.filter(run=run)}
            if receipts:
                if set(receipts) != {'availability','excess'}:
                    raise CommandError('Incomplete Guided history receipt set')
                result = {}
                for family, receipt in receipts.items():
                    count, references, rows_digest = rows_receipt(run, family)
                    expected = (admission, schema_digest(), count, references, rows_digest)
                    actual = (receipt.source_digest, receipt.schema_digest, receipt.row_count,
                              receipt.reference_count, receipt.rows_digest)
                    if actual != expected: raise CommandError('Existing Guided history receipt differs: '+family)
                    result[family] = dict(rows=count, references=references, digest=rows_digest)
                self.stdout.write(json.dumps(dict(status='PASS', created=False, families=result), sort_keys=True))
                return
            if options['verify_only']: raise CommandError('Guided history receipts do not exist')
            if (GuidedAvailabilityHistoryRow.objects.filter(run=run).exists() or
                    GuidedAvailabilitySnapshotReference.objects.filter(run=run).exists() or
                    GuidedExcessHistoryRow.objects.filter(run=run).exists()):
                raise CommandError('Unsealed Guided history rows exist; no replacement allowed')
            with connection.cursor() as cursor:
                cursor.execute("SELECT set_config('fresh.guided_history_build',%s,true)",
                               [str(run.pk)])
                self._availability(cursor, run)
                self._excess(cursor, run)
            families = {}
            for family in ('availability','excess'):
                count, references, rows_digest = rows_receipt(run, family)
                families[family] = dict(rows=count, references=references, digest=rows_digest)
            GuidedHistoryPreparedProjection.objects.bulk_create([
                GuidedHistoryPreparedProjection(run=run, family=family,
                    source_digest=admission, schema_digest=schema_digest(),
                    rows_digest=item['digest'], row_count=item['rows'],
                    reference_count=item['references'])
                for family, item in families.items()
            ])
            assert_unchanged(run, admission)
        self.stdout.write(json.dumps(dict(status='PASS', created=True, families=families,
                                         seconds=time.monotonic()-started), sort_keys=True))

    def _availability(self, cursor, run):
        relations = {}
        params = []
        for alias, path in (
                ('a', 'closing/btr/BPR'), ('s', 'closing/btr/SkuAttributeData'),
                ('l', 'closing/btr/LocationAttributeData'),
                ('p', 'closing/btr/SkuLocAttributeData'),
                ('n', 'closing/btr/BTRSnapshotForUI')):
            query, values = image_query(run, path)
            relations[alias] = query
            params.extend(values)
        snapshot_table = GuidedAvailabilitySnapshotReference._meta.db_table
        cursor.execute(
            'WITH a AS ('+relations['a']+'),s AS ('+relations['s']+'),l AS ('+relations['l']+
            '),p AS ('+relations['p']+'),n AS ('+relations['n']+'), anchors AS ('
            'SELECT n.*,min(n.vf_ordinal) OVER (PARTITION BY n."SKUCode",n."WhCode") anchor FROM n) '
            'INSERT INTO mta.'+quote(snapshot_table)+
            ' (run_id,snapshot_anchor_ordinal,snapshot_ordinal,age_physical_inventory) '
            'SELECT %s,anchor,vf_ordinal,"AgePhysicalInv" FROM anchors',
            params + [run.pk])
        target = GuidedAvailabilityHistoryRow._meta.db_table
        cursor.execute(
            'WITH a AS ('+relations['a']+'),s AS ('+relations['s']+'),l AS ('+relations['l']+
            '),p AS ('+relations['p']+'),n AS ('+relations['n']+'), anchors AS ('
            'SELECT "SKUCode","WhCode",min(vf_ordinal) anchor FROM n GROUP BY "SKUCode","WhCode"), joined AS ('
            'SELECT a.vf_ordinal fact_ordinal,s.vf_ordinal sku_ordinal,l.vf_ordinal location_ordinal,'
            'p.vf_ordinal pair_ordinal,anchors.anchor snapshot_anchor_ordinal,a."ReportDate" report_date,'
            'a."SKUCode" sku_code,a."WHCode" location_code,a."ParentWhCode" parent_location_code,'
            'l."LocationType" location_type,a."PhysicalInventoryColor" physical_inventory_color '
            'FROM a JOIN s ON '+exact('a."SKUCode"','s."SKUCode"')+
            ' JOIN l ON '+exact('a."WHCode"','l."WHCode"')+
            ' LEFT JOIN p ON '+exact('a."SKUCode"','p."SKUCode"')+' AND '+exact('a."WHCode"','p."LocCode"')+
            ' LEFT JOIN anchors ON '+exact('a."SKUCode"','anchors."SKUCode"')+' AND '+exact('a."WHCode"','anchors."WhCode"')+') '
            'INSERT INTO mta.'+quote(target)+
            ' (run_id,ordinal,fact_ordinal,sku_ordinal,location_ordinal,pair_ordinal,snapshot_anchor_ordinal,'
            'report_date,sku_code,location_code,parent_location_code,location_type,physical_inventory_color) '
            'SELECT %s,row_number() OVER (ORDER BY fact_ordinal,sku_ordinal,location_ordinal,pair_ordinal NULLS FIRST)-1,* FROM joined',
            params + [run.pk])

    def _excess(self, cursor, run):
        relations = {}
        params = []
        for alias, path in (
                ('s', 'closing/importer/SkuAttributeData'),
                ('l', 'closing/importer/LocationAttributeData'),
                ('p', 'closing/importer/SkuLocAttributeData')):
            query, values = image_query(run, path)
            relations[alias] = query
            params.extend(values)
        fact = 'mta.' + quote(ExcessInventoryRow._meta.db_table)
        target = 'mta.' + quote(GuidedExcessHistoryRow._meta.db_table)
        cursor.execute(
            'WITH s AS ('+relations['s']+'),l AS ('+relations['l']+'),p AS ('+relations['p']+'), joined AS ('
            'SELECT a.ordinal fact_ordinal,s.vf_ordinal sku_ordinal,l.vf_ordinal location_ordinal,'
            'p.vf_ordinal pair_ordinal,a."ReportDate" report_date,a."SKUCode" sku_code,a."WhCode" location_code,'
            'a."ParentWhCode" parent_location_code,l."LocationType" location_type,'
            'a."PhysicalInventoryColor" physical_inventory_color,a."Amount" amount '
            'FROM '+fact+' a JOIN s ON '+exact('a."SKUCode"','s."SKUCode"')+
            ' JOIN l ON '+exact('a."WhCode"','l."WHCode"')+
            ' LEFT JOIN p ON '+exact('a."SKUCode"','p."SKUCode"')+' AND '+exact('a."WhCode"','p."LocCode"')+
            ' WHERE a.run_id=%s) INSERT INTO '+target+
            ' (run_id,ordinal,fact_ordinal,sku_ordinal,location_ordinal,pair_ordinal,report_date,sku_code,'
            'location_code,parent_location_code,location_type,physical_inventory_color,amount) '
            'SELECT %s,row_number() OVER (ORDER BY fact_ordinal,sku_ordinal,location_ordinal,pair_ordinal NULLS FIRST)-1,* FROM joined',
            params + [run.pk, run.pk])
