"""Real application-role DBM actions over exact BPR-parent read dependencies.

Rollback-owned components; native initialization/admission is not qualified here.
"""
import json
import os
import unittest
from copy import deepcopy
from contextlib import contextmanager
from unittest.mock import patch
from tests.test_scoped_action_writer_postgresql import ScopedActionWriterTests as Original
from tests.test_scoped_dbm_api_postgresql import ScopedDbmApiTests as Api
from tests.test_scoped_api_postgresql import ScopedApiTests
from tests.test_scoped_view_postgresql import ScopedViewTests
from tests.test_scoped_uptodbm_view_postgresql import ScopedUptoDbmViewTests as Scope


@unittest.skipUnless(os.environ.get('VF_PHASE_POSTGRES_PROOF')=='1','Owned PostgreSQL required')
class ScopedDbmActionWriterTests(unittest.TestCase):
    for name in ('setUp','rollback','accept','parents','fetch','positive','start','scopes',
                 'reads','prepare_dbm','finish','publication_opening','prepare','binding','no_build',
                 'selected','select_suggestions','runtime','action','audit'):
        locals()[name] = getattr(Original,name)
    row = staticmethod(Original.row)
    bpr = Scope.bpr

    def owner(self, **options):
        # Reuse the existing declared hierarchy fixture with the new scope
        # request before capture. No retained native state is seeded/replaced.
        with patch.object(ScopedViewTests,'owner',Scope.owner):
            ScopedApiTests.owner(self,**options)

    def select_suggestions(self):
        from tests import test_h3_daily_integration as supplied
        from tests.production_h3_fixture import SEASON,CHILD,supplied_day
        opening = supplied.frame()
        # This DBM execution fixture uses the same explicit Rule1 boundary as
        # test_scoped_actions_postgresql. The BPR-only nullable historical row
        # fixture cannot satisfy the DBM native output contract.
        rows = [dict(SKUCode=SEASON,WhCode=CHILD,Type=1,NewNorm=24)]
        opening['opening']['state']['dbm']['Suggestions'] = deepcopy(rows)
        opening['opening']['state']['controls']['suggestions'] = deepcopy(rows)
        opening['opening']['state']['dbm']['ReasonCodes'] = [dict(Id=1,Reason='Declared component Rule 1')]
        opening['profile']['delivery']['batch']['AutoDBMActive'] = 0
        opening['opening']['state']['dbm']['DailyConsumption'] += [dict(
            SKUCode=SEASON,WhCode=CHILD,Stock=10,Consumption=2,GIT=4,Receipts=1,BlueZone=0,
            ReportDate=day) for day in ('2037-04-08','2037-04-09')]
        def facts(day):
            value = supplied_day(day)
            for row in value['day']['raw_daily']:
                if row['SKUCode']==SEASON and row['WhCode']==CHILD: row['Stock']=0
            return value
        with patch.object(supplied,'frame',return_value=opening), \
                patch('tests.production_h3_fixture.supplied_day',side_effect=facts):
            self.selected()
        self.action_pair = [SEASON,CHILD]

    def ready(self):
        from django.test import override_settings
        from mta.runtime.scoped_actions import calculate_dbm
        from mta.runtime.scope_execution import _setting,_close_attempt
        from mta.presentation import scoped_dbm_view,scoped_selection
        self.select_suggestions()
        self.dbm = calculate_dbm(self.attempt.pk,self.attempt.worker_token,compatibility_digest='a'*64)
        with _setting('fresh.scope_worker',self.attempt.worker_token):
            _close_attempt(self.attempt,self.run,'RELEASED',{})
        self.view = scoped_dbm_view.compose(self.view,self.dbm.pk,expected_digest=self.dbm.digest)
        self.anchor = scoped_selection.candidate(self.view)
        scoped_selection.write(self.selection_path,self.anchor)
        self.enterContext(override_settings(VF_MTA_PHASE_SELECTION=self.anchor,VF_MTA_ACTIONS_ENABLED=True))
        self.enterContext(patch('mta.presentation.actions.timestamp',return_value='2037-04-10T10:00:00'))
        self.body = dict(self.payload,data=[dict(SKUCode=self.action_pair[0],WHCode=self.action_pair[1])])
        self.assertTrue(self.view.dbm_context.dbm['Suggestions'])

    def successful(self, operation):
        from mta.runtime import scoped_actions
        from mta.presentation import scoped_selection
        from mta.temporal.actions import apply_command
        from mta.serialization import storage
        self.ready()
        phase,_ = scoped_actions.restore(self.run,self.dbm)
        before = scoped_actions.state_for(phase)
        expected = storage(apply_command(before,operation,[tuple(self.action_pair)],'2037-04-10T10:00:00'))
        master = storage(self.view.dbm_context.dbm['DBMMaster'])
        with self.runtime():
            from django.db import connection,transaction,DatabaseError
            from mta.runtime.scoped_action_ownership import migration
            # The installed dependency predicate permits only this BPR parent,
            # never PRE_BPR, an unrelated phase, or a foreign run.
            from uuid import uuid4
            with connection.cursor() as cursor:
                for parent,run,expected_link in (
                    (self.receipt.pk,self.run.pk,True),
                    (self.receipt.snapshot.parent.acceptance_id,self.run.pk,False),
                    (uuid4(),self.run.pk,False),(self.receipt.pk,uuid4(),False)):
                    cursor.execute('SELECT '+migration().dependency('%s::uuid','%s::uuid','%s::uuid'),
                        [parent,self.dbm.pk,parent,self.dbm.pk,run])
                    self.assertIs(cursor.fetchone()[0],expected_link)
            response = self.action(operation)
            self.assertEqual(response.status_code,200,response.content)
            self.assertEqual(json.loads(response.content)['msg'],'Saved Succesfully')
            fresh = scoped_selection.selected()
            event = self.run.commands.get()
            self.assertEqual(event.phase_acceptance_id,self.dbm.pk)
            self.assertEqual(fresh.bpr.sources.acceptance_id,self.receipt.pk)
            self.assertEqual(fresh.dbm_phase.pk,self.dbm.pk)
            self.assertNotEqual(fresh.read_identity,self.view.read_identity)
            self.assertEqual({name:fresh.dbm_context.dbm[name] for name in scoped_actions.TABLES},expected)
            self.assertEqual(storage(fresh.dbm_context.dbm['DBMMaster']),master)
            self.assertEqual(Api.http(self)[0],200)
            self.assertEqual(Api.http(self,count=True)[0],200)
            # Same endpoint repeated has canonical no-op behavior and no DBM
            # recalculation or pending-action consumption.
            self.assertEqual(self.action(operation).status_code,200)
            self.assertEqual(self.run.commands.count(),2)
            with self.assertRaisesRegex(DatabaseError,'fresh current command'),transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute('SELECT mta.scope_cache_command(%s,%s)',
                        [self.view.reference.pk,'component-action'])
        self.run.refresh_from_db(); self.capture.refresh_from_db()
        self.assertEqual((self.run.status,self.capture.status),('RUNNING','CAPTURED'))
        self.assertEqual(self.run.phase_acceptances.count(),3)
        self.assertEqual(self.run.phase_acceptances.filter(phase='DBM').count(),1)

    def test_runtime_apply_uses_dbm_phase_and_preserves_pending_norms(self):
        self.successful('APPLY')

    def test_runtime_sleep_uses_dbm_phase_without_sleep_consumer_replay(self):
        self.successful('SLEEP')

    def test_final_composed_selection_failure_rolls_back_command_and_parent_dependencies(self):
        from mta.presentation import scoped_selection
        self.ready(); before = self.audit()
        original = scoped_selection.selected
        def fail_after_composition():
            view = original()
            if view.bpr.sources.action_revision:
                raise OSError('final DBM composition validation fault')
            return view
        with self.runtime():
            with patch.object(scoped_selection,'selected',side_effect=fail_after_composition), \
                    self.assertRaisesRegex(OSError,'final DBM composition'):
                self.action('SLEEP')
            self.assertEqual(self.audit(),before)
            self.assertEqual(original().read_identity,self.view.read_identity)
            self.assertEqual(self.action('SLEEP').status_code,200)
            self.assertEqual(self.run.commands.count(),1)

    test_late_refresh_failure_rolls_back_command_all_derived_rows_and_retry_succeeds = (
        Original.test_late_refresh_failure_rolls_back_command_all_derived_rows_and_retry_succeeds)
    test_denied_scope_disabled_action_and_unleased_generation_leave_reference_unchanged = (
        Original.test_denied_scope_disabled_action_and_unleased_generation_leave_reference_unchanged)


from tests.test_scoped_remark_writer_postgresql import ScopedRemarkWriterTests as Remark


@unittest.skipUnless(os.environ.get('VF_PHASE_POSTGRES_PROOF')=='1','Owned PostgreSQL required')
class ScopedDbmRemarkWriterTests(unittest.TestCase):
    for name in ('setUp','rollback','owner','accept','parents','fetch','positive','start','scopes',
                 'reads','prepare_dbm','finish','publication_opening','prepare','binding','no_build',
                 'selected','select_suggestions','bpr'):
        locals()[name] = getattr(ScopedDbmActionWriterTests,name)
    row = staticmethod(Original.row)
    clock = Remark.clock
    audit_state = Remark.audit_state

    @contextmanager
    def runtime(self):
        from django.db import connection
        from mta.mdm import owned_namespace
        from mta.runtime import scoped_action_ownership
        # The older remark-only fixture predates DBM selected-view admission.
        # Grant precisely the verified production invoker roster, as the action
        # fixture does; no new production privilege or definer helper is added.
        with Remark.runtime(self):
            with connection.cursor() as cursor:
                cursor.execute('RESET ROLE')
                catalogue = owned_namespace._application_catalogue(cursor)
                names = scoped_action_ownership.application_functions(catalogue)
                for function in catalogue['functions']:
                    if function['name'] in names:
                        cursor.execute('SELECT %s::oid::regprocedure::text',[function['oid']])
                        cursor.execute('GRANT EXECUTE ON FUNCTION '+cursor.fetchone()[0]+' TO vftest_g2n_20261024_runtime')
                cursor.execute('SET LOCAL ROLE vftest_g2n_20261024_runtime')
            yield

    def ready(self):
        ScopedDbmActionWriterTests.ready(self)
        from tests.production_h3_fixture import CHILD
        self.batch = dict(self.payload,data=[dict(SKUCode='SUPPLIED-Z9',WhCode=CHILD,Remark='writer batch')])
        self.actor = dict(id='component-writer',name='Fixture name')

    def test_runtime_batch_refreshes_only_parent_history_and_preserves_inflight(self):
        from mta.presentation import scoped_remark_writer
        original = scoped_remark_writer.append
        def diagnostic(*args,**kwargs):
            try:return original(*args,**kwargs)
            except Exception:
                import traceback
                traceback.print_exc()
                raise
        with patch.object(scoped_remark_writer,'append',side_effect=diagnostic):
            Remark.test_runtime_batch_refreshes_only_parent_history_and_preserves_inflight(self)
