"""HTTP ownership and explicit frontend compatibility of immutable order reads."""
import json
import os
import unittest
from unittest.mock import patch

os.environ.setdefault('VF_SECRET_KEY', 'order-report-unit-only')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
import django
django.setup()
from django.test import RequestFactory, SimpleTestCase, override_settings
from django.urls import resolve
from mta.presentation import order_reports as reader, order_report_views as views
from mta.presentation.context import PublicationUnavailable


@override_settings(MTA_TRUSTED_GATEWAY_HEADER='X-VectorFLOW-Identity')
class OrderReportTests(SimpleTestCase):
    def request(self, route, *, authenticated=True, payload=None, method='post'):
        headers = {'HTTP_X_VECTORFLOW_IDENTITY': json.dumps({'id': 8})} if authenticated else {}
        return getattr(RequestFactory(), method)('/api/mta/' + route,
            data=json.dumps(payload or {}) if method == 'post' else {},
            content_type='application/json', **headers)

    def test_exact_routes_and_authentication(self):
        for route in ('GetOrderAllocationReportData', 'GetOrderAllocationReportDataCount',
                      'GetElephantOrderData', 'GetElephantOrderDataCount'):
            match = resolve('/api/mta/' + route)
            with patch.object(reader, 'read') as read:
                response = match.func(self.request(route, authenticated=False))
            self.assertEqual(response.status_code, 403)
            read.assert_not_called()
        self.assertIs(resolve('/api/mta/EOUIConfig').func, views.ui_config)

    def test_explicit_count_wire_aliases_for_both_existing_client_paths(self):
        request = self.request('GetOrderAllocationReportDataCount')
        with patch.object(reader, 'read', return_value=7):
            oa = json.loads(views.order_data(request, count=True).content)
            eo = json.loads(views.order_data(request, count=True, elephant=True).content)
        self.assertEqual(oa['data'], [{'Count': 7, 'count': 7}])
        self.assertIsNone(oa['recordCount'])
        self.assertEqual(eo['data'], [{'count': 7}])
        self.assertEqual(eo['recordCount'], '7')

    def test_empty_elephant_is_usable_grid_with_zero_string_count(self):
        with patch.object(reader, 'read', return_value=[]):
            response = views.order_data(self.request('GetElephantOrderData'), elephant=True)
        body = json.loads(response.content)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body['data'], [])
        self.assertEqual(body['recordCount'], '0')

    def test_unavailable_publication_never_becomes_empty_success(self):
        with patch.object(reader, 'read', side_effect=PublicationUnavailable('owner_changed')):
            response = views.order_data(self.request('GetElephantOrderData'), elephant=True)
        self.assertEqual(response.status_code, 503)
        self.assertEqual(json.loads(response.content), {'error': 'owner_changed'})

    def test_new_configs_preserve_visible_original_field_names(self):
        oa = views.columns('OrderAllocationReport')
        self.assertEqual(len(oa), 14)
        self.assertEqual(oa[7]['Col_Code'], 'DueDate')
        self.assertEqual(oa[-1]['Col_Code'], 'dailydatagraph')
        self.assertNotIn('Value', oa[-1])
        self.assertNotIn('TagID', oa[0])
        eo = views.columns('ElephantOrderReport')
        self.assertEqual(len(eo), 13)
        self.assertEqual(eo[-1]['Col_Code'], 'DueDate')
        self.assertFalse(any(r['Col_Code'] == 'dueDateAction' for r in eo))

    def test_other_ui_config_response_preserved(self):
        request = self.request('GetUIConfig?reportName=missing', method='get')
        response = views.ui_config(request)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(json.loads(response.content)['error'], 'legacy_ui_config_not_migrated')

    def test_native_filter_gate_and_parameterized_product_hierarchy(self):
        custom = {'customAttributeFilter': {'filters': [dict(attributeName='skuattr1',
                    operator='equalto', value='x')]}}
        filters = reader.AllocationFilters({'filters': custom}, count=True)
        self.assertEqual(filters.compile(), 'TRUE')
        value = "x' OR 1=1 --"
        filters = reader.AllocationFilters({'filters': {'productFilter': {'filters': [
            dict(attributeName='p1', operator='equalto', value=value)]}}}, count=True)
        sql = filters.compile()
        self.assertNotIn(value, sql)
        self.assertEqual(filters.params, [value])
        self.assertIn('C."SL1"', sql)

    def test_nonexistent_legacy_allocation_filter_columns_are_not_invented(self):
        for group, field in (('locationFilter', 'location'),
                             ('supplyChainFilter', 'forchildrenlocationcode'),
                             ('availabilityFilter', 'norm')):
            filters = reader.AllocationFilters({'filters': {group: {'filters': [
                dict(attributeName=field, operator='equalto', value='1')]}}}, count=True)
            with self.assertRaises(ValueError):
                filters.compile()


if __name__ == '__main__':
    unittest.main()
