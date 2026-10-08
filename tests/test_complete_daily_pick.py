from copy import deepcopy
import unittest

from mta.application.complete_daily_pick import joined_cases, calculate_native_pick
from mta.domain.remaining_capabilities import calculate_pick_list_state
from parity.verify_pick_stage_state import fixture, PICK


def sources():
    case, declared = fixture()
    return case, dict(pick_rows=declared[PICK], sku_attributes=declared['BPR', 'SkuAttributeData'],
        location_attributes=declared['BPR', 'LocationAttributeData'],
        vehicles=declared['BPR', 'VehicleMaster'], location_vehicles=declared['BPR', 'LocationVehicleMaster'])


class NativePickInputTests(unittest.TestCase):
    def test_candidate_guards_preserve_deterministic_vehicle_and_duplicate_cases(self):
        from parity.verify_pick_integration import fixture_cases, source_arguments, SOURCE_KEYS
        cases = dict(fixture_cases())
        def calculate(name):
            return calculate_native_pick(**source_arguments({k:cases[name][k] for k in SOURCE_KEYS}))
        equal = calculate('equal-capacity-multiple-vehicles')
        self.assertEqual([(r['VehicleName'],r['NewSRNo'],r['ColorWiseAlloction'])
                          for r in equal['LogisticPickList']], [('V_EQ_1',1,2),('V_EQ_2',1,2)])
        different = cases['different-capacity-multiple-vehicles']
        with self.assertRaisesRegex(ValueError, 'differing candidate values.*candidates='):
            calculate('different-capacity-multiple-vehicles')
        # Different capacities alone are not grounds for denial: below both
        # capacities the native candidates are equal and both rows persist.
        different['BPR','VehicleMaster'][0]['Weight']=10
        different['BPR','VehicleMaster'][1]['Weight']=12
        deterministic = calculate('different-capacity-multiple-vehicles')
        self.assertEqual(len(deterministic['PickListDataForTruckFormation']),2)
        self.assertEqual(deterministic['LogisticPickList'],[])
        calculate('identical-duplicate-sku-attribute')
        for name in ('mixed-null-sku-duplicate','differing-sku-dimensions'):
            with self.assertRaisesRegex(ValueError, 'differing dimension candidates.*SKU='):
                calculate(name)
            for r in cases[name]['BPR','vf_PickListReport']:
                for f in ('TOR_B','TOR_R','TOY','TOG','TOBlue'):
                    r[f]=0
            self.assertEqual(calculate(name)['LogisticPickList'],[])

    def test_both_null_duplicate_exposes_unfiltered_final_update_conflict(self):
        _, inputs = sources()
        expected = calculate_native_pick(**inputs)
        inputs['sku_attributes'].append(dict(inputs['sku_attributes'][0], Weight=None, Volume=None))
        with self.assertRaisesRegex(ValueError, 'differing dimension candidates'):
            calculate_native_pick(**inputs)

    def test_complete_native_state_uses_actual_columns_without_input_mutation(self):
        case, inputs = sources()
        before = deepcopy(inputs)
        state = calculate_native_pick(**inputs)
        expected = calculate_pick_list_state(case)
        for name in ('LogisticPickList', 'PickListDataForTruckFormation'):
            self.assertEqual(state[name], expected[name])
        self.assertEqual(inputs, before)

    def test_join_occurrences_are_neither_collapsed_nor_cross_expanded(self):
        _, inputs = sources()
        duplicate = deepcopy(inputs['location_attributes'][0])
        inputs['location_attributes'].append(duplicate)
        alternative = dict(duplicate, LogisticsLocation='OTHER')
        inputs['location_attributes'].append(alternative)
        items = joined_cases(**inputs)[0]['items']
        self.assertEqual([r['logistics_location'] for r in items if r['sku']=='A'], ['L1', 'L1', 'OTHER'])
        inputs['sku_attributes'].append(deepcopy(inputs['sku_attributes'][0]))
        self.assertEqual(sum(r['sku']=='A' for r in joined_cases(**inputs)[0]['items']), 6)
        inputs['sku_attributes'][-1]['Weight'] = 9
        with self.assertRaisesRegex(ValueError, 'differing dimension candidates'):
            calculate_native_pick(**inputs)

    def test_native_eligibility_null_fallback_and_distinct_mapping(self):
        _, inputs = sources()
        inputs['location_vehicles'].append(deepcopy(inputs['location_vehicles'][0]))
        inputs['location_attributes'][0]['LogisticsLocation'] = None
        inputs['sku_attributes'][1].update(Weight=None, Volume=None)
        inputs['pick_rows'][2]['RationedReq'] = 0
        items = joined_cases(**inputs)[0]['items']
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['logistics_location'], 'W1')
        inputs['pick_rows'][0].update(TOR_B=None, TOR_R=-1)
        self.assertEqual(joined_cases(**inputs)[0]['items'][0]['buckets'], {})


if __name__ == '__main__':
    unittest.main()
