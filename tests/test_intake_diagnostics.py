"""Failure entry and typed codecs; local files are real, database writes mocked."""
from contextlib import nullcontext
from copy import deepcopy
from datetime import date,datetime
from importlib import import_module
from pathlib import Path
from types import SimpleNamespace as Obj
import json
import os
import tempfile
import unittest
from unittest.mock import Mock,patch
import uuid

os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY','intake-diagnostic-unit-only')
import django
django.setup()

from mta.application.intake_errors import NativeIntakeRejected
from mta.application import literal_fullkit
from mta.runtime import intake_diagnostics as subject,scope_execution,services,daily_feed
from mta.serialization import digest


def rejected():
    return NativeIntakeRejected('actual producer rejection',stage='DailyValidation',rejections=[
        dict(SKUCode='SKU',WhCode='WH',RejectionDate='2026-10-26T00:00:00.000',ReasonCode=4,ReasonDescription=None),
        dict(SKUCode='SKU',WhCode='WH',RejectionDate='2026-10-26T00:00:00.000',ReasonCode=4,ReasonDescription=None)])


class IntakeDiagnosticCodecTests(unittest.TestCase):
    def test_rejections_preserve_occurrences_null_and_exact_sql_datetime(self):
        error=rejected();source=deepcopy(error.rejections)
        rows=subject.rejection_rows(error)
        self.assertEqual([row['ordinal'] for row in rows],[0,1])
        self.assertEqual(rows[0]['RejectionDate'],datetime(2026,10,26))
        self.assertIsNone(rows[0]['ReasonDescription'])
        self.assertEqual(error.rejections,source)
        for value in (True,2.0,'2',2**31):
            error.rejections[0]['ReasonCode']=value
            with self.subTest(value=value),self.assertRaises(ValueError):subject.rejection_rows(error)

    def test_non_native_error_or_unknown_stage_does_not_gain_failure_authority(self):
        with self.assertRaises(ValueError):subject.rejection_rows(ValueError('not producer rows'))
        error=rejected();error.stage='completed'
        with self.assertRaises(ValueError):subject.rejection_rows(error)
        self.assertIsNone(subject.capture_importer(Obj(),ValueError('ordinary failure')))

    def test_native_failures_bind_original_run_scope_input_and_clock(self):
        initial=Obj(pk=uuid.uuid4(),source=Obj(digest='a'*64),configuration_digest='b'*64)
        run=Obj(pk=uuid.uuid4(),kind='DAILY_CHAIN',evidence_mode='production',business_date=date(2026,10,26),
            input_digest='c'*64,input_manifest_digest='d'*64,production_digest='e'*64,
            mdm_input_capture=Obj(source='source',revision_digest='f'*64))
        attempt=Obj(pk=uuid.uuid4(),run_id=run.pk)
        with patch('mta.runtime.models.ProductionInitialization.objects.select_related') as initialization, \
                patch('mta.runtime.daily_feed_models.DailyFeedAttempt.objects.filter') as feeds, \
                patch.object(subject,'_insert') as insert, \
                patch.object(subject.models,'IntakeDiagnostic') as model:
            initialization.return_value.get.return_value=initial;feeds.return_value.first.return_value=None
            subject.capture_importer(run,rejected(),scope_attempt=attempt)
            values=model.call_args.kwargs
            self.assertIs(values['run'],run);self.assertIs(values['scope_attempt'],attempt)
            self.assertEqual(values['clock'],datetime(2026,10,26))
            self.assertEqual(values['input_digest'],run.input_digest)
            self.assertEqual(values['metadata']['capture_revision'],'f'*64)
            self.assertEqual(len(insert.call_args.args[1]['rejections']),2)
            expected=values['id']
            subject.capture_importer(run,rejected(),scope_attempt=attempt)
            self.assertEqual(model.call_args.kwargs['id'],expected)
            attempt.pk=uuid.uuid4()
            subject.capture_importer(run,rejected(),scope_attempt=attempt)
            self.assertNotEqual(model.call_args.kwargs['id'],expected)

    def test_scope_records_facts_before_closing_claim_and_does_not_publish_files(self):
        run=Obj();attempt=Obj();events=[]
        with patch.object(scope_execution.transaction,'get_autocommit',return_value=True), \
                patch.object(scope_execution.transaction,'atomic',side_effect=lambda:nullcontext()), \
                patch.object(scope_execution,'_locked_claim',return_value=(attempt,run)), \
                patch.object(scope_execution,'_setting',side_effect=lambda *_:nullcontext()), \
                patch.object(subject,'capture_importer',side_effect=lambda *a,**k:events.append(('facts',a,k))), \
                patch.object(scope_execution,'_close_attempt',side_effect=lambda *a:events.append(('close',a))):
            error=rejected()
            self.assertIs(scope_execution.fail('id','token',compatibility_digest='digest',error=error),attempt)
            self.assertEqual([event[0] for event in events],['facts','close'])
            self.assertEqual(events[0][1],(run,error));self.assertIs(events[0][2]['scope_attempt'],attempt)

    def test_full_failure_records_typed_rows_and_status_in_one_atomic_boundary(self):
        events=[]
        run=Obj(pk=uuid.uuid4(),kind='DAILY_CHAIN',evidence_mode='production',status='RUNNING')
        with patch.object(services.transaction,'atomic',side_effect=lambda:nullcontext()), \
                patch.object(scope_execution,'_source_lock',side_effect=lambda key:events.append('lock')), \
                patch.object(services.CalculationRun.objects,'select_for_update') as locked, \
                patch.object(services.CalculationRun.objects,'filter') as filtered, \
                patch.object(subject,'capture_importer',side_effect=lambda *a:events.append('facts')):
            locked.return_value.get.return_value=run
            filtered.return_value.update.side_effect=lambda **k:events.append('failed')
            services.fail_run(run,rejected())
            self.assertEqual(events,['lock','facts','failed'])
            self.assertEqual(filtered.return_value.update.call_args.kwargs['status'],'FAILED')

    def test_file_failure_happens_after_scope_failure_closes(self):
        events=[];diagnostic=Obj(pk=uuid.uuid4())
        with patch.object(scope_execution.transaction,'get_autocommit',return_value=True), \
                patch.object(scope_execution.transaction,'atomic',side_effect=lambda:nullcontext()), \
                patch.object(scope_execution,'_locked_claim',return_value=(Obj(),Obj())), \
                patch.object(scope_execution,'_setting',side_effect=lambda *_:nullcontext()), \
                patch.object(subject,'capture_importer',return_value=diagnostic), \
                patch.object(scope_execution,'_close_attempt',side_effect=lambda *a:events.append('closed')), \
                patch('mta.runtime.diagnostic_publication.publish_importer',side_effect=OSError('zip failure')) as publish:
            with self.assertRaises(OSError):
                scope_execution.fail('id','token',compatibility_digest='digest',error=rejected())
            self.assertEqual(events,['closed']);publish.assert_called_once_with(diagnostic)


class FullkitEntryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='intake-entry-');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.source=self.root/'batch';self.source.mkdir()
        self.work=self.root/'work';self.work.mkdir();self.site=self.root/'site';self.site.mkdir()
        (self.source/'present.csv').write_bytes(b'SKU,Quantity\r\nS,3\r\n')
        (self.source/'batch.json').write_text('{"retained":"control"}')
        (self.source/'READY').write_bytes(b'')
        self.owner=Obj(pk=uuid.uuid4(),source=Obj(digest='a'*64),source_id=11)
        self.config=literal_fullkit.configuration(critical_files=[
            dict(Id=i,Path=str(self.source),FileName=name,Type='DataFiles',Exists=False,ResolvedPath=None,ResolvedFileName=None)
            for i,name in ((1,'present.csv'),(2,'absent.csv'))],
            settings=[dict(Parameter='FullkitAvailable',Value='1')],abort_opening=[],
            input_root=self.source,site_root=self.site)
        self.request=dict(schema='fresh-literal-fullkit-request-v1',initialization_id=str(self.owner.pk),
            source_digest='a'*64,business_date='2026-10-26',clock='2026-10-26T10:15:00',configuration=self.config)

    def test_real_missing_file_stops_actual_stage_before_strict_snapshot_or_day_attempt(self):
        captured=[]
        def retain(owner,rows):
            captured.append((owner,rows));return owner
        with patch.object(daily_feed,'binding_owner',return_value=({},self.owner)), \
                patch.object(daily_feed,'job_lock',side_effect=lambda *_:nullcontext()), \
                patch.object(subject.transaction,'atomic',side_effect=lambda:nullcontext()), \
                patch('mta.mdm.supplier_revisions.lock_transaction'), \
                patch.object(subject,'_insert',side_effect=retain), \
                patch.object(subject.models,'IntakeDiagnostic',side_effect=lambda **k:Obj(pk=uuid.uuid4(),**k)), \
                patch('mta.runtime.diagnostic_publication.publish_failure') as publish, \
                patch.object(daily_feed,'snapshot') as snapshot, \
                patch.object(daily_feed.DailyFeedAttempt.objects,'create') as day_attempt:
            with self.assertRaises(subject.FullkitUnavailable) as failed:
                daily_feed.stage('binding',self.source,'2026-10-26',input_root=self.root,
                    work_root=self.work,pick_root=self.root/'pick',fullkit=self.request)
            snapshot.assert_not_called();day_attempt.assert_not_called()
            owner,rows=captured[0]
            self.assertEqual(failed.exception.diagnostic_id,owner.pk)
            self.assertEqual(publish.call_args.args,(owner.pk,))
            self.assertEqual(owner.kind,'FULLKIT')
            self.assertEqual(rows['aborts'][0]['FileId'],2)
            self.assertFalse(rows['aborts'][0]['inherited'])
            self.assertEqual(rows['observations'][0]['size_bytes'],len((self.source/'present.csv').read_bytes()))
            self.assertIsNone(rows['observations'][1]['sha256'])
            folders=list(self.work.iterdir());self.assertEqual(len(folders),1)
            self.assertEqual((folders[0]/'original'/'batch.json').read_bytes(),(self.source/'batch.json').read_bytes())
            self.assertEqual(json.loads((folders[0]/'result.json').read_bytes())['status'],'REJECTED')

    def test_request_cannot_change_initialization_source_date_or_original_directory(self):
        for key,value in (('initialization_id',str(uuid.uuid4())),('source_digest','b'*64),('business_date','2026-10-25')):
            request=deepcopy(self.request);request[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):
                subject.fullkit_request(request,initialization=self.owner,business_date='2026-10-26',
                    source=self.source,input_root=self.root)
        with self.assertRaises(ValueError):
            subject.fullkit_request(self.request,initialization=self.owner,business_date='2026-10-26',
                source=self.root,input_root=self.root)

    def test_typed_fullkit_roundtrip_keeps_original_configuration_and_failed_observations(self):
        result=literal_fullkit.check(self.config,business_date='2026-10-26',run_datetime=self.request['clock'],capture_root=self.root/'capture')
        rows=subject.fullkit_rows(self.config,result)
        self.assertEqual(rows['settings'],[dict(ordinal=0,Parameter='FullkitAvailable',initial_value='1',final_value='0')])
        self.assertFalse(rows['observations'][0]['initial_exists']);self.assertTrue(rows['observations'][0]['Exists'])
        changed=deepcopy(result);changed['observations'][0]['file_id']=99
        with self.assertRaises(ValueError):subject.fullkit_rows(self.config,changed)
        self.assertNotEqual(digest(rows),digest({**rows,'aborts':[]}))


class DiagnosticGuardConsumerTests(unittest.TestCase):
    def test_new_tables_meet_actual_ingestion_watch_coverage(self):
        from tests import test_report_definition_guards as contract
        guards=import_module('mta.runtime.migrations.0237_intake_diagnostic_guards')
        with patch.object(contract,'guards',guards):
            rows=contract.watch_catalogue();contract.validate_catalogue(rows)
            with self.assertRaises(ValueError):contract.validate_catalogue(rows[:-1])

    def test_scoped_owner_uses_latest_applied_body_and_preserves_minimum(self):
        from mta.runtime import ingestion_ownership
        guards=import_module('mta.runtime.migrations.0237_intake_diagnostic_guards')
        cursor=Mock();minimum='0218_scope_read_reference_guards'
        cursor.fetchall.return_value=[(minimum,),('0234_report_definition_guards',)]
        self.assertEqual(ingestion_ownership.scoped_derived_body(cursor,minimum=minimum),guards.OLD)
        cursor.fetchall.return_value.append(('0237_intake_diagnostic_guards',))
        self.assertEqual(ingestion_ownership.scoped_derived_body(cursor,minimum=minimum),guards.NEW)
        cursor.fetchall.return_value=[('0237_intake_diagnostic_guards',)]
        with self.assertRaises(ValueError):ingestion_ownership.scoped_derived_body(cursor,minimum=minimum)
