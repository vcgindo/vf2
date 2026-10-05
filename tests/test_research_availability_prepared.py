"""Focused boundaries for exact Research availability band preparation."""
import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY', 'unit-only')
import django
django.setup()

from django.core.management.base import CommandError

from mta.presentation import research_availability_preparation as subject
from mta.runtime.management.commands import prepare_research_availability as command
from mta.runtime.models import ResearchAvailabilityBand


class ResearchAvailabilityPreparationShapeTest(unittest.TestCase):
    def setUp(self):
        self.run = SimpleNamespace(pk=subject.RUN_ID)

    def test_query_is_one_to_one_with_existing_membership_and_preserves_raw_codes(self):
        with patch.object(subject, 'image_query', return_value=('SELECT * FROM physical_source', ['image'])):
            sql, params = subject.bands_query(self.run)
        self.assertEqual(params, ['image', subject.RUN_ID])
        self.assertIn('M.ordinal AS "ordinal"', sql)
        self.assertIn('M.history_ordinal AS "history_ordinal"', sql)
        self.assertIn('A."SKUCode" AS "sku_code"', sql)
        self.assertIn('A."WhCode" AS "location_code"', sql)
        self.assertIn('JOIN A ON A.vf_ordinal=M.history_ordinal', sql)
        self.assertIn('WHERE M.run_id=%s ORDER BY M.ordinal', sql)
        self.assertNotIn('lower(', sql)
        self.assertNotIn('rtrim(', sql)
        self.assertNotIn('DISTINCT', sql)
        self.assertNotIn('SkuAttributeData', sql)
        self.assertNotIn('LocationAttributeData', sql)
        self.assertNotIn('SkuLocAttributeData', sql)

    def test_query_has_six_integer_band_counts_over_all_ninety_days(self):
        with patch.object(subject, 'image_query', return_value=('SELECT * FROM physical_source', [])):
            sql, _ = subject.bands_query(self.run)
        for name in (
            'black_01_30', 'recognized_01_30', 'black_31_60',
            'recognized_31_60', 'black_61_90', 'recognized_61_90',
        ):
            self.assertIn('AS "' + name + '"', sql)
        self.assertEqual(sql.count(" IN ('Black')"), 90)
        self.assertEqual(sql.count("'Black','Red','Yellow','Green','Blue','White'"), 90)
        for day in range(1, 91):
            self.assertEqual(sql.count('A."D' + str(day) + '"'), 2)

    def test_model_retains_only_occurrence_identity_codes_and_six_counts(self):
        names = [field.name for field in ResearchAvailabilityBand._meta.local_fields]
        self.assertEqual(names, [
            'id', 'run', 'ordinal', 'history_ordinal', 'sku_code', 'location_code',
            'black_01_30', 'recognized_01_30', 'black_31_60', 'recognized_31_60',
            'black_61_90', 'recognized_61_90',
        ])

    def test_guards_are_separate_and_bind_receipt_to_history_membership(self):
        self.assertIn('fresh_mta_historypreparedprojection', subject.FORWARD)
        self.assertIn('NEW.membership_digest', subject.FORWARD)
        self.assertIn('availability_digest', subject.FORWARD)
        self.assertIn('availability_count', subject.FORWARD)
        self.assertIn('rows and receipt are immutable', subject.FORWARD)
        self.assertNotIn('UPDATE mta.fresh_mta_historypreparedprojection', subject.FORWARD)


class ResearchAvailabilityCommandContractTest(unittest.TestCase):
    def test_history_source_must_match_existing_sealed_receipt(self):
        run = SimpleNamespace(pk=subject.RUN_ID)
        receipt = SimpleNamespace(
            status='READY', source_digest='source', dimension_digest='dimensions',
            recipe_digest='history-recipe', availability_count=97299,
            availability_digest='membership',
        )
        with patch.object(command.history_preparation, 'verify_guards'), \
             patch.object(command.HistoryPreparedProjection.objects, 'filter') as query, \
             patch.object(command.history_preparation, 'source_signatures', return_value='dimensions'), \
             patch.object(command.history_preparation, 'recipe_digest', return_value='history-recipe'):
            query.return_value.first.return_value = receipt
            self.assertEqual(command.accepted_history_source(run, 'source'), (97299, 'membership'))
            receipt.source_digest = 'changed'
            with self.assertRaisesRegex(CommandError, 'absent or changed'):
                command.accepted_history_source(run, 'source')

    def test_hash_rows_rejects_non_contiguous_membership_ordinal(self):
        class Cursor:
            batches = [[(1, 9, 'sku', 'loc', 0, 30, 0, 30, 0, 30)], []]
            def fetchmany(self, size):
                return self.batches.pop(0)
        with self.assertRaisesRegex(CommandError, 'ordinal population differs'):
            command._hash_rows(Cursor())


if __name__ == '__main__':
    unittest.main()
