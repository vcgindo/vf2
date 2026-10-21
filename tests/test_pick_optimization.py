"""Focused pure checks for indexed Pick joins and truck-loop matching."""
from copy import deepcopy
from decimal import Decimal
import unittest

from mta.application.complete_daily_pick import calculate_native_pick, joined_cases
from mta.domain.remaining_capabilities import calculate_pick_list_state


def sources(quantity=7):
    return dict(
        pick_rows=[dict(SKUCode='a ', WhCode='w ', ParentWhCode='p ',
            RationedReq=quantity, DispatchColor='Black', TOR_B=quantity,
            TOR_R=0, TOY=0, TOG=0, TOBlue=0)],
        sku_attributes=[dict(SKUCode='A', Weight='1.000', Volume='1.000')],
        location_attributes=[dict(WHCode='W', LogisticsLocation='l ')],
        vehicles=[dict(VehicleID=1, VehicleName='v ', Weight='3.000', Volume='100.000')],
        location_vehicles=[dict(LocationID='P', VehicleID=1)])


class PickOptimizationTests(unittest.TestCase):
    def test_indexed_input_joins_keep_sql_equality_occurrences_and_ordinals(self):
        raw = sources(2)
        raw['sku_attributes'].append(dict(raw['sku_attributes'][0], SKUCode='a  '))
        raw['location_attributes'].append(dict(raw['location_attributes'][0], WHCode='w  '))
        raw['location_vehicles'].append(dict(raw['location_vehicles'][0], LocationID='p  '))
        raw['vehicles'].append(dict(raw['vehicles'][0], VehicleName='second'))
        before = deepcopy(raw)
        case, = joined_cases(**raw)
        self.assertEqual([item['source_occurrence'] for item in case['items']],
                         [(0, 0, 0), (0, 0, 1), (0, 1, 0), (0, 1, 1)])
        self.assertEqual([vehicle['name'] for vehicle in case['vehicles']], ['v ', 'second'])
        self.assertTrue(all(item['_join_multiplicity'] == 2 for item in case['items']))
        self.assertEqual(raw, before)

    def test_indexed_truck_matches_keep_vehicle_options_and_duplicate_rows_separate(self):
        raw = sources()
        raw['vehicles'].append(dict(raw['vehicles'][0], VehicleID=2,
                                    VehicleName='V2', Weight='4.000'))
        raw['location_vehicles'].append(dict(LocationID='p  ', VehicleID=2))
        raw['pick_rows'].append(deepcopy(raw['pick_rows'][0]))
        before = deepcopy(raw)
        result = calculate_native_pick(**raw)
        totals = {}
        for table in ('LogisticPickList', 'PickListDataForTruckFormation'):
            for row in result[table]:
                totals[row['VehicleName']] = totals.get(row['VehicleName'], 0) + row['ColorWiseAlloction']
        self.assertEqual(totals, {'v ': 14, 'V2': 14})
        self.assertEqual(raw, before)

    def test_indexed_dimension_candidates_retain_null_exclusion_and_ambiguity(self):
        raw = sources(2)
        raw['sku_attributes'][0].update(Weight=None, Volume=None)
        self.assertEqual(calculate_native_pick(**raw),
                         {'allocations': [], 'LogisticPickList': [],
                          'PickListDataForTruckFormation': []})
        raw = sources(2)
        raw['sku_attributes'].append(dict(SKUCode='a', Weight='2.000', Volume='1.000'))
        with self.assertRaisesRegex(ValueError, 'differing dimension candidates.*SKU='):
            calculate_native_pick(**raw)

    def test_iteration_indexes_rebuild_through_full_partial_and_no_progress_rounds(self):
        case = dict(vehicle=dict(name='V', weight_capacity='3.000', volume_capacity='100.000'),
            items=[dict(case='A', sku='A', from_location='P', to_location='W1',
                        logistics_location='L1', weight='1.000', volume='1.000',
                        dispatch_color='Black', buckets={'to_black': 7})])
        state = calculate_pick_list_state(case)
        self.assertEqual([row['ColorWiseAlloction'] for row in state['LogisticPickList']], [3, 3])
        self.assertEqual([row['ColorWiseAlloction'] for row in state['PickListDataForTruckFormation']], [1])
        stuck = deepcopy(case)
        stuck['items'][0].update(weight='6.000', buckets={'to_black': 1})
        with self.assertRaisesRegex(ValueError, 'Canonical Pick nontermination'):
            calculate_pick_list_state(stuck)


if __name__ == '__main__':
    unittest.main()
