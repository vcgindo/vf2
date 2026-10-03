"""Approval boundary tests; not synthetic engine or consumer parity receipts."""
from copy import deepcopy
from datetime import date
import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

os.environ.setdefault('VF_SECRET_KEY', 'unit-only')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
import django
django.setup()
from django.test import override_settings
from django.test import Client
from mta.presentation.context import PublicationUnavailable
from mta.presentation.terminal_supplement import terminal_ancillary
from mta.presentation.bpr_read import bpr_context
from mta.presentation.bpr_response import response_row
from decimal import Decimal


class TerminalSupplementTest(unittest.TestCase):
    def setUp(self):
        self.manifest = json.loads((Path(__file__).resolve().parents[1] / 'baseline/presentation-terminal-v1.json').read_text())
        binding = self.manifest['publication']
        self.run = SimpleNamespace(pk=binding['run_id'], business_date=date.fromisoformat(binding['business_date']),
                                   output_digest=binding['output_digest'])

    def read(self, manifest=None, run=None, expected=None):
        raw = json.dumps(self.manifest if manifest is None else manifest).encode()
        with override_settings(VF_MTA_TERMINAL_FILE='explicit.json',
                VF_MTA_TERMINAL_SHA256=expected or hashlib.sha256(raw).hexdigest()), \
             patch.object(Path, 'read_bytes', return_value=raw):
            return terminal_ancillary(run or self.run)

    def test_exact_opt_in_and_absence_are_distinct(self):
        self.assertEqual(self.read(), {'InTransitData': [], 'BPRReport_RemarkDetails': []})
        with override_settings(VF_MTA_TERMINAL_FILE='', VF_MTA_TERMINAL_SHA256=''):
            with self.assertRaisesRegex(PublicationUnavailable, 'not_configured'):
                terminal_ancillary(self.run)
        with self.assertRaisesRegex(PublicationUnavailable, 'hash_mismatch'):
            self.read(expected='wrong')

    def test_wrong_run_date_digest_and_populated_or_extended_inputs_rejected(self):
        for field, value in [('pk', 'other'), ('business_date', date(2026,6,16)), ('output_digest', 'other')]:
            with self.subTest(field=field), self.assertRaisesRegex(PublicationUnavailable, 'scope_mismatch'):
                self.read(run=SimpleNamespace(**{**vars(self.run), field:value}))
        for field, value in [('InTransitData', [{'invented':1}]), ('BPRReport_RemarkDetails', [{'Remark':'new'}]),
                             ('GoodsInTransitTransporterMaster', [])]:
            changed = deepcopy(self.manifest)
            changed['populations'][field] = value
            with self.subTest(field=field), self.assertRaisesRegex(PublicationUnavailable, 'scope_mismatch'):
                self.read(manifest=changed)

    def test_selective_reader_retains_duplicate_rows_and_no_output_mutation(self):
        original = [{'GIT':0}, {'GIT':0}]
        def read(run, path):
            return original if path.endswith('/BPR_Table') else []
        with patch('mta.presentation.bpr_read.selected_run', return_value=self.run), \
             patch('mta.presentation.bpr_read.terminal_ancillary', return_value=self.read()), \
             patch('mta.presentation.bpr_read.image_rows', side_effect=read) as selected, \
             patch('mta.presentation.bpr_read.hierarchy.selected_manifest', return_value=None):
            context = bpr_context()
            self.assertEqual(selected.call_count, 7)
            self.assertIs(context.output['BPRReports'][0]['BPR_Table'], original)
            self.assertEqual(len(original), 2)
            original[0]['GIT'] = 1
            with self.assertRaisesRegex(PublicationUnavailable, 'conflicts_with_published_git'):
                bpr_context()

    def test_wire_preserves_configured_numbers_and_dbnull_string_semantics(self):
        row = dict(intransit=None, Norm=220, TechPen=Decimal('12.50'), EcoPen=None,
                   Availability_01_30=Decimal('33.30'), sl4=None, SKUCode='337', ts=2)
        self.assertEqual(response_row(row), dict(intransit='',Norm=220,TechPen=12.5,EcoPen=None,
            Availability_01_30='33.30',sl4='',SKUCode='337',ts='2'))

    def test_http_rejects_invalid_pagination_before_read(self):
        client = Client()
        with patch('mta.presentation.bpr_read.bpr_context', side_effect=AssertionError('must not read')):
            for payload,status in [({},400), ({'paginationParameter':{'pageNumber':0,'recordsPerPage':5}},400),
                ({'filters':{'productFilter':{'filters':[{'attributeName':'sku','value':'337'}]}}},400)]:
                reply = client.post('/api/mta/GetBPRData',json.dumps(payload),content_type='application/json',
                    HTTP_X_VECTORFLOW_IDENTITY='{"id":"unit"}')
                self.assertEqual(reply.status_code,status)
            self.assertEqual(client.post('/api/mta/GetBPRData', '{}',content_type='application/json').status_code,403)


if __name__ == '__main__':
    unittest.main()
