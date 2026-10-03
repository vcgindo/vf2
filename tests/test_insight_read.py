"""Selective insight boundaries: native ownership and failure propagation."""
from datetime import date
from types import SimpleNamespace
import unittest
import os
from unittest.mock import patch

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY', 'unit-test-only-not-a-serving-secret')
import django
django.setup()

from mta.presentation.insight_read import insight_context


class InsightReadTests(unittest.TestCase):
    def test_excess_uses_terminal_importer_attributes_and_checked_history(self):
        calls = []
        run = SimpleNamespace(business_date=date(2026, 6, 17))
        def read(selected, path):
            self.assertIs(selected, run)
            calls.append(path)
            return []
        with patch('mta.presentation.insight_read.selected_run', return_value=run), \
             patch('mta.presentation.insight_read.image_rows', side_effect=read), \
             patch('mta.presentation.insight_read.hierarchy.selected_manifest', return_value=None), \
             patch('mta.presentation.excess_history.selected_manifest', return_value={'bound': True}), \
             patch('mta.presentation.excess_history.read_history', return_value=[{'history': 1}]) as history:
            context = insight_context('excess-sku')
        self.assertEqual(calls, ['closing/importer/' + name for name in
            ('SkuAttributeData', 'LocationAttributeData', 'SkuLocAttributeData')])
        self.assertEqual(context.history, [{'history': 1}])
        history.assert_called_once_with(run, {'bound': True})

    def setUp(self):
        self.run = SimpleNamespace(business_date=date(2026, 6, 17))

    def test_dbm_insights_use_produced_master_not_action_overlay(self):
        calls = []
        def read(run, path):
            self.assertIs(run, self.run)
            calls.append(path)
            return [{'native': path}, {'native': path}]
        with patch('mta.presentation.insight_read.selected_run', return_value=self.run), \
             patch('mta.presentation.insight_read.image_rows', side_effect=read), \
             patch('mta.presentation.insight_read.hierarchy.selected_manifest', return_value=None), \
             patch('mta.presentation.context.read_outputs', side_effect=AssertionError('whole read')), \
             patch('mta.presentation.context.command_state', side_effect=AssertionError('action overlay')):
            context = insight_context('pie')
        self.assertEqual(context.dbm['DBMMaster'], [{'native':'closing/dbm/DBMMaster'}]*2)
        self.assertEqual(len(context.state['DBMNormSuggestionsData']), 2)
        self.assertNotIn('closing/btr/BPR', calls)
        self.assertNotIn('closing/consumer_context/NMSAllItems', calls)

    def test_corrupt_native_image_is_not_replaced_with_empty(self):
        with patch('mta.presentation.insight_read.selected_run', return_value=self.run), \
             patch('mta.presentation.insight_read.image_rows', side_effect=ValueError('checksum mismatch')):
            with self.assertRaisesRegex(ValueError, 'checksum mismatch'):
                insight_context('availability-ageing')

    def test_grid_requires_native_nms_even_when_chronic_population_empty(self):
        def read(run, path):
            if path == 'closing/consumer_context/NMSAllItems':
                raise ValueError('missing NMS image')
            return []
        with patch('mta.presentation.insight_read.selected_run', return_value=self.run), \
             patch('mta.presentation.insight_read.image_rows', side_effect=read), \
             patch('mta.presentation.insight_read.hierarchy.selected_manifest', return_value=None):
            with self.assertRaisesRegex(ValueError, 'missing NMS image'):
                insight_context('chronic-grid')


if __name__ == '__main__':
    unittest.main()
