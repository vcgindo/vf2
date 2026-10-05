"""Focused BOR-OA filter behavior from the pinned deployed alias call."""
import os
import unittest
from decimal import Decimal

os.environ.setdefault('VF_SECRET_KEY', 'unit-only')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
import django
django.setup()

from mta.presentation.boroa_filters import BorOaFilters, BorOaQueryError
from mta.presentation.context import PublicationUnavailable


def item(name, value='0', operator='greaterthan', **extra):
    return dict(attributeName=name, value=value, operator=operator, **extra)


class BorOaFilterContractTests(unittest.TestCase):
    def compile(self, filters, *, count=False):
        compiler = BorOaFilters(dict(filters=filters), count=count)
        return compiler.compile(), compiler.params, compiler.children

    def test_pinned_alias_owners_compile_to_prepared_columns(self):
        filters = {
            'supplyChainFilter': {'filters': [
                item('forlocation', 'Depot'),
                item('forlocationlocationcode', 'L1'),
                item('forchildrenlocationcode', 'P1'),
                item('forchildren', 'Plant'),
            ]},
            'productFilter': {'filters': [item('sku', 'S1'), item('p2', 'Food', 'equalto')]},
            'locationFilter': {'filters': [item('location', 'L2'), item('l3', 'West', 'equalto')]},
            'availabilityFilter': {'filters': [item('norm', '4'), item('pic', 'Red')]},
            'customAttributeFilter': {'filters': [
                item('SKULocAttr1', 'x', 'equalto'), item('SKUAttr2', 'y', 'equalto'),
                item('LocAttr3', 'z', 'equalto'),
            ]},
        }
        sql, params, children = self.compile(filters)
        for column in ('d_locationtype', 'a_whcode', 'f_parentwhcode', 'a_skucode',
                       'c_sl2', 'd_ll3', 'a_norm', 'a_dispatchcolor',
                       'b_c1', 'c_c2', 'd_c3'):
            self.assertIn('R."' + column + '"', sql)
        self.assertEqual(children, ['Plant'])
        self.assertEqual(params, ['Depot', 'L1', 'P1', 'L2', 'West', 'Food', 'S1',
                                  Decimal('4'), 'Red', 'x', 'y', 'z'])

    def test_null_builder_preserves_only_already_flushed_groups(self):
        self.assertEqual(self.compile(None), ('TRUE', [], []))
        self.assertEqual(self.compile({'productFilter': {'filters': None}}), ('TRUE', [], []))
        location = {'locationFilter': {'filters': [item('location', 'L1')]}}
        self.assertEqual(
            self.compile(location),
            self.compile({**location, 'productFilter': {'filters': None}}),
        )
        # Product SKU values are local until the complete product group builds.
        self.assertEqual(
            self.compile({'productFilter': {'filters': [item('sku', 'S1'), item(None)]}}),
            ('TRUE', [], []),
        )

    def test_native_missing_columns_and_dangling_builds_remain_failures(self):
        cases = (
            {'availabilityFilter': {'filters': [item('availability')] }},
            {'availabilityFilter': {'filters': [item('ohic', 'Red')] }},
            {'availabilityFilter': {'filters': [item('category', 'A', 'contains')] }},
            {'coverageFilter': {'filters': [item('coverage', 'A')] }},
            {'colorFilter': {'filters': [item('red', type='colorcount')] }},
            {'supplyChainFilter': {'filters': [item('forchildren', 'Plant'), item(None)]}},
        )
        for filters in cases:
            with self.subTest(filters=filters), self.assertRaises((BorOaQueryError, PublicationUnavailable)):
                self.compile(filters)

    def test_values_are_parameters_and_column_allowlist_is_closed(self):
        value = "x'); DROP TABLE example; --"
        sql, params, _ = self.compile({'productFilter': {'filters': [item('p1', value, 'equalto')]}})
        self.assertNotIn(value, sql)
        self.assertEqual(params, [value])
        with self.assertRaises(BorOaQueryError):
            BorOaFilters({}).column('A', 'PhysicalInventoryColor')
        with self.assertRaises(BorOaQueryError):
            BorOaFilters({}).column('Z', 'anything')

    def test_count_retains_only_deployed_qualified_c_alias_collision(self):
        # The count query aliases ColorSequence as C and SkuAttributeData as s,
        # product hierarchy predicates are unqualified and resolve to s.SL*.
        sql, params, _ = self.compile(
            {'productFilter': {'filters': [item('p1', 'Food', 'equalto')]}},
            count=True,
        )
        self.assertIn('R."c_sl1"', sql)
        self.assertEqual(params, ['Food'])

        # SKU custom attributes are explicitly qualified c.c* and fail because
        # C is ColorSequence in the count query.
        with self.assertRaises(BorOaQueryError):
            self.compile(
                {'customAttributeFilter': {'filters': [item('SKUAttr2', 'Food', 'equalto')]}},
                count=True,
            )

        # Direct SKU and the B/D custom owners remain valid in count SQL.
        filters = {
            'productFilter': {'filters': [item('sku', 'S1')]},
            'customAttributeFilter': {'filters': [
                item('SKULocAttr1', 'x', 'equalto'),
                item('LocAttr2', 'y', 'equalto'),
            ]},
        }
        sql, params, _ = self.compile(filters, count=True)
        self.assertIn('R."a_skucode"', sql)
        self.assertIn('R."b_c1"', sql)
        self.assertIn('R."d_c2"', sql)
        self.assertEqual(params, ['S1', 'x', 'y'])


if __name__ == '__main__':
    unittest.main()
