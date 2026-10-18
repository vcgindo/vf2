"""Focused supplier route, identity and distinct native count/data contracts.
DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
import json
import os
from types import SimpleNamespace
import unittest
from unittest.mock import patch

os.environ.setdefault('VF_SECRET_KEY', 'supplier-read-unit-only')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
import django
django.setup()
from django.test import RequestFactory, override_settings
from django.urls import resolve
from mta.presentation.supplier_allocation import SupplierFilters, query, read
from mta.presentation.boroa_filters import BorOaQueryError
from mta.presentation.context import PublicationUnavailable
from mta.presentation.views import supplier_allocation_data


def item(name, value, operator='equalto', **kw):
    return dict(attributeName=name, value=value, operator=operator, **kw)


class SupplierAllocationTests(unittest.TestCase):
    def test_exact_original_frontend_routes_resolve(self):
        for suffix in ('', 'Count'):
            match = resolve('/api/mta/getSupplierWiseAllocationReportData' + suffix)
            function = getattr(match.func, 'func', match.func)
            self.assertIs(function, supplier_allocation_data)

    @override_settings(MTA_TRUSTED_GATEWAY_HEADER='X-VectorFLOW-Identity')
    def test_authenticated_supplier_name_cannot_be_replaced_in_browser_body(self):
        request = RequestFactory().post('/api/mta/getSupplierWiseAllocationReportData',
            data=json.dumps(dict(user=dict(name='OTHER'), supplier_name='OTHER', filters={})),
            content_type='application/json',
            HTTP_X_VECTORFLOW_IDENTITY=json.dumps(dict(id=8, name='LDC001')))
        with patch('mta.presentation.views._require_report'), \
                patch('mta.presentation.supplier_allocation.read', return_value=[]) as reader:
            response = supplier_allocation_data(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(reader.call_args.args[1], 'LDC001')
        self.assertEqual(json.loads(response.content)['data'], [])

    @override_settings(MTA_TRUSTED_GATEWAY_HEADER='X-VectorFLOW-Identity')
    def test_missing_gateway_identity_denied_before_reader(self):
        request = RequestFactory().post('/api/mta/getSupplierWiseAllocationReportData',
            data='{"user":{"name":"LDC001"}}', content_type='application/json')
        with patch('mta.presentation.supplier_allocation.read') as reader:
            response = supplier_allocation_data(request)
        self.assertEqual(response.status_code, 403)
        reader.assert_not_called()

    def test_supplier_predicate_is_mandatory_parameterized_and_dispatch_positive(self):
        forged = "LDC001' OR 1=1 --"
        for count in (True, False):
            with patch('mta.presentation.supplier_allocation.remark_query', return_value=('SELECT 1', [])):
                sql, params = query(SimpleNamespace(pk='owned-run'), dict(filters={}), forged, count=count)
            self.assertNotIn(forged, sql)
            self.assertIn('R."a_dispatchqty">0', sql)
            self.assertIn('lower(rtrim(R."a_suppliercode"::text', sql)
            self.assertEqual(params, ['owned-run', forged])

    def test_count_preserves_native_joins_without_data_only_occurrences(self):
        sql, _ = query(SimpleNamespace(pk='run'), dict(filters={}), 'LDC001', count=True)
        self.assertIn('SELECT DISTINCT', sql)
        for owner in ('a', 'b', 'c', 'd', 'e'):
            self.assertIn('"' + owner + '_ordinal"', sql)
        for absent in ('f_ordinal', 's1_ordinal', 's2_ordinal', 's3_ordinal', 'LEFT JOIN RM'):
            self.assertNotIn(absent, sql)
        self.assertIn('count(*)', sql)

    def test_data_retains_remark_ties_projection_order_and_native_pagination(self):
        with patch('mta.presentation.supplier_allocation.remark_query', return_value=('SELECT * FROM remarks_owned WHERE run_id=%s', ['run'])):
            sql, params = query(SimpleNamespace(pk='run'),
                dict(filters={}, paginationParameter=dict(pageNumber=2, recordsPerPage=5)), 'LDC001')
        self.assertIn('SELECT * FROM prepared', sql)
        self.assertIn('M."RemarkDate"=T.d', sql)
        self.assertIn('AS "SupplierDesc"', sql)
        self.assertIn('AS "Remark"', sql)
        self.assertIn('R."e_sequenceno" ASC NULLS FIRST', sql)
        self.assertTrue(sql.endswith('WHERE "RN" BETWEEN %s AND %s ORDER BY "RN"'))
        self.assertEqual(params, ['run', 'run', 'LDC001', 6, 10])

    def test_valid_hierarchy_and_direct_filters_use_their_native_owners(self):
        filters = dict(productFilter=dict(filters=[item('sku', '337'), item('p2', 'Selected')]),
            locationFilter=dict(filters=[item('location', 'DP010290')]),
            supplyChainFilter=dict(filters=[item('forlocation', 'CONSOLE')]))
        compiler = SupplierFilters(dict(filters=filters), count=True)
        sql = compiler.compile()
        for field in ('a_skucode', 'c_sl2', 'a_whcode', 'd_locationtype'):
            self.assertIn(field, sql)
        self.assertIn('337', compiler.params)

    def test_count_numeric_filter_does_not_repair_native_data_ambiguity(self):
        payload = dict(filters=dict(availabilityFilter=dict(filters=[item('Norm', '5', 'greaterthan')])))
        self.assertIn('a_norm', SupplierFilters(payload, count=True).compile())
        with self.assertRaisesRegex(BorOaQueryError, 'ambiguous'):
            SupplierFilters(payload).compile()

    def test_ignored_child_join_and_missing_replaced_parent_column_are_distinct(self):
        payload = dict(filters=dict(supplyChainFilter=dict(filters=[item('forchildren', 'Depot')])))
        self.assertEqual(SupplierFilters(payload).compile(), 'TRUE')
        payload['filters']['supplyChainFilter']['filters'] = [item('forchildrenlocationcode', 'PARENT')]
        with self.assertRaisesRegex(BorOaQueryError, 'column missing'):
            SupplierFilters(payload).compile()

    def test_unknown_numeric_operator_does_not_invent_a_predicate(self):
        payload = dict(filters=dict(availabilityFilter=dict(filters=[item('Norm', '5', 'unknown')])))
        self.assertEqual(SupplierFilters(payload).compile(), 'TRUE')
        payload['filters']['productFilter'] = dict(filters=[item('sku', '337')])
        with self.assertRaisesRegex(BorOaQueryError, 'empty filter operator'):
            SupplierFilters(payload).compile()

    def test_native_missing_color_and_coverage_owners_remain_failures(self):
        for filters in (
                dict(availabilityFilter=dict(filters=[item('pic', 'Black')])),
                dict(colorFilter=dict(filters=[item('Black', '2', type='colorcount')])),
                dict(coverageFilter=dict(filters=[item('coverage', 'Low')]))):
            with self.subTest(filters=filters), self.assertRaises(BorOaQueryError):
                SupplierFilters(dict(filters=filters)).compile()

    def test_custom_only_is_ignored_under_original_callers_condition(self):
        payload = dict(filters=dict(customAttributeFilter=dict(filters=[item('SKUAttr1', 'x')])))
        self.assertEqual(SupplierFilters(payload).compile(), 'TRUE')
        payload['filters']['productFilter'] = dict(filters=[])
        self.assertIn('c_c1', SupplierFilters(payload).compile())

    def test_missing_prepared_receipt_cannot_fall_back_to_raw_or_latest(self):
        with patch('mta.presentation.boroa_sources.admitted_sources', return_value=(SimpleNamespace(pk='run'), SimpleNamespace(source_digest='source'))), \
                patch('mta.presentation.native_publication.enabled', return_value=True), \
                patch('mta.presentation.native_publication.require_mode'), \
                patch('mta.runtime.boroa_models.BorOaPreparedReceipt.objects') as receipts, \
                patch('mta.presentation.supplier_allocation.query') as builder:
            receipts.filter.return_value.first.return_value = None
            with self.assertRaisesRegex(PublicationUnavailable, 'receipt_missing'):
                read(dict(filters={}), 'LDC001')
        builder.assert_not_called()
