"""Opt-in real storage/rollback regression on an explicitly owned guard fixture."""
from decimal import Decimal
import hashlib
import os
import unittest
from uuid import uuid4

os.environ.setdefault('VF_SECRET_KEY', 'unit-only')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
import django
django.setup()

from django.db import connection, transaction, DatabaseError
from mta.presentation.btr_copy import write_batch
from mta.presentation.btr_snapshot import ROW_FIELDS
from mta.runtime.models import CalculationRun, BtrReportingGeneration, BtrPresentationRow


@unittest.skipUnless(os.environ.get('VF_BTR_COPY_POSTGRES_PROOF') == '1', 'Owned PostgreSQL guard fixture required')
class BtrCopyPostgresqlTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(connection.settings_dict['NAME'].startswith('vftest_fresh_btr_copy64_guard_'))
        with connection.cursor() as cursor:
            cursor.execute("SELECT shobj_description(oid,'pg_database') FROM pg_database WHERE datname=current_database()")
            self.assertTrue(cursor.fetchone()[0].startswith('Owned isolated full BTR COPY comparison'))
        self.qualified_run = CalculationRun.objects.filter(kind='DAILY_CHAIN', status='SUCCEEDED').first()
        self.assertIsNotNone(self.qualified_run, 'Owned fixture must explicitly provide qualified run metadata')

    def generation(self):
        return BtrReportingGeneration.objects.create(run=self.qualified_run, version=2,
            source_kind=self.qualified_run.kind, business_date=self.qualified_run.business_date,
            source_digest=hashlib.sha256(uuid4().bytes).hexdigest(), status='BUILDING')

    def rows(self, generation, count):
        return [BtrPresentationRow(generation=generation, branch='tech', a_ordinal=index,
            filter_e_norm=Decimal('1.23456789015') if index%2 else None,
            display_skudescription_text="O'Brien\tline\nback\\slash \\N Ω中",
            available_prefix=[0]*91, empty_prefix=[0]*91,
            nonfinite_fields=['D1'], nonfinite_tokens=[None]) for index in range(count)]

    def test_full_stored_fields_match_orm_including_branch_tail(self):
        with transaction.atomic():
            values=[]
            for copy in (False, True):
                generation=self.generation()
                rows=self.rows(generation,65)
                for batch in (rows[:64],rows[64:]):
                    if copy:write_batch(batch)
                    else:BtrPresentationRow.objects.bulk_create(batch,batch_size=64)
                stored=list(BtrPresentationRow.objects.filter(generation=generation)
                    .order_by('id').values_list(*ROW_FIELDS))
                self.assertEqual(len(stored),65)
                values.append(stored)
            self.assertEqual(values[0],values[1])
            norm=ROW_FIELDS.index('filter_e_norm')
            self.assertIsNone(values[1][0][norm])
            self.assertEqual(values[1][1][norm],Decimal('1.2345678902'))
            transaction.set_rollback(True)

    def test_late_server_error_rolls_back_earlier_batch_and_generation(self):
        identifier=None
        with self.assertRaises(DatabaseError):
            with transaction.atomic():
                generation=self.generation();identifier=generation.pk
                write_batch(self.rows(generation,64))
                batch=self.rows(generation,64);batch[-1].branch='invalid'
                write_batch(batch)
        self.assertFalse(BtrPresentationRow.objects.filter(generation_id=identifier).exists())
        self.assertFalse(BtrReportingGeneration.objects.filter(pk=identifier).exists())


if __name__ == '__main__':
    unittest.main()
