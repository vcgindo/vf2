"""Focused ordinary certified CSV frozen-retry boundary; no live day."""
from contextlib import ExitStack, nullcontext
from copy import deepcopy
from datetime import date
import json
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
from types import SimpleNamespace as Obj
import os
import unittest
from unittest.mock import patch, Mock
import uuid

os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY','frozen-csv-retry-unit-only')
import django
django.setup()

from mta.runtime import production_daily, capture_preparation, daily_feed as service
from mta.serialization import digest
from mta.row_sequences import RecordRows


class FrozenCsvRetryTests(unittest.TestCase):
    def test_nonempty_allocation_preserves_rows_and_domain_checks_with_record_rows(self):
        from tests.test_production_order_allocation import inputs,daily,order,route,colour,master
        from mta.application.production_order_allocation import allocated_orders
        args=inputs(daily_consumption=[daily('C',stock=20)],spike_orders=[order()],
            route_original=[route(1,'C','C')],order_colours=[colour(1,'C','C')],
            dbm_master=[master('C')],sku_loc_attributes=[dict(SKUCode='A',LocCode='C',PackSize=1)])
        before=digest(args)
        expected=allocated_orders(**args)
        self.assertTrue(expected)
        streamed=dict(args,daily_consumption=RecordRows.from_rows(args['daily_consumption']),
            sku_loc_attributes=RecordRows.from_rows(args['sku_loc_attributes']))
        self.assertEqual(allocated_orders(**streamed),expected)
        self.assertEqual(allocated_orders(**streamed),expected)
        self.assertEqual(digest(args),before)
        self.assertEqual(digest(list(streamed['daily_consumption'])),digest(args['daily_consumption']))
        invalid=deepcopy(args['daily_consumption']);invalid[0]['Stock']='bad'
        with self.assertRaisesRegex(ValueError,'native SQL int'):
            allocated_orders(**dict(streamed,daily_consumption=RecordRows.from_rows(invalid)))
        with self.assertRaisesRegex(ValueError,'ordered row table'):
            allocated_orders(**dict(args,daily_consumption=iter(args['daily_consumption'])))

    def test_ordinary_retry_retains_capture_and_uses_fresh_certified_commit_metadata(self):
        owner=Obj(pk=uuid.uuid4(),source=Obj(digest='a'*64),configuration_digest='b'*64)
        parent=Obj(pk=uuid.uuid4(),output_digest='c'*64)
        frame=dict(profile={'import_non_nms':False},opening={})
        day=dict(business_date='2037-04-10',raw_non_nms=[])
        ready=Obj(initialization_id=str(owner.pk),source_digest=owner.source.digest,
            certification_digest='e'*64,master_revision_id=str(uuid.uuid4()),configuration_digest='b'*64)
        def reached(**kwargs):
            holder=kwargs.pop('_native_preparation')
            self.assertIsNone(kwargs.pop('day'));self.assertIsNone(kwargs.pop('profile'))
            kwargs.update(zip(holder.FIELDS,holder.take(kwargs['execution_revision'])))
            self.assertIs(kwargs['prepared_state'],ready)
            self.assertEqual(kwargs['mdm_retry'],'original-failed-capture')
            self.assertIsNone(kwargs['mdm_source'])
            self.assertIsNone(kwargs['scope_request'])
            return 'native-boundary'
        with ExitStack() as stack:
            for target,value in (
                ('release.native_identity.require_current',{}),
                ('mta.runtime.daily_preparation.prepare',b'raw'),
                ('mta.runtime.production_daily.inspect_execution',({},owner,parent,frame)),
                ('mta.runtime.production_preflight.require',None),
                ('mta.runtime.production_daily.decode',{'consumer_opening':None,'day':day}),
                ('mta.runtime.execution_settings.daily_frame',frame),
                ('mta.mdm.production_families.require_initialization',None),
                ('mta.runtime.production_daily._daily_initialization',frame),
                ('mta.runtime.production_daily.working_day',day),
                ('mta.mdm.location_transition.admit',None)):
                stack.enter_context(patch(target,return_value=value))
            query=stack.enter_context(patch('mta.runtime.models.ProductionInitialization.objects.select_related'))
            query.return_value.get.return_value=owner
            stack.enter_context(patch('mta.runtime.models.CalculationRun.objects.get',return_value=parent))
            stack.enter_context(patch('mta.runtime.ingestion_admission.preparation_source',return_value=ready))
            execute=stack.enter_context(patch('mta.runtime.temporal.execute_day',side_effect=reached))
            self.assertEqual(production_daily.execute(b'raw','d'*64,initialization_id=owner.pk,
                source_digest=owner.source.digest,configuration_digest=owner.configuration_digest,
                execution_revision='reviewed-retry',pick_output_root='/owned',predecessor_id=parent.pk,
                predecessor_output_digest=parent.output_digest,retry_capture_id='original-failed-capture'),
                'native-boundary')
            execute.assert_called_once()
        cut=[1,2,3,4,5]
        def save(**kwargs):cut[3]+=1
        run=Obj(pk=uuid.uuid4(),predecessor_id=parent.pk,save=save,
            production_manifest={'ingestion_preparation':capture_preparation.seed(ready,reused=False)},
            mdm_input_capture=Obj(source=owner.source))
        base=Obj(run_id=parent.pk,master_epoch=1,configuration_epoch=2)
        with patch.object(capture_preparation,'epochs',side_effect=lambda *a,**k:list(cut)), \
                patch('mta.runtime.occurrence_text_policy.admit',return_value={'owner':'separately-tested-policy'}), \
                patch('mta.runtime.ingestion_models.InitializationCertification.objects.get',
                    return_value=Obj(initialization_id=owner.pk,receipt_digest=ready.certification_digest)), \
                patch('mta.runtime.ingestion_models.MasterInputRevision.objects.get',return_value=base), \
                patch('mta.runtime.ingestion_models.IngestionRevisionState.objects.select_for_update') as states:
            states.return_value.get.return_value=Obj(master_epoch=1,configuration_epoch=2)
            capture_preparation.seal(run)
            commit=capture_preparation.require_commit(run)
            self.assertEqual(commit['capture_cut'],[1,2,3,5,5])
            capture_preparation.publication_metadata(run,commit,
                {'configuration_digest':owner.configuration_digest,'reused':False})
            self.assertEqual(run.production_manifest['master_preparation']['master_cut'],[1,2])
            self.assertIsNotNone(commit)  # Existing finish_run's master-revision acceptance hook is selected.

    def test_resume_preserves_failure_and_reuses_one_frozen_retry_without_calculation(self):
        with TemporaryDirectory() as td,ExitStack() as stack:
            root=Path(td);old_root=root/'failed';(old_root/'original').mkdir(parents=True)
            (old_root/'original'/'READY').write_bytes(b'')
            (old_root/'original'/'batch.json').write_bytes(b'{}')
            manifest=dict(schema='vectorflow-csv-snapshot-v1',files={p.name:service.file_identity(p)
                for p in (old_root/'original').iterdir()})
            manifest['digest']=digest(manifest)
            service.atomic_json(old_root/'original'/'snapshot.json',manifest)
            (old_root/'native-day.json').write_bytes(b'frozen-native-day')
            original_release={'manifest_sha256':'a'*64,'implementation_sha256':'original'}
            historical={'manifest_sha256':'b'*64,'implementation_sha256':'first-repair'}
            target={'manifest_sha256':'c'*64,'implementation_sha256':'next-repair'}
            source=Obj(pk=1,digest='d'*64,receipt={'owned_namespace':{'release_identity':original_release}})
            owner=Obj(pk=uuid.uuid4(),source=source,source_id=1)
            absent=Obj(exists=lambda:False)
            parent=Obj(pk=uuid.uuid4(),output_digest='e'*64,successors=Obj(filter=lambda **k:absent))
            canonical=digest(dict(initialization=str(owner.pk),date='2037-04-11',binding='binding',batch=manifest['digest']))
            common=dict(initialization=owner,initialization_id=owner.pk,business_date=date(2037,4,11),
                batch_id='batch',batch_digest=manifest['digest'],binding_digest='binding',
                input_sha256=service.file_identity(old_root/'native-day.json')['sha256'],
                predecessor_id=parent.pk,predecessor_output_digest=parent.output_digest)
            rejected=Obj(**common,attempt_id=uuid.uuid4(),request_key=canonical,status='REJECTED',phase='VALIDATE',error={})
            failure={'type':'ValueError','message':'DailyConsumption must be an ordered row table'}
            capture=Obj(source_id=1,status='CAPTURED',request_digest='f'*64,revision_digest='1'*64)
            run=Obj(pk=uuid.uuid4(),status='FAILED',kind='DAILY_CHAIN',evidence_mode='production',
                failure=failure,input_digest='2'*64,input_manifest_digest='3'*64,mdm_input_capture=capture,
                output_digest='',production_digest='',output_roster=[],checkpoints=absent,phase_snapshots=absent,
                scope_attempts=absent,commands=absent,successors=absent)
            origin=Obj(**common,pk=1,attempt_id=uuid.uuid4(),request_key=service._revalidation_key(rejected),
                status='FAILED',phase='VALIDATED',error=failure,run_id=run.pk,run=run,
                accepted_facts={'sealed':True},prepared_context={'sealed':True},archive_path=str(old_root),
                certification_id=None,master_revision_id=None)
            service.atomic_json(old_root/'revalidation.json',dict(contract='fresh-csv-revalidation-v1',
                origin_attempt=str(rejected.attempt_id),origin_digest=service._revalidation_origin_digest(rejected),
                canonical_request_key=canonical,replacement_attempt=str(origin.attempt_id),
                original_release=original_release,target_release=historical))
            frozen_before=service._revalidation_origin_digest(origin)
            attempts={canonical:rejected,origin.request_key:origin}
            class Query(list):
                def exists(self):return bool(self)
                def first(self):return self[0] if self else None
                def select_related(self,*a):return self
            def query(**kw):
                if 'request_key' in kw:
                    item=attempts.get(kw['request_key']);return Query([item] if item else [])
                return Query([rejected] if kw.get('status')=='REJECTED' else [])
            def create(**kw):
                retry=Obj(**kw,pk=2,initialization_id=owner.pk,predecessor_id=parent.pk,run_id=None,run=None,
                    accepted_facts={},prepared_context={},error={},save=lambda **k:None,refresh_from_db=lambda:None)
                attempts[retry.request_key]=retry
                return retry
            created=stack.enter_context(patch.object(service.DailyFeedAttempt.objects,'create',side_effect=create))
            stack.enter_context(patch.object(service.DailyFeedAttempt.objects,'filter',side_effect=query))
            binding=dict(_binding_digest='binding',initialization_id=str(owner.pk),source_digest=source.digest,
                configuration_digest='4'*64)
            stack.enter_context(patch.object(service,'binding_owner',return_value=(binding,owner)))
            stack.enter_context(patch.object(service,'job_lock',side_effect=lambda o:nullcontext(lambda:None)))
            stack.enter_context(patch.object(service,'batch_contract'))
            def snapshot(src,dst,input_root):
                shutil.copytree(old_root/'original',dst);return {'batch_id':'batch'},manifest
            stack.enter_context(patch.object(service,'snapshot',side_effect=snapshot))
            stack.enter_context(patch('release.native_identity.require_current',return_value=target))
            historical_admit=stack.enter_context(patch('mta.runtime.ingestion_admission._admit'))
            stack.enter_context(patch.object(service.connection,'cursor',side_effect=lambda:nullcontext(Obj())))
            stack.enter_context(patch('mta.runtime.ingestion_admission.preparation_source',return_value=Obj()))
            stack.enter_context(patch.object(service,'predecessor',return_value=parent))
            stack.enter_context(patch.object(service,'unresolved_attempts',return_value=Obj(exclude=lambda **k:absent)))
            stack.enter_context(patch('mta.runtime.publication_models.DailyUiPublication.objects.filter',return_value=absent))
            leaves=Obj(values_list=lambda *a,**k:[run.pk])
            stack.enter_context(patch('mta.runtime.mdm_daily_models.MdmDailyInputCapture.objects.filter',return_value=leaves))
            stack.enter_context(patch('mta.presentation.native_selection.read',return_value=dict(run_id=str(parent.pk),
                output_digest=parent.output_digest,initialization_id=str(owner.pk))))
            from mta.runtime.temporal import resolved_pick_root
            pick=root/'pick';pick.mkdir()
            stack.enter_context(patch('mta.runtime.input_reader.read_input',return_value={'pick_output_root':resolved_pick_root(pick)}))
            producer=stack.enter_context(patch('mta.runtime.production_daily.execute'))
            args=dict(input_root=root,work_root=root/'attempts',pick_root=pick,resume=True)
            first=service.stage('binding',root,'2037-04-11',**args)
            second=service.stage('binding',root,'2037-04-11',**args)
            self.assertEqual(first['attempt_id'],second['attempt_id'])
            created.assert_called_once();producer.assert_not_called()
            self.assertTrue(any(call.args[2]==historical for call in historical_admit.call_args_list))
            self.assertEqual(service._revalidation_origin_digest(origin),frozen_before)
            retry=attempts[service._capture_retry_key(origin,target)]
            run.input_manifest_digest='changed'
            with self.assertRaisesRegex(ValueError,'Frozen retry lineage'):
                service.stage('binding',root,'2037-04-11',**args)
            run.input_manifest_digest='3'*64
            retry.run_id=uuid.uuid4();retry.run=Obj(status='RUNNING');retry.phase='CALCULATE'
            with self.assertRaisesRegex(ValueError,'reconcile native state'):
                service.stage('binding',root,'2037-04-11',**args)
            created.assert_called_once();producer.assert_not_called()
            retry.run_id=None;retry.run=None;retry.phase='VALIDATED'
            selected_manager=stack.enter_context(patch.object(service.DailyFeedAttempt.objects,'select_related'))
            selected_manager.return_value.get.side_effect=lambda **kw:(retry if kw['attempt_id']==retry.attempt_id else origin)
            class ReachedFrozenProducer(Exception):pass
            producer.side_effect=ReachedFrozenProducer('unit stop before native business execution')
            with self.assertRaises(ReachedFrozenProducer):
                service.execute(str(retry.attempt_id),'binding',pick_root=pick,resume=True)
            producer.assert_called_once()
            self.assertEqual(producer.call_args.kwargs['retry_capture_id'],str(origin.run_id))
            self.assertEqual(producer.call_args.kwargs['execution_revision'],'csv-retry-v1-'+retry.request_key)
            self.assertLessEqual(len(producer.call_args.kwargs['execution_revision']),80)
            self.assertEqual(service._revalidation_origin_digest(origin),frozen_before)
