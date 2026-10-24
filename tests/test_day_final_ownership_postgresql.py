"""DAY_FINAL storage/ownership components; not common Full-flow acceptance."""
import os
import unittest
from unittest.mock import patch
from tests import test_calculation_effects_postgresql as calculation_tests


@unittest.skipUnless(os.environ.get('VF_PHASE_POSTGRES_PROOF')=='1','Owned PostgreSQL required')
class DayFinalOwnershipTests(unittest.TestCase):
    for _name in ('setUp','rollback','owner','accept','counter_claim','prepare_bpr','accept_phase'):
        locals()[_name]=getattr(calculation_tests.CalculationEffectsPostgresTests,_name)

    def prepared_final(self):
        from mta.runtime.scope_execution import _setting,_close_attempt,_claim
        from mta.temporal.chain import produce_dbm,produce_btr
        from mta.application.native_output_contracts import native_assignments
        self.prepare_bpr();bpr=self.accept_phase(self.bpr,self.pre)
        with _setting('fresh.scope_worker',self.attempt.worker_token):
            _close_attempt(self.attempt,self.run,'RELEASED',{})
        self.attempt=_claim(self.run.pk,scope='PostBPR',command_key='post-bpr',
            worker_reference='DAY_FINAL-STORAGE-COMPONENT',compatibility_digest='a'*64,
            expected_phase='BPR',expected_receipt_digest=bpr.digest)
        with native_assignments(True):self.dbm=produce_dbm(self.bpr)
        self.accept_phase(self.dbm,bpr)
        with native_assignments(True):self.output=produce_btr(self.dbm)

    def store_root(self):
        from django.utils import timezone
        from mta.runtime.relational_state import save_daily
        from mta.runtime.receipt_integrity import source_receipts,operational_roster,output_root,audit_output
        from mta.serialization import digest,storage
        from mta.mdm.daily_input import _consume_capture
        from mta.presentation.pick_storage import _write_pick_rows
        from mta.runtime.report_sources import _write_route_rows
        from mta.presentation.daily_sources import write_sources
        self.run.production_manifest=save_daily(self.run,self.output)
        self.run.production_manifest['version']=3
        self.run.production_manifest['ingestion_preparation']=self.counter_carrier[-1]
        audit_output(self.run)
        _write_pick_rows(self.run,self.sources.pick_bands,provenance={'origin':'production-calculation'},
                         calculation_digest=self.sources.calculation_digest)
        self.run.production_manifest['report_sources']=dict(contract=self.output['_ReportBoundary'],
            routes=_write_route_rows(self.run,self.sources.routes))
        write_sources(self.run,self.output,opening=self.dbm.context.prior)
        from mta.runtime.scope_execution import _setting
        with _setting('fresh.mdm_consuming_run',self.run.pk):
            _consume_capture(self.capture,timezone.now())
        self.run.production_manifest['sources']=storage(source_receipts(self.run))
        self.run.production_digest=digest(self.run.production_manifest)
        self.run.output_roster=list(operational_roster(self.run))
        self.run.output_digest=output_root(self.run)
        self.run.status='SUCCEEDED';self.run.completed_at=timezone.now()
        self.run.save(update_fields=['production_manifest','production_digest','output_roster',
                                    'output_digest','status','completed_at'])

    def test_actual_typed_root_seals_then_closes_worker_without_duplicate_snapshot(self):
        from django.db import connection,DatabaseError,transaction
        from mta.runtime.scope_execution import _setting,_begin_phase,_seal_day_final,_close_attempt,head
        from mta.runtime.scope_revisions import require_current
        from mta.runtime.receipt_integrity import verify_root
        self.prepared_final()
        with _setting('fresh.scope_worker',self.attempt.worker_token):
            receipt=_begin_phase(self.attempt,self.run,'DAY_FINAL')
            self.store_root()
            _seal_day_final(receipt)
            self.assertIsNone(receipt.snapshot_id)
            self.assertEqual(head(self.run.pk),('DAY_FINAL',receipt.digest))
            self.assertEqual(require_current(self.run),receipt.metadata['revision_after'])
            _close_attempt(self.attempt,self.run,'RELEASED',{})
            verify_root(self.run)
            with connection.cursor() as cursor:
                cursor.execute('SET CONSTRAINTS phase_acceptance_complete IMMEDIATE')
                cursor.execute('SET CONSTRAINTS phase_acceptance_complete DEFERRED')
            with self.assertRaises(DatabaseError),transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute("UPDATE mta.fresh_mta_calculationrun SET output_digest=%s WHERE id=%s",['f'*64,self.run.pk])

    def test_unsealed_final_and_wrong_worker_cannot_commit_or_consume(self):
        import uuid
        from django.db import connection,DatabaseError,transaction
        from django.utils import timezone
        from mta.runtime.scope_execution import _setting,_begin_phase,_seal_day_final
        from mta.mdm.daily_input import _consume_capture
        self.prepared_final()
        with self.assertRaises(DatabaseError),transaction.atomic():
            _consume_capture(self.capture,timezone.now())
        with transaction.atomic(),_setting('fresh.scope_worker',self.attempt.worker_token):
            receipt=_begin_phase(self.attempt,self.run,'DAY_FINAL')
            with self.assertRaises(DatabaseError),transaction.atomic():
                with connection.cursor() as cursor:cursor.execute('SET CONSTRAINTS phase_acceptance_complete IMMEDIATE')
            with _setting('fresh.scope_worker',uuid.uuid4()),self.assertRaisesRegex(ValueError,'no longer owns'):
                _seal_day_final(receipt)
            with self.assertRaisesRegex(ValueError,'completed run'):_seal_day_final(receipt)
            transaction.set_rollback(True)

    def test_late_final_failure_rolls_back_root_capture_and_counters_preserving_dbm(self):
        from django.db import transaction
        from mta.runtime.scope_execution import _setting,_begin_phase,head,_seal_day_final
        from mta.runtime.scope_revisions import require_current
        from mta.runtime.models import RunPhaseAcceptance
        self.prepared_final();before=require_current(self.run);accepted=head(self.run.pk)
        with self.assertRaisesRegex(ValueError,'late final failure'),transaction.atomic(), \
                _setting('fresh.scope_worker',self.attempt.worker_token):
            _begin_phase(self.attempt,self.run,'DAY_FINAL')
            self.store_root()
            raise ValueError('late final failure')
        self.run.refresh_from_db();self.capture.refresh_from_db()
        self.assertEqual((self.run.status,self.capture.status),('RUNNING','CAPTURED'))
        self.assertFalse(self.run.output_digest)
        self.assertFalse(RunPhaseAcceptance.objects.filter(run=self.run,phase='DAY_FINAL').exists())
        self.assertEqual(require_current(self.run),before)
        self.assertEqual(head(self.run.pk),accepted)
        with _setting('fresh.scope_worker',self.attempt.worker_token):
            receipt=_begin_phase(self.attempt,self.run,'DAY_FINAL')
            self.store_root();_seal_day_final(receipt)
