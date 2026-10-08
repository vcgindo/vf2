"""Pure tests for the bounded post-rank Pick tie witness; no native SQL."""
from copy import deepcopy
import hashlib
from pathlib import Path
import unittest

from parity import verify_pick_tie_witness as verifier


def staged_rows():
    common = dict(ParentWHCode='P', TotalWeight=None, TotalVolume=None,
        VehicleWeightCapacity='4.000', VehicleVolumeCapacity='100.000',
        RemainingWeight='0.000', RemainingVolume='0.000', DispatchColor='Red',
        VehicleName='fixture-vehicle', Priority=2, ColorWiseAlloction=3,
        LogisticLocation='L1', NoTruckFlag=False)
    before = [dict(NewSRNo=1, SKUCode='A', WHCode='W1', **common),
              dict(NewSRNo=2, SKUCode='B', WHCode='W2', **common)]
    return before, [dict(before[0], NewSRNo=2), dict(before[1], NewSRNo=1)]


class PickTieWitnessTests(unittest.TestCase):
    def source(self):
        return Path('F:/VFlow_Local/local-runtime/mta-engine/Scripts/BPR/Ration_Scripts/GenerateLogisticPickList.sql').read_bytes()

    def test_source_instrumentation_is_recoverable_and_suffix_exact(self):
        canonical = self.source()
        derived, receipt = verifier.instrument_source_bytes(canonical)
        self.assertTrue(verifier.validate_source_instrumentation(canonical, derived, receipt))
        self.assertEqual(verifier.recover_original_bytes(derived, receipt), canonical)
        self.assertEqual(receipt['canonical_sha256'], verifier.CANONICAL_PIN)
        self.assertEqual(receipt['derived_sha256'], hashlib.sha256(derived).hexdigest())
        self.assertEqual((receipt['inserted_statement_count'], receipt['mutation_statement_count']), (5, 1))
        self.assertFalse(receipt['unmodified_native_oracle'])
        offset, length = receipt['insertion_offset'], receipt['insertion_length']
        self.assertEqual(derived[offset + length:], canonical[offset:])
        self.assertIn(b'PICK_TIE_STAGE_BEFORE', derived[offset:offset + length])
        self.assertIn(b'PICK_TIE_STAGE_AFTER', derived[offset:offset + length])

    def test_instrumentation_rejects_source_drift_and_tampering(self):
        canonical = self.source()
        with self.assertRaisesRegex(ValueError, 'identity'):
            verifier.instrument_source_bytes(canonical + b' ')
        derived, receipt = verifier.instrument_source_bytes(canonical)
        damaged = bytearray(derived); damaged[-1] ^= 1
        with self.assertRaisesRegex(ValueError, 'hash'):
            verifier.validate_source_instrumentation(canonical, bytes(damaged), receipt)
        with self.assertRaisesRegex(ValueError, 'statement count'):
            verifier.validate_source_instrumentation(canonical, derived,
                dict(receipt, inserted_statement_count=4))
        with self.assertRaisesRegex(ValueError, 'inserted SQL'):
            verifier.validate_source_instrumentation(canonical, derived,
                dict(receipt, inserted_bytes_base64=receipt['inserted_bytes_base64'][:-4] + 'AAAA'))

    def test_exact_rank_only_permutation_passes(self):
        result = verifier.validate_rank_permutation(*staged_rows())
        self.assertEqual(result['status'], 'PASS')
        self.assertEqual(result['changed_fields'], ['NewSRNo'])
        self.assertEqual(result['legacy_tie_key'], ['P', 'L1', 2])

    def test_moved_untied_rank_is_rejected(self):
        before, after = staged_rows(); after[1]['Priority'] = 3
        with self.assertRaisesRegex(ValueError, 'eligibility|untied|non-rank'):
            verifier.validate_rank_permutation(before, after)

    def test_changed_quantity_is_rejected(self):
        before, after = staged_rows(); after[0]['ColorWiseAlloction'] = 2
        with self.assertRaisesRegex(ValueError, 'non-rank field'):
            verifier.validate_rank_permutation(before, after)

    def test_changed_multiplicity_is_rejected(self):
        before, after = staged_rows(); after.append(deepcopy(after[0]))
        with self.assertRaisesRegex(ValueError, 'multiplicity'):
            verifier.validate_rank_permutation(before, after)

    def test_other_partition_is_rejected(self):
        before, after = staged_rows()
        before[1]['LogisticLocation'] = after[1]['LogisticLocation'] = 'L2'
        with self.assertRaisesRegex(ValueError, 'partition'):
            verifier.validate_rank_permutation(before, after)

    def test_fixture_is_unique_tie_and_reverse_changes_strict_state_sequence(self):
        case, declared = verifier.tied_fixture()
        self.assertTrue(verifier.validate_tied_fixture(case, declared))
        forward = verifier.calculate_pick_list_state(deepcopy(case), allow_priority_ties=True)
        reverse_case = deepcopy(case); reverse_case['items'].reverse()
        reverse = verifier.calculate_pick_list_state(reverse_case, allow_priority_ties=True)
        self.assertEqual([r['SKUCode'] for r in forward['LogisticPickList']], ['A', 'B'])
        self.assertEqual([r['SKUCode'] for r in reverse['LogisticPickList']], ['B', 'A'])
        bad = deepcopy(declared)
        bad[('BPR', 'SkuAttributeData')].append(deepcopy(bad[('BPR', 'SkuAttributeData')][0]))
        with self.assertRaisesRegex(ValueError, 'unique'):
            verifier.validate_tied_fixture(case, bad)

    def test_downstream_requires_exact_cells(self):
        case, _ = verifier.tied_fixture()
        state = verifier.calculate_pick_list_state(case, allow_priority_ties=True)
        native = {name: deepcopy(state[name]) for name in
                  ('LogisticPickList', 'PickListDataForTruckFormation')}
        self.assertEqual(verifier.compare_downstream(native, state)['status'], 'PASS')
        native['LogisticPickList'][0]['ColorWiseAlloction'] -= 1
        with self.assertRaisesRegex(ValueError, 'downstream'):
            verifier.compare_downstream(native, state)
        native = {name: deepcopy(state[name]) for name in
                  ('LogisticPickList', 'PickListDataForTruckFormation')}
        native['LogisticPickList'].reverse()
        with self.assertRaisesRegex(ValueError, 'downstream'):
            verifier.compare_downstream(native, state)


if __name__ == '__main__':
    unittest.main()
