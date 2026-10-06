"""Unselected startup must never admit a report or hide an invalid selection."""
import os
import unittest
import io
from types import SimpleNamespace
from unittest.mock import Mock, patch
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY', 'isolated-proof')
import django
django.setup()
from django.test import override_settings
from mta.presentation import admission


class DailyShellTests(unittest.TestCase):
    def test_selection_emits_nothing_when_native_readback_fails(self):
        from mta.runtime.management.commands.check_daily_selection import Command
        run = SimpleNamespace(kind='DAILY_CHAIN', status='SUCCEEDED',
            output_digest='expected', parity_summary={'status':'PASS'})
        output = io.StringIO()
        with patch('mta.runtime.management.commands.check_daily_selection.CalculationRun.objects.get',
                   return_value=run), patch.object(admission, 'verify',
                   side_effect=ValueError('native readback drift')):
            with self.assertRaisesRegex(ValueError, 'native readback drift'):
                Command(stdout=output).handle(run_id='test-only', output_digest='expected')
        self.assertEqual(output.getvalue(), '')

    @override_settings(VF_MTA_DAILY_PUBLICATION=True, VF_MTA_ALLOW_UNSELECTED_STARTUP=True,
        VF_MTA_PUBLISHED_RUN='', VF_MTA_PUBLISHED_DIGEST='', VF_MTA_FIXTURE_FILE='', VF_MTA_FIXTURE_SHA256='')
    def test_empty_shell_is_alive_but_reports_fail_closed(self):
        app = Mock(return_value=[b'alive'])
        with patch.object(admission, 'admit') as admit:
            wrapper = admission.AdmittedApplication(app)
            admit.assert_not_called()
        start = Mock()
        self.assertEqual(wrapper({'PATH_INFO':'/healthz'}, start), [b'alive'])
        app.reset_mock()
        response = wrapper({'PATH_INFO':'/api/mta/GetBPRDataGrid'}, start)
        self.assertEqual(response.status_code, 503)
        app.assert_not_called()

    @override_settings(VF_MTA_DAILY_PUBLICATION=True, VF_MTA_ALLOW_UNSELECTED_STARTUP=True,
        VF_MTA_PUBLISHED_RUN='invalid', VF_MTA_PUBLISHED_DIGEST='', VF_MTA_FIXTURE_FILE='', VF_MTA_FIXTURE_SHA256='')
    def test_partial_identity_does_not_use_empty_shell_exception(self):
        with patch.object(admission, 'admit', side_effect=ValueError('invalid selected identity')):
            with self.assertRaisesRegex(ValueError, 'invalid selected'):
                admission.AdmittedApplication(Mock())

    @override_settings(VF_MTA_DAILY_PUBLICATION=False, VF_MTA_ALLOW_UNSELECTED_STARTUP=True)
    def test_other_deployments_keep_existing_startup_contract(self):
        with patch.object(admission, 'admit', side_effect=ValueError('normal admission')):
            with self.assertRaisesRegex(ValueError, 'normal admission'):
                admission.AdmittedApplication(Mock())
