"""Admission failures must never expose an unverified publication to HTTP."""
from contextlib import ExitStack
from datetime import date
from io import BytesIO
import os
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

os.environ.setdefault('VF_SECRET_KEY', 'test-only-not-a-serving-credential')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
import django
django.setup()
from django.test import RequestFactory, override_settings
from mta.presentation import admission
from mta.presentation import btr_reporting, fixture
from mta.presentation.context import PublicationUnavailable
from vectorflow.urls import ready


class AdmissionTest(unittest.TestCase):
    def test_planning_summary_rechecks_changed_generation_next_request(self):
        from mta.presentation.planning_summary_admission import require_ready
        from mta.presentation.request_scope import read_request
        with patch('mta.presentation.planning_summary_daily.require_ready',
                   side_effect=['receipt', PublicationUnavailable('generation changed')]) as check:
            with read_request('/api/mta/GetPlanningDataCount'):
                self.assertEqual(require_ready('run'), 'receipt')
                self.assertEqual(require_ready('run'), 'receipt')
            with read_request('/api/mta/GetPlanningDataCount'):
                with self.assertRaisesRegex(PublicationUnavailable, 'generation changed'):
                    require_ready('run')
            self.assertEqual(check.call_count, 2)

    def test_planning_summary_full_validation_and_offline_are_not_skipped(self):
        from mta.presentation.planning_summary_admission import require_ready
        from mta.presentation.request_scope import read_request
        with patch('mta.presentation.planning_summary_daily.require_ready',
                   return_value='receipt') as check:
            with read_request('/api/mta/GetPlanningDataCount'):
                require_ready('run')
                require_ready('run', verify_rows=True)
            require_ready('run')
            require_ready('run')
            self.assertEqual(check.call_count, 4)
            self.assertTrue(check.call_args_list[1].kwargs['verify_rows'])

    def setUp(self):
        self.run = SimpleNamespace(pk='accepted', business_date=date(2026, 6, 17), output_digest='native')
        self.addCleanup(setattr, admission, '_admitted', admission._admitted)
        admission._admitted = None

    def test_startup_checks_once_and_requests_only_check_identity(self):
        with patch.object(admission, 'binding', return_value=(self.run, 'identity')), \
                patch.object(admission, 'verify') as verify:
            proof = admission.admit()
            for _ in range(3):
                self.assertEqual(admission.require_admission(), 'identity')
            verify.assert_called_once_with(self.run)
            self.assertEqual(proof['output_digest'], 'native')
            self.assertEqual(admission._admitted, 'identity')

    def test_missing_identity_never_reaches_native_verification(self):
        with patch.object(admission, 'binding', side_effect=PublicationUnavailable('identity')), \
                patch.object(admission, 'verify') as verify:
            with self.assertRaises(PublicationUnavailable): admission.admit()
            verify.assert_not_called()
            self.assertIsNone(admission._admitted)

    def test_native_or_projection_integrity_failure_revokes_prior_admission(self):
        for error in ('Operational output checksum drift', 'Pick projection typed values/multiplicity drift'):
            admission._admitted = 'previous'
            with patch.object(admission, 'binding', return_value=(self.run, 'identity')), \
                    patch.object(admission, 'verify', side_effect=ValueError(error)):
                with self.assertRaisesRegex(ValueError, error): admission.admit()
                self.assertIsNone(admission._admitted)

    def test_identity_changed_during_verification_is_not_admitted(self):
        with patch.object(admission, 'binding', side_effect=[(self.run, 'before'), (self.run, 'after')]), \
                patch.object(admission, 'verify'):
            with self.assertRaisesRegex(PublicationUnavailable, 'changed_during'): admission.admit()
            self.assertIsNone(admission._admitted)

    def test_changed_run_projection_or_configuration_fails_until_new_startup(self):
        for changed in ('new-run', 'new-projection', 'new-config'):
            admission._admitted = 'old'
            with patch.object(admission, 'binding', return_value=(self.run, changed)), \
                    patch.object(admission, 'verify') as verify:
                with self.assertRaisesRegex(PublicationUnavailable, 'restart_required'):
                    admission.require_admission()
                self.assertIsNone(admission._admitted)
                verify.assert_not_called()
                # Even restoring old identity cannot silently bypass startup.
                with self.assertRaisesRegex(PublicationUnavailable, 'not_admitted'):
                    admission.require_admission()
                admission.admit()
                self.assertEqual(admission.require_admission(), changed)

    def test_failed_preload_aborts_startup_and_closes_database_before_fork(self):
        with patch.object(admission, 'admit', side_effect=ValueError('corrupt')), \
                patch.object(admission.logger, 'exception'), \
                patch.object(admission.connections, 'close_all') as close:
            with self.assertRaisesRegex(ValueError, 'corrupt'):
                admission.AdmittedApplication(Mock())
            close.assert_called_once()

    def test_transient_database_failure_rejects_request_without_poisoning_worker(self):
        admission._admitted = 'identity'
        downstream = Mock(return_value=[b'exact existing response'])
        start = Mock()
        with patch.object(admission, 'admit'), patch.object(admission.logger, 'warning'), \
                patch.object(admission.connections, 'close_all'), \
                patch.object(admission, 'verify') as verify:
            app = admission.AdmittedApplication(downstream)
            for error in (admission.OperationalError, admission.InterfaceError):
                with patch.object(admission, 'binding', side_effect=error('unavailable')):
                    self.assertIn(b'publication_not_admitted', b''.join(app({'PATH_INFO': '/api/mta/RRRData'}, start)))
                    self.assertEqual(start.call_args.args[0], '503 Service Unavailable')
                    downstream.assert_not_called()
                    self.assertEqual(admission._admitted, 'identity')
            with patch.object(admission, 'binding', return_value=(self.run, 'identity')):
                self.assertEqual(app({'PATH_INFO': '/api/mta/RRRData'}, start), [b'exact existing response'])
                downstream.assert_called_once()
                verify.assert_not_called()

    def test_wsgi_rejects_all_mta_routes_but_allows_health_after_revocation(self):
        downstream = Mock(return_value=[b'healthy'])
        start = Mock()
        with patch.object(admission, 'admit'), \
                patch.object(admission.logger, 'warning'), \
                patch.object(admission.connections, 'close_all') as close:
            app = admission.AdmittedApplication(downstream)
            for path in ('/api/mta/GetLastRunDate', '/api/mta/GetAllPermmision', '/api/mta/DBMData'):
                self.assertIn(b'publication_not_admitted', b''.join(app({'PATH_INFO': path}, start)))
                self.assertEqual(start.call_args.args[0], '503 Service Unavailable')
            downstream.assert_not_called()
            self.assertEqual(app({'PATH_INFO': '/healthz'}, start), [b'healthy'])
            self.assertEqual(close.call_count, 4)

    def test_wsgi_preserves_admitted_request_and_response(self):
        downstream = Mock(return_value=[b'exact existing response'])
        environ = {'PATH_INFO': '/api/mta/RRRData', 'wsgi.input': BytesIO(b'body')}
        start = Mock()
        with patch.object(admission, 'admit'), patch.object(admission, 'require_admission'), \
                patch.object(admission.logger, 'warning'), \
                patch.object(admission.connections, 'close_all'):
            app = admission.AdmittedApplication(downstream)
            self.assertEqual(app(environ, start), [b'exact existing response'])
            downstream.assert_called_once_with(environ, start)

    def test_buffer_and_other_routes_use_the_same_validated_admission(self):
        # The batching experiment in972bca8 was rejected; the deployed overlay
        # deliberately restored this interface. Headers cannot bypass admission.
        downstream = Mock(return_value=[b'unchanged'])
        with patch.object(admission, 'admit'), patch.object(admission.logger, 'warning'), \
                patch.object(admission.connections, 'close_all'), \
                patch.object(admission, 'require_admission') as require:
            app = admission.AdmittedApplication(downstream)
            for path in ('/api/mta/GetBufferTrendGraphData', '/api/mta/RRRData',
                         '/api/mta/GetResearchInsightData', '/api/mta/GetBufferTrendGraphData/',
                         '/api/mta/GetBufferTrendGraphDataOther'):
                for header in ('true', 'false'):
                    require.reset_mock()
                    app({'PATH_INFO':path, 'HTTP_X_BUFFER_RECEIPTS':header}, Mock())
                    require.assert_called_once_with()

    @override_settings(VF_BTR_REPORTING_GENERATION='selected')
    def test_reporting_identity_follows_native_validation_and_keeps_full_binding(self):
        from mta.serialization import digest
        calls = []
        def native():
            calls.append('validated'); return self.run, 'native'
        def reporting(run):
            self.assertEqual(calls, ['validated'])
            self.assertIs(run, self.run)
            calls.append('reporting')
            return {'source':'same','rows':'complete','count':12}
        with patch.object(admission, 'native_binding', side_effect=native), \
                patch.object(btr_reporting, 'admission_identity', side_effect=reporting):
            self.assertEqual(admission.binding(), (self.run, digest(dict(native='native',
                btr={'source':'same','rows':'complete','count':12}))))
        with patch.object(admission, 'native_binding', side_effect=PublicationUnavailable('run_changed')), \
                patch.object(btr_reporting, 'admission_identity') as reporting:
            with self.assertRaisesRegex(PublicationUnavailable, 'run_changed'):
                admission.binding()
            reporting.assert_not_called()

    @override_settings(VF_BTR_REPORTING_GENERATION='selected')
    def test_failed_reporting_identity_revokes_admission_without_fallback(self):
        for reason in ('not_selected', 'binding_unavailable', 'source_manifest_changed', 'image_columns_changed'):
            admission._admitted = 'old'
            with patch.object(admission, 'native_binding', return_value=(self.run, 'native')), \
                    patch.object(btr_reporting, 'admission_identity', side_effect=PublicationUnavailable(reason)), \
                    patch.object(admission, 'verify') as verify:
                with self.assertRaisesRegex(PublicationUnavailable, reason):
                    admission.require_admission()
                self.assertIsNone(admission._admitted)
                verify.assert_not_called()

    def test_database_connectivity_alone_is_not_readiness(self):
        with patch('vectorflow.urls.connection.cursor') as cursor:
            cursor.return_value.__enter__.return_value.fetchone.return_value = (1,)
            response = ready(RequestFactory().get('/readyz'))
            self.assertEqual(response.status_code, 503)
            with patch.object(admission, 'require_admission', return_value='identity'):
                response = ready(RequestFactory().get('/readyz'))
                self.assertEqual(response.status_code, 200)
                self.assertIn(b'identity', response.content)

    @override_settings(VF_MTA_TERMINAL_FILE='', VF_MTA_TERMINAL_SHA256='')
    def test_verification_reuses_all_native_and_advertised_projection_validators(self):
        output = {'DBMFinal': [{'full': 'state'}]}
        names = ('mta.runtime.services.read_outputs', 'mta.runtime.temporal.command_state',
                 'mta.presentation.admission.permission_catalogue',
                 'mta.presentation.hierarchy.selected_manifest',
                 'mta.presentation.pick_storage.read_pick_bands',
                 'mta.presentation.excess_storage.read_excess',
                 'mta.presentation.fulfillment_storage.read_fulfillment',
                 'mta.presentation.expedite_storage.read_expedite',
                 'mta.presentation.pick_post_storage.read_pick_post')
        with ExitStack() as stack:
            mocks = [stack.enter_context(patch(name)) for name in names]
            mocks[0].return_value = output
            mocks[1].return_value = (output['DBMFinal'][0], [])
            mocks[3].return_value = None
            admission.verify(self.run)
            mocks[1].assert_called_once_with(self.run, output['DBMFinal'][0])
            for mock in mocks: self.assertEqual(mock.call_count, 1)
            for index in (5, 6): mocks[index].assert_called_once_with(self.run, output=output)


if __name__ == '__main__':
    unittest.main()
