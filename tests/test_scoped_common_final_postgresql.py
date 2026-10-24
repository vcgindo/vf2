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
        sources=capture_bpr(bpr,bpr.context.prior)
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
            publication_opening=dict(supplier=self.prepared.context.prior['supplier']))

    def compare_full_scope(self,terminal_scope):
        from django.db import transaction,connection,DatabaseError
        from mta.runtime.services import read_outputs
        from mta.serialization import storage
        from mta.runtime.mdm_daily_models import MdmDailySkuArchive
        from mta.runtime.scope_execution import head
        from mta.mdm.daily_current import verify_current
        self.owner(claim=False)
        with transaction.atomic():
            full=self.ordinary_full()
            expected=storage(read_outputs(full,include_reports=False))
            expected_manifest=storage(full.production_manifest)
            expected_root=full.output_digest
            transaction.set_rollback(True)
        self.run.refresh_from_db();self.capture.refresh_from_db()
        self.prepare_dbm(terminal_scope)
        from mta.mdm.daily_current import _write_partition
        def remaining_only(source,model,partition,rows,path):
            self.assertEqual(partition.get('owner'),'BTR')
            for owner in ('Importer','BPR','DBM'):
                with self.assertRaises(DatabaseError),transaction.atomic():
                    with connection.cursor() as cursor:
                        cursor.execute('UPDATE mta.fresh_mta_mdmskudescription '
                            'SET "SKUDescription"="SKUDescription" WHERE source_id=%s AND owner=%s',
                            [source.pk,owner])
            return _write_partition(source,model,partition,rows,path)
        with patch('mta.temporal.chain.produce_bpr',side_effect=AssertionError('BPR replay')), \
                patch('mta.temporal.entry_preparation.prepare',side_effect=AssertionError('PRE replay')), \
                patch('mta.mdm.daily_current._write_partition',side_effect=remaining_only), \
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

    def test_post_bpr_matches_actual_full_without_phase_or_current_copy_replay(self):
        self.compare_full_scope('PostBPR')

    def test_post_dbm_matches_actual_full_without_phase_or_current_copy_replay(self):
        self.compare_full_scope('PostDBM')

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
