"""Narrow deployed supplier value and intermediate-description boundaries."""
import os
import unittest
from unittest.mock import patch
from types import SimpleNamespace

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY', 'unit-only')
import django
django.setup()

from mta.mdm.supplier_tasks import convert
from mta.mdm.supplier_capture import location_master, require_format
from mta.mdm.supplier_reads import _review_text
from mta.mdm.supplier_permissions import triples, sql_permissions


class SupplierContractTests(unittest.TestCase):
    def test_root_permission_expansion_keeps_duplicate_triples_and_excludes_null_join(self):
        records = [dict(id=i, level_1=a, level_2=b, level_3=c) for i, a, b, c in (
            (1, 'A', None, None), (2, 'A', 'B', 'C'), (3, 'A', 'B', 'C'),
            (4, 'A', None, 'C'), (5, 'Other', 'B', 'C'))]
        with patch('mta.mdm.supplier_permissions.permission_catalogue', return_value={'products': {'records': records}}):
            self.assertEqual(dict(triples('products', [1])), {('a', 'b', 'c'): 2})
            sql, values = sql_permissions('products', [1])
            self.assertEqual(values, ['a', 'b', 'c'] * 2)
            self.assertEqual(dict(triples('products', [4])), {('a', 'b', 'c'): 2})

    def test_supplier_format_must_match_actual_importer_setting(self):
        snapshot = {'nms_active': True, 'supplier': {'moq_format': 'WithDestLoc'}}
        require_format(snapshot, [{'Parameter': 'NMSMOQInputDataFormat', 'Value': 'WithDestLoc'}])
        for settings in ([], [{'Parameter': 'NMSMOQInputDataFormat', 'Value': 'WithoutDestLoc'}]):
            with self.assertRaisesRegex(ValueError, 'explicit importer setting'):
                require_format(snapshot, settings)

    def test_review_json_text_retains_native_float_notation(self):
        self.assertEqual(_review_text(SimpleNamespace(SOB=12.375), [('sb', 'SOB')]),
                         '{"sb":1.237500000000000e+001}')
        self.assertEqual(_review_text(SimpleNamespace(SOB=0.), [('sb', 'SOB')]),
                         '{"sb":0.000000000000000e+000}')

    def test_float53_and_unquoted_sql_null_are_distinct_from_json_null(self):
        self.assertEqual(convert(4, {'sb': '12.375'}, ['sb']), {'SOB': 12.375})
        self.assertEqual(convert(4, {'sb': 'NULL'}, ['sb']), {'SOB': None})
        with self.assertRaises(ValueError):
            convert(4, {'sb': None}, ['sb'])

    def test_quoted_moq_int32_conversion(self):
        self.assertEqual(convert(5, {'mq': ''}, ['mq']), {'MOQ': 0})
        self.assertEqual(convert(5, {'mq': '2147483647'}, ['mq']), {'MOQ': 2147483647})
        for value in ('2147483648', '1.5', 'NULL'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                convert(5, {'mq': value}, ['mq'])

    def test_description_full_join_includes_unapproved_unmatched_location(self):
        rows = location_master({'descriptions': [], 'approved': [dict(
            WHCode='LDC001', WHDescription='retained supplier', Approved=False, ActionType=1)]})
        self.assertEqual(rows, [{'WHCode': 'LDC001', 'WHDescription': 'retained supplier'}])

    def test_description_approved_update_can_write_null(self):
        rows = location_master({'descriptions': [dict(WHCode='LDC001', WHDescription='opening')],
            'approved': [dict(WHCode='LDC001', WHDescription=None, Approved=True, ActionType=1)]})
        self.assertEqual(rows, [{'WHCode': 'LDC001', 'WHDescription': None}])

    def test_description_competing_update_is_not_given_an_invented_winner(self):
        with self.assertRaisesRegex(ValueError, 'SOURCE_ORDER_AMBIGUITY'):
            location_master({'descriptions': [], 'approved': [dict(
                WHCode='LDC001', WHDescription=name, Approved=True, ActionType=1) for name in ('one', 'two')]})


if __name__ == '__main__':
    unittest.main()
