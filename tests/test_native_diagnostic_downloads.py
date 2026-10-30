"""Custody priority, unavailable-vs-empty and existing route safety."""
import io
import json
import os
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault('VF_SECRET_KEY', 'native-diagnostic-unit-only')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
import django
django.setup()
from django.test import SimpleTestCase, RequestFactory, override_settings
from django.http import JsonResponse
from django.urls import resolve
from mta.presentation import native_diagnostic_downloads as subject
from mta.presentation.context import PublicationUnavailable


@override_settings(MTA_TRUSTED_GATEWAY_HEADER='X-VectorFLOW-Identity')
class NativeDiagnosticTests(SimpleTestCase):
    def request(self, identity=None):
        return RequestFactory().get('/api/mta/DownloadReports/InvalidDataReport',
            HTTP_X_VECTORFLOW_IDENTITY=json.dumps(identity or dict(id=8, entitlements=['mta-report-urls'])))

    def test_exact_routes_remain_existing_urls(self):
        self.assertIs(resolve('/api/mta/GetAllReports').func, subject.report_paths)
        self.assertIs(resolve('/api/mta/DownloadReports/InvalidDataReport').func, subject.download_report)

    def test_entitlement_denied_before_source_or_projection(self):
        for identity in (dict(id=8, is_admin=True), dict(id=8, entitlements=['mta-input-archive']),
                         dict(id=8, entitlements=['mta-report-urls', 'other'])):
            with patch.object(subject, 'native_full', return_value=True), \
                    patch.object(subject, 'selected_run') as selected, \
                    patch.object(subject, 'invalid_archive') as projected:
                response = subject.download_report(self.request(identity), report_name='InvalidDataReport')
            self.assertEqual(response.status_code, 403)
            selected.assert_not_called()
            projected.assert_not_called()

    def test_published_custody_wins_and_corruption_never_falls_back(self):
        for broken in (False, True):
            with patch.object(subject, 'native_full', return_value=True), \
                    patch.object(subject, 'selected_run', return_value=SimpleNamespace(pk='selected')), \
                    patch.object(subject.original, 'open_file', side_effect=
                        PublicationUnavailable('published_bytes_changed') if broken else None,
                        return_value=(io.BytesIO(b'original'), 'InvalidDataReport.zip', 'application/zip')), \
                    patch.object(subject, 'invalid_archive') as projected:
                response = subject.download_report(self.request(), report_name='InvalidDataReport')
                self.assertEqual(response.status_code, 503 if broken else 200)
                response.close()
            projected.assert_not_called()

    def test_only_absence_uses_the_selected_run_projection(self):
        run = SimpleNamespace(pk='selected')
        with patch.object(subject, 'native_full', return_value=True), \
                patch.object(subject, 'selected_run', return_value=run), \
                patch.object(subject.original, 'open_file', side_effect=PublicationUnavailable('diagnostic_not_published_for_source')), \
                patch.object(subject, 'invalid_archive', return_value=(io.BytesIO(b'projected'),
                    'InvalidDataReport.zip', 'application/zip')) as projected:
            response = subject.download_report(self.request(), report_name='InvalidDataReport')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(b''.join(response.streaming_content), b'projected')
            projected.assert_called_once_with(run)
            response.close()

    def test_source_failure_is_not_an_empty_or_client_error(self):
        with patch.object(subject, 'native_full', return_value=True), \
                patch.object(subject, 'selected_run', return_value=SimpleNamespace()), \
                patch.object(subject.original, 'open_file', side_effect=PublicationUnavailable('diagnostic_not_published_for_source')), \
                patch.object(subject, 'invalid_archive', side_effect=ValueError('unqualified encoding')):
            response = subject.download_report(self.request(), report_name='InvalidDataReport')
        self.assertEqual(response.status_code, 503)
        self.assertEqual(json.loads(response.content)['error'], 'native_invalid_data_report_unavailable')

    def test_missing_upload_is_a_specific_404_not_an_invented_zip(self):
        with patch.object(subject, 'native_full', return_value=True), \
                patch.object(subject, 'selected_run', return_value=SimpleNamespace()), \
                patch.object(subject.original, 'open_file', side_effect=PublicationUnavailable('diagnostic_not_published_for_source')), \
                patch.object(subject, 'unavailable_reason', return_value='upload_log_audit_not_captured'), \
                patch.object(subject, 'invalid_archive') as projected:
            response = subject.download_report(self.request(), report_name='NMSAddNewSKULoc')
        self.assertEqual(response.status_code, 404)
        self.assertEqual(json.loads(response.content)['reason'], 'upload_log_audit_not_captured')
        projected.assert_not_called()

    def test_metadata_removes_unavailable_names_and_preserves_real_files(self):
        paths = {name: {'downloadName': name + '.zip'} for name in subject.original.SELECTORS}
        paths['InputData'] = {'downloadName': 'InputData.zip'}
        retained = lambda request, payload: JsonResponse(dict(data=paths, status=200))
        with patch.object(subject, 'native_full', return_value=True), \
                patch.object(subject, 'selected_run', return_value=SimpleNamespace()), \
                patch.object(subject, 'published_names', return_value={'NMSLocMaster'}), \
                patch.object(subject, 'image_metadata', return_value={'count': 0}), \
                patch.object(subject.runtime_placement_downloads, 'report_paths', retained):
            response = subject.report_paths(self.request())
        self.assertEqual(set(json.loads(response.content)['data']), {'InputData','InvalidDataReport','NMSLocMaster'})

    def test_custody_guard_drift_cannot_become_absence_or_projected_success(self):
        with patch.object(subject, 'native_full', return_value=True), \
                patch.object(subject, 'selected_run', return_value=SimpleNamespace()), \
                patch.object(subject.original, 'open_file', side_effect=PublicationUnavailable('diagnostic_publication_unavailable')), \
                patch.object(subject, 'invalid_archive') as projected:
            response = subject.download_report(self.request(), report_name='InvalidDataReport')
        self.assertEqual(response.status_code, 503)
        projected.assert_not_called()
        from mta.runtime import intake_diagnostics as custody
        from mta.runtime.intake_diagnostic_models import DiagnosticPublication
        from django.db import connections
        with patch.object(connections['default'], 'cursor'), \
                patch.object(custody, 'verify_guards', side_effect=ValueError('guard drift')), \
                patch.object(DiagnosticPublication.objects, 'filter') as query:
            with self.assertRaises(PublicationUnavailable):
                subject.published_names(SimpleNamespace())
        query.assert_not_called()

    @override_settings(VF_MTA_PHASE_SELECTION_FILE='phase-owner.json')
    def test_phase_dispatch_never_enters_a_full_projection(self):
        with patch('mta.presentation.scoped_selection.enabled', return_value=True), \
                patch('mta.presentation.scoped_api.dispatch', return_value=JsonResponse({'phase': True})) as phase, \
                patch.object(subject, 'selected_run') as full:
            response = subject.download_report(self.request(), report_name='InvalidDataReport')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(phase.call_args.args[0].__name__, 'download_report')
        full.assert_not_called()
