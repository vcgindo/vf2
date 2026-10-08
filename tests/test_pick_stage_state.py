"""Native metadata capture must preserve the existing allocation seam."""
from copy import deepcopy
from decimal import Decimal
import unittest

from mta.domain.remaining_capabilities import calculate_pick_list, calculate_pick_list_state


def fixture():
    def item(sku, location, bucket, quantity, weight='2.000'):
        return dict(case=sku, sku=sku, from_location='P', to_location=location,
            logistics_location=location, weight=weight, volume='1.000', pack_size=1,
            dispatch_color='Black', buckets={bucket: quantity})
    return dict(vehicle=dict(name='fixture-vehicle', weight_capacity='5.000', volume_capacity='100.000'),
        items=[item('A', 'L1', 'to_black', 1), item('B', 'L1', 'to_red', 4),
               item('D', 'L2', 'to_green', 2, '1.000')])


class PickStateTests(unittest.TestCase):
    def test_full_state_preserves_allocations_and_inputs(self):
        case = fixture()
        before = deepcopy(case)
        original = calculate_pick_list(case)
        state = calculate_pick_list_state(case)
        self.assertEqual(state['allocations'], original)
        self.assertEqual(case, before)
        picked = state['LogisticPickList']
        self.assertEqual(len(picked), 3)
        self.assertEqual([r['ColorWiseAlloction'] for r in picked], [1, 1, 2])
        self.assertEqual([r['IsTruckFormed'] for r in picked], [None, True, True])
        self.assertEqual([r['CumulativeWeight'] for r in picked], list(map(Decimal, ('2.000', '10.000', '6.000'))))
        self.assertEqual([r['RemainingWeigt'] for r in picked], [None, Decimal('5.000'), Decimal('1.000')])
        self.assertEqual([r['NewSRNo'] for r in picked], [1, 2, 2])
        self.assertEqual([r['MinSRNo'] for r in picked], [2, 2, 2])
        self.assertTrue(all(len(row) == 21 and row['TransportLoadType'] == 'SXL' for row in picked))
        residual = state['PickListDataForTruckFormation']
        self.assertEqual([(r['SKUCode'], r['ColorWiseAlloction']) for r in residual], [('B', 1), ('D', 2)])
        self.assertTrue(all(len(row) == 16 and row['NoTruckFlag'] is True for row in residual))
        self.assertEqual(residual[0]['RemainingWeight'], Decimal('0.000'))
        self.assertEqual(residual[0]['TotalWeight'], Decimal('2.000'))

    def test_tied_priority_is_not_certified_by_metadata_capture(self):
        case = fixture()
        case['items'][1]['buckets'] = {'to_black': 4}
        with self.assertRaisesRegex(ValueError, 'priority-rank tie'):
            calculate_pick_list_state(case)
        self.assertTrue(calculate_pick_list(case))

    def test_volume_boundary_preserves_signed_weight_overage_and_mxl_threshold(self):
        case = fixture()
        case['vehicle'].update(weight_capacity='100.000', volume_capacity='2.500')
        for row in case['items'][:2]:
            row['weight'] = '4.500'
        result = calculate_pick_list_state(case)
        self.assertEqual(result['allocations'], calculate_pick_list(case))
        boundary = [r for r in result['LogisticPickList'] if r['IsTruckFormed']]
        self.assertEqual([r['RemainingWeigt'] for r in boundary], [Decimal('-77.500'), Decimal('-86.500')])
        self.assertEqual([r['RemainingVolume'] for r in boundary], [Decimal('2.500'), Decimal('.500')])
        self.assertTrue(all(r['TransportLoadType'] == 'MXL' for r in result['LogisticPickList']))

    def test_missing_physical_colour_is_not_invented(self):
        case = fixture()
        del case['items'][0]['dispatch_color']
        with self.assertRaises(KeyError):
            calculate_pick_list_state(case)
        self.assertTrue(calculate_pick_list(case))

    def test_null_dimension_and_zero_allocation_are_explicitly_unqualified(self):
        case = fixture()
        case['items'][0]['weight'] = None
        with self.assertRaises(ValueError):
            calculate_pick_list_state(case)
        case = fixture()
        case['items'][0]['weight'] = '6.000'
        with self.assertRaisesRegex(ValueError, 'Zero-allocation'):
            calculate_pick_list_state(case)


if __name__ == '__main__':
    unittest.main()
