"""Focused routing contract checks; persisted admission remains a native proof."""
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY', 'unit-only')
import django
django.setup()
from contextlib import ExitStack
from types import SimpleNamespace as NS
from unittest import TestCase
from unittest.mock import patch
from django.test import override_settings
from mta.presentation import terminal_read_mode as mode


class TerminalReadModeTests(TestCase):
    def guards(self, stack):
        stack.enter_context(override_settings(VF_MTA_NATIVE_PUBLICATION=True,
            VF_MTA_DAILY_PUBLICATION=True, **{flag: False for flag in mode.FLAGS}))
        names = ('native_publication.require_mode', 'native_selection.require_selected',
                 'native_publication.require_publication', 'daily_publication.require_ready')
        owners = [stack.enter_context(patch('mta.presentation.' + name)) for name in names]
        owners[-1].return_value = NS(seal_digest='seal', configuration_digest='original')
        return owners

    def test_supported_terminal_contract_is_independent_of_run_identity_and_registration(self):
        from mta.presentation.daily_publication import configuration_identity
        for identity in ('new-full', 'new-completed-bpr', 'new-completed-dbm'):
            run = NS(pk=identity, kind='DAILY_CHAIN', status='SUCCEEDED')
            with ExitStack() as stack:
                owners = self.guards(stack)
                legacy = stack.enter_context(patch('mta.presentation.terminal_bpr_delivery.binding',
                    side_effect=AssertionError('historical custody is not a reader selector')))
                registration = stack.enter_context(patch('mta.presentation.registered_report_view.configuration',
                    side_effect=AssertionError('batch roster is not UI report authority')))
                before = configuration_identity()
                for owner in owners: owner.reset_mock()
                for flag in mode.FLAGS:
                    self.assertTrue(mode.prepared(flag, run))
                self.assertEqual(before, configuration_identity())
                for owner in owners[1:]: self.assertEqual(owner.call_args.args, (run,))
                self.assertEqual(owners[-1].call_count, len(mode.FLAGS))
                legacy.assert_not_called(); registration.assert_not_called()

    def test_every_existing_authority_fails_closed(self):
        run = NS(pk='unfamiliar', kind='DAILY_CHAIN', status='SUCCEEDED')
        for index in range(4):
            with ExitStack() as stack:
                owners = self.guards(stack)
                owners[index].side_effect = ValueError('owner refused')
                for flag in mode.FLAGS:
                    with self.assertRaisesRegex(ValueError, 'owner refused'):
                        mode.prepared(flag, run)

    def test_false_flag_does_not_override_non_native_or_intermediate_contract(self):
        for native, daily, kind, status in ((False, True, 'DAILY_CHAIN', 'SUCCEEDED'),
                (True, False, 'DAILY_CHAIN', 'SUCCEEDED'),
                (True, True, 'DAILY_CHAIN', 'RUNNING'),
                (True, True, 'LEGACY_UI_FIXTURE', 'SUCCEEDED')):
            with override_settings(VF_MTA_NATIVE_PUBLICATION=native,
                    VF_MTA_DAILY_PUBLICATION=daily, **{flag: False for flag in mode.FLAGS}), \
                    patch.object(mode, 'binding') as bound:
                for flag in mode.FLAGS:
                    self.assertFalse(mode.prepared(flag, NS(pk='any', kind=kind, status=status)))
                bound.assert_not_called()

    def test_explicit_legacy_opt_in_and_unknown_flag_are_preserved(self):
        with override_settings(**{flag: True for flag in mode.FLAGS}), patch.object(mode, 'binding') as bound:
            for flag in mode.FLAGS: self.assertTrue(mode.prepared(flag, NS(pk='legacy')))
            bound.assert_not_called()
        with self.assertRaisesRegex(ValueError, 'Unknown'):
            mode.prepared('NOT_A_READER_FLAG', NS())

    def test_binding_contains_only_verified_generation_references(self):
        with ExitStack() as stack:
            self.guards(stack)
            bound = mode.binding(NS(pk='selected', kind='DAILY_CHAIN', status='SUCCEEDED'))
            self.assertEqual(bound, mode.TerminalReaders('selected', 'seal', 'original'))
