import hashlib
from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase
from django.core.management import call_command

from mta.runtime.management.commands import register_cohort6_operational as command


class RegisterCohort6OperationalTests(SimpleTestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.configuration = {
            'source_digest': 's' * 64,
            'bindings': {'opening_input_digest': command.PLACEHOLDER,
                         'runner_policy': 'cohort2-integrated-materialization-v1'},
            'settings': [{'ordinal': 0, 'name': 'One', 'value': '1'}],
            'tables': [{'ordinal': 0, 'database_name': 'owned',
                        'table_name': 'DailyDataRaw', 'condition': None}],
            'alerts': [{'ordinal': 0, 'name': 'RunFinishAlert',
                        'active': False}],
        }
        self.receipt = {
            'status': 'SUCCEEDED',
            'run_id': '12345678-1234-5678-9234-567812345678',
            'business_date': '2026-06-06', 'input_digest': 'i' * 64,
            'output_digest': 'o' * 64, 'validation_digest': '',
            'evidence_mode': 'production', 'seconds': 1.0,
            'publication': 'unselected; parity and preparation are separate',
        }
        self.config_path = self.root / 'configuration.json'
        self.receipt_path = self.root / 'run.json'
        self.config_path.write_text(json.dumps(self.configuration), encoding='utf-8')
        self.receipt_path.write_text(json.dumps(self.receipt), encoding='utf-8')
        self.config_sha = hashlib.sha256(self.config_path.read_bytes()).hexdigest()

    def test_registers_exact_first_run_bound_configuration(self):
        source = SimpleNamespace(pk='source-1', digest='d' * 64,
            database_name='owned', receipt={'artifact_sha256': 'a' * 64,
                'artifact_schema': 'schema',
                'owned_namespace': {'database_name': 'owned'}})
        run = SimpleNamespace(kind='DAILY_CHAIN', status='SUCCEEDED',
            business_date='2026-06-06', input_digest='i' * 64,
            output_digest='o' * 64,
            mdm_input_capture=SimpleNamespace(source=source))
        manager = MagicMock()
        manager.select_related.return_value.get.return_value = run
        owner = SimpleNamespace(pk='configuration-1',
                                policy='cohort2-operational-effects-v1')
        expected = json.loads(json.dumps(self.configuration))
        expected['bindings']['opening_input_digest'] = 'i' * 64
        installed = {'policy': owner.policy, **expected}
        stream = StringIO()
        instance = command.Command(stdout=stream)
        with patch('mta.runtime.models.CalculationRun.objects', manager), \
                patch('mta.mdm.daily_source.require_binding') as require, \
                patch('mta.runtime.operational_attempts.register_configuration',
                      return_value=owner) as register, \
                patch('mta.runtime.operational_attempts.configuration_value',
                      return_value=installed):
            call_command(instance, configuration=self.config_path,
                sha256=self.config_sha, first_run_receipt=self.receipt_path,
                skip_checks=True)
            result = json.loads(stream.getvalue())
        register.assert_called_once_with(**expected)
        require.assert_called_once_with(source, artifact_sha256='a' * 64,
                                        artifact_schema='schema')
        self.assertEqual(result['configuration_id'], 'configuration-1')
        self.assertEqual(result['first_run']['input_digest'], 'i' * 64)

    def test_hash_placeholder_receipt_and_run_mismatch_deny(self):
        with self.assertRaisesRegex(ValueError, 'SHA256'):
            command.configuration_value(self.config_path, '0' * 64, 'i' * 64)
        changed = json.loads(json.dumps(self.configuration))
        changed['bindings']['opening_input_digest'] = 'already-bound'
        self.config_path.write_text(json.dumps(changed), encoding='utf-8')
        changed_sha = hashlib.sha256(self.config_path.read_bytes()).hexdigest()
        with self.assertRaisesRegex(ValueError, 'placeholder'):
            command.configuration_value(self.config_path, changed_sha, 'i' * 64)
        failed = dict(self.receipt, status='FAILED')
        self.receipt_path.write_text(json.dumps(failed), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'successful'):
            command.first_run_receipt(self.receipt_path)
