"""HTTP wiring and security proof; no database creation or fixture writes."""
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY', 'logistics-unit-check-only')
import django
django.setup()
import json
import unittest
from unittest.mock import patch
from datetime import date, datetime, timezone
from django.test import RequestFactory
from django.urls import resolve
from django.db import DatabaseError
from mta.presentation import logistics_read as reader, logistics_views
from mta.presentation.permissions import PermissionCodes


class LogisticsReadContractTests(unittest.TestCase):
    routes = {'GetInTransitWhereAboutsData': ('transit_grid', [dict(OrderNo='O', Qty=4)]),
              'GetInTransitWhereAboutsDataCount': ('transit_grid', 4),
              'GetTransporterDetails': ('contacts', [dict(TransporterName='Carrier')]),
              'GetRemarkDetailsForInTransit': ('transit_history', []),
              'GetOpenExpediteRequest': ('open_requests', dict(uiConfig=[], data=[])),
              'GetRemarkDetailsForExpedite': ('expedite_history', [])}

    def request(self, route, method='POST', actor=True, body=None):
        headers = {'HTTP_X_VECTORFLOW_IDENTITY': json.dumps({'id': 1, 'name': 'fixture'})} if actor else {}
        return RequestFactory().generic(method, '/api/mta/'+route,
            data=json.dumps(body if body is not None else {'product_permissions': [], 'location_permissions': []}),
            content_type='application/json', **headers)

    def call(self, route, **kw):
        request = self.request(route, **kw)
        match = resolve(request.path)
        return match.func(request, **match.kwargs)

    def test_all_six_registered_reads_preserve_full_envelopes_and_count_type(self):
        for route, (name, result) in self.routes.items():
            with self.subTest(route=route), patch.object(logistics_views, 'selected_run', return_value='run'), \
                    patch.object(reader, name, return_value=result) as handler:
                response = self.call(route)
                self.assertEqual(response.status_code, 200)
                body = json.loads(response.content)
                self.assertEqual(body['recordCount'] if route.endswith('Count') else body['data'],
                                 str(result) if route.endswith('Count') else result)
                self.assertEqual(handler.call_count, 1)

    def test_every_read_rejects_wrong_method_and_missing_identity_before_reader(self):
        with patch.object(logistics_views, 'selected_run', side_effect=AssertionError('must not select')):
            for route in self.routes:
                self.assertEqual(self.call(route, method='GET').status_code, 405)
                self.assertEqual(self.call(route, actor=False).status_code, 403)

    def test_aliases_match_exact_configuration_and_keep_normal_get_auth(self):
        from mta.presentation import views
        expected=json.loads((views.CONFIG/'logistics'/'ui_columns_v1.json').read_text())
        for name in ('InTransitWhereAbouts', 'OpenExpeditingRequests'):
            response=self.call('GetUIConfig?reportName='+name, method='GET')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(json.loads(response.content)['data'], expected[name])

    def test_denial_unavailable_and_storage_failure_are_truthful(self):
        for error, status in [(reader.TargetDenied('denied'),403),
                              (reader.PublicationUnavailable('unavailable'),503),
                              (DatabaseError('failed'),500)]:
            with patch.object(logistics_views,'selected_run',return_value='run'), \
                    patch.object(reader,'transit_grid',side_effect=error):
                self.assertEqual(self.call('GetInTransitWhereAboutsData').status_code,status)

    def test_order_wide_scope_rejects_hidden_sibling_nulls_and_empty_targets(self):
        products=PermissionCodes({'337':1});locations=PermissionCodes({'DP':1})
        reader.authorize_targets([dict(SKUCode='337',WhCode='DP')],products,locations)
        for rows in ([],[dict(SKUCode='338',WhCode='DP')],
                     [dict(SKUCode='337',WhCode='DP'),dict(SKUCode='337',WhCode='other')],
                     [dict(SKUCode=None,WhCode='DP')]):
            with self.assertRaises(reader.TargetDenied):reader.authorize_targets(rows,products,locations)

    def test_wire_preserves_null_omission_and_native_wall_dates(self):
        self.assertEqual(reader.omit_nulls(dict(a=None,b='',c=date(2026,10,18),
            d=datetime(2026,10,18,12,1,tzinfo=timezone.utc))),
            dict(b='',c='2026-10-18',d='2026-10-18T12:01:00'))
