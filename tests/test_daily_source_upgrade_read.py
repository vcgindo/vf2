"""Qualify every retained source consumer after the action admission change."""
import os
import unittest


@unittest.skipUnless(os.environ.get('VF_IR3_DAILY_SOURCE_PG') == '1', 'retained PostgreSQL read proof')
class RetainedSourceReadTests(unittest.TestCase):
    def test_all_retained_daily_source_images_keep_original_receipts(self):
        from django.db import connection, transaction
        from mta.runtime.models import CalculationRun, DailySourceReceipt
        from mta.presentation import daily_sources
        from mta.serialization import digest
        self.assertEqual(connection.settings_dict['NAME'], 'vftest_fresh_ir3_category_20261103')
        with transaction.atomic(), connection.cursor() as cursor:
            cursor.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
            runs=list(CalculationRun.objects.filter(status='SUCCEEDED').order_by('business_date'))
            self.assertEqual(len(runs),8)
            before=list(DailySourceReceipt.objects.order_by('run_id').values())
            count=0
            for run in runs:
                receipt=daily_sources.receipt(run)
                self.assertEqual(receipt.recipe_digest,daily_sources.RETAINED_ACTION_ADMISSION_RECIPE)
                self.assertEqual(receipt.images_digest,digest(receipt.images))
                for path in receipt.images:
                    # Each existing source reader checks its own typed rows,
                    # multiplicity and storage/producer ownership.
                    list(daily_sources.image_rows(run,path))
                    count+=1
            self.assertGreater(count,0)
            self.assertEqual(list(DailySourceReceipt.objects.order_by('run_id').values()),before)
            print('Retained complete daily source images read:',count,flush=True)
