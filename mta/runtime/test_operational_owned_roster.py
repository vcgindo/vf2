"""The integrated roster requires the ownership artifact exactly when produced."""
from datetime import date
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch
from mta.runtime.operational_runner import _expected_files, verify_required_outputs


class OwnedBackupRosterTests(TestCase):
    def roster(self, backup):
        owner = SimpleNamespace(business_date=date(2026, 6, 6))
        config = {'bindings': {'input_export_database': 'retained',
            'upload_log_client_folder': None, 'postgres_backup': backup}}
        alerts = {'configuration': {'attach_invalid_data_report_zip': False},
                  'reports': {'phase_exceptions': []}}
        with patch('mta.runtime.operational_runner.read_population', return_value=[]), \
             patch('mta.runtime.operational_runner.read_alert_inputs', return_value=alerts):
            return _expected_files(owner, config)['O8']

    def test_original_and_explicit_none_keep_three_files(self):
        expected = {'backup/post.dump': [], 'backup/logical-source.json.gz': [],
                    'backup/logical-restored.json.gz': []}
        self.assertEqual(self.roster({}), expected)
        self.assertEqual(self.roster({'owned_restore': None}), expected)

    def test_owned_restore_requires_exact_additional_file(self):
        expected = self.roster({}) | {'backup/ownership.json': []}
        self.assertEqual(self.roster({'owned_restore': {'policy': 'fresh-owned-restore-v1'}}), expected)

    def test_missing_extra_and_archive_members_still_rejected(self):
        expected = self.roster({'owned_restore': {'policy': 'fresh-owned-restore-v1'}})
        for actual in [self.roster({}), expected | {'backup/unexpected.json': []},
                       expected | {'backup/ownership.json': ['unexpected']}]:
            files=[]
            for name, members in actual.items():
                files.append(SimpleNamespace(relative_path=name,
                    members=SimpleNamespace(values_list=lambda *args, _members=members, **kw: _members)))
            effect=SimpleNamespace(group='O8',files=SimpleNamespace(all=lambda: files))
            owner=SimpleNamespace(configuration=None,operations=SimpleNamespace(order_by=lambda *args: [effect]))
            with patch('mta.runtime.operational_runner.validate_configuration',return_value={}), \
                 patch('mta.runtime.operational_runner._expected_files',return_value={'O8': expected}):
                with self.assertRaisesRegex(ValueError,'artifact/member roster differs: O8'):
                    verify_required_outputs(owner)
