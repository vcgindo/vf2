import json
import os
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.http import JsonResponse
from django.test import SimpleTestCase

from api_gateway.interceptors.mta_interceptor import MTA_INTERCEPTOR
from api_gateway.interceptors.mto_interceptor import MTO_INTERCEPTOR
from api_gateway.views import API_GATEWAY_VIEW


class TestMtaInterceptorIdentity(SimpleTestCase):
    service_map = {
        "mta": {
            "base_url": "http://mta:8000",
            "application_id": 2,
        }
    }

    @staticmethod
    def request(method="GET", path="/api/mta/GetEnvironmentConfiguration", data=None):
        return SimpleNamespace(
            method=method,
            path=path,
            data={} if data is None else data,
            query_params={},
            COOKIES={"access_token": "cookie-token"},
            user=SimpleNamespace(id=7, name="Stage 7B", email="stage7b@example.invalid"),
            FILES={},
        )

    @patch("api_gateway.interceptors.mta_interceptor.Permission.objects.filter")
    @patch("api_gateway.interceptors.mta_interceptor.User_Application_Location_Permission.objects.filter")
    @patch("api_gateway.interceptors.mta_interceptor.User_Application_Product_Permission.objects.filter")
    @patch("api_gateway.interceptors.mta_interceptor.requests.request")
    def test_pick_download_requires_stored_report_grant_and_forwards_exact_scopes(
        self, request_mock, product_filter_mock, location_filter_mock, grant_filter_mock
    ):
        request = self.request('GET', '/api/mta/DownloadReports/LogisticPickListReport')
        request.user.is_admin = False
        product_filter_mock.return_value.values_list.return_value = [11]
        location_filter_mock.return_value.values_list.return_value = [22]
        grant_filter_mock.return_value.exists.return_value = False
        denied = MTA_INTERCEPTOR().forward(request, self.service_map)
        self.assertEqual(denied.status_code, 403)
        request_mock.assert_not_called()

        grant_filter_mock.return_value.exists.return_value = True
        request_mock.return_value = MagicMock(status_code=200)
        MTA_INTERCEPTOR().forward(request, self.service_map)
        forwarded = request_mock.call_args.kwargs
        header_name = os.environ.get(
            "MTA_TRUSTED_GATEWAY_HEADER", "X-VectorFLOW-Identity")
        self.assertEqual(json.loads(forwarded['headers'][header_name]), {
            'id': 7, 'name': 'Stage 7B', 'email': 'stage7b@example.invalid',
            'entitlements': ['mta-report-urls']})
        self.assertEqual(forwarded['json']['product_permissions'], [11])
        self.assertEqual(forwarded['json']['location_permissions'], [22])
        self.assertTrue(forwarded['stream'])
        self.assertEqual(forwarded['timeout'], (5, 60))

    @patch("api_gateway.interceptors.mta_interceptor.User_Application_Location_Permission.objects.filter")
    @patch("api_gateway.interceptors.mta_interceptor.User_Application_Product_Permission.objects.filter")
    @patch("api_gateway.interceptors.mta_interceptor.requests.request")
    def test_legacy_get_receives_gateway_derived_identity(
        self, request_mock, product_filter_mock, location_filter_mock
    ):
        product_filter_mock.return_value.values_list.return_value = []
        location_filter_mock.return_value.values_list.return_value = []
        request_mock.return_value = MagicMock(status_code=200)

        MTA_INTERCEPTOR().forward(self.request(), self.service_map)

        forwarded = request_mock.call_args.kwargs
        header_name = os.environ.get(
            "MTA_TRUSTED_GATEWAY_HEADER", "X-VectorFLOW-Identity"
        )
        self.assertEqual(
            json.loads(forwarded["headers"][header_name]),
            {"id": 7, "name": "Stage 7B", "email": "stage7b@example.invalid"},
        )
        self.assertEqual(forwarded["url"], "http://mta:8000/api/mta/GetEnvironmentConfiguration")

    @patch("api_gateway.interceptors.mta_interceptor.User_Application_Location_Permission.objects.filter")
    @patch("api_gateway.interceptors.mta_interceptor.User_Application_Product_Permission.objects.filter")
    @patch("api_gateway.interceptors.mta_interceptor.requests.request")
    def test_legacy_post_keeps_permission_payload_and_trusted_identity(
        self, request_mock, product_filter_mock, location_filter_mock
    ):
        product_filter_mock.return_value.values_list.return_value = [11]
        location_filter_mock.return_value.values_list.return_value = [22]
        request_mock.return_value = MagicMock(status_code=200)

        original = {
            "filters": {}, "paginationParameter": {"pageNumber": 1},
            "product_permissions": [999], "location_permissions": [999],
            "user": {"id": 999, "name": "spoofed"},
        }
        MTA_INTERCEPTOR().forward(
            self.request("POST", "/api/mta/DBMData", original), self.service_map
        )

        forwarded = request_mock.call_args.kwargs
        self.assertEqual(forwarded["json"]["product_permissions"], [11])
        self.assertEqual(forwarded["json"]["location_permissions"], [22])
        self.assertEqual(forwarded["json"]["user"], {"id": 7, "name": "Stage 7B"})
        self.assertEqual(original["user"], {"id": 999, "name": "spoofed"})
        self.assertEqual(original["product_permissions"], [999])
        self.assertTrue(forwarded['stream'])
        self.assertEqual(forwarded['timeout'], (5, 60))

    @patch("api_gateway.interceptors.mta_interceptor.User_Application_Location_Permission.objects.filter")
    @patch("api_gateway.interceptors.mta_interceptor.User_Application_Product_Permission.objects.filter")
    @patch("api_gateway.interceptors.mta_interceptor.requests.request")
    def test_planning_count_uses_assigned_scopes_not_browser_spoof(
        self, request_mock, product_filter_mock, location_filter_mock
    ):
        product_filter_mock.return_value.values_list.return_value = []
        location_filter_mock.return_value.values_list.return_value = []
        request_mock.return_value = MagicMock(status_code=200)
        original = {"product_permissions": [999], "location_permissions": [999]}

        MTA_INTERCEPTOR().forward(
            self.request("POST", "/api/mta/GetPlanningDataCount", original), self.service_map
        )

        forwarded = request_mock.call_args.kwargs
        self.assertEqual(forwarded["url"], "http://mta:8000/api/mta/GetPlanningDataCount")
        self.assertEqual(forwarded["json"]["product_permissions"], [])
        self.assertEqual(forwarded["json"]["location_permissions"], [])
        self.assertEqual(original, {"product_permissions": [999], "location_permissions": [999]})

    @patch("api_gateway.interceptors.mta_interceptor.User_Application_Location_Permission.objects.filter")
    @patch("api_gateway.interceptors.mta_interceptor.User_Application_Product_Permission.objects.filter")
    @patch("api_gateway.interceptors.mta_interceptor.requests.request")
    def test_demo_read_only_error_is_preserved_for_gateway_clients(
        self, request_mock, product_filter_mock, location_filter_mock
    ):
        product_filter_mock.return_value.values_list.return_value = []
        location_filter_mock.return_value.values_list.return_value = []
        request_mock.return_value = MagicMock(
            status_code=403, text='{"error":"demo_read_only"}',
        )
        request_mock.return_value.json.return_value = {"error": "demo_read_only"}

        response = MTA_INTERCEPTOR().forward(
            self.request("POST", "/api/mta/SubmitOpenExpediteRequest"), self.service_map
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(json.loads(response.content), {"error": "demo_read_only"})


class TestGatewayLocalJsonResponses(SimpleTestCase):
    def test_local_mta_read_only_json_is_not_converted_to_gateway_error(self):
        local_error = JsonResponse({"error": "demo_read_only"}, status=403)
        view = API_GATEWAY_VIEW()
        self.assertIs(view._passthrough_local_json(local_error), local_error)
        self.assertIsNone(view._passthrough_local_json(MagicMock()))


class TestMtoInterceptorIdentity(SimpleTestCase):
    service_map = {"mto": {"base_url": "http://mto:10015", "application_id": 3}}

    @staticmethod
    def request(headers=None, cookies=None):
        return SimpleNamespace(
            method="POST",
            path="/api/mto/getDDQData/",
            data={"user": {"id": 999}, "product_permissions": [999]},
            query_params={},
            GET={},
            COOKIES={"access_token": "cookie-token"} if cookies is None else cookies,
            user=SimpleNamespace(id=7, name="authenticated-user"),
            headers={"User-Id": "19", "User-Name": "legacy-header-user"} if headers is None else headers,
            FILES={},
        )

    @patch("api_gateway.interceptors.mto_interceptor.User_Application_Location_Permission.objects.filter")
    @patch("api_gateway.interceptors.mto_interceptor.User_Application_Product_Permission.objects.filter")
    @patch("api_gateway.interceptors.mto_interceptor.User.objects.filter")
    @patch("api_gateway.interceptors.mto_interceptor.requests.request")
    def test_browser_headers_win_over_authenticated_session_and_body(
        self, request_mock, user_filter_mock, product_filter_mock, location_filter_mock
    ):
        user_filter_mock.return_value.values.return_value = [{"is_admin": False}]
        product_filter_mock.return_value.values_list.return_value = [11]
        location_filter_mock.return_value.values_list.return_value = [22]
        request_mock.return_value = MagicMock(status_code=200)

        MTO_INTERCEPTOR().forward(self.request(), self.service_map)

        user_filter_mock.assert_called_once_with(id=19)
        product_filter_mock.assert_called_once_with(application_id=3, user_id=19)
        location_filter_mock.assert_called_once_with(application_id=3, user_id=19)
        forwarded = request_mock.call_args.kwargs
        self.assertEqual(forwarded["url"], "http://mto:10015/getDDQData/")
        self.assertEqual(forwarded["headers"]["Authorization"], "Bearer cookie-token")
        self.assertEqual(
            forwarded["json"]["user"],
            {"id": "19", "name": "legacy-header-user", "is_admin": False},
        )
        self.assertEqual(forwarded["json"]["product_permissions"], [11])
        self.assertEqual(forwarded["json"]["location_permissions"], [22])

    @patch("api_gateway.interceptors.mto_interceptor.requests.request")
    def test_missing_and_malformed_user_id_preserve_parse_errors(self, request_mock):
        with self.assertRaises(TypeError):
            MTO_INTERCEPTOR().forward(self.request(headers={}), self.service_map)
        with self.assertRaises(ValueError):
            MTO_INTERCEPTOR().forward(
                self.request(headers={"User-Id": "not-an-id"}), self.service_map
            )
        request_mock.assert_not_called()

    @patch("api_gateway.interceptors.mto_interceptor.requests.request")
    def test_cookie_is_still_required_before_header_parsing(self, request_mock):
        response = MTO_INTERCEPTOR().forward(
            self.request(headers={"User-Id": "19"}, cookies={}), self.service_map
        )
        self.assertEqual(response.status_code, 401)
        request_mock.assert_not_called()
