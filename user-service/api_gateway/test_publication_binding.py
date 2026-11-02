from types import SimpleNamespace
import hashlib
import json
from unittest.mock import Mock, patch

from django.test import SimpleTestCase
from rest_framework.test import APIRequestFactory
from api_gateway.interceptors.mta_interceptor import MTA_INTERCEPTOR
from api_gateway.mta_stream import streamed_response
from api_gateway.views import API_GATEWAY_VIEW


class PublicationTransportTests(SimpleTestCase):
    def test_bootstrap_adapter_preserves_no_store(self):
        from rest_framework.response import Response
        view = API_GATEWAY_VIEW()
        request = view.initialize_request(APIRequestFactory().get('/api/mta/PublicationBinding'))
        view.headers = {}
        response = view.finalize_response(request, Response({'mode': 'native', 'binding': 'a' * 64}))
        self.assertEqual(response['Cache-Control'], 'no-store')

    def test_real_interceptor_forwards_only_the_binding_claim_with_trusted_identity(self):
        upstream = Mock(status_code=200, headers={})
        request = SimpleNamespace(COOKIES={'access_token': 'test-cookie'},
            path='/api/mta/RRRData', method='POST', data={}, query_params={}, FILES={},
            headers={'X-VectorFLOW-Publication': 'a' * 64, 'X-VectorFLOW-Identity': 'untrusted'},
            user=SimpleNamespace(id=7, name='Test', email='test@example.invalid', is_admin=False))
        with patch('api_gateway.interceptors.mta_interceptor.authenticated_mta_context',
                   return_value={'product_permissions': [], 'location_permissions': []}), \
                patch('api_gateway.interceptors.mta_interceptor.mta_request', return_value=upstream) as send:
            result = MTA_INTERCEPTOR().forward(request, {'mta': {'base_url': 'http://internal', 'application_id': 2}})
        self.assertIs(result, upstream)
        self.assertEqual(send.call_args.kwargs['headers']['X-VectorFLOW-Publication'], 'a' * 64)
        self.assertNotEqual(send.call_args.kwargs['headers']['X-VectorFLOW-Identity'], 'untrusted')

    def test_scope_commitment_uses_effective_lists_not_browser_claims_and_preserves_order_duplicates_types(self):
        scopes = [([11, 11, '12'], [9, 8]), ([11, '12', 11], [9, 8]),
                  ([11, '12'], [9, 8]), (['11', 11, '12'], [9, 8])]
        observed = []
        for products, locations in scopes:
            request = SimpleNamespace(COOKIES={'access_token': 'test-cookie'},
                path='/api/mta/RRRData', method='POST', query_params={}, FILES={},
                data={'product_permissions': ['spoof'], 'location_permissions': ['spoof'],
                      'report_scope_digest': 'f' * 64, 'user': {'id': 999}},
                headers={'X-VectorFLOW-Identity': json.dumps({'id': 999}),
                         'X-VectorFLOW-Report-Scope': 'f' * 64},
                user=SimpleNamespace(id=7, name='Test', email='test@example.invalid', is_admin=False))
            effective = {'product_permissions': products, 'location_permissions': locations}
            with patch('api_gateway.interceptors.mta_interceptor.authenticated_mta_context', return_value=effective) as context, \
                    patch('api_gateway.interceptors.mta_interceptor.mta_request', return_value=Mock(status_code=200)) as send:
                MTA_INTERCEPTOR().forward(request, {'mta': {'base_url': 'http://internal', 'application_id': 2}})
            context.assert_called_once()  # Reuse the existing lookup; no second scope query.
            arguments = send.call_args.kwargs
            trusted = json.loads(arguments['headers']['X-VectorFLOW-Identity'])
            scope_digest = arguments['headers']['X-VectorFLOW-Report-Scope']
            expected = hashlib.sha256(json.dumps(effective, sort_keys=True,
                separators=(',', ':'), ensure_ascii=False).encode('utf-8')).hexdigest()
            self.assertEqual(trusted['id'], 7)
            self.assertNotIn('report_scope_digest', trusted)
            self.assertEqual(scope_digest, expected)
            self.assertNotEqual(scope_digest, 'f' * 64)
            self.assertEqual(arguments['json']['product_permissions'], products)
            self.assertEqual(arguments['json']['location_permissions'], locations)
            self.assertEqual(arguments['json']['user']['id'], 7)
            observed.append(scope_digest)
        self.assertEqual(len(set(observed)), len(scopes))

    def test_streamed_export_preserves_upstream_assertion(self):
        upstream = Mock(status_code=200, headers={'Content-Type': 'text/csv',
            'Content-Disposition': 'attachment', 'X-VectorFLOW-Publication': 'a' * 64})
        upstream.iter_content.return_value = iter([b'header\nrow\n'])
        result = streamed_response(SimpleNamespace(method='POST', path='/api/mta/GetExportDataAsync'), upstream)
        self.assertEqual(result['X-VectorFLOW-Publication'], 'a' * 64)
        result.close()

    def test_json_adapter_uses_owner_assertion_never_browser_echo(self):
        factory = APIRequestFactory()
        for owner in (None, 'b' * 64):
            request = factory.post('/api/mta/GetBTRDataCount', {}, format='json',
                HTTP_X_VECTORFLOW_PUBLICATION='a' * 64)
            view = API_GATEWAY_VIEW()
            request = view.initialize_request(request)
            upstream = Mock(status_code=200, text='{}', headers={})
            upstream.headers = {} if owner is None else {'X-VectorFLOW-Publication': owner}
            upstream.json.return_value = {'recordCount': '1'}
            interceptor = Mock()
            interceptor.return_value.forward.return_value = upstream
            with patch('api_gateway.views.service_map', {'mta': {'interceptor': interceptor}}):
                response = view.post(request)
                view.headers = {}
                response = view.finalize_response(request, response)
            self.assertEqual(response.get('X-VectorFLOW-Publication'), owner)
