"""Typed publication proof; fixtures are connector cases, not demo facts."""
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import patch
from django.db import DatabaseError, transaction
from django.test import TestCase
from mta.presentation import daily_transit as transit
from mta.runtime.models import CalculationRun, DailyTransitRaw, DailyTransitRow
from mta.runtime.relational_state import load_image, save_image
from mta.serialization import digest


class DailyTransitPublicationTests(TestCase):
    def test_child_expedite_sql_adds_native_sources_without_leaking_parent_key(self):
        from mta.presentation import planning_expedite_sql as reader
        from django.test import override_settings
        run = self.run_row('child-grid')
        columns = dict.fromkeys([*reader.FIELDS, 'sap', 'ec', 'rlt', 'sl4', 'sl5', 'll4', 'll5'])
        columns.update(sc='A', wc='L', rlt=2, sap=1, pip=1, pin=1, p=None)
        columns.update(branch='dispatch', ordinal=0, weight=1, age=4, sk='a', lk='l', pk='p')
        from mta.runtime.relational_state import quote
        numeric = {'rlt','sap','pip','pin','p','ordinal','weight','age'}
        query = 'SELECT ' + ','.join('%s::'+('integer' if key == 'rlt' else 'numeric' if key in numeric else 'text')+' AS '+quote(key)
                                    for key in columns)
        shipment = dict.fromkeys(transit.processor.TRANSIT_FIELDS)
        shipment.update(SKUCode='A', WhCode='L', OrderNo='A/B', InTransitQty=5)
        request = dict(SKUCode='A', WhCode='L', ParentWhCode='P', Request='latest', RequestDate=None)
        with override_settings(VF_MTA_DAILY_PUBLICATION=True), \
                patch.object(reader, 'selected_parent', return_value=(query, list(columns.values()))), \
                patch('mta.presentation.daily_preparation.ancillary_row', return_value=[shipment]), \
                patch('mta.presentation.planning_expedite_requests.empty_requests', return_value=[request]):
            result = reader.child_grid(run, {})['data']['expediteDispatches'][0]
        self.assertEqual(result['remark'], 'latest')
        self.assertEqual(result['eta'], '2026-06-08T00:00:00')
        self.assertIn('A\\/B', result['intransit'])
        self.assertNotIn('pk', result)

    def test_daily_source_receipt_wires_current_attributes_without_carryforward(self):
        from mta.presentation import daily_sources, selective
        from django.test import override_settings
        run = self.run_row('source-integration')
        inputs = {
            'closing/dbm/VFSettings': [dict(Parameter='SuperDelayFactor', Value='1.5')],
            'closing/dbm/SKULocStandardAttributes': [dict(SKUCode='A', WhCode='L', SLT=None, Price=None)],
            'closing/consumer_context/GoodsInTransitTransporterMaster': [
                dict(TransporterCode='T', TransporterName='Test', TransporterContact=None)],
            'reports/bpr/vf_RationedReqReport': [dict(SKUCode='A', WhCode='L', ParentWhCode='P', GIT=10,
                PhysicalInventoryPen='1.250', PhysicalInventoryColor='Red', DispatchColor='Red')],
        }
        run.production_manifest = {'images': {path: save_image(run, path, path, rows)
                                             for path, rows in inputs.items()}}
        with override_settings(VF_MTA_DAILY_PUBLICATION=True):
            receipt = daily_sources.write_sources(run, {}, opening={'shipment_input': self.source()})
            self.assertEqual(receipt.images[transit.PATH]['count'], 2)
            rows = selective.image_rows(run, transit.PATH)
            self.assertIsNone(rows[0]['SLT'])
            self.assertIsNone(rows[0]['ETA'])
            sql, params = selective.image_query(run, transit.PATH)
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute(sql, params)
                self.assertEqual(len(cursor.fetchall()), 2)

    def run_row(self, suffix):
        return CalculationRun.objects.create(kind='DAILY_CHAIN', status='RUNNING',
            business_date=date(2026, 6, 6), input_digest=digest(suffix),
            execution_revision='transit-'+suffix, input_payload={})

    def source(self):
        row = dict.fromkeys(transit.processor.RAW_FIELDS)
        row.update(SKUCode='A', ToLocationCode='L', FromLocationCode='P',
            TransporterCode='T', InTransitQty=5, CreationDate='2026-06-01',
            GateOutDate='2026-06-02', ReportDate='2026-06-06')
        return dict(schema='daily-transit-raw-v1', business_date='2026-06-06',
                    provenance={'connector_fixture': 'typed-duplicates'}, rows=[row, dict(row)])

    def publish(self, run, source):
        return transit.publish(run, source,
            standards=[dict(SKUCode='A', WhCode='L', SLT=None, Price=None)],
            directory=[dict(TransporterCode='T', TransporterName='Test', TransporterContact=None)],
            rationed_report=[dict(SKUCode='A', WhCode='L', ParentWhCode='P', GIT=10,
                PhysicalInventoryPen=Decimal('1.250'), PhysicalInventoryColor='Red', DispatchColor='Red')],
            super_delay_factor=Decimal('1.5'), run_timestamp=datetime(2026, 6, 6, 8))

    def test_duplicates_null_attributes_and_typed_readback(self):
        run = self.run_row('duplicates')
        images = self.publish(run, self.source())
        rows = transit.read_rows(run, transit.PATH, images[transit.PATH])
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0], rows[1])
        self.assertIsNone(rows[0]['SLT'])
        self.assertIsNone(rows[0]['ETA'])
        report = load_image(run, images[transit.TRANSPORTER_PATH])
        self.assertEqual(len(report), 2)
        self.assertIsNone(report[0]['Price'])
        self.assertIsNone(report[0]['TruckStatus'])
        self.assertEqual(report[0]['PhysicalInventoryPen'], '1.250')
        with self.assertRaises(DatabaseError), transaction.atomic():
            DailyTransitRow.objects.filter(run=run).update(InTransitQty=999)

    def test_explicit_empty_has_metadata_but_missing_source_is_denied(self):
        run = self.run_row('empty')
        with self.assertRaisesRegex(ValueError, 'provenance'):
            self.publish(run, None)
        source = self.source(); source['rows'] = []
        images = self.publish(run, source)
        self.assertEqual(transit.read_rows(run, transit.PATH, images[transit.PATH]), [])
        self.assertEqual(images[transit.PATH]['count'], 0)
        self.assertEqual(len(images[transit.PATH]['fields']), 16)

    def test_publication_rollback_leaves_no_partial_raw_or_validated_rows(self):
        run = self.run_row('rollback')
        with self.assertRaisesRegex(RuntimeError, 'later publication failure'):
            with transaction.atomic():
                self.publish(run, self.source())
                raise RuntimeError('later publication failure')
        self.assertFalse(DailyTransitRaw.objects.filter(run=run).exists())
        self.assertFalse(DailyTransitRow.objects.filter(run=run).exists())

    def test_finished_run_rejects_new_occurrences(self):
        run = self.run_row('finished')
        run.status='FAILED'; run.save(update_fields=['status'])
        with self.assertRaises(DatabaseError), transaction.atomic():
            DailyTransitRaw.objects.create(run=run, ordinal=0)
