"""Daily BPR reads produced transit; terminal-only empty guards stay scoped."""
import os
os.environ.setdefault('VF_SECRET_KEY', 'local-unit-test-only')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
import django
django.setup()
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from django.test import override_settings
from mta.presentation.bpr_read import bpr_context
from mta.presentation.context import PublicationUnavailable


class DailyBprContextTests(unittest.TestCase):
    def run_context(self, enabled):
        run = SimpleNamespace(kind='DAILY_CHAIN')
        transit = [{'SKUCode':'6120','WhCode':'DP010290','Quantity':12}]
        def rows(run, path):
            return [{'GIT':12}] if path=='reports/bpr/BPR_Table' else []
        ancillary = dict(InTransitData=transit, BPRReport_RemarkDetails=[])
        with override_settings(VF_MTA_DAILY_PUBLICATION=enabled), \
                patch('mta.presentation.bpr_read.selected_run',return_value=run), \
                patch('mta.presentation.bpr_read.image_rows',side_effect=rows), \
                patch('mta.presentation.bpr_read.hierarchy.selected_manifest',return_value=None), \
                patch('mta.presentation.bpr_read.terminal_ancillary',return_value=ancillary), \
                patch('mta.presentation.daily_preparation.ancillary_rows',return_value=ancillary):
            return bpr_context()

    def test_daily_positive_transit_uses_produced_source(self):
        context = self.run_context(True)
        self.assertEqual(context.ancillary['InTransitData'][0]['Quantity'],12)
        self.assertEqual(context.output['BPRReports'][0]['BPR_Table'],[{'GIT':12}])

    def test_terminal_positive_git_still_denied(self):
        with self.assertRaisesRegex(PublicationUnavailable,'terminal_empty_transit_conflicts'):
            self.run_context(False)

    def test_wire_preserves_nulls_duplicate_order_and_sql_json_string(self):
        import json
        from mta.presentation.bpr_response import response_row
        item = dict(lc='A/B',cd='2026-06-06',slt=None,tlt=0,ag=0,eta=None,
                    cl=None,qty=105,exeecocolor='Red',remarks=None)
        value = response_row(dict(intransit=[item,item],Stock=1),daily_transit=True)
        self.assertIsInstance(value['intransit'],str)
        self.assertIn('A\\/B',value['intransit'])
        self.assertEqual(json.loads(value['intransit']),[item,item])
        with self.assertRaises(PublicationUnavailable):response_row(dict(intransit=[item]))
        self.assertEqual(response_row(dict(intransit=None)),{'intransit':''})
