import unittest

from mta.presentation.excess_insights import project


class ExcessInsightsTests(unittest.TestCase):
    def test_value_does_not_apply_sku_white_predicate(self):
        rows = [dict(ReportDate='2026-06-17', LocationType='Depo',
                     PhysicalInventoryColor=color, SKUCode='S', Amount=amount)
                for color, amount in [('White', 4), ('White', 4), ('Black', 7)]]
        self.assertEqual(project(rows), [dict(locationtype='Depo', date='2026-06-17', countSku=2)])
        self.assertEqual(project(rows, value=True), [dict(locationtype='Depo', date='2026-06-17', value=15)])

    def test_null_location_and_literal_dash_remain_distinct_groups(self):
        rows = [dict(ReportDate='2026-06-17', LocationType=location,
                     PhysicalInventoryColor='White', SKUCode='S', Amount=None)
                for location in (None, '-')]
        self.assertEqual(project(rows, value=True), [dict(locationtype='-', date='2026-06-17')] * 2)

    def test_bigint_overflow_is_not_silently_extended(self):
        row = dict(ReportDate='2026-06-17', LocationType='Depo',
                   PhysicalInventoryColor='White', SKUCode='S', Amount=2**62)
        with self.assertRaises(OverflowError):
            project([row, row], value=True)
