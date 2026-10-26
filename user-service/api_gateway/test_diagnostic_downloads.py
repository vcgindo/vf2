"""Finite diagnostic transport and stored report entitlement, offline only."""
import json
import os
from types import SimpleNamespace
from unittest.mock import MagicMock,patch

from django.test import SimpleTestCase
from api_gateway.mta_stream import DIAGNOSTIC_DOWNLOAD_PATHS,streams_mta_read,bounded_mta_read
from api_gateway.interceptors.mta_interceptor import MTA_INTERCEPTOR


class DiagnosticDownloadTests(SimpleTestCase):
    def test_exact_names_and_methods_only(self):
        names={'DailyDataUnavailabilityReport','InvalidDataReport','NMSAddNewSKULoc',
            'NMSModifySKULoc','NMSRemoveSKULoc','NMSLocMaster','NMSSKUMaster','NMSSOBMaster',
            'NMSMOQMaster','ForceNormChangeUpload'}
        self.assertEqual(DIAGNOSTIC_DOWNLOAD_PATHS,{'/api/mta/DownloadReports/'+name for name in names})
        for path in DIAGNOSTIC_DOWNLOAD_PATHS:
            for method in ('GET','POST','DELETE','PUT'):
                request=SimpleNamespace(method=method,path=path)
                self.assertEqual(streams_mta_read(request),method in ('GET','POST'))
                self.assertEqual(bounded_mta_read(request),method in ('GET','POST'))
        for name in ('InvalidDataReport.zip','NMSAddNewSKULocLog','FailedForceNormChanges',
                     '../InvalidDataReport','invaliddatareport'):
            request=SimpleNamespace(method='GET',path='/api/mta/DownloadReports/'+name)
            self.assertFalse(streams_mta_read(request));self.assertFalse(bounded_mta_read(request))

    def test_all_ten_require_real_application_grant_and_inject_entitlement(self):
        service={'mta':{'base_url':'http://mta:8000','application_id':2}}
        for path in DIAGNOSTIC_DOWNLOAD_PATHS:
            request=SimpleNamespace(method='GET',path=path,data={'entitlements':['mta-report-urls']},
                query_params={},COOKIES={'access_token':'unit-test-token'},FILES={},user=SimpleNamespace(
                    id=7,name='fixture',email='fixture@example.invalid',is_admin=False))
            with self.subTest(path=path), \
                    patch('api_gateway.interceptors.mta_interceptor.Permission.objects.filter') as grants, \
                    patch('api_gateway.interceptors.mta_interceptor.authenticated_mta_context',
                          return_value={'product_permissions':[11],'location_permissions':[22]}), \
                    patch('api_gateway.interceptors.mta_interceptor.mta_request') as upstream:
                grants.return_value.exists.return_value=False
                self.assertEqual(MTA_INTERCEPTOR().forward(request,service).status_code,403)
                upstream.assert_not_called()
                grants.return_value.exists.return_value=True
                upstream.return_value=MagicMock(status_code=200)
                MTA_INTERCEPTOR().forward(request,service)
                grants.assert_called_with(url='mta-report-urls',role_id__user_id=7,role_id__application_id=2)
                forwarded=upstream.call_args.kwargs
                header=os.environ.get('MTA_TRUSTED_GATEWAY_HEADER','X-VectorFLOW-Identity')
                self.assertEqual(json.loads(forwarded['headers'][header])['entitlements'],['mta-report-urls'])
                self.assertTrue(forwarded['stream']);self.assertEqual(forwarded['timeout'],(5,60))
                self.assertEqual(forwarded['url'],'http://mta:8000'+path)

    def test_admin_retains_existing_download_authority_without_changing_input_archive_policy(self):
        service={'mta':{'base_url':'http://mta:8000','application_id':2}}
        request=SimpleNamespace(method='GET',path='/api/mta/DownloadReports/InvalidDataReport',
            data={},query_params={},COOKIES={'access_token':'unit-test-token'},FILES={},user=SimpleNamespace(
                id=7,name='fixture',email='fixture@example.invalid',is_admin=True))
        with patch('api_gateway.interceptors.mta_interceptor.Permission.objects.filter') as grants, \
                patch('api_gateway.interceptors.mta_interceptor.authenticated_mta_context',
                    return_value={'product_permissions':[11],'location_permissions':[22]}), \
                patch('api_gateway.interceptors.mta_interceptor.mta_request',return_value=MagicMock(status_code=200)) as upstream:
            MTA_INTERCEPTOR().forward(request,service)
            grants.assert_not_called()
            header=os.environ.get('MTA_TRUSTED_GATEWAY_HEADER','X-VectorFLOW-Identity')
            self.assertEqual(json.loads(upstream.call_args.kwargs['headers'][header])['entitlements'],['mta-report-urls'])
            request.user.is_admin=False;request.path='/api/mta/DownloadReports/InputData'
            upstream.reset_mock()
            self.assertEqual(MTA_INTERCEPTOR().forward(request,service).status_code,403)
            upstream.assert_not_called()
