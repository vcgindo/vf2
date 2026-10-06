"""Regression for the actual day-one source failure, using migrated PostgreSQL."""
from copy import deepcopy
from decimal import Decimal
import uuid
from unittest.mock import patch

from django.db import connection, transaction, DatabaseError
from django.test import TestCase, override_settings

from mta.runtime.models import CalculationRun, DailyOpeningSob, DailySourceReceipt
from mta.presentation import daily_opening_sob as sob, daily_sources, selective


@override_settings(VF_MTA_DAILY_PUBLICATION=True)
class OpeningSobTests(TestCase):
    def run_owner(self, status='RUNNING'):
        return CalculationRun.objects.create(kind='DAILY_CHAIN', status=status,
            input_digest='i'*64, execution_revision='sob-'+str(uuid.uuid4()), input_payload={},
            business_date='2026-06-06')

    def row(self, value):
        return dict(SKUCode='6120', WHCode='LDC001', SupplierCode='PL001', SOB=value)

    def test_exact_source_types_duplicates_nulls_and_native_projection(self):
        for value in ('100.0000', 100, 100.0, None):
            run = self.run_owner()
            rows = [self.row(value), self.row(value)]
            opening = dict(supplier=dict(SOBData=rows, MOQData=[dict(
                SKUCode='6120', WHCode='LDC001', SupplierCode='PL001', MOQ=10)]))
            daily_sources.write_sources(run, {}, opening=opening)
            self.assertEqual(selective.image_rows(run, sob.PATH), rows)
            self.assertEqual(selective.image_field(run, sob.PATH, 'SOB'), [value, value])
            self.assertEqual(selective.image_rows(run, 'opening/supplier/MOQData'), opening['supplier']['MOQData'])
            sql, params = selective.image_query(run, sob.PATH)
            with connection.cursor() as cursor:
                cursor.execute('SELECT vf_ordinal,"SOB" FROM ('+sql+') x ORDER BY vf_ordinal', params)
                self.assertEqual(cursor.fetchall(), [(0, None if value is None else 100.0),
                                                     (1, None if value is None else 100.0)])
            if value is not None:
                self.assertIs(type(selective.image_rows(run, sob.PATH)[0]['SOB']), type(value))

    def test_mixed_type_denial_and_exact_digest_enforcement(self):
        run = self.run_owner()
        with self.assertRaisesRegex(ValueError, 'Non-scalar'):
            sob.save(run, [self.row(Decimal('100.0000'))])
        with self.assertRaisesRegex(ValueError, 'wire type'):
            sob.save(run, [self.row('100.0000'), self.row(100.0)])
        self.assertFalse(DailyOpeningSob.objects.filter(run=run).exists())
        item = sob.save(run, [self.row('100.0000')])
        changed = deepcopy(item); changed['digest'] = '0'*64
        with self.assertRaisesRegex(ValueError, 'value/type/multiplicity'):
            sob.read(run, changed)

    def test_empty_source_preserves_empty_metadata_field_contract(self):
        run = self.run_owner()
        daily_sources.write_sources(run, {}, opening={'supplier': {'SOBData': []}})
        self.assertEqual(selective.image_metadata(run, sob.PATH)['fields'], [])
        self.assertEqual(selective.image_rows(run, sob.PATH), [])
        from mta.presentation.context import PublicationUnavailable
        with self.assertRaises(PublicationUnavailable):
            selective.image_field(run, sob.PATH, 'SOB')

    def test_source_seal_running_owner_and_mutation_guards(self):
        run = self.run_owner()
        daily_sources.write_sources(run, {}, opening={'supplier': {'SOBData': [self.row('100.0000')]}})
        for action in (
            lambda: DailyOpeningSob.objects.create(run=run, ordinal=1),
            lambda: DailyOpeningSob.objects.filter(run=run).update(SOB=1),
            lambda: DailyOpeningSob.objects.filter(run=run).delete(),
        ):
            with self.assertRaises(DatabaseError), transaction.atomic(): action()
        with self.assertRaises(DatabaseError), transaction.atomic(), connection.cursor() as cursor:
            cursor.execute('TRUNCATE mta.fresh_mta_dailyopeningsob')
        complete = self.run_owner(status='SUCCEEDED')
        with self.assertRaises(DatabaseError), transaction.atomic():
            sob.save(complete, [self.row('100.0000')])

    def test_late_source_readback_failure_rolls_back_all_rows(self):
        run = self.run_owner()
        with self.assertRaisesRegex(ValueError, 'injected'), transaction.atomic(), \
                patch.object(sob, 'read', side_effect=ValueError('injected readback mismatch')):
            daily_sources.write_sources(run, {}, opening={'supplier': {'SOBData': [self.row('100.0000')]}})
        self.assertFalse(DailyOpeningSob.objects.filter(run=run).exists())
        self.assertFalse(DailySourceReceipt.objects.filter(run=run).exists())
