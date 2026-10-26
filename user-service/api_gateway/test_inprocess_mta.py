import json
from io import BytesIO
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.core.handlers.wsgi import WSGIHandler
from django.http import FileResponse, JsonResponse
from django.test import SimpleTestCase, override_settings
from django.urls import path

from api_gateway.inprocess_mta import (
    InProcessMtaTransportError, owned_wsgi_application, owned_mdm_workflow_application, request,
)


class ProofMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, django_request):
        response = self.get_response(django_request)
        response['X-Proof-Middleware'] = 'traversed'
        return response


def json_read(django_request):
    return JsonResponse({
        'method': django_request.method,
        'body': json.loads(django_request.body or b'{}'),
        'identity': django_request.headers.get('X-VectorFLOW-Identity'),
        'query': django_request.GET.getlist('item'),
    })


def download(_django_request, report_name):
    return FileResponse(BytesIO(b'alpha,beta\r\n'), as_attachment=True,
                        filename=report_name + '.csv', content_type='text/csv')


urlpatterns = [
    path('api/mta/DBMData', json_read),
    path('api/mta/DownloadReports/<str:report_name>', download),
]
urlpatterns += [path('api/mta/' + route, json_read) for route in (
    'AddMasterData', 'ModifyMasterData', 'PostMasterAfterApproved')]


PROOF_SETTINGS = dict(
    ROOT_URLCONF=__name__,
    MIDDLEWARE=[__name__ + '.ProofMiddleware'],
)


class InProcessMtaTransportTests(SimpleTestCase):
    def test_runtime_report_read_seal_adds_only_two_exact_native_names(self):
        def application(environ, start_response):
            start_response('200 OK', [('Content-Type', 'application/octet-stream')])
            return [environ['PATH_INFO'].encode()]
        with override_settings(MTA_INPROCESS_WSGI_APPLICATION=owned_wsgi_application(application)):
            for name in ('Spike_Order_Dump', 'TotalReqReport_YYYY-MM-DD', 'LogisticPickListReport'):
                path = '/api/mta/DownloadReports/'+name
                self.assertEqual(request(base_url='http://mta', method='GET',
                    url='http://mta'+path).content, path.encode())
            for name in ('Spiker_Order_Dump.zip', 'Spike_Order_Dump.zip', 'spike_order_dump',
                         'TotalReqReport_2026-10-26', 'TotalReqReport_2026-02-30',
                         'TotalReqReport_YYYY-MM-DD.csv', 'ForeignReport', 'BOR_OrderAllocation',
                         '../Spike_Order_Dump', '%53pike_Order_Dump', 'Spike_Order_Dump/'):
                with self.subTest(name=name), self.assertRaises(InProcessMtaTransportError):
                    request(base_url='http://mta', method='GET',
                        url='http://mta/api/mta/DownloadReports/'+name)
            for method, path in (('POST', '/api/mta/DownloadReports/Spike_Order_Dump'),
                                 ('GET', '/api/mto/DownloadReports/Spike_Order_Dump')):
                with self.subTest(method=method, path=path), self.assertRaises(InProcessMtaTransportError):
                    request(base_url='http://mta', method=method, url='http://mta'+path)

    @override_settings(**PROOF_SETTINGS)
    def test_workflow_seal_is_exact_and_does_not_extend_read_seal(self):
        binding = dict(SETTINGS_MODULE='tools.mdm_approval_day_settings',
            DATABASES={'default': {'NAME': 'fresh_mdm_approval_day_20261010_002'}},
            VF_MDM_SOURCE_DIGEST='39f76f9c718a28e014737e8c856af7d29f1ab5dbdfd2370321a6cb539d010f8e',
            VF_MTA_PUBLISHED_RUN='own-accepted-D0', VF_MTA_PUBLISHED_DIGEST='d' * 64)
        with override_settings(**binding):
            application = owned_mdm_workflow_application(WSGIHandler(), run_id='own-accepted-D0', output_digest='d' * 64)
            with override_settings(MTA_INPROCESS_WSGI_APPLICATION=application):
                for route in ('AddMasterData', 'ModifyMasterData', 'PostMasterAfterApproved'):
                    response = request(base_url='http://mta', method='POST',
                        url='http://mta/api/mta/' + route, json={'id': 1})
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(response.headers['X-Proof-Middleware'], 'traversed')
                for method, route in (('POST', 'RemoveMasterData'), ('POST', 'DBMData'),
                                      ('GET', 'GetLastRunDate')):
                    with self.assertRaises(InProcessMtaTransportError):
                        request(base_url='http://mta', method=method, url='http://mta/api/mta/' + route)
                with override_settings(VF_MTA_PUBLISHED_RUN='changed'), self.assertRaisesRegex(
                        InProcessMtaTransportError, 'binding_changed'):
                    request(base_url='http://mta', method='POST', url='http://mta/api/mta/AddMasterData')
            for field, value in (('SETTINGS_MODULE', 'vectorflow.settings'),
                    ('VF_MDM_SOURCE_DIGEST', 'wrong'), ('VF_MTA_PUBLISHED_RUN', ''),
                    ('DATABASES', {'default': {'NAME': 'other'}})):
                with override_settings(**{field: value}), self.assertRaises(InProcessMtaTransportError):
                    owned_mdm_workflow_application(WSGIHandler(), run_id='own-accepted-D0', output_digest='d' * 64)
        with override_settings(MTA_INPROCESS_WSGI_APPLICATION=owned_wsgi_application(WSGIHandler())):
            with self.assertRaises(InProcessMtaTransportError):
                request(base_url='http://mta', method='POST', url='http://mta/api/mta/AddMasterData')

    def test_default_transport_is_the_unchanged_requests_call(self):
        expected = object()
        arguments = dict(method='POST', url='http://mta/api/mta/DBMData',
                         headers={'Content-Type': 'application/json'}, params={'a': 'b'},
                         json={'value': 1}, stream=True, timeout=(5, 60))
        request_mock = SimpleNamespace()
        request_mock.request = MagicMock(return_value=expected)
        with override_settings(MTA_INPROCESS_WSGI_APPLICATION=None), \
                patch.dict(sys.modules, {'requests': request_mock}):
            self.assertIs(request(base_url='http://mta', **arguments), expected)
        request_mock.request.assert_called_once_with(**arguments)

    @override_settings(**PROOF_SETTINGS)
    def test_real_wsgi_handler_traverses_middleware_url_and_json_view(self):
        application = owned_wsgi_application(WSGIHandler())
        with override_settings(MTA_INPROCESS_WSGI_APPLICATION=application):
            response = request(
                base_url='http://mta', method='POST', url='http://mta/api/mta/DBMData',
                headers={'Content-Type': 'application/json',
                         'X-VectorFLOW-Identity': '{"id":2}'},
                params={'item': ['one', 'two']}, json={'product_permissions': [71001]},
                stream=True, timeout=(5, 60))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers['X-Proof-Middleware'], 'traversed')
        self.assertEqual(response.json(), {
            'method': 'POST', 'body': {'product_permissions': [71001]},
            'identity': '{"id":2}', 'query': ['one', 'two']})

    @override_settings(**PROOF_SETTINGS)
    def test_real_wsgi_file_response_remains_streamed_with_headers(self):
        application = owned_wsgi_application(WSGIHandler())
        with override_settings(MTA_INPROCESS_WSGI_APPLICATION=application):
            response = request(base_url='http://mta', method='GET',
                url='http://mta/api/mta/DownloadReports/LogisticPickListReport',
                headers={'Content-Type': 'application/json'}, params={}, json={}, stream=True)
        self.assertEqual(response.status_code, 200, dict(response.headers))
        self.assertIn('LogisticPickListReport.csv', response.headers['Content-Disposition'])
        self.assertEqual(b''.join(response.iter_content(chunk_size=3)), b'alpha,beta\r\n')

    def test_unowned_application_and_out_of_scope_requests_fail_closed(self):
        with override_settings(MTA_INPROCESS_WSGI_APPLICATION=lambda environ, start: []), \
                self.assertRaisesRegex(InProcessMtaTransportError, 'application_not_owned'):
            request(base_url='http://mta', method='GET',
                    url='http://mta/api/mta/GetLastRunDate')
        application = owned_wsgi_application(lambda environ, start: [])
        denied = (
            dict(method='DELETE', url='http://mta/api/mta/GetLastRunDate'),
            dict(method='POST', url='http://mta/api/mta/DBMApplySelectedNorms'),
            dict(method='GET', url='http://other/api/mta/GetLastRunDate'),
            dict(method='GET', url='http://mta/api/mta/GetMasterData'),
        )
        with override_settings(MTA_INPROCESS_WSGI_APPLICATION=application):
            for arguments in denied:
                with self.subTest(arguments=arguments), self.assertRaises(InProcessMtaTransportError):
                    request(base_url='http://mta', **arguments)

    def test_upload_and_form_payloads_are_denied(self):
        application = owned_wsgi_application(lambda environ, start: [])
        with override_settings(MTA_INPROCESS_WSGI_APPLICATION=application):
            for forbidden in ({'files': {'file': object()}}, {'data': {'value': 1}}):
                with self.subTest(forbidden=forbidden), self.assertRaisesRegex(
                        InProcessMtaTransportError, 'json_reads_only'):
                    request(base_url='http://mta', method='POST',
                            url='http://mta/api/mta/DBMData', **forbidden)
