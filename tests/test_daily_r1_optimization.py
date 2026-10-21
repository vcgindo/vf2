"""Focused proof for operation-owned R1 preparation reuse and retained templates."""
from copy import deepcopy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from mta.application.r1_input import (
    _prepare_r1_operation_context,
    calculation_order_rows,
    prepare_r1_current_day,
)
from mta.application.r1_calculation import calculate_r1_requirements
from mta.application.track_a import calculate_track_a, prepare_track_a
from mta.planning.engine import calculate_current_day
from tests.test_production_order_identity import (
    TODAY,
    TOMORROW,
    calculate,
    feed,
    payload,
    state,
)


def order_free_source(*, today=TODAY):
    raw = payload([])
    raw.pop('order_input')
    raw['foundation']['snapshot']['business_date'] = today
    for row in raw['foundation']['inventory_positions']:
        row['business_date'] = today
    return raw


def calculate_with_context(raw, closing):
    context = _prepare_r1_operation_context(raw)
    raw['orders'].extend(calculation_order_rows(closing))
    before = deepcopy(raw)
    expected = calculate_current_day(
        deepcopy(raw), defer_pick=True, _owned_order_closing=closing)
    actual = calculate_current_day(
        raw, defer_pick=True, _owned_order_closing=closing,
        _owned_r1_context=context)
    return expected, actual, before, raw


class DailyR1PreparationOptimizationTests(unittest.TestCase):
    def test_root_and_successor_outputs_equal_full_preparation_without_input_mutation(self):
        root = calculate(state(91), [feed('ROOT-SPIKE', 25)])
        expected, actual, before, raw = calculate_with_context(order_free_source(), root)
        self.assertEqual(actual, expected)
        self.assertEqual(raw, before)

        prior = calculate(state(91), [feed('OLD', 25)])
        successor = calculate(
            prior, [feed('OLD', 25), feed('NEW')], TOMORROW, TODAY)
        raw = order_free_source(today=TOMORROW)
        expected, actual, before, raw = calculate_with_context(raw, successor)
        self.assertEqual(actual, expected)
        self.assertEqual(raw, before)

    def test_multipart_identity_and_complete_outputs_equal_full_preparation(self):
        order_state = state(91)
        for table, field in (
                ('BPRMaster', 'WHCode'), ('DBMMaster', 'WhCode'),
                ('AdditionalMasterData', 'WhCode')):
            order_state[table].append(
                dict(order_state[table][0], **{field: 'R1-D'}))
        closing = calculate(
            order_state, [feed('SAME', 25), feed('SAME', 25, wh='R1-D')])
        raw = order_free_source()
        raw['foundation']['locations'].append({'location_code': 'R1-D'})
        for rows in (
                raw['foundation']['sku_locations'],
                raw['foundation']['inventory_positions'],
                raw['foundation']['hierarchy'], raw['policies'],
                raw['stock_openings'], raw['routing']):
            original = next(row for row in rows if 'R1-C' in row.values())
            rows.append({key: 'R1-D' if value == 'R1-C' else deepcopy(value)
                         for key, value in original.items()})
        raw['policies'][-1]['rationing_priority'] = 2
        expected, actual, before, raw = calculate_with_context(raw, closing)
        self.assertEqual(actual, expected)
        self.assertEqual(raw, before)
        self.assertEqual(
            {(row['order_id'], row['order_key'], row['part_id'])
             for row in actual['r1_order_route']},
            {('SAME', 92, 1), ('SAME', 93, 1)},
        )

    def test_every_non_order_dependency_change_and_foreign_context_are_denied(self):
        closing = calculate(state(91), [feed('ONE', 25)])
        mutations = {
            'stock': lambda raw: raw['stock_openings'][0].update(stock=999),
            'master': lambda raw: raw['foundation']['sku_locations'][0].update(base_norm=91),
            'control': lambda raw: raw['policies'][0].update(controls=[{
                'type': 'manual', 'event_id': 'changed', 'effective_from': TODAY,
                'value': '91', 'kind': 'FORCE'}]),
            'hierarchy': lambda raw: raw['foundation']['hierarchy'][0].update(
                parent_location_code='CHANGED'),
            'dict-order': lambda raw: raw['policies'][0]['policy'].update(
                {key: raw['policies'][0]['policy'].pop(key)
                 for key in list(raw['policies'][0]['policy'])[:1]}),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                raw = order_free_source()
                context = _prepare_r1_operation_context(raw)
                raw['orders'].extend(calculation_order_rows(closing))
                mutate(raw)
                with self.assertRaisesRegex(ValueError, 'dependency drift'):
                    calculate_current_day(
                        raw, defer_pick=True, _owned_order_closing=closing,
                        _owned_r1_context=context)
        raw = order_free_source()
        context = _prepare_r1_operation_context(raw)
        copied = deepcopy(raw)
        copied['orders'].extend(calculation_order_rows(closing))
        with self.assertRaisesRegex(ValueError, 'does not belong'):
            calculate_current_day(
                copied, defer_pick=True, _owned_order_closing=closing,
                _owned_r1_context=context)

    def test_order_projection_failure_matches_existing_owned_boundary(self):
        closing = calculate(state(91), [feed('ONE', 25)])
        raw = order_free_source()
        context = _prepare_r1_operation_context(raw)
        raw['orders'].extend(calculation_order_rows(closing))
        raw['orders'][0]['outstanding_quantity'] += 1
        for arguments in ({}, {'_owned_r1_context': context}):
            with self.assertRaisesRegex(ValueError, 'projection drift'):
                calculate_current_day(
                    raw, defer_pick=True, _owned_order_closing=closing, **arguments)

    def test_track_a_shared_templates_avoid_third_pass_and_keep_both_r1_passes(self):
        raw = order_free_source()
        closing = calculate(state(91), [feed('ONE', 25)])
        raw['orders'].extend(calculation_order_rows(closing))
        import mta.application.track_a as track_a
        import mta.application.r1_calculation as r1
        with patch.object(track_a, 'calculate_requirement',
                          wraps=track_a.calculate_requirement) as preliminary, \
                patch.object(r1, 'calculate_requirement',
                             wraps=r1.calculate_requirement) as final:
            output = calculate_current_day(
                raw, defer_pick=True, _owned_order_closing=closing)
        node_count = len(raw['foundation']['sku_locations'])
        self.assertEqual(preliminary.call_count, 0)
        self.assertEqual(final.call_count, node_count * 2)
        self.assertEqual(len(output['r1_requirement']), node_count)
        self.assertTrue(all(tuple(row) == (
            'sku_code', 'location_code', 'business_date', 'effective_norm',
            'requirement', 'virtual_norm', 'orders', 'colours',
            'direct_virtual_node') for row in output['r1_requirement']))
        self.assertTrue(all({
            'sku_code', 'location_code', 'business_date', 'effective_norm',
            'requirement', 'virtual_norm', 'orders', 'colours',
            'direct_virtual_node'} <= set(row)
            for row in output['r1_requirement']))

    def test_preallocation_virtual_overflow_keeps_track_a_failure(self):
        raw = json.loads((Path(__file__).parents[1] / 'mta' / 'fixtures' /
                          'r1_raw_current_day.json').read_text())
        raw['orders'] = raw['orders'][:1]
        raw['orders'][0]['outstanding_quantity'] = 40000000000000
        # The source route remains future while its parent edge is due. With a
        # zero advance threshold, stock consumes the route before R1's first
        # pass. Preliminary Track A still rejected its preallocation Virtual Norm.
        raw['allocation']['advance_stock_threshold_percent'] = 0
        for row in raw['foundation']['sku_locations']:
            if row['location_code'] == 'R1-C':
                row['base_norm'] = 60000000000000
        for row in raw['foundation']['inventory_positions']:
            if row['location_code'] == 'R1-C':
                row['stock_quantity'] = 40000000000000
        for row in raw['stock_openings']:
            if row['location_code'] == 'R1-C':
                row.update(stock=40000000000000, norm=60000000000000)
        for row in raw['routing']:
            if row['location_code'] == 'R1-C':
                row['norm'] = 60000000000000
            elif row['location_code'] == 'R1-P':
                row['spike_threshold_percent'] = 20000000000000
        for row in raw['policies']:
            if row['location_code'] == 'R1-P':
                row['policy']['spike_override'] = 20000000000000
        prepared = prepare_r1_current_day(deepcopy(raw))
        with self.assertRaises(ValueError) as baseline:
            calculate_track_a(
                prepared.track_a, allow_negative_stock_for_requirement=True)
        with self.assertRaises(type(baseline.exception)) as candidate:
            calculate_current_day(raw, defer_pick=True)
        self.assertEqual(str(candidate.exception), str(baseline.exception))
        self.assertEqual(str(candidate.exception),
                         'Virtual Norm outside supported nonnegative range')

    def test_preallocation_parent_pack_blue_overflow_keeps_track_a_failure(self):
        raw = json.loads((Path(__file__).parents[1] / 'mta' / 'fixtures' /
                          'r1_raw_current_day.json').read_text())
        raw['orders'][0]['customer_expected_date'] = None
        raw['allocation']['advance_stock_threshold_percent'] = 0
        for row in raw['foundation']['sku_locations']:
            if row['location_code'] == 'R1-P':
                row['pack_size'] = 99999999999999
        for row in raw['foundation']['inventory_positions']:
            if row['location_code'] == 'R1-C':
                row['stock_quantity'] = 100
        for row in raw['stock_openings']:
            if row['location_code'] == 'R1-C':
                row['stock'] = 100
        prepared = prepare_r1_current_day(deepcopy(raw))
        with self.assertRaises(ValueError) as baseline:
            calculate_track_a(
                prepared.track_a, allow_negative_stock_for_requirement=True)
        with self.assertRaises(type(baseline.exception)) as candidate:
            calculate_current_day(raw, defer_pick=True)
        self.assertEqual(str(candidate.exception), str(baseline.exception))
        self.assertEqual(str(candidate.exception),
                         'Blue requirement outside supported nonnegative range')

    def test_preliminary_overflow_precedes_tied_allocation_failure(self):
        raw = json.loads((Path(__file__).parents[1] / 'mta' / 'fixtures' /
                          'r1_raw_advance_stock_competing.json').read_text())
        # Equal due/CED routes have no retained OrderKey and therefore fail in
        # allocation. A simultaneous preliminary Track A overflow must retain
        # the legacy earlier failure boundary.
        raw['orders'][1]['established_due_date'] = raw['orders'][0]['established_due_date']
        for row in raw['foundation']['sku_locations']:
            if row['location_code'] == 'R1-C1':
                row['base_norm'] = 60000000000000
        for row in raw['foundation']['inventory_positions']:
            if row['location_code'] == 'R1-C1':
                row['stock_quantity'] = 60000000000000
        for row in raw['stock_openings']:
            if row['location_code'] == 'R1-C1':
                row.update(stock=60000000000000, norm=60000000000000)
        for row in raw['routing']:
            if row['location_code'] == 'R1-C1':
                row.update(norm=60000000000000, spike_threshold_percent=100)
        for row in raw['policies']:
            if row['location_code'] == 'R1-C1':
                row['policy'].update(pso_override=0, spike_override=100)
        raw['orders'].append({
            'order_id': 'OVERFLOW-PSO', 'sku_code': 'R1SKU',
            'location_code': 'R1-C1', 'outstanding_quantity': 40000000000000,
            'accepted_on': '2026-01-12', 'customer_expected_date': '2026-01-15',
            'established_is_spike': False, 'established_due_date': None,
            'first_servicing_location_code': None,
        })
        prepared = prepare_r1_current_day(deepcopy(raw))
        with self.assertRaises(ValueError) as baseline:
            calculate_track_a(
                prepared.track_a, allow_negative_stock_for_requirement=True)
        with patch('mta.application.r1_calculation.calculate_track_a', return_value=[]):
            with self.assertRaisesRegex(
                    ValueError, '^R1_ORDER_KEY_OPENING_REQUIRED:'):
                calculate_current_day(deepcopy(raw), defer_pick=True)
        with self.assertRaises(type(baseline.exception)) as candidate:
            calculate_current_day(raw, defer_pick=True)
        self.assertEqual(str(candidate.exception), str(baseline.exception))
        self.assertEqual(str(candidate.exception),
                         'Virtual Norm outside supported nonnegative range')

    def test_earlier_component_overflow_precedes_later_preparation_error(self):
        raw = json.loads((Path(__file__).parents[1] / 'mta' / 'fixtures' /
                          'r1_raw_advance_stock_competing.json').read_text())
        prepared = prepare_r1_current_day(deepcopy(raw))
        nodes = {row['location_code']: row for row in prepared.track_a['nodes']}
        nodes['R1-C1']['orders'].append({
            'order_id': 'EARLY-PSO', 'quantity': 60000000000000,
            'accepted_on': '2026-01-12', 'due_date': '2026-01-15',
            'is_spike': False,
        })
        nodes['R1-C1']['routed_due_spike'] = 60000000000000
        nodes['R1-C2']['policy'].pop('pso_low')
        with self.assertRaisesRegex(ValueError, '^Unknown or missing input fields:'):
            prepare_track_a(
                prepared.track_a, allow_negative_stock_for_requirement=True)
        with self.assertRaises(ValueError) as baseline:
            calculate_track_a(
                prepared.track_a, allow_negative_stock_for_requirement=True)
        with self.assertRaises(type(baseline.exception)) as candidate:
            calculate_r1_requirements(prepared, raw)
        self.assertEqual(str(candidate.exception), str(baseline.exception))
        self.assertEqual(str(candidate.exception),
                         'calculated requirement outside supported nonnegative range')


if __name__ == '__main__':
    unittest.main()
