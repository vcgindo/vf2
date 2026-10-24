"""Real UptoBPR orchestration on rollback-only component sources.

The fixture has no native registration/certification. Only public autocommit
wrappers are adapted to its outer rollback; their real SQL claim/effect/fence
primitives and producers remain in use. This is not native command acceptance.
"""
from contextlib import ExitStack
import os
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from tests import test_prepared_effects_postgresql as fixtures


@unittest.skipUnless(os.environ.get('VF_PHASE_POSTGRES_PROOF')=='1','Owned PostgreSQL required')
class ProductionScopePostgresTests(unittest.TestCase):
    for _name in ('setUp','rollback','owner'):
        locals()[_name]=getattr(fixtures.PreparedEffectsPostgresTests,_name)

    def setup_scope(self,*,runtime_reports=None,**kwargs):
        from mta.runtime import production_scope as scope,scope_execution as workers
        from mta.runtime.scope_execution import _setting
        root=self.enterContext(TemporaryDirectory())
        self.value=dict(schema=scope.SCHEMA,scope='UptoBPR',command_key='native-entry-component',
            compatibility_digest='a'*64)
        if runtime_reports is not None:
            self.value.update(schema=scope.CONFIGURED_SCHEMA,runtime_reports=runtime_reports)
        self.owner(claim=False,pick_root=root,scope_request=self.value,**kwargs)
        stack=self.enterContext(ExitStack())
        stack.enter_context(patch.object(workers,'claim',side_effect=workers._claim))
        def release(attempt_id,token,*,compatibility_digest):
            attempt,run=workers.require_claim(attempt_id,token,compatibility_digest=compatibility_digest)
            with _setting('fresh.scope_worker',token):workers._close_attempt(attempt,run,'RELEASED',{})
            return attempt
        def fail(attempt_id,token,*,compatibility_digest,error):
            attempt,run=workers._locked_claim(attempt_id,token,compatibility_digest=compatibility_digest)
            with _setting('fresh.scope_worker',token):
                workers._close_attempt(attempt,run,'FAILED',dict(type=type(error).__name__,message=str(error)))
            return attempt
        stack.enter_context(patch.object(workers,'release',side_effect=release))
        stack.enter_context(patch.object(workers,'fail',side_effect=fail))

    def advance(self,**kwargs):
        from mta.runtime.production_scope import advance
        return advance(self.run,self.value,worker_reference='ROLLED-BACK-COMPONENT',**kwargs)

    def assert_paused(self):
        self.run.refresh_from_db();self.capture.refresh_from_db()
        self.assertEqual((self.run.status,self.capture.status),('RUNNING','CAPTURED'))
        self.assertFalse(self.run.output_digest)
        self.assertFalse(self.run.checkpoints.exists())
        self.assertEqual(list(self.run.phase_acceptances.order_by('accepted_at').values_list('phase',flat=True)),
            ['PRE_BPR','BPR'])

    def test_actual_entry_stops_after_bpr_and_retry_reads_without_business_replay(self):
        self.setup_scope()
        report=self.advance()
        self.assert_paused()
        self.assertTrue(report['calculation_accepted']);self.assertTrue(report['pick_files_ready'])
        self.assertFalse(report['scope_ready']);self.assertFalse(report['serving_selected'])
        identities=list(self.run.phase_acceptances.values_list('id','digest'))
        with patch('mta.temporal.chain.prepare_day',side_effect=AssertionError('replayed PRE')), \
                patch('mta.temporal.chain.produce_bpr',side_effect=AssertionError('replayed BPR')):
            repeated=self.advance()
        self.assertEqual(repeated,report)
        self.assertEqual(list(self.run.phase_acceptances.values_list('id','digest')),identities)
        self.assertEqual(self.run.scope_attempts.count(),1)
        self.assertEqual(self.run.scope_attempts.get().status,'RELEASED')

    def test_failed_pick_recovery_preserves_bpr_and_requires_explicit_attempt(self):
        self.setup_scope()
        with patch('mta.runtime.scoped_pick_files._copy_file',side_effect=OSError('injected copy failure')):
            with self.assertRaisesRegex(OSError,'injected copy failure'):self.advance()
        self.assert_paused()
        failed=self.run.scope_attempts.get()
        self.assertEqual(failed.status,'FAILED')
        identities=list(self.run.phase_acceptances.values_list('id','digest'))
        with self.assertRaisesRegex(ValueError,'explicit recovery'):self.advance()
        with patch('mta.temporal.chain.prepare_day',side_effect=AssertionError('replayed PRE')), \
                patch('mta.temporal.chain.produce_bpr',side_effect=AssertionError('replayed BPR')):
            report=self.advance(recovery_of=failed.pk)
        self.assertTrue(report['pick_files_ready'])
        self.assertEqual(list(self.run.phase_acceptances.values_list('id','digest')),identities)
        recovery=self.run.scope_attempts.get(recovery_of=failed)
        self.assertEqual((recovery.status,recovery.attempt_no),('RELEASED',2))
        self.assertEqual(self.run.scope_attempts.get(pk=failed.pk).status,'FAILED')

    def test_restart_from_accepted_pre_uses_typed_reader_without_preparation(self):
        from mta.runtime.scope_execution import _claim,_setting,_close_attempt
        from mta.runtime.prepared_effects import _accept_prepared
        self.setup_scope()
        attempt=_claim(self.run.pk,scope='UptoBPR',command_key=self.value['command_key'],
            worker_reference='interrupted-component',compatibility_digest='a'*64,
            expected_phase='START',expected_receipt_digest='')
        pre=_accept_prepared(attempt.pk,attempt.worker_token,self.prepared,compatibility_digest='a'*64)
        with _setting('fresh.scope_worker',attempt.worker_token):
            _close_attempt(attempt,self.run,'FAILED',dict(type='INTERRUPTED',message='component restart'))
        with patch('mta.temporal.chain.prepare_day',side_effect=AssertionError('replayed PRE')):
            report=self.advance(recovery_of=attempt.pk)
        self.assert_paused()
        self.assertEqual(self.run.phase_acceptances.get(phase='PRE_BPR').pk,pre.pk)
        self.assertTrue(report['calculation_accepted'])

    def test_explicit_fence_during_calculation_prevents_stale_bpr_acceptance(self):
        from mta.temporal.chain import produce_bpr
        from mta.runtime.scope_execution import _setting,_close_attempt
        self.setup_scope()
        def fence_then_calculate(prepared):
            active=self.run.scope_attempts.get(status='ACTIVE')
            with _setting('fresh.scope_fence',active.pk):
                _close_attempt(active,self.run,'FAILED',dict(type='FENCED',message='explicit test operator'))
            return produce_bpr(prepared)
        with patch('mta.temporal.chain.produce_bpr',side_effect=fence_then_calculate):
            with self.assertRaisesRegex(ValueError,'Stale or incompatible'):self.advance()
        failed=self.run.scope_attempts.get()
        self.assertEqual(failed.failure['type'],'FENCED')
        self.assertEqual(list(self.run.phase_acceptances.values_list('phase',flat=True)),['PRE_BPR'])
        with patch('mta.temporal.chain.prepare_day',side_effect=AssertionError('replayed PRE')):
            self.assertTrue(self.advance(recovery_of=failed.pk)['calculation_accepted'])
        self.assert_paused()

    def configured_reports(self,mode):
        from mta.serialization import storage
        from mta.runtime.scoped_actions import restore
        from mta.presentation.production_reports import current
        self.setup_scope(report_mode=mode)
        with patch('mta.presentation.production_reports.current',wraps=current) as producer:
            report=self.advance()
        self.assertEqual(producer.call_count,1)
        _output,opening=producer.call_args.args
        self.assertIn('production_report_policy',opening)
        self.assertEqual(opening['production_report_opening'],
            dict(BOR_OrderAllocationHistory=[],RRR_OrderAllocationHistory=[]))
        receipt=self.run.phase_acceptances.get(phase='BPR')
        _phase,sources=restore(self.run,receipt)
        # The persisted reader exposes canonical decimal/date wire values.
        # Compare every cell/order/NULL through the existing lossless codec.
        self.assertEqual(sources.production_reports,storage(current(_output,opening)))
        expected={'BORWithOrderAllocation','RRR_OrderAllocation','AllocatedOrders','BOROARequirement'}
        if mode=='expanded':expected.add('SupplierDispatchReq')
        self.assertEqual(set(sources.production_reports),expected)
        self.assertFalse(report['scope_ready'])
        self.assert_paused()

    def test_basic_configured_report_sources_survive_the_bpr_cut(self):
        self.configured_reports('basic')

    def test_expanded_configured_report_sources_survive_the_bpr_cut(self):
        self.configured_reports('expanded')

    def test_explicit_empty_runtime_reports_survive_typed_capture_and_exact_scope_retry(self):
        from copy import deepcopy
        from mta.runtime import production_scope as scope,scope_runtime_reports as reports
        from mta.runtime.input_reader import read_input
        from tests.test_scope_runtime_reports import reference
        configured=reference();self.setup_scope(runtime_reports=configured)
        report=self.advance();self.assert_paused()
        self.assertEqual(report['runtime_reports'],reports.status(configured))
        self.assertFalse(report['scope_ready']);self.assertIn('configured_artifact_readiness',report['pending'])
        self.run.refresh_from_db()
        self.assertEqual(self.run.input_payload['schema'],'fresh-daily-input-manifest-v2')
        self.assertEqual(read_input(self.run,components=('scope_request',))['scope_request'],self.value)
        identities=list(self.run.phase_acceptances.values_list('id','digest'))
        with patch('mta.temporal.chain.prepare_day',side_effect=AssertionError('replayed PRE')), \
                patch('mta.temporal.chain.produce_bpr',side_effect=AssertionError('replayed BPR')):
            self.assertEqual(self.advance(),report)
            changed=deepcopy(self.value);changed['runtime_reports']=reference()
            changed['runtime_reports']['sha256']='f'*64
            with self.assertRaisesRegex(ValueError,'Captured native scope identity differs'):
                scope.advance(self.run,changed,worker_reference='must-not-recapture')
        self.assertEqual(list(self.run.phase_acceptances.values_list('id','digest')),identities)
        self.assertEqual(self.run.scope_attempts.count(),1)
        self.assertEqual(self.run.scope_attempts.get().status,'RELEASED')
