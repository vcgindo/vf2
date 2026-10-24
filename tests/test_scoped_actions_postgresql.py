"""Real typed paused actions on explicitly overridden supplied shallow inputs."""
from copy import deepcopy
import os
import unittest
from unittest.mock import patch
from tests import test_prepared_effects_postgresql as prepared_tests


@unittest.skipUnless(os.environ.get('VF_PHASE_POSTGRES_PROOF')=='1','Owned PostgreSQL required')
class ScopedActionTests(unittest.TestCase):
    for _name in ('setUp','rollback','owner','accept'):
        locals()[_name]=getattr(prepared_tests.PreparedEffectsPostgresTests,_name)

    def pause_bpr(self,*,duplicates=False,scope='UptoBPR',counter=False):
        from tests.test_h3_daily_integration import frame
        from tests.production_h3_fixture import SEASON,CHILD
        from mta.runtime.scope_execution import _claim,_setting,_close_attempt
        from mta.runtime.calculation_effects import _accept_calculation
        from mta.temporal.chain import produce_bpr
        from mta.application.native_output_contracts import native_assignments
        from mta.application.stage_calculation_sources import capture_bpr
        opening=frame()
        # Declared historical Suggestions input, never a seeded current result.
        suggestions=[dict(SKUCode=SEASON,WhCode=CHILD,Type=1,NewNorm=24)]
        if duplicates:suggestions.append(dict(SKUCode=SEASON,WhCode=CHILD,Type=None,NewNorm=None))
        opening['opening']['state']['dbm']['Suggestions']=deepcopy(suggestions)
        opening['opening']['state']['controls']['suggestions']=deepcopy(suggestions)
        if scope=='UptoDBM':
            # Explicit manual-action test policy; no automatic acceptance queue.
            opening['profile']['delivery']['batch']['AutoDBMActive']=0
            # Two declared historical facts plus today meet retained RCP/GCP=3.
            opening['opening']['state']['dbm']['DailyConsumption'] += [dict(
                SKUCode=SEASON,WhCode=CHILD,Stock=10,Consumption=2,GIT=4,Receipts=1,BlueZone=0,
                ReportDate=day) for day in ('2037-04-08','2037-04-09')]
        from tests.production_h3_fixture import supplied_day
        def facts(day):
            value=supplied_day(day)
            if scope=='UptoDBM':
                # Declared raw Stock=0 boundary computes a fresh Rule1 suggestion.
                for row in value['day']['raw_daily']:
                    if row['SKUCode']==SEASON and row['WhCode']==CHILD:row['Stock']=0
            return value
        with patch('tests.test_h3_daily_integration.frame',return_value=opening), \
                patch('tests.production_h3_fixture.supplied_day',side_effect=facts):self.owner(claim=False)
        if counter:
            from tests.test_scope_revisions_postgresql import bind_metadata_counter_owner
            self.counter_carrier=bind_metadata_counter_owner(self.run,self.source)
        self.attempt=_claim(self.run.pk,scope=scope,command_key='action-start',
            worker_reference='OWNED-ACTION-COMPONENT',compatibility_digest='a'*64,
            expected_phase='START',expected_receipt_digest='')
        pre=self.accept()
        with native_assignments(True):bpr=produce_bpr(self.prepared)
        sources=capture_bpr(bpr,{'supplier':bpr.context.prior['supplier']})
        self.bpr=_accept_calculation(self.attempt.pk,self.attempt.worker_token,bpr,sources,
            parent=pre,compatibility_digest='a'*64)
        if scope=='UptoDBM':
            from mta.runtime.scoped_actions import calculate_dbm
            self.bpr=calculate_dbm(self.attempt.pk,self.attempt.worker_token,compatibility_digest='a'*64)
        with _setting('fresh.scope_worker',self.attempt.worker_token):
            _close_attempt(self.attempt,self.run,'RELEASED',{})
        self.run.refresh_from_db()
        self.selected=[[SEASON,CHILD]]
        self.base_state=self.state(self.bpr,0)
        if scope=='UptoBPR':
            self.assertEqual([row for row in self.base_state['Suggestions']
                              if [row['SKUCode'],row['WhCode']]==self.selected[0]],suggestions)
        else:
            self.assertIn(dict(SKUCode=SEASON,WhCode=CHILD,Type=1,NewNorm=16),self.base_state['Suggestions'])
            self.selected=[[SEASON,CHILD]]

    def state(self,receipt,revision):
        from mta.runtime.scoped_actions import restore,state_after
        phase,_=restore(self.run,receipt)
        return state_after(self.run,receipt,phase,expected_revision=revision)

    def action(self,operation='SLEEP',*,expected_revision=0,key='scoped-command'):
        from mta.runtime.scoped_actions import record
        return record(self.run.pk,phase_id=self.bpr.pk,phase_digest=self.bpr.digest,
            expected_revision=expected_revision,operation=operation,selected=self.selected,
            timestamp=self.run.business_date.isoformat()+'T10:00:00',actor='owned-scoped-test',idempotency_key=key)

    def resume_dbm(self):
        from mta.runtime.scope_execution import _claim
        from mta.runtime.scoped_actions import calculate_dbm
        self.attempt=_claim(self.run.pk,scope='PostBPR',command_key='action-post-bpr',
            worker_reference='OWNED-ACTION-COMPONENT',compatibility_digest='a'*64,
            expected_phase='BPR',expected_receipt_digest=self.bpr.digest)
        return calculate_dbm(self.attempt.pk,self.attempt.worker_token,compatibility_digest='a'*64)

    def finish(self):
        from mta.runtime.scoped_final import _finish_accepted_day
        return _finish_accepted_day(self.attempt.pk,self.attempt.worker_token,compatibility_digest='a'*64)

    def test_sleep_before_dbm_has_exact_immediate_and_consumed_state(self):
        from mta.runtime.scoped_actions import restore
        from mta.serialization import digest
        original=None
        self.pause_bpr();original=self.bpr.snapshot.state_digest
        event=self.action()
        state=self.state(self.bpr,event.pk)
        expected=deepcopy(self.base_state)
        expected['Suggestions']=[row for row in expected['Suggestions']
            if [row['SKUCode'],row['WhCode']]!=self.selected[0]]
        expected['NormsInSleepModeTbl']+=[dict(SKUCode=self.selected[0][0],WhCode=self.selected[0][1],
            StartDate=self.run.business_date.isoformat())]
        self.assertEqual(state,expected)
        self.assertEqual(event.before_digest,digest(self.base_state))
        dbm=self.resume_dbm()
        phase,_=restore(self.run,dbm)
        self.assertEqual(phase.final_dbm['NormsInSleepModeTbl'],[])
        waits=[row for row in phase.final_dbm['SuspendNormsInSleepModeTbl']
               if [row['SKUCode'],row['WhCode']]==self.selected[0]]
        self.assertEqual(len(waits),1)
        self.assertEqual(waits[0]['WaitStartDate'],self.run.business_date.isoformat())
        self.assertEqual(waits[0]['WaitTillDate'],'2037-04-13')
        self.assertFalse(waits[0]['WaitForReceipts'])
        with patch('mta.presentation.daily_sources.write_sources',side_effect=ValueError('late action final failure')):
            with self.assertRaisesRegex(ValueError,'late action final failure'):self.finish()
        self.run.refresh_from_db();self.capture.refresh_from_db()
        self.assertEqual((self.run.status,self.capture.status),('RUNNING','CAPTURED'))
        from mta.runtime.models import RunCommand
        self.assertEqual(RunCommand.objects.filter(run=self.run).count(),1)
        result=self.finish()
        self.assertEqual(result.status,'SUCCEEDED')
        self.bpr.snapshot.refresh_from_db()
        self.assertEqual(self.bpr.snapshot.state_digest,original)
        from mta.runtime.services import read_outputs
        from mta.runtime.temporal import command_states
        terminal=read_outputs(result,include_reports=False)['ClosingState'][0]
        next_opening,commands=command_states(result,terminal)
        self.assertEqual(next_opening,terminal)
        self.assertEqual(commands,[])
        self.assertEqual(terminal['dbm']['NormsInSleepModeTbl'],[])

    def test_apply_duplicate_null_acceptances_keeps_immediate_norms_and_idempotency(self):
        self.pause_bpr(duplicates=True)
        event=self.action('APPLY')
        state=self.state(self.bpr,event.pk)
        self.assertEqual(state['DBMMaster'],self.base_state['DBMMaster'])
        self.assertEqual(state['Suggestions'],self.base_state['Suggestions'])
        old=next(row['Norm'] for row in self.base_state['DBMMaster']
                 if [row['SKUCode'],row['WhCode']]==self.selected[0])
        self.assertEqual([row for row in state['NormAcceptanceTbl']
            if [row['SKUCode'],row['WhCode']]==self.selected[0]],
            [dict(SKUCode=self.selected[0][0],WhCode=self.selected[0][1],
             AcceptanceDate=self.run.business_date.isoformat(),OldNorm=old,NewNorm=norm)
             for norm in (24,None)])
        again=self.action('APPLY')
        self.assertEqual(again.pk,event.pk)
        self.assertEqual(self.state(self.bpr,event.pk),state)
        with self.assertRaisesRegex(ValueError,'different scoped action facts'):self.action('SLEEP')
        second=self.action('SLEEP',expected_revision=event.pk,key='second-action')
        after=self.state(self.bpr,second.pk)
        self.assertEqual(second.scope_parent_revision,event.pk)
        self.assertEqual(after['NormAcceptanceTbl'],state['NormAcceptanceTbl'])
        self.assertEqual(len(after['NormsInSleepModeTbl']),len(state['NormsInSleepModeTbl'])+2)

    def test_apply_before_dbm_is_consumed_into_stock_suspension_without_norm_change(self):
        """Canonical03.1 clears acceptance after creating its suspension, before BTR."""
        from mta.runtime.scoped_actions import restore
        self.pause_bpr()
        self.action('APPLY')
        receipt=self.resume_dbm()
        phase,_=restore(self.run,receipt)
        chosen=lambda rows:[row for row in rows if [row['SKUCode'],row.get('WhCode',row.get('WHCode'))]==self.selected[0]]
        self.assertEqual(chosen(phase.final_dbm['DBMMaster'])[0]['Norm'],12)
        self.assertEqual(chosen(phase.final_dbm['NormAcceptanceTbl']),[])
        self.assertEqual(chosen(phase.final_dbm['SuspendAcceptedNormsStockType']),[
            dict(SKUCode=self.selected[0][0],WhCode=self.selected[0][1],DeltaNorm=12,
                 WaitStartDate='2037-04-10',WaitTillDate='2037-04-13',WaitForReceipts=False,
                 HasStockComeOutOfRed=True,IsRedEnabled=False,IsGreenEnabled=False)])

    def test_stale_revision_and_active_worker_deny_actions(self):
        self.pause_bpr()
        event=self.action('APPLY')
        with self.assertRaisesRegex(ValueError,'released stage/action head'):
            self.action('SLEEP',key='stale')
        self.resume_dbm()
        with self.assertRaisesRegex(ValueError,'released stage/action head'):
            self.action('SLEEP',expected_revision=event.pk,key='concurrent')

    def test_late_action_image_failure_rolls_back_header_and_all_images(self):
        from mta.runtime.models import RunCommand
        from mta.runtime.scoped_actions import revision
        self.pause_bpr()
        with patch('mta.runtime.relational_state.save_image',side_effect=ValueError('injected image failure')):
            with self.assertRaisesRegex(ValueError,'injected image failure'):self.action()
        self.assertFalse(RunCommand.objects.filter(run=self.run).exists())
        self.assertEqual(revision(self.run),0)
        self.assertEqual(self.state(self.bpr,0),self.base_state)
        self.assertTrue(self.action().state_sealed)

    def finish_post_dbm(self):
        from mta.runtime.scope_execution import _claim
        self.attempt=_claim(self.run.pk,scope='PostDBM',command_key='action-post-dbm',
            worker_reference='OWNED-ACTION-COMPONENT',compatibility_digest='a'*64,
            expected_phase='DBM',expected_receipt_digest=self.bpr.digest)
        with patch('mta.temporal.chain.produce_dbm',side_effect=AssertionError('DBM replay')):
            return self.finish()

    def test_sleep_after_dbm_remains_pending_through_final_and_is_not_replayed(self):
        from mta.runtime.services import read_outputs
        from mta.runtime.temporal import command_states
        self.pause_bpr(scope='UptoDBM')
        event=self.action()
        immediate=self.state(self.bpr,event.pk)
        result=self.finish_post_dbm()
        terminal=read_outputs(result,include_reports=False)['ClosingState'][0]
        self.assertEqual(terminal['dbm']['NormsInSleepModeTbl'],immediate['NormsInSleepModeTbl'])
        self.assertTrue(terminal['dbm']['NormsInSleepModeTbl'])
        self.assertEqual(terminal['dbm']['Suggestions'],immediate['Suggestions'])
        next_opening,commands=command_states(result,terminal)
        self.assertEqual(next_opening,terminal)
        self.assertEqual(commands,[])
        self.assertEqual(self.action().pk,event.pk)  # Exact retry after terminal commit.

    def test_apply_after_dbm_keeps_norm_and_pending_acceptance_through_final(self):
        from mta.runtime.services import read_outputs
        self.pause_bpr(scope='UptoDBM')
        event=self.action('APPLY')
        immediate=self.state(self.bpr,event.pk)
        self.assertEqual(immediate['DBMMaster'],self.base_state['DBMMaster'])
        self.assertNotEqual(immediate['NormAcceptanceTbl'],self.base_state['NormAcceptanceTbl'])
        result=self.finish_post_dbm()
        terminal=read_outputs(result,include_reports=False)['ClosingState'][0]
        self.assertEqual(terminal['dbm']['DBMMaster'],immediate['DBMMaster'])
        self.assertEqual(terminal['dbm']['NormAcceptanceTbl'],immediate['NormAcceptanceTbl'])
        self.assertTrue(terminal['dbm']['NormAcceptanceTbl'])

    def raw_header(self,key,**changes):
        from mta.runtime.models import RunCommand
        from mta.serialization import digest
        payload=dict(operation='APPLY',selected=self.selected,
            timestamp=self.run.business_date.isoformat()+'T10:00:00',actor='raw-denial-test')
        fields=dict(run=self.run,phase_acceptance=self.bpr,idempotency_key=key,payload=payload,
            digest=digest(payload),before_digest=digest(self.base_state),after_digest=digest(self.base_state),
            state_sealed=False,scope_parent_revision=0)
        fields.update(changes)
        return RunCommand.objects.create(**fields)

    def test_raw_stage_cut_and_partial_or_branched_seals_are_denied(self):
        from django.db import connection,transaction,DatabaseError
        from mta.runtime.models import RunCommand,RunPhaseAcceptance
        from mta.runtime.relational_state import save_image
        self.pause_bpr()
        pre=RunPhaseAcceptance.objects.get(run=self.run,phase='PRE_BPR')
        for changes in ({'phase_acceptance':pre},
                        {'phase_acceptance':None},
                        {'scope_revision_before':[0,0,0,0,0]},
                        {'scope_parent_revision':1}):
            with self.subTest(changes=changes):
                with self.assertRaises(DatabaseError),transaction.atomic():self.raw_header('wrong',**changes)
        with self.assertRaises(DatabaseError),transaction.atomic():
            self.raw_header('partial')
            with connection.cursor() as cursor:cursor.execute('SET CONSTRAINTS accepted_command_complete IMMEDIATE')
        self.assertFalse(RunCommand.objects.filter(run=self.run).exists())
        with self.assertRaisesRegex(DatabaseError,'released stage/action head'),transaction.atomic():
            first=self.raw_header('branch-one');second=self.raw_header('branch-two')
            for event in (first,second):
                event.state_manifest={'NormAcceptanceTbl':save_image(self.run,
                    'action/'+str(event.pk)+'/NormAcceptanceTbl','closing/dbm/NormAcceptanceTbl',
                    self.base_state['NormAcceptanceTbl'])}
                event.save(update_fields=['state_manifest'])
        self.assertFalse(RunCommand.objects.filter(run=self.run).exists())
        event=self.action('APPLY')
        with self.assertRaises(DatabaseError),transaction.atomic():
            RunCommand.objects.filter(pk=event.pk).update(state_manifest={})

    def test_real_counter_guard_tracks_action_images_and_denies_unknown_write(self):
        """Actual PostgreSQL counter mechanics; metadata carrier, NOT native admission."""
        from django.db import transaction
        from mta.runtime.scope_revisions import require_current
        from mta.runtime.models import RunCommand
        from mta.runtime.mdm_models import MdmTask
        self.pause_bpr(counter=True)
        before=require_current(self.run)
        event=self.action('APPLY')
        after=require_current(self.run)
        self.assertEqual(event.scope_revision_before,before)
        self.assertEqual(event.scope_revision_after,after)
        self.assertGreater(after[3],before[3])
        self.assertEqual(after[:3]+after[4:],before[:3]+before[4:])
        with transaction.atomic():
            MdmTask.objects.create(source=self.source,TaskID='FOREIGN-ACTION-INPUT',TaskStatus='1',MasterId='1',Actiontype=1)
            with self.assertRaisesRegex(ValueError,'revision changed'):
                self.action('SLEEP',expected_revision=event.pk,key='unknown-input-conflict')
            self.assertEqual(RunCommand.objects.filter(run=self.run).count(),1)
            transaction.set_rollback(True)
        self.assertEqual(require_current(self.run),after)
        self.assertEqual(self.action('APPLY').pk,event.pk)

    def test_phase_sql_denies_missing_action_revision_at_consumer_seal(self):
        from django.db import connection,transaction,DatabaseError
        from django.utils import timezone
        from mta.runtime.scope_execution import _claim,_setting,_begin_phase
        self.pause_bpr();self.action('APPLY')
        attempt=_claim(self.run.pk,scope='PostBPR',command_key='wrong-consumer',
            worker_reference='OWNED-ACTION-COMPONENT',compatibility_digest='a'*64,
            expected_phase='BPR',expected_receipt_digest=self.bpr.digest)
        with self.assertRaisesRegex(DatabaseError,'exact action revision'),transaction.atomic(), \
                _setting('fresh.scope_worker',attempt.worker_token):
            receipt=_begin_phase(attempt,self.run,'DBM')
            with connection.cursor() as cursor:
                cursor.execute('UPDATE mta.fresh_mta_runphaseacceptance SET state_sealed=true, '
                    "metadata='{}'::jsonb,digest=%s,accepted_at=%s WHERE id=%s",
                    ['f'*64,timezone.now(),receipt.pk])
