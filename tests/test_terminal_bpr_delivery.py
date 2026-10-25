"""Terminal reuse must not bypass scope, byte equality or the approved policy."""
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY', 'unit-only')
import django
django.setup()
from contextlib import ExitStack
from io import BytesIO
from types import SimpleNamespace as NS
from unittest import TestCase
from unittest.mock import patch
from mta.presentation import terminal_bpr_delivery as delivery, pick_downloads as pick


class TerminalBprDeliveryTests(TestCase):
    def test_policy_cannot_replace_capture_or_apply_to_another_owner(self):
        self.assertFalse(delivery.applicable(NS(pk='another-run')))
        with patch.object(delivery, 'binding', side_effect=AssertionError('must reject first')):
            for day in ({}, {'production_report_schema': 'fresh-production-source-inputs-v1',
                             'production_report_policy': {}}):
                with self.assertRaisesRegex(ValueError, 'original_policy'):
                    delivery.output_policy(NS(), day)

    def test_retained_file_requires_scope_and_exact_terminal_population_bytes(self):
        for allowed, actual in ((False, b'accepted'), (True, b'changed'), (True, b'acceptedextra'), (True, b'accepted')):
            stream = BytesIO(actual)
            with self.subTest(allowed=allowed, actual=actual), ExitStack() as stack:
                stack.enter_context(patch.object(delivery, 'binding', return_value=NS(bpr=NS(sources=NS(
                    acceptance_id='phase', acceptance_digest='digest')))))
                stack.enter_context(patch.object(pick, '_complete_state', return_value={}))
                stack.enter_context(patch.object(pick, '_fully_scoped', return_value=allowed))
                stack.enter_context(patch.object(pick, '_expected_chunks', return_value=iter((b'accepted',))))
                opened = stack.enter_context(patch('mta.runtime.scoped_pick_files.open_file', return_value=stream))
                if allowed and actual == b'accepted':
                    result, name = delivery.open_report(NS(), {}, 'LogisticPickListReport')
                    self.assertIs(result, stream)
                    self.assertEqual(result.tell(), 0)
                    self.assertEqual(name, pick.REPORTS['LogisticPickListReport'])
                    stream.close()
                else:
                    with self.assertRaises(pick.PickDownloadDenied):
                        delivery.open_report(NS(), {}, 'LogisticPickListReport')
                    if allowed: self.assertTrue(stream.closed)
                    else: opened.assert_not_called()

    def test_missing_archive_declaration_does_not_fall_back_or_generate(self):
        with patch('mta.presentation.scoped_artifacts.configured', return_value=None), \
                patch('mta.presentation.scoped_artifacts.open_archive') as opened:
            with self.assertRaisesRegex(ValueError, 'not_configured'):
                delivery.open_archive(NS())
            opened.assert_not_called()

    def test_bor_download_keeps_exact_policy_gate(self):
        with patch.object(delivery, 'binding', return_value=NS()), \
                patch('mta.presentation.scoped_bor.policy', side_effect=ValueError('policy denied')), \
                patch('mta.presentation.scoped_batch_downloads.open_file') as opened:
            with self.assertRaisesRegex(ValueError, 'policy denied'):
                delivery.open_report(NS(), {}, 'BOR_OrderAllocation')
            opened.assert_not_called()
