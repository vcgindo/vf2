"""Pure/mocked restricted truck-state proof tests; no SQL/day execution."""
from contextlib import nullcontext
from copy import deepcopy
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from parity import verify_pick_stage_state as verifier
from tests.test_verify_complete_daily_pick_files import CanonicalGenericSchema


class RestrictedTruckStateTests(unittest.TestCase):
    def test_original_full_allocation_regression_and_additive_metadata(self):
        case, declared = verifier.fixture()
        before = deepcopy((case, declared))
        verifier.validate_fixture(case, declared)
        self.assertEqual(verifier.producer.calculate_pick_list(case), verifier.original_allocations())
        state = verifier.modern_state(case)
        self.assertEqual(state['allocations'], verifier.original_allocations())
        picked, residual = state['LogisticPickList'], state['PickListDataForTruckFormation']
        self.assertEqual((len(picked), len(residual)), (3, 2))
        self.assertTrue(all(len(r) == 21 for r in picked))
        self.assertTrue(all(len(r) == 16 for r in residual))
        self.assertEqual([(r['SKUCode'], r['ColorWiseAlloction'], r['TruckCount']) for r in picked],
                         [('A', 1, 1), ('B', 1, 1), ('B', 2, 2)])
        self.assertEqual([r['IsTruckFormed'] for r in picked], [None, True, True])
        self.assertEqual([r['NewSRNo'] for r in picked], [1, 2, 2])
        self.assertEqual([r['MinSRNo'] for r in picked], [2, 2, 2])
        self.assertEqual(picked[1]['CumulativeWeight'], Decimal('10.000'))
        self.assertEqual(picked[1]['RemainingWeigt'], Decimal('5.000'))
        self.assertEqual(picked[1]['RemainingVolume'], Decimal('-95.000'))
        self.assertEqual(picked[2]['CumulativeWeight'], Decimal('6.000'))
        self.assertEqual(picked[2]['RemainingWeigt'], Decimal('1.000'))
        self.assertTrue(all(r['TransportLoadType'] == 'SXL' for r in picked))
        self.assertEqual([(r['SKUCode'], r['ColorWiseAlloction'], r['NewSRNo']) for r in residual],
                         [('B', 1, 2), ('D', 2, 1)])
        self.assertTrue(all(r['NoTruckFlag'] is True for r in residual))
        self.assertTrue(all(r['RemainingWeight'] == Decimal('0.000') and r['RemainingVolume'] == Decimal('0.000') for r in residual))
        self.assertEqual((case, declared), before)

    def test_full_fixture_schema_and_row_rosters_use_generic_canonical_sources(self):
        schema = CanonicalGenericSchema()
        cases = verifier.fixture_cases()
        self.assertEqual(len(cases), 2)
        result = verifier.preflight_fixtures(schema, [(name, declared) for name, _, declared in cases])
        self.assertEqual(result['errors'], [])
        for _, case, declared in cases:
            verifier.validate_fixture(case, declared)
            state = verifier.modern_state(case)
            for key, count in ((verifier.LOGISTIC, 21), (verifier.REMAINING, 16)):
                columns = schema.schema(*key)
                self.assertEqual(len(columns), count)
                self.assertTrue(all(set(row) == {c['name'] for c in columns} for row in state[key[1]]))

    def test_volume_boundary_mxl_threshold_and_negative_weight_overage(self):
        case, declared = verifier.fixture('volume')
        verifier.validate_fixture(case, declared)
        state = verifier.modern_state(case)
        self.assertEqual(state['allocations'], verifier.original_allocations('volume'))
        picked = state['LogisticPickList']
        self.assertEqual([r['ColorWiseAlloction'] for r in picked], [1, 1, 2])
        self.assertEqual([r['TransportLoadType'] for r in picked], ['MXL', 'MXL', 'MXL'])
        self.assertEqual(picked[1]['CumulativeWeight'], Decimal('22.500'))
        self.assertEqual(picked[1]['CumulativeVolume'], Decimal('5.000'))
        self.assertEqual(picked[1]['RemainingWeigt'], Decimal('-77.500'))
        self.assertEqual(picked[1]['RemainingVolume'], Decimal('2.500'))
        self.assertEqual(picked[2]['RemainingWeigt'], Decimal('-86.500'))
        self.assertEqual(picked[2]['RemainingVolume'], Decimal('0.500'))
        self.assertEqual([(r['SKUCode'], r['ColorWiseAlloction']) for r in state['PickListDataForTruckFormation']], [('B', 1), ('D', 2)])

    def test_fixture_refuses_unresolved_ties_nulls_duplicates_and_different_facts(self):
        case, declared = verifier.fixture()
        case['items'][1]['buckets'].update(to_red=0, to_black=4)
        with self.assertRaisesRegex(ValueError, 'priority ranks'):
            verifier.validate_fixture(case, declared)
        case, declared = verifier.fixture()
        case['items'][0]['weight'] = None
        with self.assertRaisesRegex(ValueError, 'non-NULL'):
            verifier.validate_fixture(case, declared)
        case, declared = verifier.fixture()
        declared[('BPR', 'SkuAttributeData')].append(dict(declared[('BPR', 'SkuAttributeData')][0]))
        with self.assertRaisesRegex(ValueError, 'attribute joins'):
            verifier.validate_fixture(case, declared)
        case, declared = verifier.fixture()
        declared[verifier.PICK][0]['TOR_B'] = 2
        with self.assertRaisesRegex(ValueError, 'band quantities'):
            verifier.validate_fixture(case, declared)

    def test_missing_api_changed_allocation_or_roster_is_denied(self):
        case, _ = verifier.fixture()
        with patch.object(verifier.producer, 'calculate_pick_list_state', None):
            with self.assertRaisesRegex(ValueError, 'not implemented'):
                verifier.modern_state(case)
        with patch.object(verifier.producer, 'calculate_pick_list_state', return_value={
                'allocations': [], 'LogisticPickList': [], 'PickListDataForTruckFormation': []}):
            with self.assertRaisesRegex(ValueError, 'changed original allocation'):
                verifier.modern_state(case)
        with patch.object(verifier.producer, 'calculate_pick_list_state', return_value={'allocations': verifier.original_allocations()}):
            with self.assertRaisesRegex(ValueError, 'declared modern full-state API'):
                verifier.modern_state(case)

    def test_original_narrow_fields_and_numeric_wire_scale_are_unchanged(self):
        case, _ = verifier.fixture()
        projected = verifier.modern_narrow(verifier.original_allocations(), case['vehicle'])
        self.assertEqual([r['picked_quantity'] for r in projected['logistic_pick']], ['1', '1', '2'])
        self.assertEqual([r['total_weight'] for r in projected['logistic_pick']], ['2.000', '2.000', '4.000'])
        self.assertEqual([r['sku'] for r in projected['pick_remaining']], ['D', 'B'])
        self.assertEqual([r['remaining_quantity'] for r in projected['pick_remaining']], ['2', '1'])
        for name, rows in projected.items():
            self.assertTrue(all(tuple(row) == verifier.NARROW[name][1] for row in rows))
        self.assertEqual(verifier.wire(Decimal('2.000')), '2.000')
        self.assertEqual(verifier.wire(2), '2')

    def test_state_same_bag_reorder_still_fails_and_stops_before_narrow_queries(self):
        case, declared = verifier.fixture()
        state = verifier.modern_state(case)
        schema = CanonicalGenericSchema()
        class MemorySQL:
            def __init__(self, *args):
                self.fills = []
                self.loaded = {}
            def schema(self, *key):
                return schema.schema(*key)
            def load(self, *key_and_rows):
                role, table, rows = key_and_rows
                self.loaded[(role, table)] = rows
            def rows(self, *key):
                if key == verifier.LOGISTIC:
                    return list(reversed(state['LogisticPickList']))
                if key == verifier.REMAINING:
                    return state['PickListDataForTruckFormation']
                return self.loaded[key]
            def scratch(self):
                return {}
        raw = Mock()
        with patch.object(verifier, 'FixtureSQL', MemorySQL), patch.object(verifier, 'execute_native') as native:
            result = verifier.qualify(raw, None, None, case, declared, state)
        self.assertEqual(result['status'], 'FAIL')
        self.assertIn('UNACCEPTED_STATE_TABLE_ORDER_GAP', result['failure'])
        comparison = result['full_images']['BPR.LogisticPickList']
        self.assertEqual(comparison['status'], 'PASS')
        self.assertEqual(comparison['strict_observed_sequence_status'], 'FAIL')
        native.assert_called_once()
        raw.execute.assert_not_called()

    def test_failed_native_case_always_rolls_back_without_commit_or_retry(self):
        from parity import legacy_isolation as isolation
        class EmptySQL:
            def __init__(self, *args):
                pass
            def rows(self, *args):
                return []
            def schema(self, *args):
                return []
            def scratch(self):
                return {}
        raw = Mock()
        raw.raw.autocommit = True
        raw.execute.return_value.fetchval.return_value = 0
        script = SimpleNamespace(source_path=verifier.PATH, source_sha256=verifier.PIN)
        with TemporaryDirectory() as directory:
            output = Path(directory) / 'proof.json'
            for db in verifier.namespace(verifier.OWNER).values():
                (Path(directory) / (db + '-schema.json')).write_text('{}')
            with patch.object(verifier, 'guard_options', return_value=output), \
                    patch.object(verifier, 'prepare', return_value=(script, {})), \
                    patch.object(verifier, 'data_directory', return_value=Path(directory)), \
                    patch.object(verifier, 'scalar_binding', return_value={}), \
                    patch.object(verifier, 'native_context', return_value={}), \
                    patch.object(verifier, 'preflight_fixtures', return_value={'status': 'PASS'}), \
                    patch.object(verifier, 'FixtureSQL', EmptySQL), \
                    patch.object(isolation, 'exclusive_replay', return_value=nullcontext()), \
                    patch.object(isolation, 'connection', return_value=nullcontext(raw)), \
                    patch.object(verifier, 'qualify', return_value={'status': 'FAIL'}) as qualify:
                result = verifier.run(verifier.OWNER, output)
            self.assertEqual(result['status'], 'FAIL')
            self.assertEqual(len(result['cases']), 1)
            qualify.assert_called_once()
        raw.rollback.assert_called_once()
        raw.commit.assert_not_called()
        self.assertTrue(raw.raw.autocommit)


if __name__ == '__main__':
    unittest.main()
