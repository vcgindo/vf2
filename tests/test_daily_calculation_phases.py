"""Pure phase-cut contracts; no run persistence, scope completion or readiness."""
from copy import deepcopy
from unittest import TestCase
from unittest.mock import Mock, patch

from tests import test_h3_daily_integration as supplied
from mta.application.native_output_contracts import native_assignments
from mta.serialization import storage
from mta.temporal import chain
from mta.temporal.day_phases import PreparedDay, BprDay, DbmDay


def inputs():
    frame = supplied.frame()
    prior = deepcopy(frame['opening']['state'])
    day = supplied.supplied_day('2037-04-10')['day']
    frozen = supplied.captured(prior, 'WithDestLoc')
    day.update(raw_master=supplied.compose(frozen, supplied.nms_master_raw(prior),
               last_run_date='2037-04-09'), exclusions=[],
               supplier_feeds=supplied.complete_feeds(frozen, prior))
    supplied.replace_working_inputs(frozen, prior, day, None)
    return prior, day, frame['profile']


def calculation(source, **owned):
    return supplied.calculate_current_day(source, defer_pick=True, **owned), 'pure-phase-test'


def prepare(prior, day, profile, execute=calculation, **kwargs):
    return chain.prepare_day(prior, '2037-04-09', day, profile,
                             'pure-phase-test', execute, native_daily=True, **kwargs)


class DailyCalculationPhaseTests(TestCase):
    def test_real_producers_stop_at_each_cut_and_btr_preserves_dbm_standards(self):
        prior, day, profile = inputs()
        from mta.application.operational_capture import CAPTURE_POLICY
        from mta.application.operational_input_capture import INPUT_CAPTURE_POLICY
        profile.update(operational_sources=CAPTURE_POLICY,
                       operational_input_sources=INPUT_CAPTURE_POLICY)
        prior_before, day_before = storage(prior), storage(day)
        execute = Mock(side_effect=calculation)
        btr_standard = []
        original_btr = chain.connected_btr_stages
        def observe_btr(*args, **kwargs):
            for name, state in original_btr(*args, **kwargs):
                btr_standard[:] = [deepcopy(state['SKULocStandardAttributes'])]
                yield name, state
        with native_assignments(True), \
             patch.object(chain, 'connected_dbm_stages', wraps=chain.connected_dbm_stages) as dbm, \
             patch.object(chain, 'connected_btr_stages', side_effect=observe_btr) as btr:
            prepared = prepare(prior, day, profile, execute)
            self.assertIsInstance(prepared, PreparedDay)
            execute.assert_not_called()
            dbm.assert_not_called()
            btr.assert_not_called()
            self.assertEqual(prepared.completed_boundaries, ['controls'])

            bpr = chain.produce_bpr(prepared)
            self.assertIsInstance(bpr, BprDay)
            self.assertIs(bpr.context, prepared.context)
            self.assertIs(bpr.importer, prepared.importer)
            execute.assert_called_once()
            dbm.assert_not_called()
            btr.assert_not_called()
            self.assertIn('final-bpr-bluezone', bpr.completed_boundaries)
            self.assertIsNotNone(bpr.complete)
            self.assertIsNotNone(bpr.operational_input_tables)

            dbm_phase = chain.produce_dbm(bpr)
            self.assertIsInstance(dbm_phase, DbmDay)
            self.assertIs(dbm_phase.context, prepared.context)
            dbm.assert_called_once()
            btr.assert_not_called()
            self.assertNotIn('btr-insights', dbm_phase.completed_boundaries)
            original_mapping = dbm_phase.final_dbm
            original_standard = original_mapping['SKULocStandardAttributes']
            standard_before = storage(original_standard)

            result = chain.produce_btr(dbm_phase)
            btr.assert_called_once()
            self.assertIs(dbm_phase.final_dbm, original_mapping)
            self.assertIs(dbm_phase.final_dbm['SKULocStandardAttributes'], original_standard)
            self.assertEqual(storage(original_standard), standard_before)
            terminal = result['DBMFinal'][0]['SKULocStandardAttributes']
            self.assertEqual(terminal, btr_standard[0])
            self.assertIsNot(terminal, original_standard)
            self.assertEqual(result['_CompletedBoundaries'][-2:], ['btr-insights', 'closing-state'])
        self.assertEqual(storage(prior), prior_before)
        self.assertEqual(storage(day), day_before)

    def test_btr_final_writer_replaces_only_the_continuations_standards_mapping(self):
        prior, day, profile = inputs()
        with native_assignments(True):
            dbm = chain.produce_dbm(chain.produce_bpr(prepare(prior, day, profile)))
            original_mapping = dbm.final_dbm
            original = original_mapping['SKULocStandardAttributes']
            before = storage(original)
            # A distinct boundary value proves assembly reads the BTR writer;
            # this injected test output makes no business-calculation claim.
            written = deepcopy(original)
            written[0]['Category'] = 7
            def final_writer(_today, opening, *args, **kwargs):
                yield 'test-final-writer', {**deepcopy(opening),
                                           'SKULocStandardAttributes': written}
            with patch.object(chain, 'connected_btr_stages', side_effect=final_writer):
                result = chain.produce_btr(dbm)
            self.assertIs(dbm.final_dbm, original_mapping)
            self.assertIs(original_mapping['SKULocStandardAttributes'], original)
            self.assertEqual(storage(original), before)
            self.assertEqual(result['DBMFinal'][0]['SKULocStandardAttributes'], written)
            self.assertEqual(result['ClosingState'][0]['dbm']['SKULocStandardAttributes'], written)

    def test_prepared_input_and_master_qualification_owners_survive_all_handoffs(self):
        from mta.temporal import entry_preparation
        prior, day, profile = inputs()
        captured = []
        snapshot = object()
        original = entry_preparation.prepare
        def observe(*args, **kwargs):
            entry = original(*args, **kwargs)
            captured.append(entry)
            return entry
        with native_assignments(True), \
             patch.object(entry_preparation, 'prepare', side_effect=observe), \
             patch('mta.application.persistent_master.qualify', return_value=True) as qualify:
            prepared = prepare(prior, day, profile, master_snapshot=snapshot)
            context = prepared.context
            self.assertIs(context.prior, captured[0]['prior'])
            self.assertIs(context.day, captured[0]['day'])
            self.assertIs(context.master, captured[0]['master'])
            self.assertIs(context.master_work, captured[0]['master_work'])
            self.assertIs(context.master_snapshot, snapshot)
            self.assertIsNot(prepared.importer, context.master['tables'])
            bpr = chain.produce_bpr(prepared)
            dbm = chain.produce_dbm(bpr)
            result = chain.produce_btr(dbm)
            qualify.assert_called_once_with(context.master, profile, context.day,
                                           result['ClosingState'][0], snapshot=snapshot)

    def test_preparation_failure_does_not_invoke_later_producers(self):
        prior, day, profile = inputs()
        error = RuntimeError('preparation failed')
        execute = Mock()
        with patch('mta.temporal.entry_preparation.prepare', side_effect=error), \
             patch.object(chain, 'connected_dbm_stages') as dbm, \
             patch.object(chain, 'connected_btr_stages') as btr:
            with self.assertRaises(RuntimeError) as raised:
                prepare(prior, day, profile, execute)
            self.assertIs(raised.exception, error)
            execute.assert_not_called()
            dbm.assert_not_called()
            btr.assert_not_called()

    def test_bpr_failure_propagates_before_dbm_or_btr(self):
        prior, day, profile = inputs()
        error = RuntimeError('R1 failed')
        execute = Mock(side_effect=error)
        with native_assignments(True), \
             patch.object(chain, 'connected_dbm_stages') as dbm, \
             patch.object(chain, 'connected_btr_stages') as btr:
            prepared = prepare(prior, day, profile, execute)
            with self.assertRaises(RuntimeError) as raised:
                chain.produce_bpr(prepared)
            self.assertIs(raised.exception, error)
            execute.assert_called_once()
            dbm.assert_not_called()
            btr.assert_not_called()

    def test_dbm_failure_propagates_without_btr(self):
        prior, day, profile = inputs()
        error = RuntimeError('DBM failed')
        with native_assignments(True):
            bpr = chain.produce_bpr(prepare(prior, day, profile))
            with patch.object(chain, 'connected_dbm_stages', side_effect=error), \
                 patch.object(chain, 'connected_btr_stages') as btr:
                with self.assertRaises(RuntimeError) as raised:
                    chain.produce_dbm(bpr)
                self.assertIs(raised.exception, error)
                btr.assert_not_called()

    def test_btr_failure_preserves_the_dbm_phase_standards(self):
        prior, day, profile = inputs()
        error = RuntimeError('BTR failed')
        with native_assignments(True):
            dbm = chain.produce_dbm(chain.produce_bpr(prepare(prior, day, profile)))
            original = dbm.final_dbm['SKULocStandardAttributes']
            before = storage(original)
            with patch.object(chain, 'connected_btr_stages', side_effect=error):
                with self.assertRaises(RuntimeError) as raised:
                    chain.produce_btr(dbm)
                self.assertIs(raised.exception, error)
            self.assertIs(dbm.final_dbm['SKULocStandardAttributes'], original)
            self.assertEqual(storage(original), before)
