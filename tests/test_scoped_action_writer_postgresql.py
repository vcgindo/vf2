"""Actual guarded runtime transaction on rollback fixtures, not native acceptance."""
from contextlib import contextmanager
from copy import deepcopy, copy
import json
import os
import unittest
from unittest.mock import patch
from uuid import uuid4

from tests import test_scoped_dbm_api_postgresql as fixtures


@unittest.skipUnless(os.environ.get('VF_PHASE_POSTGRES_PROOF')=='1','Owned PostgreSQL required')
class ScopedActionWriterTests(unittest.TestCase):
    for name in ('setUp','rollback','owner','accept','bpr','parents','fetch','positive','start','scopes',
                 'reads','prepare_dbm','finish','publication_opening','prepare','binding','no_build','selected',
                 'select_suggestions'):
        locals()[name]=getattr(fixtures.ScopedDbmApiTests,name)
    row=staticmethod(fixtures.ScopedDbmApiTests.row)

    def ready(self):
        from django.test import override_settings
        from mta.runtime.scope_execution import _setting,_close_attempt
        self.select_suggestions()
        with _setting('fresh.scope_worker',self.attempt.worker_token):
            _close_attempt(self.attempt,self.run,'RELEASED',{})
        self.body=dict(self.payload,data=[dict(SKUCode=self.action_pair[0],WHCode=self.action_pair[1])])
        self.enterContext(override_settings(VF_MTA_ACTIONS_ENABLED=True))
        self.enterContext(patch('mta.presentation.actions.timestamp',return_value='2037-04-10T10:00:00'))

    @contextmanager
    def runtime(self):
        from django.db import connection
        from mta.mdm import owned_namespace as owned
        from mta.runtime import scoped_action_ownership as capability
        role='vftest_g2n_20261024_runtime'
        with connection.cursor() as c:
            c.execute('CREATE SCHEMA fresh_control')
            c.execute('CREATE TABLE fresh_control.owned_namespace(singleton boolean,consumer_oid oid)')
            c.execute('INSERT INTO fresh_control.owned_namespace VALUES(TRUE,(SELECT oid FROM pg_roles WHERE rolname=%s))',[role])
            c.execute('CREATE TABLE fresh_control.application_capability(singleton boolean,binding jsonb)')
            c.execute('INSERT INTO fresh_control.application_capability VALUES(TRUE,%s::jsonb)',
                [json.dumps(dict(original_registration=dict(consumer_role=role)))])
            body=capability.application_guard_body(owned.APPLICATION_WRITE_GUARD_BODY)
            c.execute('CREATE FUNCTION fresh_control.guard_application_write() RETURNS trigger LANGUAGE plpgsql AS $guard$'+body+'$guard$')
            for name,kind in owned.APPLICATION_WRITE_GUARDS.items():
                c.execute('CREATE TRIGGER application_write_boundary BEFORE '+('INSERT' if kind==7 else 'UPDATE')+
                    ' ON '+name+' FOR EACH ROW EXECUTE FUNCTION fresh_control.guard_application_write()')
            c.execute('GRANT USAGE ON SCHEMA mta,mta_state,mta_opening,fresh_control TO '+role)
            c.execute('GRANT SELECT ON ALL TABLES IN SCHEMA mta,mta_state,mta_opening,fresh_control TO '+role)
            c.execute('GRANT UPDATE(id) ON mta.fresh_mta_calculationrun,mta.fresh_mta_mdmsource TO '+role)
            c.execute('GRANT UPDATE(next_ordinal) ON mta.fresh_mta_remarkowner TO '+role)
            c.execute('GRANT INSERT ON mta_state.dbm_normacceptancetbl,mta_state.dbm_suggestions,mta_state.dbm_normsinsleepmodetbl TO '+role)
            catalogue=owned._application_catalogue(c)
            from mta.runtime.scoped_remark_ownership import application_grants as remark_grants
            grants={**remark_grants(catalogue),**capability.application_grants(catalogue)}
            self.assertTrue(grants)
            for name,grant in grants.items():
                for privilege in grant['table']:
                    cols='('+','.join(grant['columns'])+')' if privilege=='UPDATE' else ''
                    c.execute('GRANT '+privilege+cols+' ON '+name+' TO '+role)
                if 'INSERT' in grant['table']:
                    for item in owned.application_sequences(catalogue,name,production=True):
                        c.execute('GRANT USAGE ON SEQUENCE '+item['name']+' TO '+role)
            names=capability.application_functions(catalogue)|{
                'mta.scope_action_revision(target uuid)','mta.finite_capture_prefix_digest(leaf uuid)'}
            for function in catalogue['functions']:
                if function['name'] in names:
                    c.execute('SELECT %s::oid::regprocedure::text',[function['oid']])
                    c.execute('GRANT EXECUTE ON FUNCTION '+c.fetchone()[0]+' TO '+role)
            c.execute('SET LOCAL ROLE '+role)
        try:
            yield
        finally:
            if not connection.needs_rollback:
                with connection.cursor() as c:c.execute('RESET ROLE')

    def action(self,operation,body=None,*,authenticated=True):
        from django.test import RequestFactory
        from mta.presentation import views
        request=RequestFactory().post('/api/mta/Apply' if operation=='APPLY' else '/api/mta/Sleep',
            data=json.dumps(self.body if body is None else body),content_type='application/json',
            **({'HTTP_X_VECTORFLOW_IDENTITY':json.dumps(dict(id='component-action'))} if authenticated else {}))
        return views.dbm_action(request,operation=operation)

    def audit(self):
        from django.db import connection
        from mta.runtime.scoped_action_ownership import grants
        from mta.runtime.scoped_remark_ownership import GRANTS
        values={}
        with connection.cursor() as c:
            for table in sorted(set(grants())|set(GRANTS)|{'mta_state.dbm_normacceptancetbl','mta_state.dbm_suggestions','mta_state.dbm_normsinsleepmodetbl'}):
                c.execute('SELECT count(*) FROM '+table)
                values[table]=c.fetchone()[0]
        return values

    def _successful(self,operation):
        from mta.presentation import scoped_selection,scoped_dbm
        from mta.runtime import scoped_actions
        from mta.temporal.actions import apply_command
        from mta.serialization import storage
        self.ready()
        phase,_=scoped_actions.restore(self.run,self.receipt)
        before=scoped_actions.state_for(phase)
        expected=storage(apply_command(before,operation,[tuple(self.action_pair)],'2037-04-10T10:00:00'))
        old_rows=self.view.bpr.reports.rows('ExcessInventoryDetails')
        with self.runtime():
            response=self.action(operation)
            self.assertEqual(response.status_code,200,response.content)
            wire=json.loads(response.content)
            self.assertEqual(wire['data'],'' if operation=='APPLY' else None)
            self.assertEqual(wire['msg'],'Saved Succesfully')
            fresh=scoped_selection.selected()
            self.assertNotEqual(fresh.read_identity,self.view.read_identity)
            event=self.run.commands.get()
            self.assertTrue(event.state_sealed)
            self.assertTrue(event.append_transaction)
            actual=scoped_dbm.bind(self.receipt.pk,expected_digest=self.receipt.digest,action_revision=event.pk)
            self.assertEqual({name:actual.dbm[name] for name in scoped_actions.TABLES},expected)
            status,grid=fixtures.ScopedDbmApiTests.http(self)
            self.assertEqual(status,200,grid)
            status,count=fixtures.ScopedDbmApiTests.http(self,count=True)
            self.assertEqual((status,count['recordCount']),(200,'0'))
            self.assertEqual(self.view.bpr.reports.rows('ExcessInventoryDetails'),old_rows)
            self.assertEqual(len(event.scope_revision_after),5)
        self.run.refresh_from_db();self.capture.refresh_from_db()
        self.assertEqual((self.run.status,self.capture.status),('RUNNING','CAPTURED'))
        self.assertEqual(self.run.phase_acceptances.count(),2)

    def test_runtime_apply_commits_current_reference_and_exact_canonical_state(self):
        self._successful('APPLY')

    def test_runtime_sleep_commits_current_reference_and_exact_canonical_state(self):
        self._successful('SLEEP')

    def test_repeated_sleep_preserves_canonical_noop_with_nonempty_accepted_norms(self):
        from django.db import connection,transaction,DatabaseError
        from mta.runtime import scoped_actions
        from mta.presentation import scoped_selection,scoped_dbm
        from mta.temporal.actions import apply_command
        from mta.serialization import storage
        self.ready()
        phase,_=scoped_actions.restore(self.run,self.receipt)
        expected=scoped_actions.state_for(phase)
        reference=self.view.read_identity
        with self.runtime():
            for operation in ('APPLY','SLEEP','SLEEP'):
                lease_reference=reference
                expected=storage(apply_command(expected,operation,[tuple(self.action_pair)],'2037-04-10T10:00:00'))
                response=self.action(operation)
                self.assertEqual(response.status_code,200,response.content)
                current=scoped_selection.selected()
                self.assertNotEqual(current.read_identity,reference)
                reference=current.read_identity
                event=self.run.commands.order_by('-id').first()
                actual=scoped_dbm.bind(self.receipt.pk,expected_digest=self.receipt.digest,action_revision=event.pk)
                self.assertEqual({name:actual.dbm[name] for name in scoped_actions.TABLES},expected)
            self.assertEqual(event.before_digest,event.after_digest)
            self.assertEqual(set(event.state_manifest),{'NormAcceptanceTbl'})
            self.assertGreater(event.state_manifest['NormAcceptanceTbl']['count'],0)
            self.assertIsNone(json.loads(response.content)['msg'])
            self.assertEqual(self.run.commands.count(),3)
            for reference_id,actor in ((lease_reference['id'],'wrong-actor'),(uuid4(),'component-action')):
                with self.assertRaisesRegex(DatabaseError,'fresh current command'),transaction.atomic():
                    with connection.cursor() as c:
                        c.execute('SELECT mta.scope_cache_command(%s,%s)',[reference_id,actor])

    def test_disabled_rebound_or_public_transaction_guards_are_denied(self):
        from django.db import connection,transaction
        from mta.runtime.scoped_action_ownership import verify_guards
        for mutation in (
            'ALTER TABLE mta.fresh_mta_scopereportgeneration DISABLE TRIGGER scope_action_cache_insert',
            'ALTER FUNCTION mta.stamp_scoped_action_transaction() SECURITY DEFINER',
            'GRANT EXECUTE ON FUNCTION mta.stamp_scoped_action_transaction() TO PUBLIC'):
            with transaction.atomic():
                with connection.cursor() as c:c.execute(mutation)
                with self.assertRaises(ValueError):verify_guards()
                transaction.set_rollback(True)
            verify_guards()

    def test_late_refresh_failure_rolls_back_command_all_derived_rows_and_retry_succeeds(self):
        from mta.presentation import scoped_view,scoped_selection
        self.ready()
        before=self.audit()
        original=scoped_view.prepare
        def fail(*args,**kwargs):
            original(*args,**kwargs)
            raise OSError('late action reference fault')
        with self.runtime():
            with patch.object(scoped_view,'prepare',side_effect=fail),self.assertRaisesRegex(OSError,'late action'):
                self.action('SLEEP')
            self.assertEqual(self.audit(),before)
            self.assertEqual(scoped_selection.selected().read_identity,self.view.read_identity)
            self.assertEqual(self.action('SLEEP').status_code,200)
            self.assertEqual(self.run.commands.count(),1)

    def test_denied_scope_disabled_action_and_unleased_generation_leave_reference_unchanged(self):
        from django.db import connection,transaction,DatabaseError
        from django.test import override_settings
        from mta.presentation import scoped_selection
        self.ready();before=self.audit()
        with self.runtime():
            response=self.action('APPLY',dict(self.body,product_permissions=[]))
            self.assertEqual(response.status_code,403,response.content)
            self.assertEqual(self.action('APPLY',authenticated=False).status_code,403)
            with override_settings(VF_MTA_ACTIONS_ENABLED=False):
                self.assertEqual(self.action('APPLY').status_code,403)
            with self.assertRaises(DatabaseError),transaction.atomic():
                row=copy(self.view.bpr.reports.generation)
                row.pk=uuid4();row.save(force_insert=True)
            with self.assertRaisesRegex(DatabaseError,'requires its trusted table owner'),transaction.atomic():
                with connection.cursor() as c:
                    c.execute('UPDATE mta.fresh_mta_ingestionrevisionstate SET initialization_id=initialization_id')
            self.assertEqual(self.audit(),before)
            self.assertEqual(scoped_selection.selected().read_identity,self.view.read_identity)


@unittest.skipUnless(os.environ.get('VF_PHASE_POSTGRES_PROOF')=='1','Owned PostgreSQL required')
class ScopedFullGuardCompatibilityTests(unittest.TestCase):
    setUp=fixtures.ScopedDbmApiTests.setUp
    rollback=fixtures.ScopedDbmApiTests.rollback

    def test_extended_guard_retains_both_original_full_writer_boundaries(self):
        from tests.test_accepted_state_ownership_postgresql import AcceptedStateOwnershipTests as original
        from mta.runtime.scoped_action_ownership import application_guard_body
        from mta.mdm import owned_namespace
        for name in ('run_owner','sql','denied','command','manifest','seal'):
            setattr(self,name,getattr(original,name).__get__(self))
        body=application_guard_body(owned_namespace.APPLICATION_WRITE_GUARD_BODY)
        with patch.object(owned_namespace,'APPLICATION_WRITE_GUARD_BODY',body):
            original.test_original_consumer_guard_still_allows_manifest_only_sealing(self)
            original.test_restricted_consumer_seals_without_new_column_update_or_function_grants(self)
