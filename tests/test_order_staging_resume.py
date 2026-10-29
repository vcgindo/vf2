"""Observed successor row boundary and one unexecuted CSV rejection recovery."""
from contextlib import ExitStack, nullcontext
from io import StringIO
from copy import deepcopy
from datetime import date
import json
import os
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
from types import SimpleNamespace as Obj
import unittest
from unittest.mock import Mock, patch
import uuid

os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY','order-staging-unit-only')
import django
django.setup()

from mta.runtime import daily_feed as service, production_preflight as pf, relational_state
from mta.row_sequences import RecordRows
from mta.serialization import digest
from tests.test_production_preflight import context, INIT, SOURCE, OUTPUT
from tests.production_daily_fixture import day_input
from tests.test_production_daily_contract import encoded_day


class OrderStagingResumeTests(unittest.TestCase):
    def test_existing_management_resume_reaches_stage(self):
        from django.core.management import call_command
        with patch.object(service,'stage',return_value={'status':'VALIDATED'}) as staged:
            call_command('process_daily_csv','stage','--date','2037-04-11',
                '--input-directory','/incoming/day','--resume',stdout=StringIO())
        self.assertIs(staged.call_args.kwargs['resume'],True)
        self.assertEqual(staged.call_args.kwargs['selection_file'],'/var/lib/vectorflow/selection.json')

    def test_typed_successor_current_orders_keep_list_contract_without_mutating_prior(self):
        frame=context()
        closing=deepcopy(frame['opening']['state'])
        closing['dbm']['IntermediateTables']=[dict(table='dbo.AcceptedNorms',rows=[])]
        rows=[dict(OrderKey=i+1,CustomerOrderId='ORDER-'+str(i),PartId=1,IsSpike=False,IsElephant=False,
            OriginalQty=1,Qty=1,SKUCode='SUPPLIED-Z9',WhCode='OWN-WH8',CustomerExpectedDate=None,
            FirstServicingWhCode=None,DueDate=None,IntroDate='2037-04-08') for i in range(10001)]
        before=digest(rows)
        self.enterContext(patch.object(relational_state,'iter_image',lambda *a,**k:iter(rows)))
        self.enterContext(patch.dict(os.environ,{'VF_WORK_ROOT':''}))
        streamed=relational_state.load_image(Obj(pk=uuid.uuid4()),dict(count=len(rows)))
        self.assertIsInstance(streamed,RecordRows)
        closing['orders']['OrderIdentity']=[dict(Seed=1,Increment=1,LastValue=10001)]
        parent=dict(run_id=str(uuid.uuid4()),business_date='2037-04-10',kind='DAILY_CHAIN',status='SUCCEEDED',
            output_digest=OUTPUT,initialization_id=INIT,source_digest=SOURCE,capture_status='CONSUMED',closing_state=closing)
        raw,sha=encoded_day(day_input('2037-04-11'))
        with TemporaryDirectory() as root:
            args=dict(frame=frame,predecessor=parent,initialization_id=INIT,source_digest=SOURCE,
                configuration_digest=digest(frame['profile']),predecessor_output_digest=OUTPUT,
                pick_output_root=root,execution_revision='row-boundary')
            closing['orders']['SpikeOrderData']=rows
            listed=pf.daily(raw,sha,**args)
            closing['orders']['SpikeOrderData']=streamed
            actual=pf.daily(raw,sha,**args)
        self.assertTrue(actual['stage_eligibility']['day'],actual['issues'])
        self.assertEqual(actual,listed)
        self.assertIs(closing['orders']['SpikeOrderData'],streamed)
        self.assertEqual(digest(rows),before)
        self.assertEqual(digest(list(streamed)),before)

    def _fixture(self, root, stack):
        source=Obj(digest='source',receipt={'owned_namespace':{'release_identity':{'implementation_sha256':'old'}}})
        owner=Obj(pk=uuid.uuid4(),source=source)
        binding={'_binding_digest':'binding','source_digest':'source','configuration_digest':'configuration'}
        parent=Obj(pk=uuid.uuid4(),output_digest='output',status='SUCCEEDED')
        original=root/'old';(original/'original').mkdir(parents=True)
        (original/'original'/'READY').write_bytes(b'')
        (original/'original'/'batch.json').write_bytes(b'{}')
        files={p.name:service.file_identity(p) for p in (original/'original').iterdir()}
        manifest=dict(schema='vectorflow-csv-snapshot-v1',files=files)
        manifest['digest']=digest(manifest)
        service.atomic_json(original/'original'/'snapshot.json',manifest)
        (original/'native-day.json').write_bytes(b'unchanged-input')
        report={'issues':[dict(category='input',code='CONTRACT_INVALID',message='Order source tables must be row lists',
            owner='r1_order_input.validate_order_input',path='/day/order_feed',stages=['day'])]}
        service.atomic_json(original/'preflight.json',report)
        key=digest(dict(initialization=str(owner.pk),date='2037-04-11',binding='binding',batch=manifest['digest']))
        old=Obj(attempt_id=uuid.uuid4(),initialization_id=owner.pk,initialization=owner,business_date=date(2037,4,11),
            batch_id='batch',request_key=key,batch_digest=manifest['digest'],binding_digest='binding',
            input_sha256=service.file_identity(original/'native-day.json')['sha256'],predecessor_id=parent.pk,
            predecessor_output_digest='output',status='REJECTED',phase='VALIDATE',run_id=None,run=None,
            accepted_facts={},prepared_context={},archive_path=str(original),
            error={'type':'PreflightError','message':json.dumps(report,sort_keys=True)[:2000]},refresh_from_db=lambda:None)
        selected=root/'selection.json'
        service.atomic_json(selected,dict(run_id=str(parent.pk),output_digest='output',initialization_id=str(owner.pk)))
        attempts={key:old}
        def query(**kwargs):
            if 'request_key' in kwargs:
                return Obj(first=lambda:attempts.get(kwargs['request_key']))
            return Obj(exists=lambda:False)
        def create(**kwargs):
            attempt=Obj(**kwargs,initialization_id=owner.pk,status='RUNNING',phase='VALIDATE',run_id=None,run=None,
                predecessor_id=None,predecessor=None,input_sha256='',predecessor_output_digest='',error={},
                accepted_facts={},prepared_context={},refresh_from_db=lambda:None)
            def save(**kwargs):
                attempt.predecessor_id=attempt.predecessor.pk if attempt.predecessor else None
            attempt.save=save
            attempts[attempt.request_key]=attempt
            return attempt
        created=stack.enter_context(patch.object(service.DailyFeedAttempt.objects,'create',side_effect=create))
        stack.enter_context(patch.object(service.DailyFeedAttempt.objects,'filter',side_effect=query))
        stack.enter_context(patch.object(service.CalculationRun.objects,'filter',return_value=Obj(exists=lambda:False)))
        stack.enter_context(patch('mta.runtime.mdm_daily_models.MdmDailyInputCapture.objects.filter',return_value=Obj(exists=lambda:False)))
        cursor=Mock();cursor.fetchone.return_value=(False,)
        stack.enter_context(patch.object(service.connection,'cursor',return_value=nullcontext(cursor)))
        stack.enter_context(patch.object(service,'binding_owner',return_value=(binding,owner)))
        stack.enter_context(patch.object(service,'job_lock',return_value=nullcontext()))
        stack.enter_context(patch.object(service,'unresolved_attempts',return_value=Obj(exists=lambda:False)))
        stack.enter_context(patch.object(service,'predecessor',return_value=parent))
        stack.enter_context(patch.object(service,'batch_contract'))
        batch={'batch_id':'batch','feeds':{}}
        def snapshot(source,destination,input_root):
            shutil.copytree(original/'original',destination)
            return batch,manifest
        stack.enter_context(patch.object(service,'snapshot',side_effect=snapshot))
        def assemble(*args,**kwargs):
            kwargs['output_file'].write_bytes(b'unchanged-input')
            return Obj(sha256=old.input_sha256),{}
        stack.enter_context(patch.object(service,'assemble',side_effect=assemble))
        stack.enter_context(patch('mta.runtime.daily_preparation.prepare',side_effect=lambda raw,sha:raw))
        stack.enter_context(patch('mta.runtime.ingestion_admission.preparation_source',return_value=Obj()))
        stack.enter_context(patch('release.native_identity.require_current',return_value={'implementation_sha256':'new'}))
        stack.enter_context(patch.object(service,'_native_inspect',return_value={'issues':[]}))
        stack.enter_context(patch('mta.runtime.accepted_daily.seal'))
        producer=stack.enter_context(patch('mta.runtime.production_daily.execute'))
        args=dict(input_root=root,work_root=root/'attempts',pick_root=root/'pick',selection_file=selected)
        return old,created,producer,args

    def test_rejected_resume_keeps_origin_and_returns_one_replacement_without_calculation(self):
        with TemporaryDirectory() as td,ExitStack() as stack:
            root=Path(td);old,created,producer,args=self._fixture(root,stack)
            before=service._revalidation_origin_digest(old)
            first=service.stage('binding',root,'2037-04-11',resume=True,**args)
            second=service.stage('binding',root,'2037-04-11',resume=True,**args)
            ordinary=service.stage('binding',root,'2037-04-11',**args)
            self.assertEqual(first['attempt_id'],second['attempt_id'])
            self.assertEqual(first['phase'],'VALIDATED')
            self.assertEqual(ordinary['attempt_id'],str(old.attempt_id))
            created.assert_called_once();producer.assert_not_called()
            self.assertEqual(service._revalidation_origin_digest(old),before)
            self.assertTrue((Path(old.archive_path)/'preflight.json').is_file())

    def test_changed_frozen_input_stops_before_replacement_or_calculation(self):
        with TemporaryDirectory() as td,ExitStack() as stack:
            root=Path(td);old,created,producer,args=self._fixture(root,stack)
            (Path(old.archive_path)/'native-day.json').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'Preserved rejected input bytes differ'):
                service.stage('binding',root,'2037-04-11',resume=True,**args)
            created.assert_not_called();producer.assert_not_called()
