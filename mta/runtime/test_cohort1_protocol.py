"""Cohort1 transaction/retry protocol; stub calculation is not business parity."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from unittest.mock import patch
from django.db import connection
from django.test import TransactionTestCase, override_settings
from mta.runtime.test_temporal import TemporalPersistenceTest
from mta.runtime.models import CalculationRun
from mta.runtime.mdm_models import MdmSource, MdmTask, MdmSubTask, MdmSkuHistory
from mta.runtime.mdm_daily_models import MdmPairExclusionSource
from development.temporal import execute_day
from mta.runtime.services import read_outputs
from mta.runtime.input_reader import read_input
from mta.runtime.relational_state import table_sql
from mta.runtime.complete_daily_state import BINDINGS
from mta.application import daily_finalization as final
from mta.serialization import digest

@override_settings(VF_MTA_DAILY_PUBLICATION=False)
class Cohort1ProtocolTest(TransactionTestCase):
    available_apps=['mta.runtime','django.contrib.contenttypes']
    def setUp(self):
        TemporalPersistenceTest.setUp(self)
        self.state['importer_settings']=[dict(Parameter=k,Value=v) for k,v in (
            ('NMSActive','0'),('TaskStatusLogHorizon','7'),('IsBatchFileExecuted','0'),
            ('IsBPRBatchFileExecuted','1'),('BatchFileExecutionDate','2026-06-05'))]
        complete={name:[] for name in final.REQUIRED}
        complete['ScriptExecutedFlag']=deepcopy(final.FLAG_SEED)
        self.state['complete']=complete
        config=dict(policy=final.POLICY,consumption_days=90,remark_days=90)
        self.supplement=json.dumps(dict(schema='generic-finalization-input-v1',artifact_sha256='a'*64,configuration=config,opening_complete=complete)).encode()
        self.profile.update(complete_pick={'policy':'canonical-tied-order-v1'},complete_daily=config,complete_daily_config_sha256=hashlib.sha256(self.supplement).hexdigest(),complete_daily_artifact_sha256='a'*64)
        self.source=MdmSource.objects.create(digest=digest(self.revision),database_name='cohort1-protocol',dll_digest='b'*64,receipt={})
        MdmPairExclusionSource.objects.create(source=self.source,digest=digest([]),row_count=0,provenance={'kind':'explicit-protocol-empty'})
    def calculate(self, prior, opening_date, day, profile, identity, calculate, exceptions):
        prior=final.begin(prior,day['business_date'])
        for row in prior['complete']['ScriptExecutedFlag']:
            row['IsScriptExecuted']=row['ScriptName'] not in ('NMSImportData.sql','NMSClearInputTables.sql','NMSTaskStatusUpdate.sql')
        prior['importer_settings']=final.validate_completion(prior['complete'],prior['importer_settings'],day['business_date'],kind='BPR')
        prior['importer_settings']=final.finish(prior['complete'],prior['importer_settings'],day['business_date'])
        result=TemporalPersistenceTest.calculate(self,prior,opening_date,day,profile,identity,calculate,exceptions)
        result['_Cohort1']=dict(policy=final.POLICY,business_date=day['business_date'],configuration_digest=digest(profile),qualification='inactive-nms-critical-flags-remain-false',flag_digest=digest(prior['complete']['ScriptExecutedFlag']))
        return result
    def run_day(self,index=0,**extra):
        arguments=dict(day=dict(business_date=f'2026-06-{6+index:02d}',raw_master=[]),profile=self.profile,execution_revision=self.revision,opening=self.opening,mdm_source=self.source,pick_output_root=Path(self.directory.name),finalization_config=self.supplement)
        arguments.update(extra)
        if arguments.get('predecessor') is not None:arguments['opening']=None
        if arguments.get('mdm_retry') is not None:arguments.pop('mdm_source')
        with patch('mta.runtime.temporal.calculate_day',side_effect=self.calculate),patch('mta.application.complete_daily_batch_files.write_run_pick_files'):
            return execute_day(**arguments)
    def test_successor_failure_rolls_back_task_consumption_and_retries_frozen_owner(self):
        parent=self.run_day()
        task=MdmTask.objects.create(source=self.source,TaskID='TASK',TaskStatus='1',MasterId='1',Actiontype=2)
        sub=MdmSubTask.objects.create(source=self.source,TaskID='TASK',ApproverId='2',TaskStatus='2')
        MdmSkuHistory.objects.create(source=self.source,TaskId='TASK',SKUCode='APPROVED',SKUDescription='Approved',Status='3')
        original_stamp=sub.DBUpdatedDate
        with patch('mta.presentation.pick_storage.write_pick_bands',side_effect=RuntimeError('after typed writer')):
            with self.assertRaisesRegex(RuntimeError,'after typed writer'):
                self.run_day(1,predecessor=parent)
        failed=CalculationRun.objects.get(predecessor=parent)
        self.assertEqual(failed.status,'FAILED')
        self.assertEqual(failed.mdm_input_capture.status,'CAPTURED')
        self.assertFalse(failed.checkpoints.exists())
        self.assertFalse(failed.production_manifest)
        with connection.cursor() as cursor:
            cursor.execute('SELECT count(*) FROM '+table_sql(BINDINGS['closing/complete/ScriptExecutedFlag'])+' WHERE vf_run_id=%s',[failed.pk])
            self.assertEqual(cursor.fetchone()[0],0)
        task.refresh_from_db();sub.refresh_from_db()
        self.assertEqual((task.TaskStatus,sub.TaskStatus,sub.DBUpdatedDate),('1','2',original_stamp))
        self.assertIsNone(failed.mdm_input_capture.task_occurrences.get().transitioned_at)
        captured=read_input(failed)['mdm_input']
        with self.assertRaisesRegex(ValueError,'identity drift|failed daily request'):
            self.run_day(1,predecessor=parent,mdm_retry=failed)
        retry=self.run_day(1,predecessor=parent,mdm_retry=failed,execution_revision=self.revision+'-retry')
        self.assertEqual(retry.status,'SUCCEEDED')
        self.assertEqual(retry.mdm_input_capture.origin_id,failed.mdm_input_capture.pk)
        self.assertEqual(read_input(retry)['mdm_input'],captured)
        final.verify_successor(read_outputs(retry),self.profile,'2026-06-07')
        task.refresh_from_db();sub.refresh_from_db()
        self.assertEqual((task.TaskStatus,sub.TaskStatus),('7','4'))
        transition=retry.mdm_input_capture.task_occurrences.get().transitioned_at
        self.assertIsNotNone(transition)
        stamp=sub.DBUpdatedDate
        flags=read_outputs(retry)['ClosingState'][0]['complete']['ScriptExecutedFlag']
        self.assertTrue(next(r['IsScriptExecuted'] for r in flags if r['ScriptName']=='NMSTaskStatusUpdate.sql'))
        seen=len(self.seen)
        self.assertEqual(self.run_day(1,predecessor=parent,mdm_retry=failed,execution_revision=self.revision+'-retry').pk,retry.pk)
        self.assertEqual(len(self.seen),seen)
        self.assertEqual(retry.mdm_input_capture.task_occurrences.get().transitioned_at,transition)
        sub.refresh_from_db();self.assertEqual(sub.DBUpdatedDate,stamp)
        failed.refresh_from_db();self.assertEqual(failed.status,'FAILED')
    def _fixture_teardown(self):
        pass  # Keep the isolated proof DB; immutable guards prohibit global flush.
