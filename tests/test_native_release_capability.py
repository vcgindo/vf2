"""Focused immutable capability binding tests with database connections forbidden."""
import os
import unittest
from unittest.mock import patch

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY', 'source-only-capability-test')
import django
with patch('django.db.backends.base.base.BaseDatabaseWrapper.ensure_connection', side_effect=AssertionError('Database forbidden')):
    django.setup()
from mta.mdm import owned_namespace as owned
from mta.serialization import digest


class NativeReleaseCapabilityTests(unittest.TestCase):
    def setUp(self):
        self.block = patch('django.db.backends.base.base.BaseDatabaseWrapper.ensure_connection', side_effect=AssertionError('Database forbidden'))
        self.block.start()
        self.addCleanup(self.block.stop)
        self.release = {'source_commit': 'a'*40, 'manifest_sha256': 'b'*64}
        self.pin = patch('release.native_identity.require_current', return_value=self.release)
        self.pin.start()
        self.addCleanup(self.pin.stop)
        self.original = {'adapter_sha256': 'c'*64, 'artifact_sha256': 'd'*64}
        self.catalogue = {'objects_digest': 'e'*64, 'grants_digest': 'f'*64, 'schema_digest': '1'*64}
        self.binding = dict(policy=owned.PRODUCTION_APPLICATION_POLICY, original_registration=self.original,
            original_implementation_sha256='c'*64, implementation_sha256='c'*64,
            profile_digest=owned._production_application_profile_digest(),
            release_identity=self.release, **self.catalogue)
        self.binding['receipt_digest'] = digest(self.binding)

    def verify(self, **kwargs):
        return owned._validate_application_binding(kwargs.get('binding', self.binding), self.original,
            kwargs.get('implementation', 'c'*64), kwargs.get('catalogue', self.catalogue), production=True)

    def test_fresh_release_retains_original_input_and_receipt_identity(self):
        result = self.verify()
        self.assertEqual(result['artifact_sha256'], self.original['artifact_sha256'])
        self.assertEqual(result['receipt_digest'], self.binding['receipt_digest'])

    def test_source_schema_implementation_and_receipt_changes_deny(self):
        for key, value in (('release_identity', {}), ('schema_digest', '0'*64),
                           ('implementation_sha256', '0'*64), ('receipt_digest', '0'*64)):
            binding = {**self.binding, key: value}
            if key != 'receipt_digest':
                binding['receipt_digest'] = digest({k:v for k,v in binding.items() if k != 'receipt_digest'})
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.verify(binding=binding)

    def test_additional_fields_historical_policy_or_privilege_drift_deny(self):
        for binding in ({**self.binding, 'allowlist': []},
                        {**self.binding, 'policy': owned.APPLICATION_POLICY}):
            with self.assertRaises(ValueError):
                self.verify(binding=binding)
        with self.assertRaises(ValueError):
            self.verify(catalogue={**self.catalogue, 'grants_digest': '0'*64})
