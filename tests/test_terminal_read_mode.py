import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY', 'unit-only')
import django
django.setup()
from types import SimpleNamespace as NS
from unittest import TestCase
from unittest.mock import patch
from django.test import override_settings
from django.conf import settings
from mta.presentation import terminal_read_mode as mode
from mta.runtime.bpr_history_completion import AUTHORITY


class TerminalReadModeTests(TestCase):
    def test_exact_completed_native_owner_uses_guarded_readers_without_changing_configuration(self):
        from mta.presentation.daily_publication import configuration_identity
        with override_settings(VF_MTA_NATIVE_PUBLICATION=True, VF_MTA_DAILY_PUBLICATION=True,
                               **{flag: False for flag in mode.FLAGS}):
            original = configuration_identity()
            run = NS(pk=AUTHORITY['run'], status='SUCCEEDED')
            with patch('mta.presentation.terminal_bpr_delivery.binding') as binding:
                for flag in mode.FLAGS:
                    self.assertTrue(mode.prepared(flag, run))
                    self.assertFalse(getattr(settings, flag))
                self.assertEqual(binding.call_count, len(mode.FLAGS))
            self.assertEqual(original, configuration_identity())
            with patch('mta.presentation.terminal_bpr_delivery.binding', side_effect=ValueError('changed owner')):
                with self.assertRaisesRegex(ValueError, 'changed owner'):
                    mode.prepared('VF_BPR_PREPARED', run)

    def test_other_owners_and_modes_keep_existing_flags(self):
        for native, daily, owner, status in ((False, True, AUTHORITY['run'], 'SUCCEEDED'),
                (True, False, AUTHORITY['run'], 'SUCCEEDED'),
                (True, True, 'another-run', 'SUCCEEDED'), (True, True, AUTHORITY['run'], 'RUNNING')):
            with self.subTest(native=native, daily=daily, owner=owner, status=status), \
                    override_settings(VF_MTA_NATIVE_PUBLICATION=native, VF_MTA_DAILY_PUBLICATION=daily,
                                      **{flag: False for flag in mode.FLAGS}), \
                    patch('mta.presentation.terminal_bpr_delivery.binding') as binding:
                for flag in mode.FLAGS:
                    self.assertFalse(mode.prepared(flag, NS(pk=owner, status=status)))
                binding.assert_not_called()
        with override_settings(VF_BPR_PREPARED=True):
            self.assertTrue(mode.prepared('VF_BPR_PREPARED', NS(pk='another-run')))
