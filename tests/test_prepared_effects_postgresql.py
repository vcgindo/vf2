"""Actual scoped effect/projection transactions on supplied component fixtures.

No legacy oracle, native initialization, scope/file readiness or serving claim.
Every fixture and receipt is rolled back in the uniquely owned G2 database.
"""
from copy import deepcopy
import os
import unittest
from unittest.mock import patch
import uuid

if os.environ.get('VF_PHASE_POSTGRES_PROOF') == '1':
    os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
    import django
    django.setup()


@unittest.skipUnless(os.environ.get('VF_PHASE_POSTGRES_PROOF') == '1',
                     'Explicit owned PostgreSQL proof required')
class PreparedEffectsPostgresTests(unittest.TestCase):
    def setUp(self):
        from django.db import connection,transaction
        if connection.settings_dict['NAME'] != 'VFTEST_Fresh_LifecycleG2_20261024':
            raise RuntimeError('Prepared effects require their uniquely owned test database')
        self.atomic=transaction.atomic();self.atomic.__enter__()
        self.addCleanup(self.rollback)

    def rollback(self):
        from django.db import transaction
        transaction.set_rollback(True);self.atomic.__exit__(None,None,None)

    def owner(self,*,claim=True,operational=False,report_mode=None,predecessor=None,pick_root=None,
              scope_request=None,predecessor_input=False):
        from django.db import connection
        from mta.serialization import digest,storage
        from mta.mdm.daily_source import SCHEMA,APPROVAL_DAY_ARTIFACT_SHA
        from mta.mdm.master_owners import owner_batches
        from mta.mdm.daily_current import _write_partition
        from mta.mdm.daily_input import (install_pair_exclusions,select_capture,
            compose_pair_exclusions,capture_prune_candidates,compose,nms_master_raw,bind_capture)
        from mta.mdm.force_source import OWNER_SCHEMA,ARTIFACT_SHA,TRIAL_OVERRIDE,HIERARCHY_SUPPLEMENT,configuration_sha
        from mta.mdm.source import DLL
        from mta.mdm.supplier_revisions import source_lock
        from mta.mdm.supplier_capture import complete_feeds
        from mta.mdm.integration_source import replace_working_inputs
        from mta.runtime.mdm_models import (MdmSource,MdmFamilySource,MdmSkuApproved,MdmTask,MdmSubTask,MdmSkuHistory)
        from mta.runtime.mdm_force_models import MdmForceOwner,MdmForceQueue
        from mta.runtime.models import CalculationRun
        from mta.runtime.input_storage import save_input
        from mta.runtime.production_daily import input_table
        from mta.runtime.scope_execution import _claim
        from mta.application.native_output_contracts import native_assignments
        from mta.temporal.chain import prepare_day
        from tests.test_h3_daily_integration import frame
        from tests.production_h3_fixture import supplied_day,CHILD
        from tests.test_daily_calculation_phases import calculation
        from datetime import date,timedelta
        opening=frame();prior=deepcopy(opening['opening']['state'])
        opening_date='2037-04-09';today='2037-04-10'
        if predecessor is not None:
            from mta.runtime.services import read_outputs
            prior=read_outputs(predecessor,include_reports=False)['ClosingState'][0]
            opening_date=predecessor.business_date.isoformat()
            today=(predecessor.business_date+timedelta(days=1)).isoformat()
        if operational:
            from mta.application.operational_capture import CAPTURE_POLICY
            opening['profile']['operational_sources']=CAPTURE_POLICY
        self.source=MdmSource.objects.create(digest=uuid.uuid4().hex*2,
            database_name='owned-prepared-effect-COMPONENT',dll_digest=DLL,
            receipt=dict(schema=SCHEMA,artifact_sha256=APPROVAL_DAY_ARTIFACT_SHA,
                         fixture='supplied component guards; no registered artifact acceptance'))
        with connection.cursor() as cursor:
            cursor.execute("SELECT set_config('fresh.mdm_current_bootstrap',%s,true)",[str(self.source.pk)])
        for _family,model,partition,rows,path in owner_batches(prior):
            _write_partition(self.source,model,partition,rows,path)
        with connection.cursor() as cursor:
            cursor.execute("SELECT set_config('fresh.mdm_current_bootstrap','',true)")
        p=dict(schema=OWNER_SCHEMA,artifact_sha256=ARTIFACT_SHA,configuration_sha256=configuration_sha(),
            fixture_override=TRIAL_OVERRIDE,hierarchy_supplement=HIERARCHY_SUPPLEMENT,root_state_digest=digest(prior))
        self.force=MdmForceOwner.objects.create(source=self.source,provenance=p,receipt_digest=digest(p),
            root_state_digest=digest(prior),opening_digest=digest(prior['importer']['ForceNormChange']),
            closing_digest=digest(prior['importer']['ForceNormChange']),closing_log_digest=digest(prior['controls']['upload_log']))
        MdmFamilySource.objects.create(source=self.source,master_id=13,digest=digest(p),receipt=p)
        with source_lock(self.source.pk,deciding=True):
            self.force_row=MdmForceQueue.objects.create(source=self.source,SKUCode='SUPPLIED-Z9',
                WhCode=CHILD,NewNorm=18,Approved=True,RequestedBy='component')
        sku=prior['importer']['SkuAttributeData'][0]
        self.approved=MdmSkuApproved.objects.create(source=self.source,**sku,
            SKUDescription='Scoped component description',ActionType=1,Approved=True,Reverted=False)
        self.task=MdmTask.objects.create(source=self.source,TaskID='PREPARED-TASK',TaskStatus='1',MasterId='1',Actiontype=1)
        self.sub=MdmSubTask.objects.create(source=self.source,TaskID='PREPARED-TASK',ApproverId='2',TaskStatus='2')
        MdmSkuHistory.objects.create(source=self.source,TaskId='PREPARED-TASK',SKUCode=sku['SKUCode'],
            SKUDescription='Scoped component description',Status='3')
        install_pair_exclusions(self.source,[],provenance={'fixture':'explicit empty exclusions'})
        snapshot=select_capture(self.source,nms_active=True,task_status_log_horizon=7)
        snapshot=compose_pair_exclusions(snapshot,[])
        snapshot=capture_prune_candidates(snapshot,self.source,date.fromisoformat(today))
        day=supplied_day(today)['day']
        day.update(raw_master=compose(snapshot,nms_master_raw(prior),last_run_date=opening_date),
                   exclusions=[],supplier_feeds=complete_feeds(snapshot,prior))
        if report_mode is not None:
            if report_mode not in ('basic','expanded'):raise ValueError('Unknown component report mode')
            day['production_report_policy']=dict(bor_history_horizon=90,rrr_history_horizon=90)
            day['production_report_opening']=(None if predecessor is not None else
                dict(BOR_OrderAllocationHistory=[],RRR_OrderAllocationHistory=[]))
            if report_mode=='expanded':
                from mta.application import production_output_policy
                day['production_report_schema']=production_output_policy.SOURCE_SCHEMA
                day['production_report_policy']['output_contract']=production_output_policy.contract()
        replace_working_inputs(snapshot,prior,day,None)
        identity=uuid.uuid4()
        opening['profile']['daily_publication']=True
        raw=dict(profile=opening['profile'],lineage=dict(schema='supplied-component-lineage-v1'),opening=dict(identity='component-prepared',
            opening_date=opening_date,state=prior),day=day,mdm_input=snapshot)
        if predecessor_input:
            if predecessor is None:raise ValueError('Explicit component predecessor required')
            # Match the persisted-input representation of execute_day, without
            # claiming native registration or changing this supplied fixture.
            if predecessor.commands.exists():raise ValueError('This fixture requires its explicit empty action list')
            raw['opening']=None
            raw['lineage']=dict(run_id=str(predecessor.pk),output_digest=predecessor.output_digest,commands=[])
        if pick_root is not None:raw['pick_output_root']=str(pick_root)
        if scope_request is not None:raw['scope_request']=deepcopy(scope_request)
        self.run=CalculationRun.objects.create(id=identity,kind='DAILY_CHAIN',business_date=today,predecessor=predecessor,
            execution_revision='prepared-effects-'+identity.hex,input_digest=digest(raw),input_payload={})
        self.run.input_payload=save_input(self.run,raw,table_selector=input_table)
        self.run.input_manifest_digest=digest(self.run.input_payload)
        self.run.save(update_fields=['input_payload','input_manifest_digest'])
        self.capture=bind_capture(self.run,snapshot,request_digest='d'*64)
        if operational:
            from mta.runtime.operational_source import authorize_new_run
            authorize_new_run(self.run)
        with native_assignments(True):
            self.prepared=prepare_day(prior,opening_date,day,opening['profile'],str(identity),calculation,native_daily=True)
        if claim:
            self.attempt=_claim(self.run.pk,scope='UptoBPR',command_key='prepared-effects',
                worker_reference='rolled-back-component-proof',compatibility_digest='a'*64,
                expected_phase='START',expected_receipt_digest='')
        self.nonimporter={model.__name__+str(partition):storage(list(model.objects.filter(
            source=self.source,**partition).order_by('ordinal').values()))
            for _family,model,partition,_rows,_path in owner_batches(prior)
            if partition.get('owner','Importer') != 'Importer'}

    def accept(self):
        from mta.runtime.prepared_effects import _accept_prepared
        return _accept_prepared(self.attempt.pk,self.attempt.worker_token,self.prepared,compatibility_digest='a'*64)

    def test_actual_effects_and_importer_projection_seal_without_day_completion(self):
        from mta.runtime.mdm_models import MdmSkuApproved,MdmSkuDescription
        from mta.runtime.mdm_daily_models import MdmDailySkuArchive
        from mta.runtime.prepared_effects import prepared_family_owner
        from mta.mdm.force_capture import capture
        from mta.mdm.daily_input import select_capture
        from mta.mdm.master_owners import owner_batches
        from mta.serialization import storage
        self.owner();receipt=self.accept()
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute('SET CONSTRAINTS phase_acceptance_complete IMMEDIATE')
            cursor.execute('SET CONSTRAINTS phase_acceptance_complete DEFERRED')
        self.assertFalse(MdmSkuApproved.objects.filter(pk=self.approved.pk).exists())
        self.assertEqual(MdmDailySkuArchive.objects.filter(source=self.source).count(),1)
        self.sub.refresh_from_db();self.assertEqual(self.sub.TaskStatus,'4')
        self.assertTrue(MdmSkuDescription.objects.filter(source=self.source,owner='Importer',
            SKUDescription='Scoped component description').exists())
        for _family,model,partition,_rows,_path in owner_batches(self.prepared.context.prior):
            if partition.get('owner','Importer') != 'Importer':
                self.assertEqual(storage(list(model.objects.filter(source=self.source,**partition)
                    .order_by('ordinal').values())),self.nonimporter[model.__name__+str(partition)])
        self.force.refresh_from_db();self.capture.refresh_from_db();self.run.refresh_from_db()
        self.assertEqual(self.force.last_run_id,self.run.pk)
        self.assertEqual(prepared_family_owner(self.source,self.force,'force').pk,receipt.pk)
        self.assertEqual(capture(self.source)['anchor']['phase_acceptance_digest'],receipt.digest)
        self.assertEqual((self.run.status,self.capture.status),('RUNNING','CAPTURED'))
        self.assertIsNone(self.capture.consumed_at)
        self.assertFalse(self.run.output_digest);self.assertFalse(self.run.checkpoints.exists())
        with self.assertRaisesRegex(ValueError,'unaccepted producer'):self.accept()
        with self.assertRaisesRegex(ValueError,'unconsumed daily capture'):
            select_capture(self.source,nms_active=True,task_status_log_horizon=7)
        from mta.mdm.master_owners import importer_batches,business_fields
        for _family,model,partition,rows,_path in importer_batches(self.prepared.importer,self.prepared.nms['NMSAllItems']):
            self.assertEqual(storage(list(model.objects.filter(source=self.source,**partition)
                .order_by('ordinal').values(*[f.name for f in business_fields(model)]))),storage(rows))

    def test_late_snapshot_failure_rolls_back_effects_and_current_rows_before_retry(self):
        from mta.runtime.mdm_models import MdmSkuApproved,MdmSkuDescription
        from mta.runtime.mdm_daily_models import MdmDailySkuArchive
        from mta.runtime.models import RunPhaseAcceptance
        self.owner()
        def fail(*args,**kwargs):
            self.assertFalse(MdmSkuApproved.objects.filter(pk=self.approved.pk).exists())
            self.sub.refresh_from_db();self.assertEqual(self.sub.TaskStatus,'4')
            self.assertTrue(MdmSkuDescription.objects.filter(source=self.source,owner='Importer',
                SKUDescription='Scoped component description').exists())
            raise ValueError('injected after real prepared effects/projection')
        with patch('mta.runtime.prepared_effects.phase_state.save',side_effect=fail), \
                self.assertRaisesRegex(ValueError,'injected after real'):
            self.accept()
        self.assertTrue(MdmSkuApproved.objects.filter(pk=self.approved.pk).exists())
        self.assertFalse(MdmDailySkuArchive.objects.filter(source=self.source).exists())
        self.assertFalse(MdmSkuDescription.objects.filter(source=self.source,owner='Importer',
            SKUDescription='Scoped component description').exists())
        self.assertFalse(RunPhaseAcceptance.objects.filter(run=self.run).exists())
        self.sub.refresh_from_db();self.force.refresh_from_db()
        self.assertEqual(self.sub.TaskStatus,'2');self.assertIsNone(self.force.last_run_id)
        self.accept()
        self.assertEqual(MdmDailySkuArchive.objects.filter(source=self.source).count(),1)

    def test_pending_unit_and_worker_are_required_and_copies_stay_protected(self):
        from django.db import connection,DatabaseError,transaction
        from mta.runtime.scope_execution import _setting,_begin_phase
        self.owner()
        def denied(sql,arguments=()):
            with self.assertRaises(DatabaseError),transaction.atomic():
                with connection.cursor() as cursor:cursor.execute(sql,arguments)
        with _setting('fresh.scope_worker',self.attempt.worker_token), \
                _setting('fresh.mdm_consuming_run',self.run.pk):
            denied("UPDATE mta.fresh_mta_mdmtask SET \"TaskStatus\"='7' WHERE id=%s",[self.task.pk])
            with transaction.atomic():
                _begin_phase(self.attempt,self.run,'PRE_BPR')
                with _setting('fresh.mdm_current_run',self.run.pk):
                    denied("UPDATE mta.fresh_mta_mdmskudescription SET \"SKUDescription\"='unproduced' "
                           "WHERE source_id=%s AND owner='BPR'",[self.source.pk])
                with _setting('fresh.scope_worker',uuid.uuid4()):
                    denied("UPDATE mta.fresh_mta_mdmtask SET \"TaskStatus\"='7' WHERE id=%s",[self.task.pk])
                transaction.set_rollback(True)
        denied('UPDATE mta.fresh_mta_mdmdailyinputcapture SET nms_active=false WHERE run_id=%s',[self.run.pk])
        denied('INSERT INTO mta.fresh_mta_mdmdailypairexclusion(capture_id,ordinal) VALUES (%s,1)',[self.run.pk])
        denied('TRUNCATE mta.fresh_mta_mdmdailyinputtask')
        from copy import copy
        from mta.runtime.prepared_effects import _accept_prepared
        certified_shape=copy(self.run)
        certified_shape.production_manifest={'ingestion_preparation':{'fixture':'UNQUALIFIED-ENTRY-DENIAL'}}
        with patch('mta.runtime.prepared_effects.require_claim',return_value=(self.attempt,certified_shape)), \
                self.assertRaisesRegex(ValueError,'qualified phase revision cut'):
            _accept_prepared(self.attempt.pk,self.attempt.worker_token,self.prepared,compatibility_digest='a'*64)

    def test_accepted_effects_survive_worker_failure_and_fenced_recovery_without_replay(self):
        from django.utils import timezone
        from mta.runtime.scope_execution import _setting,_claim,require_claim
        from mta.runtime.prepared_effects import prepared_family_owner
        from mta.runtime.mdm_daily_models import MdmDailySkuArchive
        self.owner();receipt=self.accept()
        with _setting('fresh.scope_worker',self.attempt.worker_token):
            self.attempt.status='FAILED';self.attempt.failure=dict(type='EXPLICIT_COMPONENT_FAILURE')
            self.attempt.finished_at=timezone.now()
            self.attempt.save(update_fields=['status','failure','finished_at'])
        self.force.refresh_from_db()
        self.assertEqual(prepared_family_owner(self.source,self.force,'force').pk,receipt.pk)
        retry=_claim(self.run.pk,scope='UptoBPR',command_key='prepared-effects',
            worker_reference='recovery-component',compatibility_digest='a'*64,
            expected_phase='PRE_BPR',expected_receipt_digest=receipt.digest,recovery_of=self.attempt.pk)
        with self.assertRaisesRegex(ValueError,'Stale'):
            require_claim(self.attempt.pk,self.attempt.worker_token,compatibility_digest='a'*64)
        self.assertEqual(require_claim(retry.pk,retry.worker_token,compatibility_digest='a'*64)[0].pk,retry.pk)
        self.assertEqual(MdmDailySkuArchive.objects.filter(source=self.source).count(),1)
        self.run.refresh_from_db();self.capture.refresh_from_db()
        self.assertEqual((self.run.status,self.capture.status),('RUNNING','CAPTURED'))

    def test_actual_accepted_prepared_restore_keeps_complete_full_calculation_and_closing(self):
        from mta.application.native_output_contracts import native_assignments
        from mta.application.daily_finalization import mark,finish,ACTIVE_POLICY
        from mta.runtime import phase_state
        from mta.runtime.relational_state import production_projection
        from mta.serialization import storage
        from mta.temporal import chain
        from tests.test_daily_calculation_phases import calculation
        self.owner()
        with native_assignments(True):
            full=chain.produce_btr(chain.produce_dbm(chain.produce_bpr(deepcopy(self.prepared))))
            receipt=self.accept()
            context=self.prepared.context
            restored,_=phase_state.read(receipt.snapshot,prior=context.prior,day=context.day,
                profile=context.profile,master_snapshot=context.master_snapshot,execute_calculation=calculation)
            with patch('mta.temporal.entry_preparation.prepare',side_effect=AssertionError('intake replay')):
                split=chain.produce_btr(chain.produce_dbm(chain.produce_bpr(restored)))
        # These are the unchanged normal Full finisher's actual remaining flag
        # and settings functions, not substitute successful-day publication.
        for output in (full,split):
            closing=output['ClosingState'][0]
            mark(closing['complete'],'NMSTaskStatusUpdate.sql','NMSImportData.sql',
                 'NMSArchiveInputData.sql','NMSClearInputTables.sql')
            closing['importer_settings']=finish(closing['complete'],closing['importer_settings'],
                                               '2037-04-10',policy=ACTIVE_POLICY)
        self.assertEqual(storage(full['CalculationOutputs']),storage(split['CalculationOutputs']))
        self.assertEqual(storage(production_projection(full)),storage(production_projection(split)))

    def counter_claim(self):
        from tests.test_scope_revisions_postgresql import bind_metadata_counter_owner
        from mta.runtime.scope_execution import _claim
        self.owner(claim=False)
        self.counter_carrier=bind_metadata_counter_owner(self.run,self.source)
        self.attempt=_claim(self.run.pk,scope='UptoBPR',command_key='prepared-effects',
            worker_reference='actual-effects-METADATA-COUNTER-CARRIER',compatibility_digest='a'*64,
            expected_phase='START',expected_receipt_digest='')

    def test_counter_carrier_tracks_actual_effects_in_all_domains_and_preserves_retry(self):
        """Real effect/counter coupling; the carrier is not native admission."""
        from mta.runtime.scope_revisions import require_current
        from mta.runtime.scope_execution import _setting,_close_attempt,_claim
        from mta.runtime.prepared_effects import prepared_family_owner
        from mta.runtime.mdm_daily_models import MdmDailySkuArchive
        self.counter_claim();before=self.attempt.revision_after
        receipt=self.accept();after=receipt.metadata['revision_after']
        self.assertTrue(all(a>b for a,b in zip(after,before)))
        self.assertEqual(require_current(self.run),after)
        self.assertEqual(receipt.revision_before,before)
        with _setting('fresh.scope_worker',self.attempt.worker_token):
            _close_attempt(self.attempt,self.run,'FAILED',{'type':'EXPLICIT_EFFECT_WORKER_FAILURE'})
        retry=_claim(self.run.pk,scope='UptoBPR',command_key='prepared-effects',
            worker_reference='after-accepted-effects',compatibility_digest='a'*64,
            expected_phase='PRE_BPR',expected_receipt_digest=receipt.digest,recovery_of=self.attempt.pk)
        self.assertEqual(require_current(self.run),retry.revision_after)
        self.force.refresh_from_db()
        self.assertEqual(prepared_family_owner(self.source,self.force,'force').pk,receipt.pk)
        self.assertEqual(MdmDailySkuArchive.objects.filter(source=self.source).count(),1)
        self.run.refresh_from_db();self.capture.refresh_from_db()
        self.assertEqual(self.run.production_manifest['ingestion_preparation'],self.counter_carrier[-1])
        self.assertEqual((self.run.status,self.capture.status),('RUNNING','CAPTURED'))

    def test_actual_effect_failure_rolls_counters_back_with_rows_before_retry(self):
        from mta.runtime.scope_revisions import require_current
        from mta.runtime.mdm_daily_models import MdmDailySkuArchive
        self.counter_claim();before=self.attempt.revision_after
        with patch('mta.runtime.prepared_effects.phase_state.save',side_effect=ValueError('counter-coupled late failure')), \
                self.assertRaisesRegex(ValueError,'counter-coupled late failure'):
            self.accept()
        self.assertEqual(require_current(self.run),before)
        self.assertFalse(MdmDailySkuArchive.objects.filter(source=self.source).exists())
        receipt=self.accept()
        self.assertEqual(require_current(self.run),receipt.metadata['revision_after'])
        self.assertEqual(MdmDailySkuArchive.objects.filter(source=self.source).count(),1)
