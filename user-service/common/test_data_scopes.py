"""Administrator catalogue expansion must never widen ordinary user grants.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
import requests
from django.test import SimpleTestCase
from common.data_scopes import effective_data_scopes
from common.mta_catalogue import CatalogueUnavailable


SERVICES = {'mta': {'application_id': 2, 'active': True, 'base_url': 'http://mta:8000'},
            'mto': {'application_id': 3, 'active': True, 'base_url': 'http://mto:10015'}}


def mta_catalogue(products=(11, 12), locations=(21, 22)):
    return {kind: [dict(id=i, **{prefix+str(n): 'Level'+str(n) for n in (1, 2, 3)}) for i in values]
            for kind, values, prefix in [('product', products, 'product_hierarchy_'),
                                         ('location', locations, 'location_heirarchy_')]}


class AdministratorDataScopeTests(SimpleTestCase):
    @patch('common.mta_catalogue.enabled', return_value=False)
    @patch('common.startup_probe.permission_request')
    def test_admin_without_grant_rows_gets_current_mta_catalogue_and_new_ids(self, request, enabled):
        response = request.return_value
        response.status_code = 200
        response.json.return_value = mta_catalogue()
        self.assertEqual(effective_data_scopes(1, 2, administrator=True, services=SERVICES), ([11, 12], [21, 22]))
        response.json.return_value = mta_catalogue(products=(11, 12, 13))
        self.assertEqual(effective_data_scopes(1, 2, administrator=True, services=SERVICES)[0], [11, 12, 13])
        self.assertEqual(request.call_args.kwargs['timeout'], (5, 20))

    @patch('common.mta_catalogue.enabled', return_value=True)
    @patch('common.mta_catalogue.payload', return_value=mta_catalogue())
    @patch('common.startup_probe.permission_request', side_effect=AssertionError('No network'))
    def test_local_mta_catalogue_uses_existing_verified_provider(self, request, payload, enabled):
        self.assertEqual(effective_data_scopes(1, 2, administrator=True, services=SERVICES), ([11, 12], [21, 22]))

    @patch('common.startup_probe.permission_request')
    def test_mto_current_catalogue_and_genuine_blank_install(self, request):
        request.return_value.status_code = 200
        request.return_value.json.return_value = {'data': {'Orders': [[{'id': 31}, {'id': 32}]], 'Location': [[{'id': 41}]]}}
        self.assertEqual(effective_data_scopes(1, 3, administrator=True, services=SERVICES), ([31, 32], [41]))
        request.return_value.json.return_value = {'data': {}}
        self.assertEqual(effective_data_scopes(1, 3, administrator=True, services=SERVICES), ([], []))

    @patch('common.startup_probe.permission_request')
    def test_unavailable_or_invalid_catalogue_fails_closed(self, request):
        request.return_value.status_code = 200
        for body in [{'data': None}, {'data': {'Orders': []}},
                     {'data': {'Orders': [[{'id': True}]], 'Location': [[]]}},
                     {'data': {'Orders': [[{'id': 1}, {'id': 1}]], 'Location': [[]]}}]:
            request.return_value.json.return_value = body
            with self.subTest(body=body), self.assertRaises(CatalogueUnavailable):
                effective_data_scopes(1, 3, administrator=True, services=SERVICES)
        request.side_effect = requests.Timeout()
        with self.assertRaises(CatalogueUnavailable):
            effective_data_scopes(1, 3, administrator=True, services=SERVICES)
        request.side_effect = None
        request.return_value.status_code = 500
        with self.assertRaises(CatalogueUnavailable):
            effective_data_scopes(1, 3, administrator=True, services=SERVICES)

    @patch('api.models.User_Application_Location_Permission.objects.filter')
    @patch('api.models.User_Application_Product_Permission.objects.filter')
    @patch('common.startup_probe.permission_request', side_effect=AssertionError('No admin lookup'))
    def test_ordinary_scope_grants_and_revocation_remain_exact(self, request, products, locations):
        products.return_value.values_list.return_value = [12]
        locations.return_value.values_list.return_value = [21]
        self.assertEqual(effective_data_scopes(7, 2), ([12], [21]))
        products.return_value.values_list.return_value = []
        self.assertEqual(effective_data_scopes(7, 2), ([], [21]))
        products.assert_called_with(application_id=2, user_id=7)

    @patch('api_gateway.interceptors.mta_interceptor.effective_data_scopes', return_value=([11, 12], [21, 22]))
    def test_mta_expansion_uses_authenticated_flag_not_browser_values(self, resolve):
        from api_gateway.interceptors.mta_interceptor import authenticated_mta_context
        request = SimpleNamespace(user=SimpleNamespace(id=1, name='Admin', email='admin@fixture.invalid', is_admin=True),
                                  data={'is_admin': False, 'product_permissions': [999]})
        actual = authenticated_mta_context(request, services=SERVICES)
        self.assertEqual(actual['product_permissions'], [11, 12])
        resolve.assert_called_once_with(1, 2, administrator=True, services=SERVICES)
        request.user.is_admin = False
        request.data['is_admin'] = True
        authenticated_mta_context(request, services=SERVICES)
        self.assertFalse(resolve.call_args.kwargs['administrator'])

    @patch('api_gateway.interceptors.mto_interceptor.effective_data_scopes', return_value=([31], [41]))
    @patch('api_gateway.interceptors.mto_interceptor.User.objects.filter')
    @patch('api_gateway.interceptors.mto_interceptor.requests.request')
    def test_mto_expansion_requires_matching_authenticated_admin_subject(self, request_out, users, resolve):
        from api_gateway.interceptors.mto_interceptor import MTO_INTERCEPTOR
        users.return_value.values.return_value = [{'is_admin': True}]
        request = SimpleNamespace(user=SimpleNamespace(id=1, is_admin=True),
            headers={'User-Id': '1', 'User-Name': 'Admin'}, method='POST',
            path='/api/mto/getDDQData/', data={}, query_params={}, GET={}, FILES={}, COOKIES={'access_token': 'test-cookie'})
        MTO_INTERCEPTOR().forward(request, SERVICES)
        resolve.assert_called_with(1, 3, administrator=True, services=SERVICES)
        self.assertEqual(request_out.call_args.kwargs['json']['product_permissions'], [31])
        request.headers['User-Id'] = '99'
        MTO_INTERCEPTOR().forward(request, SERVICES)
        resolve.assert_called_with(99, 3, administrator=False, services=SERVICES)

    @patch('api_gateway.views.service_map', {'mta': {'interceptor': MagicMock}})
    def test_gateway_preserves_unavailable_scope_as_503(self):
        from api_gateway.views import API_GATEWAY_VIEW
        with patch('api_gateway.views.service_map', {'mta': {'interceptor': lambda: SimpleNamespace(
                forward=MagicMock(side_effect=CatalogueUnavailable()))}}):
            response = API_GATEWAY_VIEW._forward(SimpleNamespace(), 'mta')
        self.assertEqual(response.status_code, 503)
