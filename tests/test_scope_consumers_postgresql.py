"""Actual consumer/counter SQL over rollback-only component captures.

No native registration, selected-view admission or concurrency acceptance is
implied by the metadata carrier or the adapted Full selection in these tests.
"""
from copy import deepcopy
from datetime import datetime,timezone
import json
import os
import unittest
from unittest.mock import patch
from tests import test_scoped_remarks_postgresql as fixtures


@unittest.skipUnless(os.environ.get('VF_PHASE_POSTGRES_PROOF')=='1','Owned PostgreSQL required')
class ScopeConsumerTests(unittest.TestCase):
    for _name in ('setUp','rollback','owner','accept','bpr','parents','binding','row'):
        locals()[_name]=fixtures.ScopedRemarkTests.__dict__[_name]

    def raw(self):
        from mta.runtime.accepted_daily import epochs
        return epochs(self.run.production_manifest['ingestion_preparation']['initialization_id'])

    def counters(self):
        from mta.runtime.ingestion_models import IngestionRevisionState
        from mta.runtime.scope_consumers import FIELDS
        return list(IngestionRevisionState.objects.values_list(*FIELDS).get(
            pk=self.run.production_manifest['ingestion_preparation']['initialization_id']))

    def append(self,number=1,*,family=None):
        from mta.presentation import ancillary_live as live
        values=[{k:v for k,v in self.row('later-'+str(i),None).items() if k!='RemarkDate'} for i in range(number)]
        if family==live.BOR:
            for value in values:value['SupplierCode']='SUPPLIER'
        return live.append(family or live.BPR,values,actor_id='consumer',timestamp=datetime(2037,4,11,tzinfo=timezone.utc))

    def input_owner(self,*,opted_in,provenance=None):
        from mta.presentation import ancillary_live as live
        from mta.runtime.scope_revisions import require_current
        from tests.test_scope_revisions_postgresql import bind_metadata_counter_owner
        from mta.serialization import digest
        if provenance is None:provenance={'fixture':'scoped-remark-component-facts-no-native-certification'}
        live.initialize_owner(live.BPR,provenance_digest=digest(provenance),provenance_receipt=provenance)
        self.snapshot=live.snapshot_all(business_date='2037-04-10',bpr_remark_horizon=13)
        self.owner(claim=False)
        self.counter_owner=bind_metadata_counter_owner(self.run,self.source,
            consumer_snapshot=self.snapshot[live.BPR] if opted_in else None)
        require_current(self.run)

    def test_exact_multistatement_repeated_empty_and_rolled_back_deltas(self):
        from django.db import transaction
        from mta.runtime.ancillary_models import BprLiveRemark
        from mta.runtime.scope_revisions import require_current
        self.parents(counter=True,consumer_cut=True)
        bound=self.binding();expected=require_current(self.run);raw=self.raw();counters=self.counters()
        create=BprLiveRemark.objects.bulk_create
        with patch.object(BprLiveRemark.objects,'bulk_create',side_effect=lambda rows:create(rows,batch_size=2)):
            self.assertEqual(self.append(5),'5')
        self.assertEqual(self.raw(),[*raw[:3],raw[3]+1,raw[4]+3])
        self.assertEqual(self.counters(),[counters[0]+1,counters[1]+3])
        self.assertEqual(require_current(self.run),expected)
        self.assertEqual(bound.remarks.rows(),[])
        self.assertEqual(len(self.binding().remarks.rows()),5)
        raw=self.raw();counters=self.counters()
        self.assertEqual(self.append(0),'0')
        self.assertEqual((self.raw(),self.counters()),(raw,counters))
        with transaction.atomic():
            self.append(2)
            self.assertEqual(require_current(self.run),expected)
            transaction.set_rollback(True)
        self.assertEqual((self.raw(),self.counters()),(raw,counters))
        self.append(1)
        self.assertEqual(self.counters(),[counters[0]+1,counters[1]+1])
        self.assertEqual(require_current(self.run),expected)

    def test_original_full_and_no_policy_scope_keep_raw_conflicts(self):
        from mta.runtime.capture_preparation import require_commit
        from mta.runtime.scope_revisions import require_current
        self.input_owner(opted_in=False)
        self.assertNotIn('bpr_consumer_cut',require_commit(self.run))
        self.append()
        self.assertEqual(self.counters(),[1,1])
        with self.assertRaisesRegex(ValueError,'changed during calculation'):require_commit(self.run)
        with self.assertRaisesRegex(ValueError,'revision changed'):require_current(self.run)

    def test_capture_locks_only_declared_history_owners_in_snapshot_order(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        from mta.presentation import ancillary_live as live
        from mta.runtime.scope_consumers import lock_history_owners
        from mta.serialization import digest
        provenance={'fixture':'scope-owner-lock-order'}
        for family in (live.BPR,live.BOROA,live.BOR):
            live.initialize_owner(family,provenance_digest=digest(provenance),provenance_receipt=provenance)
        with CaptureQueriesContext(connection) as queries:
            actual=lock_history_owners()
        self.assertEqual(actual,tuple(sorted((live.BPR,live.BOR,live.BOROA))))
        self.assertEqual(len(queries),1)
        self.assertIn('ORDER BY',queries[0]['sql']);self.assertIn('FOR UPDATE',queries[0]['sql'])
        for name in ('provenance_receipt','next_ordinal','bprliveremark'):
            self.assertNotIn(name,queries[0]['sql'])

    def test_new_capture_pins_nonzero_baseline_without_resealing_the_old_owner(self):
        import uuid
        from mta.presentation import ancillary_live as live
        from mta.runtime.models import CalculationRun
        from mta.runtime.input_reader import read_input
        from mta.runtime.input_storage import save_input
        from mta.runtime.production_daily import input_table
        from mta.mdm.daily_input import bind_capture
        from mta.runtime.capture_preparation import seal
        from mta.runtime.scope_revisions import require_current
        from mta.serialization import digest
        self.input_owner(opted_in=True);old=self.run;original=deepcopy(old.production_manifest)
        self.append(2);self.assertEqual(self.counters(),[1,1])
        raw=read_input(old)
        raw['remark_inputs']=live.snapshot_all(business_date='2037-04-10',bpr_remark_horizon=13)
        identity=uuid.uuid4()
        fresh=CalculationRun.objects.create(id=identity,kind='DAILY_CHAIN',business_date=old.business_date,
            execution_revision='new-consumer-capture-'+identity.hex,input_digest=digest(raw),input_payload={})
        fresh.input_payload=save_input(fresh,raw,table_selector=input_table)
        fresh.input_manifest_digest=digest(fresh.input_payload)
        fresh.save(update_fields=['input_payload','input_manifest_digest'])
        bind_capture(fresh,raw['mdm_input'],request_digest='e'*64)
        live.bind_snapshots(fresh,raw['remark_inputs'])
        seed={k:v for k,v in original['ingestion_preparation'].items()
            if k not in ('capture_cut','bpr_consumer_cut','run_id','predecessor_id','receipt_digest')}
        fresh.production_manifest={'ingestion_preparation':seed}
        seal(fresh,consumer_snapshot=raw['remark_inputs'][live.BPR])
        policy=fresh.production_manifest['ingestion_preparation']['bpr_consumer_cut']
        self.assertEqual((policy['operational'],policy['action'],policy['watermark']),(1,1,2))
        expected=require_current(fresh)
        self.append()
        self.assertEqual(require_current(fresh),expected)
        old.refresh_from_db();self.assertEqual(old.production_manifest,original)

    def test_production_receipt_cannot_borrow_another_initialization(self):
        self.assertRaisesRegex(ValueError,'initialization or source',self.input_owner,opted_in=True,
            provenance=dict(schema='fresh-production-consumer-opening-v1',
                initialization_id='00000000-0000-0000-0000-000000000001',source_digest='0'*64))

    def test_mixed_family_owner_statement_is_not_a_bpr_consumer_advance(self):
        from django.db import connection
        from django.db.models import F
        from mta.presentation import ancillary_live as live
        from mta.runtime.ancillary_models import BprLiveRemark,BorLiveRemarkDaily,RemarkOwner
        from mta.runtime.scope_revisions import require_current
        from mta.serialization import digest
        provenance={'fixture':'mixed-BOR-owner'}
        live.initialize_owner(live.BOR,provenance_digest=digest(provenance),provenance_receipt=provenance)
        self.parents(counter=True,consumer_cut=True);raw=self.raw();before=self.counters()
        with connection.cursor() as cursor:cursor.execute("SELECT set_config('fresh.daily_remark_actor','mixed',true)")
        BprLiveRemark.objects.create(owner_id=live.BPR,ordinal=0,actor_id='mixed',
            **self.row('BPR',datetime(2037,4,11,tzinfo=timezone.utc)))
        BorLiveRemarkDaily.objects.create(owner_id=live.BOR,ordinal=0,actor_id='mixed',SupplierCode='SUPPLIER',
            **self.row('BOR',datetime(2037,4,11,tzinfo=timezone.utc)))
        RemarkOwner.objects.filter(pk__in=(live.BPR,live.BOR)).update(next_ordinal=F('next_ordinal')+1)
        self.assertEqual(self.raw(),[*raw[:3],raw[3]+1,raw[4]+2])
        self.assertEqual(self.counters(),[before[0],before[1]+1])
        with self.assertRaisesRegex(ValueError,'revision changed'):require_current(self.run)

    def test_unknown_bor_and_captured_state_changes_still_conflict(self):
        from django.db import transaction
        from mta.presentation import ancillary_live as live
        from mta.runtime.ancillary_models import BprCapturedRemark
        from mta.runtime.scope_revisions import positions,require_current
        from mta.serialization import digest
        for unknown in ('BOR','captured'):
            with self.subTest(unknown=unknown),transaction.atomic():
                provenance={'fixture':'unrelated-BOR-owner'}
                live.initialize_owner(live.BOR,provenance_digest=digest(provenance),provenance_receipt=provenance)
                self.parents(counter=True,consumer_cut=True);bound=self.binding()
                self.append()
                if unknown=='BOR':self.append(family=live.BOR)
                else:BprCapturedRemark.objects.create(capture_id=bound.remarks.capture_id,ordinal=0,
                    source_ordinal=0,**self.row('foreign captured insert',datetime(2037,4,11,tzinfo=timezone.utc)))
                expected,observed=positions(self.run)
                self.assertNotEqual(expected,observed)
                with self.assertRaisesRegex(ValueError,'revision changed'):require_current(self.run)
                transaction.set_rollback(True)

    def test_incomplete_journal_denies_until_the_guarded_owner_advance(self):
        from django.db import transaction,connection
        from mta.runtime.ancillary_models import BprLiveRemark,RemarkOwner
        from mta.presentation import ancillary_live as live
        from mta.runtime.scope_revisions import require_current
        self.parents(counter=True,consumer_cut=True);expected=require_current(self.run)
        owner=RemarkOwner.objects.get(pk=live.BPR)
        with connection.cursor() as cursor:cursor.execute("SELECT set_config('fresh.daily_remark_actor','direct',true)")
        BprLiveRemark.objects.create(owner=owner,ordinal=owner.next_ordinal,actor_id='direct',
            **self.row('unpaired',datetime(2037,4,11,tzinfo=timezone.utc)))
        with self.assertRaisesRegex(ValueError,'revision changed'):require_current(self.run)
        owner.next_ordinal+=1;owner.save(update_fields=['next_ordinal'])
        self.assertEqual(require_current(self.run),expected)

    def test_incomplete_append_can_be_fenced_and_completed_without_cut_adoption(self):
        from django.db import connection
        from mta.presentation import ancillary_live as live
        from mta.runtime.ancillary_models import BprLiveRemark,RemarkOwner
        from mta.runtime.scope_execution import _setting,_close_attempt,_claim
        from mta.runtime.scope_revisions import positions,require_current,next_cut
        self.parents(counter=True,consumer_cut=True);original=self.receipt.digest
        self.append()  # Previously complete deltas also stay unwaived during the conflict.
        owner=RemarkOwner.objects.get(pk=live.BPR)
        with connection.cursor() as cursor:cursor.execute("SELECT set_config('fresh.daily_remark_actor','direct',true)")
        BprLiveRemark.objects.create(owner=owner,ordinal=owner.next_ordinal,actor_id='direct',
            **self.row('unpaired',datetime(2037,4,11,tzinfo=timezone.utc)))
        expected,observed=positions(self.run)
        self.assertNotEqual(expected,observed)
        with _setting('fresh.scope_fence',self.attempt.pk):
            _close_attempt(self.attempt,self.run,'FAILED',{'type':'FENCED'})
        self.assertEqual(self.attempt.failure['revision_conflict'],dict(expected=expected,observed=observed))
        self.assertEqual(self.attempt.revision_closed,next_cut(expected))
        self.assertNotEqual(self.attempt.revision_closed,next_cut(observed))
        with self.assertRaisesRegex(ValueError,'revision changed'):require_current(self.run)
        owner.next_ordinal+=1;owner.save(update_fields=['next_ordinal'])
        self.assertEqual(require_current(self.run),self.attempt.revision_closed)
        retry=_claim(self.run.pk,scope=self.attempt.scope,command_key=self.attempt.command_key,
            worker_reference='exact-recovery',compatibility_digest='a'*64,expected_phase='BPR',
            expected_receipt_digest=self.receipt.digest,recovery_of=self.attempt.pk)
        self.assertNotEqual(retry.worker_token,self.attempt.worker_token)
        self.receipt.refresh_from_db();self.assertEqual(self.receipt.digest,original)

    def test_baseline_types_owner_counter_regression_and_guard_drift_are_denied(self):
        from django.db import transaction,connection,DatabaseError
        from mta.runtime.ingestion_models import IngestionRevisionState
        from mta.runtime.scope_consumers import verify_guards
        from mta.serialization import digest
        self.input_owner(opted_in=True)
        original=deepcopy(self.run.production_manifest)
        invalid=[None,{},False,dict(original['ingestion_preparation']['bpr_consumer_cut'],action=0.0),
            dict(original['ingestion_preparation']['bpr_consumer_cut'],operational=True),
            dict(original['ingestion_preparation']['bpr_consumer_cut'],watermark=-1),
            dict(original['ingestion_preparation']['bpr_consumer_cut'],capture_id=9223372036854775808),
            dict(original['ingestion_preparation']['bpr_consumer_cut'],action=1),
            dict(original['ingestion_preparation']['bpr_consumer_cut'],provenance_digest='0'*64)]
        for value in invalid:
            with self.subTest(value=value),transaction.atomic():
                manifest=deepcopy(original);body=manifest['ingestion_preparation'];body['bpr_consumer_cut']=value
                body['receipt_digest']=digest({k:v for k,v in body.items() if k!='receipt_digest'})
                self.run.production_manifest=manifest;self.run.save(update_fields=['production_manifest'])
                with self.assertRaises(DatabaseError),transaction.atomic():
                    with connection.cursor() as cursor:
                        cursor.execute('SELECT mta.scope_native_cut(%s)',[self.run.pk])
                transaction.set_rollback(True)
        self.run.refresh_from_db();self.append()
        initial=self.run.production_manifest['ingestion_preparation']['initialization_id']
        with self.assertRaisesRegex(DatabaseError,'cannot regress'),transaction.atomic():
            IngestionRevisionState.objects.filter(pk=initial).update(bpr_remark_action_epoch=0)
        with self.assertRaises(DatabaseError),transaction.atomic():
            IngestionRevisionState.objects.filter(pk=initial).update(bpr_remark_action_epoch=999999)
        with connection.cursor() as cursor:cursor.execute('SET CONSTRAINTS ALL IMMEDIATE')
        with transaction.atomic():
            with connection.cursor() as cursor:cursor.execute('ALTER FUNCTION mta.scope_bpr_consumer_cut(uuid,jsonb) SECURITY DEFINER')
            with self.assertRaisesRegex(ValueError,'guard contract'):verify_guards()
            transaction.set_rollback(True)
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute('CREATE SCHEMA consumer_guard_substitution')
                cursor.execute('CREATE FUNCTION consumer_guard_substitution.ingestion_authority_guard() RETURNS trigger '
                    "LANGUAGE plpgsql AS $$ BEGIN RETURN NEW; END $$")
                cursor.execute('DROP TRIGGER ingestion_authority ON mta.fresh_mta_ingestionrevisionstate')
                cursor.execute('CREATE TRIGGER ingestion_authority BEFORE INSERT OR UPDATE OR DELETE '
                    'ON mta.fresh_mta_ingestionrevisionstate FOR EACH ROW '
                    'EXECUTE FUNCTION consumer_guard_substitution.ingestion_authority_guard()')
            with self.assertRaisesRegex(ValueError,'authority triggers'):verify_guards()
            transaction.set_rollback(True)
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute('ALTER TABLE mta.fresh_mta_ingestionrevisionstate DROP CONSTRAINT bpr_consumer_action_bounded')
            with self.assertRaisesRegex(ValueError,'counter constraints'):verify_guards()
            transaction.set_rollback(True)

    def continue_dbm(self):
        from mta.runtime.scope_execution import _setting,_close_attempt,_claim
        from mta.runtime.scoped_actions import calculate_dbm
        self.attempt.refresh_from_db();self.run.refresh_from_db()
        with _setting('fresh.scope_worker',self.attempt.worker_token):_close_attempt(self.attempt,self.run,'RELEASED',{})
        worker=_claim(self.run.pk,scope='PostBPR',command_key='consumer-post-bpr',worker_reference='component',
            compatibility_digest='a'*64,expected_phase='BPR',expected_receipt_digest=self.receipt.digest)
        return calculate_dbm(worker.pk,worker.worker_token,compatibility_digest='a'*64)

    def test_previous_actual_full_writer_and_post_bpr_preserve_exact_calculation(self):
        from django.db import transaction
        from django.test import override_settings
        from tests.test_scoped_common_final_postgresql import ScopedCommonFinalTests
        from mta.presentation import ancillary_live as live,bpr_remarks
        from mta.runtime.scope_revisions import require_current
        from mta.serialization import digest
        provenance={'fixture':'scoped-remark-component-facts-no-native-certification'}
        live.initialize_owner(live.BPR,provenance_digest=digest(provenance),provenance_receipt=provenance)
        snapshot=live.snapshot_all(business_date='2037-04-10',bpr_remark_horizon=13)
        previous=ScopedCommonFinalTests('test_post_bpr_matches_actual_full_without_phase_or_current_copy_replay')
        self.addCleanup(previous.doCleanups)
        previous.owner(claim=False,remark_inputs=snapshot)
        # The real Full owner normally ends its outer transaction. Restore its
        # transaction-local consumption setting inside this rollback fixture.
        from mta.runtime.scope_execution import _setting
        with _setting('fresh.mdm_consuming_run',''):full=previous.ordinary_full()
        self.assertEqual(full.status,'SUCCEEDED')
        self.parents(counter=True,consumer_cut=True);bound=self.binding();expected=require_current(self.run)
        from mta.runtime.scoped_final import _finish_accepted_day
        def deny_unqualified_publication(dbm):
            # This counter carrier deliberately has no certified native master
            # producer receipt. It qualifies continuation through DBM only;
            # publication must retain its independent producer check.
            from mta.runtime.scope_execution import head
            before=head(self.run.pk)
            with self.assertRaisesRegex(ValueError,'Native prepared producer result differs'):
                _finish_accepted_day(dbm.attempt_id,dbm.attempt.worker_token,compatibility_digest='a'*64)
            self.run.refresh_from_db()
            self.assertEqual(head(self.run.pk),before)
            self.assertEqual((self.run.status,self.run.output_digest),('RUNNING',''))
        with transaction.atomic():
            dbm=self.continue_dbm()
            reference=dbm.snapshot.state_digest
            deny_unqualified_publication(dbm)
            transaction.set_rollback(True)
        original=self.receipt.digest
        with override_settings(VF_MTA_DAILY_PUBLICATION=True),patch.object(bpr_remarks,'selected_run',return_value=full), \
                patch.object(bpr_remarks,'datetime',wraps=datetime) as clock:
            clock.now.return_value=datetime(2037,4,11,12,tzinfo=timezone.utc)
            self.assertEqual(bpr_remarks.append({'data':[dict(SKUCode='SUPPLIED-Z9',WhCode='OWN-WH8',Remark='after pause')]},
                {'id':'component-human','name':'Fixture user'}),'1')
        self.assertEqual(require_current(self.run),expected)
        self.assertEqual(bound.remarks.rows(),[])
        self.assertEqual(self.binding().remarks.rows()[0]['Remark'],'after pause')
        actual=self.continue_dbm()
        self.assertEqual(actual.snapshot.state_digest,reference)
        deny_unqualified_publication(actual)
        self.receipt.refresh_from_db();self.assertEqual(self.receipt.digest,original)
        full.refresh_from_db();self.assertEqual(full.status,'SUCCEEDED')
