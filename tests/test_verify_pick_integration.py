"""Pure finite-fixture and strict-comparison tests; no native SQL."""
from copy import deepcopy
from decimal import Decimal
import unittest

from mta.application.complete_daily_pick import calculate_native_pick
from parity import verify_pick_integration as verifier
from tests.test_verify_complete_daily_pick_files import CanonicalGenericSchema


def arguments(declared):
    return verifier.source_arguments({key: deepcopy(declared[key]) for key in verifier.SOURCE_KEYS})


class PickIntegrationVerifierTests(unittest.TestCase):
    def test_fixture_roster_is_exact_and_nonterminating_case_is_absent(self):
        cases = verifier.fixture_cases()
        self.assertEqual(tuple(name for name, _ in cases), verifier.CASE_NAMES)
        self.assertTrue(verifier.validate_fixture_cases(cases))
        self.assertNotIn('single-null-underfilled', verifier.CASE_NAMES)
        self.assertTrue(all(set(verifier.SOURCE_KEYS) <= set(declared) for _, declared in cases))

    def test_fixture_construction_covers_declared_native_boundaries(self):
        cases = dict(verifier.fixture_cases())
        concurrent = cases['concurrent-active-queues']
        self.assertEqual(next(r for r in concurrent[verifier.PICK] if r['SKUCode']=='D')['TOR_B'], 12)
        duplicate = cases['duplicate-pick-sticky-flag']
        self.assertEqual((len(duplicate[verifier.PICK]), duplicate[verifier.PICK][0]['TOR_B'],
                          duplicate[verifier.SKU][0]['Weight'], duplicate[verifier.VEHICLE][0]['Weight']),
                         (2, 7, Decimal('1.000'), Decimal('4.000')))
        self.assertEqual(len(cases['duplicate-pick-and-location'][verifier.LOCATION]), 2)
        self.assertEqual(len(cases['identical-duplicate-sku-attribute'][verifier.SKU]), 2)
        self.assertEqual([r['LogisticsLocation'] for r in cases['distinct-logistics-locations'][verifier.LOCATION]],
                         ['L1', 'L2'])
        self.assertEqual((cases['both-null-excluded'][verifier.SKU][0]['Weight'],
                          cases['both-null-excluded'][verifier.SKU][0]['Volume']), (None, None))
        self.assertEqual((cases['both-zero-residual'][verifier.SKU][0]['Weight'],
                          cases['both-zero-residual'][verifier.SKU][0]['Volume']),
                         (Decimal('0.000'), Decimal('0.000')))
        self.assertEqual(cases['single-null-exact-fit'][verifier.PICK][0]['TOR_B'], 5)
        self.assertEqual(cases['single-null-overshoot-capacity-flaw'][verifier.PICK][0]['TOR_B'], 6)
        zero = cases['zero-boundary-after-prefix']
        self.assertEqual([(r['SKUCode'], r['TOR_B'], r['TOR_R']) for r in zero[verifier.PICK]],
                         [('A', 4, 0), ('B', 0, 1)])

    def test_selected_modern_outputs_bind_sticky_null_and_capacity_flaw_semantics(self):
        cases = dict(verifier.fixture_cases())
        sticky = calculate_native_pick(**arguments(cases['duplicate-pick-sticky-flag']))
        self.assertEqual([r['ColorWiseAlloction'] for r in sticky['PickListDataForTruckFormation']], [6])
        exact = calculate_native_pick(**arguments(cases['single-null-exact-fit']))
        self.assertEqual((exact['LogisticPickList'][0]['TotalWeight'],
                          exact['LogisticPickList'][0]['ColorWiseAlloction'],
                          exact['LogisticPickList'][0]['TransportLoadType']), (None, 5, 'SXL'))
        overshoot = calculate_native_pick(**arguments(cases['single-null-overshoot-capacity-flaw']))
        self.assertEqual((overshoot['LogisticPickList'][0]['ColorWiseAlloction'],
                          overshoot['LogisticPickList'][0]['TotalVolume'],
                          overshoot['LogisticPickList'][0]['VehicleVolumeCapacity']),
                         (6, Decimal('6.000'), Decimal('5.000')))

    def test_source_arguments_requires_exact_five_images(self):
        declared = verifier.fixture_cases()[0][1]
        images = {key: declared[key] for key in verifier.SOURCE_KEYS}
        self.assertEqual(set(verifier.source_arguments(images)),
                         {'pick_rows', 'sku_attributes', 'location_attributes', 'vehicles', 'location_vehicles'})
        images.pop(verifier.PICK)
        with self.assertRaisesRegex(ValueError, 'five'):
            verifier.source_arguments(images)

    def test_d1_full_state_reorder_is_qualified_with_strict_failure_retained(self):
        declared = verifier.fixture_cases()[0][1]
        modern = calculate_native_pick(**arguments(declared))
        native = {name: deepcopy(modern[name]) for name in ('LogisticPickList', 'PickListDataForTruckFormation')}
        native['LogisticPickList'].reverse()
        result = verifier.compare_full_state(native, modern, CanonicalGenericSchema())
        self.assertEqual(result['status'], 'PASS')
        table = result['tables']['LogisticPickList']
        self.assertEqual(table['typed_bag_status'], 'PASS')
        self.assertEqual(table['missing'], [])
        self.assertEqual(table['extra'], [])
        self.assertEqual(table['strict_sequence_status'], 'FAIL')

    def test_d1_rejects_quantity_rank_and_duplicate_corruption(self):
        declared = verifier.fixture_cases()[0][1]
        modern = calculate_native_pick(**arguments(declared))
        for field in ('ColorWiseAlloction', 'NewSRNo', 'TruckCount'):
            native = deepcopy(modern)
            native['LogisticPickList'][0][field] += 1
            self.assertEqual(verifier.compare_full_state(native, modern, CanonicalGenericSchema())['status'], 'FAIL')
        native = deepcopy(modern)
        native['LogisticPickList'].append(deepcopy(native['LogisticPickList'][0]))
        self.assertEqual(verifier.compare_full_state(native, modern, CanonicalGenericSchema())['status'], 'FAIL')

    def test_downstream_comparison_is_exact_not_totals_only(self):
        declared = verifier.fixture_cases()[0][1]
        modern = calculate_native_pick(**arguments(declared))
        native = {name: deepcopy(modern[name]) for name in ('LogisticPickList', 'PickListDataForTruckFormation')}
        self.assertEqual(verifier.compare_downstream(native, modern)['status'], 'PASS')
        native['LogisticPickList'].reverse()
        self.assertEqual(verifier.compare_downstream(native, modern)['status'], 'PASS')


if __name__ == '__main__':
    unittest.main()
