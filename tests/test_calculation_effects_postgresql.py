"""Rolled-back actual producer/copy proofs, not native scope acceptance."""
import os
import unittest
from unittest.mock import patch
from tests import test_prepared_effects_postgresql as prepared_tests


@unittest.skipUnless(os.environ.get('VF_PHASE_POSTGRES_PROOF')=='1','Owned PostgreSQL required')
class CalculationEffectsPostgresTests(unittest.TestCase):
    setUp=prepared_tests.PreparedEffectsPostgresTests.setUp
    rollback=prepared_tests.PreparedEffectsPostgresTests.rollback
    owner=prepared_tests.PreparedEffectsPostgresTests.owner
    accept=prepared_tests.PreparedEffectsPostgresTests.accept
    counter_claim=prepared_tests.PreparedEffectsPostgresTests.counter_claim

    def prepare_bpr(self):
        from mta.temporal.chain import produce_bpr
        from mta.application.native_output_contracts import native_assignments
        from mta.application.stage_calculation_sources import capture_bpr
        self.counter_claim()
        self.pre=self.accept()
        with native_assignments(True):self.bpr=produce_bpr(self.prepared)
        self.sources=capture_bpr(self.bpr,self.bpr.context.prior)

    def accept_phase(self,phase,parent):
        from mta.runtime.calculation_effects import _accept_calculation
        return _accept_calculation(self.attempt.pk,self.attempt.worker_token,phase,self.sources,
                                  parent=parent,compatibility_digest='a'*64)

    def assert_copies(self,owner,state):
        from mta.mdm.master_owners import phase_copy_batches,business_fields
        from mta.serialization import storage
        for _,model,partition,rows,_ in phase_copy_batches(owner,state):
            self.assertEqual(storage(list(model.objects.filter(source=self.source,**partition)
                .order_by('ordinal').values(*[f.name for f in business_fields(model)]))),storage(rows))

    def test_actual_bpr_then_restored_dbm_copies_keep_capture_unconsumed(self):
        from django.db import connection
        from mta.runtime import phase_state
        from mta.runtime.scope_revisions import require_current
        from mta.temporal.chain import produce_dbm
        from mta.application.native_output_contracts import native_assignments
        from mta.runtime.mdm_daily_models import MdmDailySkuArchive
        self.prepare_bpr()
        bpr=self.accept_phase(self.bpr,self.pre)
        self.assert_copies('BPR',self.bpr.importer)
        self.assertEqual(require_current(self.run),bpr.metadata['revision_after'])
        from mta.runtime.scope_execution import _setting,_close_attempt,_claim
        with _setting('fresh.scope_worker',self.attempt.worker_token):
            _close_attempt(self.attempt,self.run,'RELEASED',{})
        self.attempt=_claim(self.run.pk,scope='PostBPR',command_key='post-bpr',
            worker_reference='restored-dbm-component',compatibility_digest='a'*64,
            expected_phase='BPR',expected_receipt_digest=bpr.digest)
        context=self.bpr.context
        restored,sources=phase_state.read(bpr.snapshot,prior=context.prior,day=context.day,
            profile=context.profile,master_snapshot=context.master_snapshot)
        self.sources=sources
        with native_assignments(True):dbm=produce_dbm(restored)
        receipt=self.accept_phase(dbm,bpr)
        self.assert_copies('DBM',dbm.final_dbm)
        self.assert_copies('BPR',self.bpr.importer)
        self.assertEqual(require_current(self.run),receipt.metadata['revision_after'])
        self.assertEqual(MdmDailySkuArchive.objects.filter(source=self.source).count(),1)
        self.capture.refresh_from_db();self.run.refresh_from_db()
        self.assertEqual((self.capture.status,self.run.status),('CAPTURED','RUNNING'))
        self.assertFalse(self.run.output_digest)
        with connection.cursor() as cursor:
            cursor.execute('SET CONSTRAINTS phase_acceptance_complete IMMEDIATE')
            cursor.execute('SET CONSTRAINTS phase_acceptance_complete DEFERRED')
        with self.assertRaisesRegex(ValueError,'accepted business parent'):
            self.accept_phase(dbm,bpr)

    def test_late_bpr_failure_rolls_copies_and_counters_back_before_retry(self):
        from mta.runtime.scope_revisions import require_current
        from mta.runtime.models import RunPhaseAcceptance
        from mta.runtime.mdm_models import MdmSkuDescription
        self.prepare_bpr();before=require_current(self.run)
        old=list(MdmSkuDescription.objects.filter(source=self.source,owner='BPR').values())
        with patch('mta.runtime.calculation_effects.phase_state.save',side_effect=ValueError('late phase failure')), \
                self.assertRaisesRegex(ValueError,'late phase failure'):
            self.accept_phase(self.bpr,self.pre)
        self.assertEqual(require_current(self.run),before)
        self.assertEqual(list(MdmSkuDescription.objects.filter(source=self.source,owner='BPR').values()),old)
        self.assertEqual(list(RunPhaseAcceptance.objects.filter(run=self.run).values_list('phase',flat=True)),['PRE_BPR'])
        self.accept_phase(self.bpr,self.pre)
        self.assert_copies('BPR',self.bpr.importer)

    def test_pending_bpr_rejects_other_partitions_and_fenced_worker(self):
        from django.db import connection,transaction,DatabaseError
        from mta.runtime.scope_execution import _setting,_begin_phase,_close_attempt,_claim
        self.prepare_bpr()
        with transaction.atomic():
            with _setting('fresh.scope_worker',self.attempt.worker_token):
                _begin_phase(self.attempt,self.run,'BPR')
                with _setting('fresh.mdm_current_run',self.run.pk):
                    for owner in ('Importer','DBM','BTR'):
                        with self.assertRaises(DatabaseError),transaction.atomic():
                            with connection.cursor() as cursor:
                                cursor.execute('UPDATE mta.fresh_mta_mdmskudescription '
                                    'SET "SKUDescription"=\'wrong phase\' WHERE source_id=%s AND owner=%s',
                                    [self.source.pk,owner])
            transaction.set_rollback(True)
        with _setting('fresh.scope_worker',self.attempt.worker_token):
            _close_attempt(self.attempt,self.run,'FAILED',{'type':'EXPLICIT_BEFORE_BPR'})
        retry=_claim(self.run.pk,scope='UptoBPR',command_key='prepared-effects',
            worker_reference='retry-before-bpr',compatibility_digest='a'*64,
            expected_phase='PRE_BPR',expected_receipt_digest=self.pre.digest,recovery_of=self.attempt.pk)
        with self.assertRaises(ValueError):self.accept_phase(self.bpr,self.pre)
        self.attempt=retry
        self.accept_phase(self.bpr,self.pre)
        self.assert_copies('BPR',self.bpr.importer)
