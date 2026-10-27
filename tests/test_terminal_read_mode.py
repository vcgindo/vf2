import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY', 'unit-only')
import django
django.setup()
from types import SimpleNamespace as NS
from unittest import TestCase
from unittest.mock import patch
from contextlib import ExitStack
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

    def test_registered_terminal_bpr_requires_all_existing_owners_without_configuration_change(self):
        from mta.presentation.daily_publication import configuration_identity
        run = NS(pk='registered-terminal', kind='DAILY_CHAIN', status='SUCCEEDED')
        checks = ('native_publication.require_mode', 'registered_report_view.configuration',
                  'native_selection.require_selected', 'native_publication.require_publication')
        with ExitStack() as stack:
            stack.enter_context(override_settings(VF_MTA_NATIVE_PUBLICATION=True,
                VF_MTA_DAILY_PUBLICATION=True, **{flag: False for flag in mode.FLAGS}))
            applicable = stack.enter_context(patch('mta.presentation.registered_report_view.applicable_run', return_value=True))
            owners = [stack.enter_context(patch('mta.presentation.' + name)) for name in checks]
            legacy = stack.enter_context(patch('mta.presentation.terminal_bpr_delivery.binding'))
            original = configuration_identity()
            for owner in owners:owner.reset_mock()
            self.assertTrue(mode.prepared('VF_BPR_PREPARED', run))
            applicable.assert_called_once_with(run)
            owners[0].assert_called_once_with()
            for owner in owners[1:]:owner.assert_called_once_with(run)
            self.assertEqual(configuration_identity(), original)
            self.assertFalse(settings.VF_BPR_PREPARED)
            legacy.assert_not_called()
            # This correction does not silently route other report families.
            for flag in mode.FLAGS - {'VF_BPR_PREPARED'}:
                self.assertFalse(mode.prepared(flag, run))
            applicable.reset_mock()
            applicable.return_value = False
            self.assertFalse(mode.prepared('VF_BPR_PREPARED', run))
            applicable.return_value = True
            for failed in owners:
                with self.subTest(owner=failed):
                    failed.side_effect = ValueError('owner validation refused')
                    with self.assertRaisesRegex(ValueError, 'owner validation refused'):
                        mode.prepared('VF_BPR_PREPARED', run)
                    failed.side_effect = None

    def test_unfinished_or_non_native_days_do_not_enter_registered_terminal_path(self):
        for native, daily, kind, status in ((False, True, 'DAILY_CHAIN', 'SUCCEEDED'),
                (True, False, 'DAILY_CHAIN', 'SUCCEEDED'),
                (True, True, 'DAILY_CHAIN', 'RUNNING'),
                (True, True, 'LEGACY_UI_FIXTURE', 'SUCCEEDED')):
            with self.subTest(native=native, daily=daily, kind=kind, status=status), \
                    override_settings(VF_MTA_NATIVE_PUBLICATION=native,
                        VF_MTA_DAILY_PUBLICATION=daily, VF_BPR_PREPARED=False), \
                    patch('mta.presentation.registered_report_view.applicable_run') as applicable:
                self.assertFalse(mode.prepared('VF_BPR_PREPARED', NS(pk='other', kind=kind, status=status)))
                applicable.assert_not_called()
