"""Retain existing HTTP shapes and fail-closed scoped report boundaries."""
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY', 'scoped-dispatch-unit')
import django
django.setup()
import json
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch
from django.test import RequestFactory
from mta.presentation import scoped_api, scoped_selection, views
from mta.presentation.context import PublicationUnavailable


class ScopedReportDispatchTests(unittest.TestCase):
    def setUp(self):
        self.view = NS(run=NS(pk='run'))
        self.request = RequestFactory().post('/api/mta/BORData')
        self.enterContext(patch.object(scoped_selection, 'selected', return_value=self.view))

    def dispatch(self, name, **arguments):
        function = NS(__name__=name, __module__='mta.presentation.views')
        return scoped_api.dispatch(function, self.request, {}, arguments)

    def test_count_and_empty_shapes_remain_distinct(self):
        with patch('mta.presentation.bor_sql.read_bor', return_value=0) as read:
            self.assertEqual(json.loads(self.dispatch('bor_data', count=True).content)['recordCount'], '0')
            read.assert_called_once_with({}, count=True, analytics=False, read_binding=self.view)
        with patch('mta.presentation.boroa_sql.read_boroa', return_value=[]) as read:
            self.assertEqual(json.loads(self.dispatch('boroa_data').content)['data'], '')
            read.assert_called_once_with({}, count=False, read_binding=self.view)
        with patch('mta.presentation.boroa_sql.read_boroa', return_value=0):
            self.assertEqual(json.loads(self.dispatch('boroa_data', count=True).content)['data'], [{'count': 0}])

    def test_missing_owner_does_not_turn_into_empty(self):
        with patch('mta.presentation.bor_sql.read_bor', side_effect=PublicationUnavailable('owner absent')):
            with self.assertRaisesRegex(PublicationUnavailable, 'owner absent'):
                self.dispatch('bor_data')

    def test_writes_are_not_enabled_by_read_binding(self):
        for name in ('bor_remark', 'boroa_remark', 'supplier_allocation_data'):
            with self.subTest(name=name), self.assertRaisesRegex(PublicationUnavailable, 'phase_endpoint_not_prepared'):
                self.dispatch(name)

    def test_export_keeps_colour_layout_and_native_headers(self):
        with patch('mta.presentation.boroa_sql.read_boroa', return_value=[{'RN': 1, 'SKUCode': 'SKU'}]) as read, \
                patch('mta.presentation.boroa_sql.projection', return_value=[('SKUCode', 'unused')]), \
                patch('mta.presentation.scoped_bor.require_binding') as binding, \
                patch.object(views, 'identity', return_value={'id': 7}), \
                patch.object(views.ui_state, 'get_layout', return_value={}) as layout, \
                patch('mta.presentation.rrr_export.selected_headers', return_value=['RN', 'SKUCode']) as headers, \
                patch('mta.presentation.rrr_export.csv_chunks', return_value=[b'csv']):
            binding.return_value.configuration.return_value = {'columns': ['native']}
            response = scoped_api._bor_export(self.view, self.request, {}, 'BOROA')
            self.assertEqual(b''.join(response.streaming_content), b'csv')
            self.assertEqual(response['Content-Disposition'], 'attachment')
            layout.assert_called_once_with(7, 'BORColorBandwise')
            headers.assert_called_once_with({}, ['RN', 'SKUCode'], configuration=['native'])
            read.assert_called_once_with({}, export=True, read_binding=self.view)

    def test_batch_download_requires_server_entitlement(self):
        with patch.object(views, 'identity', return_value={'id': 7}), \
                patch('mta.presentation.scoped_bor.require_binding') as binding:
            response = scoped_api._download(self.view, self.request, {}, 'BOR_OrderAllocation')
            self.assertEqual(response.status_code, 403)
            binding.assert_not_called()
