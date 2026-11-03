"""Actual certified-counter mechanics on rollback-only metadata fixtures.

Certificates here are explicit metadata carriers, not initialized application
or business certification. No native source, accepted day or release is claimed.
All production triggers remain enabled throughout these tests.
"""
from copy import deepcopy
import os
import unittest
import uuid

if os.environ.get('VF_PHASE_POSTGRES_PROOF') == '1':
    os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
    import django
    django.setup()


def bind_metadata_counter_owner(run,source,*,consumer_snapshot=None,configuration_digest='c'*64):
    """Isolated metadata carrier only; never native registration/certification."""
    from django.db import connection
    from mta.runtime.models import ProductionInitialization
    from mta.runtime.ingestion_models import InitializationCertification,IngestionRevisionState,MasterInputRevision
    from mta.runtime.capture_preparation import seal,CONTRACT
    if connection.settings_dict['NAME'] not in ('VFTEST_Fresh_LifecycleG2_20261024',
            'vftest_fresh_transit_20261030', 'vftest_fresh_ir3_history1_20261103'):
        raise RuntimeError('Metadata counter fixture requires its uniquely owned database')
    if connection.settings_dict['NAME']=='vftest_fresh_transit_20261030':
        with connection.cursor() as cursor:
            cursor.execute("SELECT shobj_description(oid,'pg_database') FROM pg_database WHERE datname=current_database()")
            if cursor.fetchone()[0]!='owned transit lifecycle proof 20261030; isolated native typed SQL only':
                raise RuntimeError('Transit metadata fixture database ownership differs')
    initial_id=uuid.uuid4()
    with connection.cursor() as cursor:
        cursor.execute("SELECT set_config('fresh.production_initialization',%s,true)",[str(initial_id)])
    initial=ProductionInitialization.objects.create(id=initial_id,source=source,
        opening_identity='METADATA_ONLY-'+initial_id.hex,opening_date='2037-04-09',
        input_sha256=uuid.uuid4().hex*2,recipe_sha256='b'*64,configuration_digest=configuration_digest,
        implementation_digest='d'*64,input_digest='e'*64,input_manifest_digest='f'*64)
    with connection.cursor() as cursor:
        cursor.execute("SELECT set_config('fresh.production_initialization','',true)")
        cursor.execute('SELECT oid FROM pg_database WHERE datname=current_database()')
        database_oid=cursor.fetchone()[0]
    state=IngestionRevisionState.objects.create(initialization=initial)
    cert=InitializationCertification.objects.create(initialization=initial,
        contract='METADATA_ONLY_SCOPE_COUNTERS',database_name=connection.settings_dict['NAME'],
        database_oid=database_oid,namespace=uuid.uuid4(),source_digest=source.digest,
        content_digest='e'*64,configuration_digest=configuration_digest,schema_digest='1'*64,
        guard_digest='2'*64,release_digest='3'*64,receipt_digest='4'*64,
        populations={'fixture':'NO_BUSINESS_CERTIFICATION'})
    base=MasterInputRevision.objects.create(initialization=initial,master_epoch=0,
        configuration_epoch=0,partitions={'fixture':'NO_MASTER_ACCEPTANCE'},
        receipt_digest='5'*64,status='ACCEPTED')
    run.production_manifest={'ingestion_preparation':dict(contract=CONTRACT,
        initialization_id=str(initial.pk),source_digest=source.digest,
        certification_digest=cert.receipt_digest,base_revision_id=str(base.pk),
        configuration_digest=configuration_digest,qualified_master_reuse=False)}
    # Model creation accepts an ISO string; policy admission consumes DateField's
    # actual persisted Python date, just as the native production entry does.
    run.refresh_from_db(fields=['business_date'])
    seal(run,consumer_snapshot=consumer_snapshot)
    return initial,state,cert,base,deepcopy(run.production_manifest['ingestion_preparation'])


@unittest.skipUnless(os.environ.get('VF_PHASE_POSTGRES_PROOF') == '1',
                     'Explicit owned PostgreSQL proof required')
class ScopeRevisionPostgresTests(unittest.TestCase):
    def setUp(self):
        from django.db import connection,transaction
        if connection.settings_dict['NAME'] != 'VFTEST_Fresh_LifecycleG2_20261024':
            raise RuntimeError('Scoped revisions require their uniquely owned database')
        self.atomic=transaction.atomic();self.atomic.__enter__();self.addCleanup(self.rollback)

    def rollback(self):
        from django.db import transaction
        transaction.set_rollback(True);self.atomic.__exit__(None,None,None)

    def owner(self):
        from mta.runtime.test_mdm_force_capture import ForceCaptureTests
        from mta.runtime.models import CalculationRun
        from mta.runtime.input_storage import save_input
        from mta.runtime.production_daily import input_table
        from mta.mdm.daily_input import bind_capture
        from mta.application.native_output_contracts import native_assignments
        from mta.serialization import digest
        from tests.test_phase_state import native_prepared
        fixture=ForceCaptureTests();fixture.setUp();self.source=fixture.source
        snapshot=fixture.snapshot();identity=uuid.uuid4()
        with native_assignments(True):self.prepared,self.opening,refs=native_prepared(str(identity))
        raw=dict(profile=refs['profile'],day=refs['day'],mdm_input=snapshot,
            opening=dict(identity='scope-revision-METADATA-FIXTURE',opening_date='2037-04-09',state=refs['prior']))
        self.run=CalculationRun.objects.create(id=identity,kind='DAILY_CHAIN',business_date='2037-04-10',
            execution_revision='scope-revision-'+identity.hex,input_digest=digest(raw),input_payload={})
        self.run.input_payload=save_input(self.run,raw,table_selector=input_table)
        self.run.input_manifest_digest=digest(self.run.input_payload)
        self.run.save(update_fields=['input_payload','input_manifest_digest'])
        self.capture=bind_capture(self.run,snapshot,request_digest='d'*64)
        self.initial,self.state,self.cert,self.base,self.original=bind_metadata_counter_owner(self.run,self.source)

    def claim(self,**changes):
        from mta.runtime.scope_execution import _claim
        values=dict(scope='UptoDBM',command_key='metadata-revision-proof',
            worker_reference='rolled-back-counter-fixture',compatibility_digest='a'*64,
            expected_phase='START',expected_receipt_digest='')
        values.update(changes)
        return _claim(self.run.pk,**values)

    def deny_sql(self,sql,arguments=()):
        from django.db import DatabaseError,connection,transaction
        with self.assertRaises(DatabaseError),transaction.atomic():
            with connection.cursor() as cursor:cursor.execute(sql,arguments)

    def test_claim_owns_only_its_exact_append_and_full_guard_remains_strict(self):
        from mta.runtime.capture_preparation import require_commit
        from mta.runtime.scope_revisions import require_current,next_cut
        from mta.runtime.scope_execution import require_claim
        self.owner();self.assertEqual(require_commit(self.run),self.original)
        attempt=self.claim()
        self.assertEqual(attempt.revision_before,self.original['capture_cut'])
        self.assertEqual(attempt.revision_after,next_cut(attempt.revision_before))
        self.assertEqual(require_current(self.run),attempt.revision_after)
        self.assertEqual(require_claim(attempt.pk,attempt.worker_token,compatibility_digest='a'*64)[0].pk,attempt.pk)
        with self.assertRaisesRegex(ValueError,'changed during calculation'):require_commit(self.run)
        self.run.refresh_from_db();self.assertEqual(self.run.production_manifest['ingestion_preparation'],self.original)

    def test_phase_seal_carries_its_actual_writes_and_retry_preserves_the_accepted_cut(self):
        from mta.application.native_output_contracts import native_assignments
        from mta.runtime import phase_state
        from mta.runtime.scope_execution import _setting,_begin_phase,_seal_phase,_close_attempt,require_claim
        from mta.runtime.scope_revisions import require_current,next_cut
        from mta.serialization import digest
        self.owner();attempt=self.claim()
        with _setting('fresh.scope_worker',attempt.worker_token),native_assignments(True):
            receipt=_begin_phase(attempt,self.run,'PRE_BPR')
            image=phase_state.save(self.run,self.prepared,None,acceptance=receipt)
            _seal_phase(receipt,image,effect_digest=digest({'fixture':'NO_BUSINESS_EFFECTS'}),partitions=[])
            self.assertEqual(receipt.revision_before,attempt.revision_after)
            self.assertGreater(receipt.metadata['revision_after'][3],receipt.revision_before[3]+1)
            self.assertEqual(require_current(self.run),receipt.metadata['revision_after'])
            _close_attempt(attempt,self.run,'FAILED',{'type':'EXPLICIT_METADATA_FAILURE'})
        self.assertEqual(attempt.revision_closed,next_cut(receipt.metadata['revision_after']))
        retry=self.claim(recovery_of=attempt.pk,expected_phase='PRE_BPR',expected_receipt_digest=receipt.digest)
        self.assertEqual(retry.revision_before,attempt.revision_closed)
        self.assertNotEqual(retry.worker_token,attempt.worker_token)
        require_claim(retry.pk,retry.worker_token,compatibility_digest='a'*64)
        self.run.refresh_from_db();self.assertEqual(self.run.status,'RUNNING')

    def test_interrupted_phase_rolls_its_counter_writes_back_before_recovery(self):
        from django.db import transaction
        from mta.application.native_output_contracts import native_assignments
        from mta.runtime import phase_state
        from mta.runtime.scope_execution import _setting,_begin_phase,_close_attempt
        from mta.runtime.scope_revisions import require_current
        self.owner();attempt=self.claim()
        with self.assertRaisesRegex(RuntimeError,'interrupted phase'),transaction.atomic(), \
                _setting('fresh.scope_worker',attempt.worker_token),native_assignments(True):
            receipt=_begin_phase(attempt,self.run,'PRE_BPR')
            phase_state.save(self.run,self.prepared,None,acceptance=receipt)
            raise RuntimeError('interrupted phase')
        self.assertEqual(require_current(self.run),attempt.revision_after)
        with _setting('fresh.scope_fence',attempt.pk):
            _close_attempt(attempt,self.run,'FAILED',{'type':'FENCED_METADATA_WORKER'})
        retry=self.claim(recovery_of=attempt.pk)
        self.assertEqual(require_current(self.run),retry.revision_after)

    def test_every_external_revision_domain_is_denied(self):
        from django.db import transaction
        from django.db.models import F
        from mta.runtime.accepted_daily import EPOCHS
        from mta.runtime.scope_revisions import require_current
        from mta.runtime.scope_execution import require_claim
        self.owner();attempt=self.claim()
        for field in EPOCHS:
            with self.subTest(domain=field),transaction.atomic():
                type(self.state).objects.filter(pk=self.state.pk).update(**{field:F(field)+1})
                with self.assertRaisesRegex(ValueError,'revision changed'):
                    require_claim(attempt.pk,attempt.worker_token,compatibility_digest='a'*64)
                transaction.set_rollback(True)
        self.assertEqual(require_current(self.run),attempt.revision_after)

    def test_real_late_queue_write_cannot_be_adopted_by_fencing_or_retry(self):
        from mta.mdm.supplier_revisions import source_lock
        from mta.runtime.mdm_force_models import MdmForceQueue
        from mta.runtime.scope_execution import _setting,_close_attempt,require_claim
        from mta.runtime.scope_revisions import positions,next_cut
        self.owner();attempt=self.claim()
        with source_lock(self.source.pk,deciding=True):
            MdmForceQueue.objects.create(source=self.source,SKUCode='LATE',WhCode='LATE',NewNorm=0,Approved=True)
        expected,observed=positions(self.run)
        self.assertNotEqual(expected,observed)
        with self.assertRaisesRegex(ValueError,'revision changed'):
            require_claim(attempt.pk,attempt.worker_token,compatibility_digest='a'*64)
        with _setting('fresh.scope_fence',attempt.pk):
            _close_attempt(attempt,self.run,'FAILED',{'type':'FENCED'})
        self.assertEqual(attempt.failure['revision_conflict'],dict(expected=expected,observed=observed))
        self.assertEqual(attempt.revision_closed,next_cut(expected))
        self.assertNotEqual(attempt.revision_closed,next_cut(observed))
        with self.assertRaisesRegex(ValueError,'revision changed'):self.claim(recovery_of=attempt.pk)

    def test_direct_header_edits_and_false_counter_claims_are_denied(self):
        from mta.runtime.scope_execution import _setting
        self.owner();attempt=self.claim()
        with _setting('fresh.scope_worker',attempt.worker_token):
            self.deny_sql("UPDATE mta.fresh_mta_runscopeattempt SET status='FAILED',failure=%s,finished_at=now() WHERE id=%s",
                ['{"type":"MISSING_CUT"}',attempt.pk])
            self.deny_sql('UPDATE mta.fresh_mta_runscopeattempt SET revision_after=%s WHERE id=%s',
                ['[0,0,0,99999,0]',attempt.pk])
            self.deny_sql("UPDATE mta.fresh_mta_calculationrun SET production_manifest='{}' WHERE id=%s",[self.run.pk])

    def test_invalidated_certificate_can_retire_worker_without_readmitting_business(self):
        from mta.runtime.scope_execution import _setting,_close_attempt,require_claim
        from mta.runtime.scope_revisions import positions
        self.owner();attempt=self.claim()
        self.cert.status='INVALIDATED';self.cert.save(update_fields=['status'])
        with self.assertRaisesRegex(ValueError,'invalidated'):
            require_claim(attempt.pk,attempt.worker_token,compatibility_digest='a'*64)
        with _setting('fresh.scope_fence',attempt.pk):
            _close_attempt(attempt,self.run,'FAILED',{'type':'EXPLICIT_REVOKED_WORKER_FENCE'})
        self.assertEqual(attempt.failure['certification_status'],'INVALIDATED')
        self.assertEqual(attempt.revision_closed,attempt.revision_after)
        self.assertEqual(positions(self.run,retained=True),(attempt.revision_closed,attempt.revision_closed))
        with self.assertRaisesRegex(ValueError,'invalidated'):self.claim(recovery_of=attempt.pk)

    def test_invalidated_failure_preserves_an_existing_foreign_revision_conflict(self):
        from django.db.models import F
        from mta.runtime.scope_execution import _setting,_close_attempt
        from mta.runtime.scope_revisions import positions
        self.owner();attempt=self.claim()
        type(self.state).objects.filter(pk=self.state.pk).update(action_epoch=F('action_epoch')+1)
        expected,observed=positions(self.run)
        self.cert.status='INVALIDATED';self.cert.save(update_fields=['status'])
        with _setting('fresh.scope_worker',attempt.worker_token):
            _close_attempt(attempt,self.run,'FAILED',{'type':'REVOKED_WITH_FOREIGN_CHANGE'})
        self.assertEqual(attempt.failure['revision_conflict'],dict(expected=expected,observed=observed))
        self.assertEqual(attempt.failure['certification_status'],'INVALIDATED')
        self.assertEqual(attempt.revision_closed,expected)
        self.assertEqual(positions(self.run,retained=True),(expected,observed))

    def test_revision_cut_scalar_types_do_not_follow_jsonb_numeric_coercion(self):
        import json
        from django.db import connection,DatabaseError,transaction
        from mta.runtime.scope_execution import _setting
        from mta.runtime.scope_revisions import next_cut
        invalid=(None,False,{},0,[],[0]*4,[0,0,0,0,True],[0,0,0,0,'0'],
                 [0,0,0,0,0.0],[0,0,0,-1,0],[0,0,0,0,9223372036854775808])
        with connection.cursor() as cursor:
            for value in invalid:
                cursor.execute('SELECT mta.valid_scope_cut(%s::jsonb)',[json.dumps(value)])
                self.assertIs(cursor.fetchone()[0],False)
            cursor.execute('SELECT mta.valid_scope_cut(%s::jsonb)',[json.dumps([0,0,0,0,0])])
            self.assertIs(cursor.fetchone()[0],True)
        for value in invalid[1:]:
            with self.assertRaises(ValueError):next_cut(value)
        self.owner()
        from mta.runtime.models import RunScopeAttempt
        from mta.runtime.scope_revisions import next_cut
        before=list(self.original['capture_cut']);after=next_cut(before)
        before[3]=float(before[3]);after[3]=float(after[3])
        with self.assertRaisesRegex(DatabaseError,'exact integer revision cut'),transaction.atomic():
            RunScopeAttempt.objects.create(run=self.run,scope='UptoDBM',command_key='bad-numeric-type',
                attempt_no=1,worker_reference='metadata-type-denial',expected_phase='START',
                expected_receipt_digest='',input_digest=self.run.input_digest,
                input_manifest_digest=self.run.input_manifest_digest,compatibility_digest='a'*64,
                revision_before=before,revision_after=after)
        attempt=self.claim()
        coerced=list(attempt.revision_after);coerced[3]=float(coerced[3])
        with _setting('fresh.scope_worker',attempt.worker_token), \
                self.assertRaisesRegex(DatabaseError,'exact integer revision cut'),transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute('UPDATE mta.fresh_mta_runscopeattempt SET revision_after=%s::jsonb WHERE id=%s',
                               [json.dumps(coerced),attempt.pk])

    def test_revision_identity_reads_only_the_required_authority_headers(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        from mta.runtime.scope_revisions import identity
        self.owner();self.claim()
        with CaptureQueriesContext(connection) as queries:
            self.assertEqual(identity(self.run),self.original)
        self.assertLessEqual(len(queries),4)
        for query in queries.captured_queries:
            for column in ('"input_payload"','"populations"','"partitions"','"receipt"'):
                self.assertNotIn(column,query['sql'])
