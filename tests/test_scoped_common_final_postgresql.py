"""Actual Full/scoped common publisher; rolled-back supplied component proof."""
from copy import deepcopy
import os
import unittest
from unittest.mock import patch
from tests import test_prepared_effects_postgresql as prepared_tests


@unittest.skipUnless(os.environ.get('VF_PHASE_POSTGRES_PROOF')=='1','Owned PostgreSQL required')
class ScopedCommonFinalTests(unittest.TestCase):
    for _name in ('setUp','rollback','owner','accept'):
        locals()[_name]=getattr(prepared_tests.PreparedEffectsPostgresTests,_name)

    def prepare_dbm(self,terminal_scope='PostBPR'):
        from mta.runtime.scope_execution import _claim,_setting,_close_attempt
        from mta.runtime.calculation_effects import _accept_calculation
        from mta.application.native_output_contracts import native_assignments
        from mta.application.stage_calculation_sources import capture_bpr
        from mta.temporal.chain import produce_bpr,produce_dbm
        from mta.runtime import phase_state
        self.attempt=_claim(self.run.pk,scope='UptoDBM' if terminal_scope=='PostDBM' else 'UptoBPR',command_key='common-final-bpr',
            worker_reference='COMMON-FINAL-COMPONENT',compatibility_digest='a'*64,
            expected_phase='START',expected_receipt_digest='')
        pre=self.accept()
        with native_assignments(True):bpr=produce_bpr(self.prepared)
        sources=capture_bpr(bpr,self.publication_opening())
        receipt=_accept_calculation(self.attempt.pk,self.attempt.worker_token,bpr,sources,
            parent=pre,compatibility_digest='a'*64)
        if terminal_scope=='PostBPR':
            with _setting('fresh.scope_worker',self.attempt.worker_token):
                _close_attempt(self.attempt,self.run,'RELEASED',{})
            self.attempt=_claim(self.run.pk,scope='PostBPR',command_key='common-final-post-bpr',
                worker_reference='COMMON-FINAL-COMPONENT',compatibility_digest='a'*64,
                expected_phase='BPR',expected_receipt_digest=receipt.digest)
        context=bpr.context
        restored,sources=phase_state.read(receipt.snapshot,prior=context.prior,day=context.day,
            profile=context.profile,master_snapshot=context.master_snapshot)
        with native_assignments(True):dbm=produce_dbm(restored)
        self.dbm=_accept_calculation(self.attempt.pk,self.attempt.worker_token,dbm,sources,
            parent=receipt,compatibility_digest='a'*64)
        if terminal_scope=='PostDBM':
            with _setting('fresh.scope_worker',self.attempt.worker_token):
                _close_attempt(self.attempt,self.run,'RELEASED',{})
            self.attempt=_claim(self.run.pk,scope='PostDBM',command_key='common-final-post-dbm',
                worker_reference='COMMON-FINAL-COMPONENT',compatibility_digest='a'*64,
                expected_phase='DBM',expected_receipt_digest=self.dbm.digest)

    def finish(self):
        from mta.runtime.scoped_final import _finish_accepted_day
        return _finish_accepted_day(self.attempt.pk,self.attempt.worker_token,compatibility_digest='a'*64)

    def publication_opening(self):
        context=self.prepared.context
        result=dict(supplier=context.prior['supplier'])
        for name in ('shipment_input','transporter_input','production_report_policy',
                     'production_report_opening','production_report_schema'):
            if name in context.day:result[name]=context.day[name]
        return result

    def ordinary_full(self):
        from mta.temporal.chain import produce_bpr,produce_dbm,produce_btr
        from mta.application.native_output_contracts import native_assignments
        from mta.runtime.input_reader import read_input
        from mta.runtime.services import finish_run
        with native_assignments(True):
            output=produce_btr(produce_dbm(produce_bpr(deepcopy(self.prepared))))
        output.pop('_CompletedBoundaries')
        lineage=read_input(self.run,components=('lineage',))['lineage']
        lineage['cohort1']=output.pop('_Cohort1')
        sources=output.pop('_PickSourceDigests',None)
        if sources is not None:lineage['pick_source_digests']=sources
        output['Lineage']=[lineage]
        return finish_run(self.run,output,expected_digest=self.run.input_digest,
            publication_opening=self.publication_opening())

    def compare_full_scope(self,terminal_scope,*,operational=False,report_mode=None,predecessor=None):
        from django.db import transaction,connection,DatabaseError
        from mta.runtime.services import read_outputs
        from mta.serialization import storage
        from mta.runtime.mdm_daily_models import MdmDailySkuArchive
        from mta.runtime.scope_execution import head
        from mta.mdm.daily_current import verify_current
        self.owner(claim=False,operational=operational,report_mode=report_mode,predecessor=predecessor)
        with transaction.atomic():
            full=self.ordinary_full()
            expected=storage(read_outputs(full,include_reports=False))
            expected_manifest=storage(full.production_manifest)
            expected_root=full.output_digest
            transaction.set_rollback(True)
        self.run.refresh_from_db();self.capture.refresh_from_db()
        self.prepare_dbm(terminal_scope)
        from mta.mdm.daily_current import _write_partition
        from mta.mdm.native_audit import finalize as finalize_audit
        def remaining_only(source,model,partition,rows,path):
            self.assertEqual(partition.get('owner'),'BTR')
            with connection.cursor() as cursor:
                cursor.execute("SELECT current_setting('fresh.mdm_consuming_run',true)")
                self.assertEqual(cursor.fetchone()[0],'')
            for owner in ('Importer','BPR','DBM'):
                with self.assertRaises(DatabaseError),transaction.atomic():
                    with connection.cursor() as cursor:
                        cursor.execute('UPDATE mta.fresh_mta_mdmskudescription '
                            'SET "SKUDescription"="SKUDescription" WHERE source_id=%s AND owner=%s',
                            [source.pk,owner])
            return _write_partition(source,model,partition,rows,path)
        def owned_audit(run):
            with connection.cursor() as cursor:
                cursor.execute("SELECT current_setting('fresh.mdm_consuming_run',true)")
                self.assertEqual(cursor.fetchone()[0],str(run.pk))
            return finalize_audit(run)
        with patch('mta.temporal.chain.produce_bpr',side_effect=AssertionError('BPR replay')), \
                patch('mta.temporal.entry_preparation.prepare',side_effect=AssertionError('PRE replay')), \
                patch('mta.mdm.daily_current._write_partition',side_effect=remaining_only), \
                patch('mta.mdm.native_audit.finalize',side_effect=owned_audit), \
                patch('mta.mdm.daily_input._apply_consumption_effects',side_effect=AssertionError('effects replay')):
            result=self.finish()
        self.assertEqual(storage(read_outputs(result,include_reports=False)),expected)
        self.assertEqual(storage(result.production_manifest),expected_manifest)
        self.assertEqual(result.output_digest,expected_root)
        self.assertEqual(head(result.pk)[0],'DAY_FINAL')
        self.capture.refresh_from_db();self.attempt.refresh_from_db()
        self.assertEqual((result.status,self.capture.status,self.attempt.status),('SUCCEEDED','CONSUMED','RELEASED'))
        self.assertEqual(MdmDailySkuArchive.objects.filter(source=self.source).count(),1)
        verify_current(self.source,expected['ClosingState'][0])
        with connection.cursor() as cursor:
            cursor.execute('SET CONSTRAINTS phase_acceptance_complete IMMEDIATE')
            cursor.execute('SET CONSTRAINTS phase_acceptance_complete DEFERRED')
        return result

    def test_post_bpr_matches_actual_full_without_phase_or_current_copy_replay(self):
        self.compare_full_scope('PostBPR')

    def test_post_dbm_matches_actual_full_without_phase_or_current_copy_replay(self):
        self.compare_full_scope('PostDBM')

    def test_operational_and_basic_reports_match_full_with_own_successor_history(self):
        parent=self.compare_full_scope('PostBPR',operational=True,report_mode='basic')
        result=self.compare_full_scope('PostDBM',operational=True,report_mode='basic',predecessor=parent)
        self.assert_own_histories(parent,result)

    def test_operational_and_expanded_reports_match_full_with_own_successor_history(self):
        parent=self.compare_full_scope('PostDBM',operational=True,report_mode='expanded')
        result=self.compare_full_scope('PostBPR',operational=True,report_mode='expanded',predecessor=parent)
        self.assert_own_histories(parent,result)

    def assert_own_histories(self,parent,result):
        from mta.runtime.production_report_storage import read
        from mta.runtime.input_reader import read_input
        from mta.runtime.operational_source import read_source
        profile=read_input(result,components=('day',))['day']
        policy=profile['production_report_policy']
        self.assertEqual(result.predecessor_id,parent.pk)
        self.assertIsNone(profile['production_report_opening'])
        self.assertTrue(read_source(result)['requirement_bands'])
        self.assertTrue(read(result,'AllocatedOrders'))
        # Consecutive dates within both horizons: independently expect exact
        # retained predecessor occurrences, followed by today's actual rows.
        self.assertEqual((result.business_date-parent.business_date).days,1)
        for current,history,horizon in (
                ('BORWithOrderAllocation','BOR_OrderAllocationHistory','bor_history_horizon'),
                ('RRR_OrderAllocation','RRR_OrderAllocationHistory','rrr_history_horizon')):
            previous=read(parent,history);present=read(result,current)
            self.assertTrue(previous);self.assertTrue(present)
            self.assertGreater(policy[horizon],1)
            expected=previous+[dict(row,ReportDate=result.business_date.isoformat()) for row in present]
            self.assertEqual(read(result,history),expected)

    def test_common_writer_late_failure_retains_prefix_and_capture_for_retry(self):
        from mta.runtime.models import RunPhaseAcceptance,PickProjection
        from mta.runtime.scope_execution import head
        self.owner(claim=False);self.prepare_dbm()
        with patch('mta.presentation.daily_sources.write_sources',side_effect=ValueError('late common writer failure')), \
                self.assertRaisesRegex(ValueError,'late common writer failure'):
            self.finish()
        self.run.refresh_from_db();self.capture.refresh_from_db()
        self.assertEqual((self.run.status,self.capture.status),('RUNNING','CAPTURED'))
        self.assertEqual(head(self.run.pk),('DBM',self.dbm.digest))
        self.assertFalse(PickProjection.objects.filter(run=self.run).exists())
        self.assertFalse(RunPhaseAcceptance.objects.filter(run=self.run,phase='DAY_FINAL').exists())
        self.assertEqual(self.finish().status,'SUCCEEDED')
