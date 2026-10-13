"""Canonical category equality joins preserve unmatched NULL-key targets."""
from copy import deepcopy
from datetime import date
import unittest
from mta.domain.btr_finalization import _categories
from mta.temporal.chain import initialise_sku_loc_standard_attributes


class CategoryNullKeyTests(unittest.TestCase):
    def test_daily_distinct_retains_null_keys_then_category_join_leaves_them_unchanged(self):
        raw=[dict(SKUCode='337',WhCode='DP010290'),dict(SKUCode='5328',WhCode=None),
             dict(SKUCode=None,WhCode='PL002'),dict(SKUCode=None,WhCode=None),
             dict(SKUCode='5954',WhCode='DP020819')]
        attrs=initialise_sku_loc_standard_attributes(dict(MasterDataRaw=raw+raw,
            MasterDataRawNonNMS=[]))
        self.assertEqual([(r['SKUCode'],r['WhCode']) for r in attrs],
                         [('337','DP010290'),('5328',None),(None,'PL002'),(None,None),('5954','DP020819')])
        attrs[1]['Category']='retained'
        attrs.append(deepcopy(attrs[0]))  # Category UPDATE preserves target multiplicity.
        before=deepcopy(attrs)
        facts=dict(SKULocStandardAttributes=attrs,MasterData=[],DailyConsumption=[],
            GoodsInTransitTransporterMaster=[],Suggestions=[dict(SKUCode='337',WhCode='DP010290',Type=5)])
        result=_categories(date(2026,7,3),dict(BTRSnapshotForUI=[],BufferTrendPhysicalInv=[]),
            facts,dict(up={1},down={5}))
        expected=deepcopy(before)
        expected[0]['Category']=expected[-1]['Category']='7'
        self.assertEqual(result['SKULocStandardAttributes'],expected)
        self.assertEqual(attrs,before)

    def test_null_sku_never_matches_a_python_none_equality_join(self):
        attrs=[dict(SKUCode=None,WhCode='LDC001',Category='kept')]
        facts=dict(SKULocStandardAttributes=attrs,MasterData=[],DailyConsumption=[],
            GoodsInTransitTransporterMaster=[],Suggestions=[dict(SKUCode=None,WhCode='LDC001',Type=5)])
        result=_categories(date(2026,7,3),dict(BTRSnapshotForUI=[],BufferTrendPhysicalInv=[]),
            facts,dict(up={1},down={5}))
        self.assertEqual(result['SKULocStandardAttributes'],attrs)

    def test_missing_location_field_remains_an_error(self):
        with self.assertRaisesRegex(KeyError,'WhCode'):
            _categories(date(2026,7,3),{},dict(SKULocStandardAttributes=[dict(SKUCode='337')]),{})

    def test_missing_sku_field_remains_an_error_even_for_null_location(self):
        with self.assertRaisesRegex(KeyError,'SKUCode'):
            _categories(date(2026,7,3),{},dict(SKULocStandardAttributes=[dict(WhCode=None)]),{})
