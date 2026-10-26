"""HTTP adapter contracts; native selection/custody proof remains separate."""
import io,json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase,RequestFactory,override_settings
from mta.presentation import runtime_placement_downloads as delivery


@override_settings(MTA_TRUSTED_GATEWAY_HEADER='X-Fixture-Gateway')
class PlacementDownloadHttpTests(SimpleTestCase):
    def setUp(self):
        self.factory=RequestFactory()
        scope=patch('mta.presentation.scoped_selection.enabled',return_value=False)
        scope.start();self.addCleanup(scope.stop)

    def request(self,*,entitlements=None,identity=True):
        fields={}
        if identity:fields['HTTP_X_FIXTURE_GATEWAY']=json.dumps(dict(id=7,entitlements=entitlements or []))
        return self.factory.get('/api/mta/DownloadReports/BOR%20WH%20Efficiency%20report',**fields)

    def test_roster_is_exact_retained_names_and_excludes_independent_rrr(self):
        retained=json.loads((Path(__file__).parents[2]/'tests/fixtures/runtime_reports_retained_20261019.json').read_bytes())
        self.assertEqual(delivery.SELECTORS,{row['ReportName']:row['Id'] for row in retained})
        self.assertNotIn('RRR',delivery.SELECTORS)

    def test_missing_identity_and_wrong_entitlement_cannot_open_file(self):
        with patch.object(delivery,'_selected',return_value=object()),patch.object(delivery,'open_file') as opened:
            for request in (self.request(identity=False),self.request(entitlements=['mta-input-archive'])):
                result=delivery.download_report(request,report_name='BOR WH Efficiency report')
                self.assertEqual(result.status_code,403)
            opened.assert_not_called()

    def test_zip_and_csv_content_type_and_original_filename_are_preserved(self):
        with patch.object(delivery,'_selected',return_value=object()):
            for name,mimetype in (('BOR_Efficiency.zip','application/zip'),('BOR_Color_Bandwise.csv','text/csv')):
                with patch.object(delivery,'open_file',return_value=(io.BytesIO(b'accepted-bytes'),name,mimetype)):
                    result=delivery.download_report(self.request(entitlements=['mta-report-urls']),
                                                    report_name='BOR WH Efficiency report')
                    self.assertEqual(result.status_code,200)
                    self.assertEqual(result['Content-Type'],mimetype)
                    self.assertIn(name,result['Content-Disposition'])
                    self.assertEqual(b''.join(result.streaming_content),b'accepted-bytes')
                    result.close()

    def test_partial_permission_and_missing_bytes_deny_without_fallback(self):
        with patch.object(delivery,'_selected',return_value=object()):
            for error,status in ((PermissionError('partial'),403),(FileNotFoundError('missing'),503)):
                with patch.object(delivery,'open_file',side_effect=error):
                    result=delivery.download_report(self.request(entitlements=['mta-report-urls']),
                                                    report_name='BOR WH Efficiency report')
                    self.assertEqual(result.status_code,status)

    def test_prior_selected_run_keeps_existing_report_path_response(self):
        with patch.object(delivery,'_selected',return_value=None), \
                patch('mta.presentation.terminal_bpr_delivery.report_paths',return_value={'retained':{'path':''}}):
            response=delivery.report_paths(self.request())
            self.assertEqual(response.status_code,200,response.content)
            self.assertEqual(json.loads(response.content)['data'],{'retained':{'path':''}})

    def test_scoped_dispatch_preserves_original_handler_name(self):
        sentinel=object()
        with patch('mta.presentation.scoped_selection.enabled',return_value=True), \
                patch('mta.presentation.scoped_api.dispatch',return_value=sentinel) as dispatch, \
                patch.object(delivery,'_selected') as terminal:
            result=delivery.download_report(self.request(),report_name='Spike_Order_Dump')
            self.assertIs(result,sentinel)
            self.assertEqual(dispatch.call_args.args[0].__name__,'download_report')
            terminal.assert_not_called()
