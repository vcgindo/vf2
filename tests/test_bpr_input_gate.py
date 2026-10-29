"""BPR gate completes source/order preparation once, before calculation."""
from copy import deepcopy
import unittest
from unittest.mock import Mock, patch

from mta.application import r1_input
from mta.application import r1_calculation, r1_daily_entry
from mta.application.native_output_contracts import native_assignments
from mta.planning.engine import calculate_current_day
from mta.serialization import storage
from mta.temporal import chain
from mta.temporal.day_phases import ReadyBprDay
from tests.test_daily_calculation_phases import inputs, prepare, calculation
from tests.test_daily_r1_optimization import order_free_source
from tests.test_production_order_identity import calculate, state, feed


class BprInputGateTests(unittest.TestCase):
    def test_gate_stops_before_math_and_ready_consumption_does_not_prepare_again(self):
        prior, day, profile = inputs()
        execute = Mock(side_effect=calculation)
        with native_assignments(True), \
                patch.object(r1_input, '_dependency_fingerprint', wraps=r1_input._dependency_fingerprint) as fingerprint, \
                patch.object(r1_input, '_prepare_r1_orders', wraps=r1_input._prepare_r1_orders) as orders, \
                patch.object(chain, '_prepare_r1_operation_context', wraps=chain._prepare_r1_operation_context) as context, \
                patch.object(r1_calculation, 'prepare_track_a', wraps=r1_calculation.prepare_track_a) as track_a, \
                patch.object(r1_daily_entry, 'native_auxiliary_stock_balances', wraps=r1_daily_entry.native_auxiliary_stock_balances) as auxiliary, \
                patch.object(chain, 'connected_dbm_stages') as dbm, \
                patch.object(chain, 'connected_btr_stages') as btr:
            phase = prepare(prior, day, profile, execute)
            ready = chain.prepare_bpr_inputs(phase)
            self.assertIsInstance(ready, ReadyBprDay)
            self.assertIs(ready.phase, phase)
            self.assertIs(ready.context, phase.context)
            self.assertIs(ready.r1.source, ready.source)
            self.assertIs(ready.r1.closing, ready.order_state)
            execute.assert_not_called()
            dbm.assert_not_called()
            btr.assert_not_called()
            self.assertEqual(phase.completed_boundaries, ['controls'])
            fingerprint.assert_called_once()
            context.assert_called_once()
            track_a.assert_called_once()
            auxiliary.assert_called_once()
            self.assertIsInstance(ready.r1.auxiliary_stock, tuple)
            self.assertIsNotNone(ready.r1.prepared._track_a_preparation)
            prepared_order_calls = orders.call_count
            self.assertGreater(prepared_order_calls, 0)
            result = chain.produce_bpr(ready)
            execute.assert_called_once()
            self.assertEqual(orders.call_count, prepared_order_calls)
            fingerprint.assert_called_once()
            context.assert_called_once()
            track_a.assert_called_once()
            auxiliary.assert_called_once()
            self.assertIs(result.context, ready.context)
            self.assertIn('final-bpr-bluezone', result.completed_boundaries)

    def test_ready_and_existing_checked_entry_keep_all_outputs_and_auxiliary_stock(self):
        prior, day, profile = inputs()
        checked_outputs = []

        def checked(source, **owned):
            # The existing checked internal path remains independently callable.
            raw = deepcopy(source)
            raw['orders'] = []
            context = r1_input._prepare_r1_operation_context(raw)
            raw['orders'] = deepcopy(source['orders'])
            original_owned = dict(owned)
            original_owned.pop('_owned_r1_ready')
            expected = calculate_current_day(raw, defer_pick=True,
                _owned_r1_context=context, **original_owned)
            actual, identity = calculation(source, **owned)
            self.assertEqual(storage(actual), storage(expected))
            checked_outputs.append(actual)
            return actual, identity

        with native_assignments(True):
            ready = chain.prepare_bpr_inputs(prepare(prior, day, profile, checked))
            chain.produce_bpr(ready)
        self.assertEqual(len(checked_outputs), 1)

    def test_private_ready_denies_foreign_source_order_owner_and_public_dict(self):
        closing = calculate(state(91), [feed('ONE', 25)])
        raw = order_free_source()
        context = r1_input._prepare_r1_operation_context(raw)
        raw['orders'].extend(r1_input.calculation_order_rows(closing))
        ready = r1_input._ready_r1_for_owned_orders(context, raw, closing)
        expected = calculate_current_day(raw, defer_pick=True, _owned_order_closing=closing,
            _owned_r1_context=context)
        actual = calculate_current_day(raw, defer_pick=True, _owned_order_closing=closing,
            _owned_r1_ready=ready)
        self.assertEqual(storage(actual), storage(expected))
        for source, owner, candidate in ((deepcopy(raw), closing, ready),
                (raw, deepcopy(closing), ready), (raw, closing, {'prepared': ready.prepared})):
            with self.subTest(source_owned=source is raw, closing_owned=owner is closing):
                with self.assertRaisesRegex(ValueError, 'does not belong'):
                    calculate_current_day(source, defer_pick=True,
                        _owned_order_closing=owner, _owned_r1_ready=candidate)

    def test_gate_keeps_duplicate_owned_order_key_failure(self):
        closing = calculate(state(91), [feed('ONE', 25)])
        closing['SpikeOrderData'].append(deepcopy(closing['SpikeOrderData'][0]))
        raw = order_free_source()
        context = r1_input._prepare_r1_operation_context(raw)
        raw['orders'].extend(r1_input.calculation_order_rows(closing))
        for consume in (r1_input._consume_r1_operation_context, r1_input._ready_r1_for_owned_orders):
            with self.assertRaisesRegex(ValueError, 'Duplicate owned order keys'):
                consume(context, raw, closing)

    def test_auxiliary_rejection_occurs_at_gate_before_track_a_or_calculation(self):
        prior, day, profile = inputs()
        execute = Mock()
        error = ValueError('auxiliary source rejected')
        with native_assignments(True):
            phase = prepare(prior, day, profile, execute)
            with patch.object(r1_daily_entry, 'native_auxiliary_stock_balances', side_effect=error), \
                    patch.object(r1_calculation, 'prepare_track_a') as track_a:
                with self.assertRaises(ValueError) as raised:
                    chain.prepare_bpr_inputs(phase)
                self.assertIs(raised.exception, error)
                track_a.assert_not_called()
        execute.assert_not_called()

    def test_gate_track_a_failure_retains_original_canonical_failure_precedence(self):
        prior, day, profile = inputs()
        execute = Mock()
        with native_assignments(True):
            phase = prepare(prior, day, profile, execute)
            canonical = ValueError('earlier canonical failure')
            with patch.object(r1_calculation, 'prepare_track_a', side_effect=ValueError('eager failure')), \
                    patch.object(r1_calculation, 'calculate_track_a', side_effect=canonical):
                with self.assertRaises(ValueError) as raised:
                    chain.prepare_bpr_inputs(phase)
                self.assertIs(raised.exception, canonical)
        execute.assert_not_called()
