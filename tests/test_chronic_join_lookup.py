"""Chronic location lookup indexing preserves the deployed nested-loop bag."""
from itertools import product
import unittest
from unittest.mock import patch

from mta.presentation import insights


def nested_loop_rows(btr, *, filter_owners=False):
    """Retained pre-index chronic-loc reconstruction used as the test oracle."""
    result = []
    for row in btr['ChronicUnavalabilityData']:
        sku, loc = insights._key(row)
        populations = [
            [r for r in btr['SkuAttributeData'] if r['SKUCode'] == sku],
            [r for r in btr['LocationAttributeData'] if r['WHCode'] == loc],
            [r for r in btr['SkuLocAttributeData'] if insights._key(r) == (sku, loc)] or [{}],
            [r for r in btr['SiteDescriptionTbl'] if r['WHCode'] == loc],
            [{}],
        ]
        for sa, la, sla, description, master in product(*populations):
            value = {**row, 'WHCode': loc,
                     'ParentWhCode': master.get('ParentWhCode', row.get('ParentWhCode')),
                     '_sku': sa, '_loc': la, '_description': description}
            value.update({f'SKUAttribute{i}': sa.get(f'c{i}') for i in range(1, 16)})
            value.update({f'LocAttribute{i}': la.get(f'c{i}') for i in range(1, 16)})
            value.update({f'SkuLocAttribute{i}': sla.get(f'c{i}') for i in range(1, 16)})
            value.update({k: v for k, v in sa.items() if not k.startswith('c')})
            value.update({k: v for k, v in la.items() if not k.startswith('c')})
            if filter_owners:
                value.update(_a=row, _location=la, _pair=sla, _master=master)
            result.append(value)
    return result


def chronic(sku, location, *, rlt=2, age=3, colour='Red'):
    return dict(SKUCode=sku, WhCode=location, ParentWhCode='P', RLT=rlt, BRAge=age,
                PhysicalInventoryColor=colour, PhysicalInventoryPen='10.00',
                PipelineInventoryColor='Green', PipelineInventoryPen='20.00', RationedQty=1)


class ChronicLocationLookupTests(unittest.TestCase):
    def setUp(self):
        self.state = {
            'ChronicUnavalabilityData': [
                chronic('S1', 'L1'),
                chronic('S2', 'L2', colour='Black'),
                chronic('S3', 'L3'),                         # optional pair missing
                chronic('S4', 'L4'),                         # required SKU missing
                chronic('S5', 'L5'),                         # required location missing
                chronic('S6', 'L6'),                         # required description missing
                chronic(None, None),                         # preserve Python NULL-key matching
                chronic('S7', 'L7', rlt=3, age=3),           # threshold tie is excluded
                chronic('S8', 'L8', rlt=None, age=4),        # NULL threshold is excluded
                chronic('S9', 'L9', rlt=2, age=None),        # NULL age is excluded
            ],
            'SkuAttributeData': [
                {'SKUCode': 'S1', 'SL1': 'first', 'c1': 's1-a'},
                {'SKUCode': 'S1', 'SL1': 'second', 'c1': 's1-b'},
                *[{'SKUCode': sku, 'SL1': sku, 'c1': sku} for sku in
                  ('S2', 'S3', 'S5', 'S6', 'S7', 'S8', 'S9')],
                {'SKUCode': None, 'SL1': 'null-sku', 'c1': None},
            ],
            'LocationAttributeData': [
                {'WHCode': 'L1', 'LL1': 'first', 'c1': 'l1-a'},
                {'WHCode': 'L1', 'LL1': 'second', 'c1': 'l1-b'},
                *[{'WHCode': loc, 'LL1': loc, 'c1': loc} for loc in
                  ('L2', 'L3', 'L4', 'L6', 'L7', 'L8', 'L9')],
                {'WHCode': None, 'LL1': 'null-location', 'c1': None},
            ],
            'SkuLocAttributeData': [
                {'SKUCode': 'S1', 'LocCode': 'L1', 'c1': 'pair-a'},
                {'SKUCode': 'S1', 'LocCode': 'L1', 'c1': 'pair-b'},
                *[{'SKUCode': sku, 'LocCode': loc, 'c1': sku + loc} for sku, loc in
                  (('S2', 'L2'), ('S4', 'L4'), ('S5', 'L5'), ('S6', 'L6'),
                   ('S7', 'L7'), ('S8', 'L8'), ('S9', 'L9'))],
                {'SKUCode': None, 'LocCode': None, 'c1': None},
            ],
            'SiteDescriptionTbl': [
                {'WHCode': 'L1', 'WHDescription': 'one-a'},
                {'WHCode': 'L1', 'WHDescription': 'one-b'},
                *[{'WHCode': loc, 'WHDescription': loc} for loc in
                  ('L2', 'L3', 'L4', 'L5', 'L7', 'L8', 'L9')],
                {'WHCode': None, 'WHDescription': 'null-description'},
            ],
        }

    def assert_same_rows(self, filter_owners):
        expected = nested_loop_rows(self.state, filter_owners=filter_owners)
        actual = insights.joined_rows(self.state, {}, 'chronic-loc',
                                      filter_owners=filter_owners)
        self.assertEqual(actual, expected)
        return expected, actual

    def test_complete_ordered_bag_matches_nested_loop_without_filter_owners(self):
        expected, actual = self.assert_same_rows(False)
        self.assertEqual(len(actual), 22)
        self.assertEqual([row['SkuLocAttribute1'] for row in actual[:8]],
                         ['pair-a', 'pair-a', 'pair-b', 'pair-b'] * 2)
        self.assertEqual(actual, expected)

    def test_complete_ordered_bag_and_projection_match_with_filter_owners(self):
        expected, actual = self.assert_same_rows(True)
        self.assertTrue(all(set(('_a', '_location', '_pair', '_master')) <= set(row)
                            for row in actual))
        self.assertEqual(insights.project(actual, 'chronic-loc'),
                         insights.project(expected, 'chronic-loc'))
        projected = insights.project(actual, 'chronic-loc')
        self.assertEqual([row.get('whcode') for row in projected], ['L1', 'L2', 'L3', None])
        self.assertEqual(projected[0]['countSku'], 16)
        self.assertEqual(projected[1]['countSku'], 1)

    def test_other_join_kinds_retain_their_own_description_contract(self):
        state = {
            'ChronicUnavalabilityData': [chronic('S1', 'L1')],
            'SkuAttributeData': [{'SKUCode': 'S1'}],
            'LocationAttributeData': [{'WHCode': 'L1'}],
            'SkuLocAttributeData': [],
            'SKUDescriptionTbl': [{'SKUCode': 'S1', 'SKUDescription': 'one'}],
        }
        rows = insights.joined_rows(state, {}, 'chronic-sku', filter_owners=True)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['_description']['SKUDescription'], 'one')


if __name__ == '__main__':
    unittest.main()
