"""HTTP/persistence protocol only. Stub calculation/scope is NOT parity proof."""
import json
from types import SimpleNamespace
from unittest.mock import patch
from django.test import TransactionTestCase, override_settings
from mta.runtime.models import RunCommand
from mta.runtime.services import read_outputs
from mta.runtime.temporal import command_state
from mta.runtime.test_temporal import TemporalPersistenceTest


class DBMActionHTTPTest(TransactionTestCase):
    available_apps=['mta.runtime','django.contrib.contenttypes']
    setUp=TemporalPersistenceTest.setUp
    calculate=TemporalPersistenceTest.calculate
    run_day=TemporalPersistenceTest.run_day

    def post(self,path,payload=None,user='authenticated-test-actor'):
        headers={} if user is None else {'HTTP_X_VECTORFLOW_IDENTITY':json.dumps({'id':user})}
        return self.client.post('/api/mta/'+path,json.dumps(payload if payload is not None else {
            'data':[{'SKUCode':'337','WHCode':'AG515802'}], 'user':{'id':'forged-actor'}}),
            content_type='application/json',**headers)

    def context(self):
        output=read_outputs(self.run)
        state,_=command_state(self.run,output['DBMFinal'][0])
        return SimpleNamespace(run=self.run,output=output,dbm=state)

    def exercise(self,path):
        self.run=self.run_day()
        with override_settings(VF_MTA_PUBLISHED_RUN=str(self.run.pk),VF_MTA_ACTIONS_ENABLED=True), \
             patch('mta.presentation.actions.publication',side_effect=self.context), \
             patch('mta.presentation.actions.scope',return_value=({'337'},{'AG515802'})), \
             patch('mta.presentation.actions.timestamp',return_value='2026-06-06T12:00:00+05:30'):
            return self.post(path)

    def test_apply_wire_actor_persistence_and_next_own_state(self):
        response=self.exercise('DBMApplySelectedNorms')
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json()['data'],'')
        self.assertEqual(response.json()['msg'],'Saved Succesfully')
        self.assertEqual(RunCommand.objects.get().payload['actor'],'authenticated-test-actor')
        second=self.run_day(1,predecessor=self.run)
        self.assertEqual(second.predecessor_id,self.run.pk)
        self.assertEqual(self.seen[-1]['dbm']['NormAcceptanceTbl'],[dict(
            SKUCode='337',WhCode='AG515802',AcceptanceDate='2026-06-06',OldNorm=220,NewNorm=250)])

    def test_sleep_wire_and_next_own_state(self):
        response=self.exercise('DBMUpdateSleepTbl')
        self.assertEqual(response.status_code,200)
        self.assertIsNone(response.json()['data'])
        self.assertEqual(response.json()['msg'],'Saved Succesfully')
        self.run_day(1,predecessor=self.run)
        self.assertEqual(self.seen[-1]['dbm']['Suggestions'],[])
        self.assertEqual(self.seen[-1]['dbm']['NormsInSleepModeTbl'],[dict(
            SKUCode='337',WhCode='AG515802',StartDate='2026-06-06')])

    def test_preview_read_only_and_missing_identity_do_not_read_or_write(self):
        with patch('mta.presentation.actions.publication',side_effect=AssertionError('must not read')):
            for path in ('DBMApplySelectedNorms','DBMUpdateSleepTbl'):
                self.assertEqual(self.post(path,user=None).status_code,403)
                self.assertEqual(self.post(path).json(),{'error':'demo_read_only'})
        self.assertEqual(RunCommand.objects.count(),0)

    def test_out_of_scope_member_rejects_whole_selection_before_any_command(self):
        self.run=self.run_day()
        with override_settings(VF_MTA_PUBLISHED_RUN=str(self.run.pk),VF_MTA_ACTIONS_ENABLED=True), \
             patch('mta.presentation.actions.publication',side_effect=self.context), \
             patch('mta.presentation.actions.scope',return_value=({'337'},set())), \
             patch('mta.presentation.actions.record_command',side_effect=AssertionError('must not write')):
            response=self.post('DBMApplySelectedNorms')
        self.assertEqual(response.status_code,403)
        self.assertEqual(RunCommand.objects.count(),0)

    def test_duplicate_selection_is_membership_and_no_suggestion_has_no_success_message(self):
        self.run=self.run_day()
        with override_settings(VF_MTA_PUBLISHED_RUN=str(self.run.pk),VF_MTA_ACTIONS_ENABLED=True), \
             patch('mta.presentation.actions.publication',side_effect=self.context), \
             patch('mta.presentation.actions.scope',return_value=({'337'},{'AG515802'})), \
             patch('mta.presentation.actions.timestamp',return_value='2026-06-06T12:00:00+05:30'):
            response=self.post('DBMUpdateSleepTbl',{'data':[{'SKUCode':'337','WHCode':'AG515802'}]*2})
            self.assertEqual(response.json()['msg'],'Saved Succesfully')
            self.assertIsNone(self.post('DBMUpdateSleepTbl').json()['msg'])
        state,_=command_state(self.run,read_outputs(self.run)['DBMFinal'][0])
        self.assertEqual(len(state['NormsInSleepModeTbl']),1)

    def test_command_write_failure_rolls_back_http_action(self):
        self.run=self.run_day()
        before=read_outputs(self.run)
        with override_settings(VF_MTA_PUBLISHED_RUN=str(self.run.pk),VF_MTA_ACTIONS_ENABLED=True), \
             patch('mta.presentation.actions.publication',side_effect=self.context), \
             patch('mta.presentation.actions.scope',return_value=({'337'},{'AG515802'})), \
             patch('mta.presentation.actions.timestamp',return_value='2026-06-06T12:00:00+05:30'), \
             patch('mta.runtime.relational_state.save_image',side_effect=RuntimeError('injected action failure')):
            with self.assertRaisesMessage(RuntimeError,'injected action failure'):
                self.post('DBMApplySelectedNorms')
        self.assertEqual(RunCommand.objects.count(),0)
        self.assertEqual(read_outputs(self.run),before)
