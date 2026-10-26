"""Registration/request representation boundaries, not native capture proof."""
from copy import deepcopy
import json
import unittest
from unittest.mock import patch

from mta.runtime import runtime_report_registered_request as registered
from mta.runtime import runtime_report_request as placement
from mta.serialization import digest
from tests.test_report_definition_registration import encode, INIT


class RegisteredRequestTests(unittest.TestCase):
    def setUp(self):
        self.release = patch('release.native_identity.require_current',
                             return_value={'local-test': 'release-a'})
        self.release.start(); self.addCleanup(self.release.stop)

    def request(self, scope='UptoBPR'):
        stored = encode()
        with patch.object(registered.registrations, 'read', return_value=stored) as read:
            value = registered.request(scope, 'new-owned-command',
                registration_digest=stored['registration_digest'],
                initialization_id=INIT, source_digest='b'*64)
        read.assert_called_once_with(stored['registration_digest'],
                                     initialization_id=INIT, source_digest='b'*64)
        return value

    def test_factory_uses_persisted_registration_and_round_trips_all_scopes(self):
        for scope in placement.SCOPES:
            with self.subTest(scope=scope):
                value = self.request(scope)
                self.assertEqual(registered.validate_request(value['report_registration_request'], value['scope_request']), value['report_registration_request'])
                self.assertEqual(registered.validate_read_request(value['report_registration_request'], value['scope_request']), value['report_registration_request'])
                definition = json.loads(value['scope_request']['runtime_reports']['configuration_json'])
                for row in definition['RuntimeReports']:
                    del row['LastGeneratedFileName']
                # Registration binds the whole native configuration, including
                # disabled UI settings; placement.DEFINITIONS_DIGEST binds only
                # the eight-row RuntimeReports roster. These are different cuts.
                self.assertEqual(value['report_registration_request']['registration']['definition_digest'], digest(definition))
                self.assertEqual(value['report_registration_request']['registration']['seed_digest'],
                                 placement.FILENAME_SEED_DIGEST)
        with patch.object(registered.registrations, 'read', side_effect=ValueError('not installed')):
            with self.assertRaisesRegex(ValueError, 'not installed'):
                registered.request('UptoBPR', 'key', registration_digest='f'*64,
                                   initialization_id=INIT, source_digest='b'*64)

    def test_inner_request_is_unchanged_and_attachment_cannot_be_executed(self):
        current = self.request()
        old = placement.request('UptoBPR', 'new-owned-command',
                                runtime_reports=current['scope_request']['runtime_reports'])
        self.assertEqual(current['scope_request'], old)
        self.assertEqual(placement.validate_request(old), old)
        with self.assertRaises(ValueError):
            placement.validate_request(current['report_registration_request'])
        with self.assertRaises(ValueError):
            registered.validate_request(old, old)
        from mta.runtime.production_scope import validate_request
        self.assertEqual(validate_request(current['scope_request']), old)
        with self.assertRaises(ValueError): validate_request(current)

    def test_read_does_not_reseal_execution_identity(self):
        value = self.request('UptoDBM'); before = deepcopy(value)
        with patch('release.native_identity.require_current', return_value={'local-test': 'release-b'}):
            with self.assertRaises(ValueError):
                registered.validate_request(value['report_registration_request'], value['scope_request'])
            self.assertEqual(registered.validate_read_request(value['report_registration_request'],
                             value['scope_request']), before['report_registration_request'])
        self.assertEqual(value, before)
        value['scope_request']['compatibility_digest'] = 'bad'
        with self.assertRaises(ValueError):
            registered.validate_read_request(value['report_registration_request'], value['scope_request'])

    def test_rehashed_binding_cannot_hide_changed_definition_seed_or_policy(self):
        for key in ('definition_digest', 'seed_digest', 'configuration_digest',
                    'reference_digest', 'policy_digest'):
            value = self.request()
            value['report_registration_request']['registration'][key] = 'f'*64
            header = {k: v for k, v in value['report_registration_request']['registration'].items()
                      if k != 'registration_digest'}
            value['report_registration_request']['registration']['registration_digest'] = digest(header)
            with self.subTest(key=key), self.assertRaises(ValueError):
                registered.validate_read_request(value['report_registration_request'], value['scope_request'])
        for key in ('certificate_id', 'certificate_digest', 'source_digest', 'initialization_id'):
            value = self.request()
            value['report_registration_request']['registration'][key] = ('20000000-0000-4000-8000-000000000001'
                if key.endswith('_id') else 'f'*64)
            with self.subTest(key=key), self.assertRaises(ValueError):
                registered.validate_request(value['report_registration_request'], value['scope_request'])

    def test_whole_inner_request_and_attachment_are_bound(self):
        original = self.request()
        for key in ('scope', 'command_key', 'report_hooks', 'dispositions', 'publication_recipe'):
            value = deepcopy(original)
            value['scope_request'][key] = {'scope': 'PostBPR', 'command_key': 'other-key', 'report_hooks': {},
                          'dispositions': {}, 'publication_recipe': 'f'*64}[key]
            with self.subTest(key=key), self.assertRaises(ValueError):
                registered.validate_request(value['report_registration_request'], value['scope_request'])
        for key in ('scope_request_digest','attachment_digest','attachment_recipe'):
            value = deepcopy(original); value['report_registration_request'][key] = 'f'*64
            with self.subTest(key=key), self.assertRaises(ValueError):
                registered.validate_read_request(value['report_registration_request'], value['scope_request'])
        value = deepcopy(original); value['report_registration_request']['registration']['arbitrary'] = True
        with self.assertRaises(ValueError):
            registered.validate_read_request(value['report_registration_request'], value['scope_request'])
        value = deepcopy(original); value['report_registration_request']['arbitrary'] = True
        with self.assertRaises(ValueError):
            registered.validate_read_request(value['report_registration_request'], value['scope_request'])


if __name__ == '__main__':
    unittest.main()
