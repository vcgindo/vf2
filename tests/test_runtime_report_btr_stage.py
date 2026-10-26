"""Complete assembly comparisons against the unchanged native phase path."""
from copy import deepcopy
import unittest
from unittest.mock import patch

from mta.application import runtime_report_btr_stage as assembly
from mta.application import daily_finalization
from mta.application.native_output_contracts import native_assignments
from mta.serialization import digest,storage
from mta.temporal import chain
from mta.runtime import phase_state
from tests.test_phase_state import native_bpr,MemoryImages


class RuntimeReportBtrStageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with native_assignments(True):
            bpr,cls.sources,cls.references=native_bpr('new-placement-assembly-test')
            cls.phase=chain.produce_dbm(bpr)

    def test_full_complete_output_equals_original_assembly(self):
        with native_assignments(True):
            expected=chain.produce_btr(deepcopy(self.phase))
            phase=deepcopy(self.phase)
            before=storage(phase.final_dbm)
            boundary=assembly.prepare_btr_boundary(phase)
            actual=assembly.finish_btr_boundary(boundary)
        self.assertEqual(storage(actual),storage(expected))
        self.assertEqual(digest(actual),digest(expected))
        self.assertEqual(storage(phase.final_dbm),before)

    def test_persisted_codec_scoped_output_equals_original_assembly(self):
        memory=MemoryImages()
        image=phase_state.encode(deepcopy(self.phase),deepcopy(self.sources),
            row_writer=memory.rows,export_writer=memory.export)
        restored,sources=phase_state.decode(image,**deepcopy(self.references),
            row_reader=memory.read,export_reader=memory.read)
        self.assertIsNone(restored.calculated)
        with native_assignments(True):
            expected=chain.produce_btr_from_snapshot(deepcopy(restored),deepcopy(sources),
                pick_source_digests=restored.pick_source_digests)
            boundary=assembly.prepare_btr_boundary(restored,sources=sources,
                pick_source_digests=restored.pick_source_digests)
            actual=assembly.finish_btr_boundary(boundary)
        self.assertEqual(storage(actual.output),storage(expected.output))
        self.assertIs(actual.calculation_sources,sources)
        self.assertEqual(storage(actual.calculation_sources.__dict__),
                         storage(expected.calculation_sources.__dict__))

    def test_prepared_stage_is_before_finalization_and_master_qualification(self):
        phase=deepcopy(self.phase)
        with native_assignments(True), \
                patch.object(daily_finalization,'finish',wraps=daily_finalization.finish) as final, \
                patch('mta.application.persistent_master.qualify',return_value=True) as master:
            boundary=assembly.prepare_btr_boundary(phase)
            final.assert_not_called()
            master.assert_not_called()
            self.assertEqual(phase.completed_boundaries[-1],'btr-insights')
            self.assertIn('LastBatchRunTbl',boundary.trend_state)
            self.assertIn('SkuLocAttributeData',boundary.trend_state)
            actual=assembly.finish_btr_boundary(boundary)
            if phase.context.finalization['policy']==daily_finalization.ACTIVE_POLICY:
                # The existing atomic finish_run still owns this branch.
                final.assert_not_called()
            else:
                final.assert_called_once()
            master.assert_called_once()
            self.assertEqual(actual['_CompletedBoundaries'][-1],'closing-state')

    def test_inactive_final_gate_is_invoked_only_after_boundary(self):
        phase=deepcopy(self.phase)
        # A branch-order witness, not an inactive business-input qualification.
        phase.context.finalization=dict(phase.context.finalization,policy=daily_finalization.POLICY)
        with native_assignments(True), \
                patch.object(daily_finalization,'finish',side_effect=lambda _state,settings,_date: settings) as final, \
                patch('mta.application.persistent_master.qualify',return_value=True):
            boundary=assembly.prepare_btr_boundary(phase)
            final.assert_not_called()
            assembly.finish_btr_boundary(boundary)
            final.assert_called_once_with(phase.complete,phase.control_final['importer_settings'],phase.context.today)

    def test_btr_failure_does_not_run_finalization(self):
        failure=RuntimeError('retained BTR failure witness')
        with native_assignments(True), \
                patch.object(chain,'connected_btr_stages',side_effect=failure), \
                patch.object(daily_finalization,'finish') as final:
            with self.assertRaises(RuntimeError) as caught:
                assembly.prepare_btr_boundary(deepcopy(self.phase))
            self.assertIs(caught.exception,failure)
            final.assert_not_called()

    def test_full_and_scoped_source_forms_cannot_be_mixed(self):
        with self.assertRaisesRegex(ValueError,'Full or authenticated scoped'):
            assembly.prepare_btr_boundary(deepcopy(self.phase),sources=self.sources)
        with self.assertRaisesRegex(ValueError,'Prepared native'):
            assembly.finish_btr_boundary(self.phase)
