"""Actual request builders; run with offline Django settings, no database."""
from copy import deepcopy
from types import SimpleNamespace
from pathlib import Path
import unittest
from unittest.mock import patch

from django import conf
from mta.runtime import runtime_report_registered_request as registered
from mta.serialization import digest
from tests import test_runtime_report_registered_request as request_tests
from tests.test_report_definition_registration import INIT


@unittest.skipUnless(conf.settings.configured, 'Offline Django settings required; no database used')
class RegisteredCaptureIdentityTests(unittest.TestCase):
    def setUp(self):
        global production_daily, temporal
        from mta.runtime import production_daily, temporal
        self.release = patch('release.native_identity.require_current',
                             return_value={'local-test': 'release-a'})
        self.release.start(); self.addCleanup(self.release.stop)
        self.request = request_tests.RegisteredRequestTests().request()
        self.inner = self.request['scope_request']
        self.outer = self.request['report_registration_request']
        self.initial = {'identity': 'retained-root', 'state': {}, 'opening_date': '2026-10-22'}
        self.day = {'business_date': '2026-10-23'}
        self.owner = SimpleNamespace(pk=INIT, source=SimpleNamespace(digest='b'*64),
            input_sha256='c'*64, input_digest='d'*64, configuration_digest='e'*64)
        self.binding = dict(id=INIT, source_digest='b'*64, input_sha256='c'*64,
                            content_digest='d'*64, configuration_digest='e'*64)
        self.lineage = dict(opening_identity='retained-root', opening_digest=digest(self.initial),
                            initialization_id=INIT)
        self.root = temporal.resolved_pick_root(Path(__file__).parent)
        self.arguments = dict(day=self.day, profile={}, initial=self.initial,
            lineage=self.lineage, initialization_binding=self.binding,
            daily_input_sha256='f'*64, complete_pick=True, pick_output_root=self.root,
            scope_request=self.inner)

    def test_old_input_shape_and_digest_are_unchanged_when_attachment_absent(self):
        expected = dict(schema='fresh-daily-chain-v1', day=self.day, profile={}, opening=self.initial,
            lineage=self.lineage, report_exceptions={}, initialization_binding=self.binding,
            daily_input_sha256='f'*64, pick_output_root=self.root, scope_request=self.inner)
        self.assertEqual(temporal.request_input(**self.arguments), expected)
        self.assertEqual(temporal.request_input(**self.arguments, report_registration_request=None), expected)
        self.assertNotIn('report_registration_request', expected)

    def test_attachment_enters_real_capture_digest_and_inspection_reconstruction(self):
        old = temporal.request_input(**self.arguments)
        actual = temporal.request_input(**self.arguments, report_registration_request=self.outer)
        expected = dict(old, report_registration_request=self.outer)
        self.assertEqual(actual, expected)
        self.assertNotEqual(digest(actual), digest(old))
        with patch.object(production_daily, 'decode', return_value={'day': self.day}), \
                patch.object(production_daily, 'working_day', return_value=self.day):
            _day, _prior, checksum, binding = production_daily.inspection_request(
                b'offline-input', 'f'*64, self.owner,
                {'opening': self.initial, 'profile': {}}, None, None, self.root,
                scope_request=self.inner, report_registration_request=self.outer)
        self.assertEqual(checksum, digest(expected)); self.assertEqual(binding, self.binding)
        # Both builders are pure; neither caller-owned request is extended.
        self.assertNotIn('report_registration_request', old)
        self.assertNotIn('registration', self.inner)

    def test_foreign_initialization_and_mismatched_inner_refused_before_hashing(self):
        arguments = deepcopy(self.arguments)
        arguments['initialization_binding']['source_digest'] = 'a'*64
        with self.assertRaises(ValueError):
            temporal.request_input(**arguments, report_registration_request=self.outer)
        arguments = deepcopy(self.arguments)
        arguments['scope_request']['command_key'] = 'foreign'
        with self.assertRaises(ValueError):
            temporal.request_input(**arguments, report_registration_request=self.outer)

    def test_repeated_command_cannot_add_drop_or_replace_registration(self):
        run = object()
        old = dict(scope_request=self.inner)
        current = dict(old, report_registration_request=self.outer)
        with patch('mta.runtime.input_reader.read_input', return_value=old):
            registered.check_repeated(run, self.inner, None)
            with self.assertRaises(ValueError): registered.check_repeated(run, self.inner, self.outer)
        with patch('mta.runtime.input_reader.read_input', return_value=current):
            registered.check_repeated(run, self.inner, self.outer)
            with self.assertRaises(ValueError): registered.check_repeated(run, self.inner, None)
            changed = deepcopy(self.outer); changed['attachment_digest'] = 'f'*64
            with self.assertRaises(ValueError): registered.check_repeated(run, self.inner, changed)

    def resolve(self, arguments):
        return registered.request_for_execution(b'input', 'f'*64, scope='UptoBPR',
            command_key='new-owned-command',
            registration_digest=self.outer['registration']['registration_digest'], arguments=arguments)

    def test_frozen_repetition_uses_original_attachment_before_live_admission(self):
        arguments = dict(initialization_id=INIT, source_digest='b'*64, execution_revision='retained')
        owner = object()
        with patch.object(production_daily, 'decode', return_value={'day':self.day}), \
                patch.object(temporal.CalculationRun.objects, 'filter', return_value=[owner]) as find, \
                patch.object(registered, 'read_captured', return_value=self.outer) as read, \
                patch('mta.runtime.input_reader.read_input', return_value={'scope_request':self.inner}), \
                patch.object(registered, 'request', side_effect=AssertionError('live admission reached')):
            self.assertEqual(self.resolve(arguments), self.request)
            read.assert_called_once_with(owner)
            find.assert_called_once_with(kind='DAILY_CHAIN', business_date='2026-10-23',
                execution_revision='retained', mdm_input_capture__source__digest='b'*64)
            with patch.object(registered, 'read_captured', return_value=None):
                with self.assertRaisesRegex(ValueError, 'inner-only'): self.resolve(arguments)
            foreign = deepcopy(self.outer); foreign['registration']['source_digest']='a'*64
            with patch.object(registered, 'read_captured', return_value=foreign):
                with self.assertRaises(ValueError): self.resolve(arguments)

    def test_explicit_retry_resolves_original_run_before_live_factory(self):
        arguments = dict(initialization_id=INIT, source_digest='b'*64,
                         execution_revision='new-attempt', retry_capture_id='original-run')
        owner = object()
        with patch.object(production_daily, 'decode', return_value={'day':self.day}), \
                patch.object(temporal.CalculationRun.objects, 'filter', return_value=[]), \
                patch.object(temporal.CalculationRun.objects, 'get', return_value=owner) as find, \
                patch.object(registered, 'read_captured', return_value=self.outer), \
                patch('mta.runtime.input_reader.read_input', return_value={'scope_request':self.inner}), \
                patch.object(registered, 'request', side_effect=AssertionError('live factory reached')):
            self.assertEqual(self.resolve(arguments), self.request)
            find.assert_called_once_with(pk='original-run')
        # This tests selection order only; native preflight separately permits
        # the failed-capture successor exclusively for Full, not UptoBPR.

    def test_only_genuinely_new_capture_uses_live_registration(self):
        arguments = dict(initialization_id=INIT, source_digest='b'*64, execution_revision='new')
        with patch.object(production_daily, 'decode', return_value={'day':self.day}), \
                patch.object(temporal.CalculationRun.objects, 'filter', return_value=[]), \
                patch.object(registered, 'read_captured', side_effect=AssertionError('no frozen owner')), \
                patch.object(registered, 'request', return_value=self.request) as factory:
            self.assertEqual(self.resolve(arguments), self.request)
            factory.assert_called_once_with('UptoBPR', 'new-owned-command',
                registration_digest=self.outer['registration']['registration_digest'],
                initialization_id=INIT, source_digest='b'*64)


if __name__ == '__main__':
    unittest.main()
