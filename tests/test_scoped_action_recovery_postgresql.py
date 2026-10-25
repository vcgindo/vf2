"""Released recovery ownership over the existing rollback-owned action fixture."""
import os
import unittest
from unittest.mock import patch
from tests import test_scoped_actions_postgresql as action_tests


@unittest.skipUnless(os.environ.get('VF_PHASE_POSTGRES_PROOF')=='1', 'Owned PostgreSQL required')
class ScopedActionRecoveryTests(unittest.TestCase):
    for _name in ('setUp','rollback','owner','accept','pause_bpr','state','action'):
        locals()[_name]=getattr(action_tests.ScopedActionTests, _name)

    def actionable(self):
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute('SELECT mta.actionable_scope_phase(%s,%s)', [self.run.pk,self.bpr.pk])
            return cursor.fetchone()[0]

    def failed_producer(self):
        from mta.runtime import scope_execution as workers
        close=workers._close_attempt
        def fail(attempt, run, status, failure):
            self.assertEqual(status,'RELEASED')
            return close(attempt, run, 'FAILED', {'type':'OwnedPreparationFailure'})
        with patch.object(workers,'_close_attempt',side_effect=fail):
            self.pause_bpr()
        self.producer=self.attempt
        self.producer.refresh_from_db()
        self.assertEqual(self.producer.status,'FAILED')
        self.assertFalse(self.actionable())

    def recover(self, *, status='RELEASED', previous=None):
        from mta.runtime.scope_execution import _claim,_setting,_close_attempt
        previous=previous or self.producer
        attempt=_claim(self.run.pk, scope=previous.scope, command_key=previous.command_key,
            worker_reference='RECOVERED-ACTION-OWNERSHIP-COMPONENT',
            compatibility_digest=previous.compatibility_digest, expected_phase='BPR',
            expected_receipt_digest=self.bpr.digest, recovery_of=previous.pk)
        if status!='ACTIVE':
            with _setting('fresh.scope_worker',attempt.worker_token):
                _close_attempt(attempt,self.run,status,{} if status=='RELEASED' else {'type':'OwnedRetryFailure'})
        return attempt

    def test_original_released_stage_still_actionable(self):
        self.pause_bpr()
        self.assertTrue(self.actionable())

    def test_forward_replacement_preserves_oid_acl_and_other_function_definitions(self):
        from django.db import connection
        from importlib import import_module
        migration=import_module('mta.runtime.migrations.0222_recovered_scope_actions')
        with connection.cursor() as cursor:
            def identities():
                cursor.execute("SELECT oid,proacl,proowner,prosecdef,proconfig FROM pg_proc "
                    "WHERE oid=to_regprocedure('mta.actionable_scope_phase(uuid,uuid)')")
                return cursor.fetchone()
            cursor.execute(migration.replace(migration.OLD))
            before=identities()
            cursor.execute("SELECT oid,pg_get_functiondef(oid) FROM pg_proc WHERE pronamespace='mta'::regnamespace "
                "AND oid<>to_regprocedure('mta.actionable_scope_phase(uuid,uuid)') ORDER BY oid")
            others=cursor.fetchall()
            cursor.execute(migration.SQL)
            self.assertEqual(identities(),before)
            cursor.execute("SELECT oid,pg_get_functiondef(oid) FROM pg_proc WHERE pronamespace='mta'::regnamespace "
                "AND oid<>to_regprocedure('mta.actionable_scope_phase(uuid,uuid)') ORDER BY oid")
            self.assertEqual(cursor.fetchall(),others)

    def test_released_recovery_keeps_failed_producer_and_permits_sleep(self):
        self.failed_producer()
        original=(self.bpr.attempt_id,self.bpr.digest,self.bpr.snapshot.state_digest)
        self.recover()
        self.assertTrue(self.actionable())
        event=self.action('SLEEP')
        self.assertTrue(event.state_sealed)
        self.producer.refresh_from_db();self.bpr.refresh_from_db()
        self.assertEqual(self.producer.status,'FAILED')
        self.assertEqual((self.bpr.attempt_id,self.bpr.digest,self.bpr.snapshot.state_digest),original)
        self.assertEqual(self.state(self.bpr,event.pk)['Suggestions'],[])

    def test_recovery_chain_permits_apply(self):
        self.failed_producer()
        failed=self.recover(status='FAILED')
        self.assertFalse(self.actionable())
        self.recover(previous=failed)
        self.assertTrue(self.actionable())
        event=self.action('APPLY')
        self.assertTrue(event.state_sealed)
        self.assertNotEqual(event.before_digest,event.after_digest)

    def test_active_or_failed_latest_recovery_denies(self):
        self.failed_producer()
        failed=self.recover(status='FAILED')
        self.assertFalse(self.actionable())
        self.recover(previous=failed,status='ACTIVE')
        self.assertFalse(self.actionable())
        with self.assertRaisesRegex(ValueError,'exact released'):
            self.action()

    def test_later_unrelated_command_denies_and_cannot_release_without_its_target(self):
        from django.db import transaction, DatabaseError
        from mta.runtime.scope_execution import _claim,_setting,_close_attempt
        self.pause_bpr()
        later=_claim(self.run.pk,scope='PostBPR',command_key='unrelated-command',
            worker_reference='UNRELATED-OWNERSHIP-COMPONENT',compatibility_digest='a'*64,
            expected_phase='BPR',expected_receipt_digest=self.bpr.digest)
        self.assertFalse(self.actionable())
        with self.assertRaisesRegex(DatabaseError,'calculation target'),transaction.atomic(), _setting('fresh.scope_worker',later.worker_token):
            _close_attempt(later,self.run,'RELEASED',{})
        later.refresh_from_db()
        with _setting('fresh.scope_worker',later.worker_token):
            _close_attempt(later,self.run,'FAILED',{'type':'OwnedUnrelatedFailure'})
        self.assertFalse(self.actionable())

    def test_delivery_finalization_rechecks_global_worker_under_run_lock(self):
        from mta.runtime import production_scope
        from mta.runtime.scope_execution import _claim
        self.pause_bpr()
        value=dict(command_key=self.attempt.command_key,compatibility_digest=self.attempt.compatibility_digest)
        with patch.object(production_scope,'_advance',return_value='delivery-only') as inner:
            self.assertEqual(production_scope.advance(self.run,value,worker_reference='test',delivery_only=True),'delivery-only')
            inner.assert_called_once()
        _claim(self.run.pk,scope='PostBPR',command_key='new-worker',worker_reference='COMPONENT',
            compatibility_digest='a'*64,expected_phase='BPR',expected_receipt_digest=self.bpr.digest)
        with patch.object(production_scope,'_advance') as inner,self.assertRaisesRegex(ValueError,'latest released'):
            production_scope.advance(self.run,value,worker_reference='test',delivery_only=True)
        inner.assert_not_called()

    def test_recovery_cannot_change_command_compatibility_or_head(self):
        from mta.runtime.scope_execution import _claim
        self.failed_producer()
        base=dict(scope='UptoBPR',command_key=self.producer.command_key,
            worker_reference='DENIED-RECOVERY-COMPONENT',compatibility_digest='a'*64,
            expected_phase='BPR',expected_receipt_digest=self.bpr.digest,recovery_of=self.producer.pk)
        for change in (dict(command_key='foreign'),dict(compatibility_digest='b'*64),
                dict(expected_phase='PRE_BPR'),dict(expected_receipt_digest='c'*64)):
            with self.subTest(change=change),self.assertRaises(ValueError):
                _claim(self.run.pk,**dict(base,**change))
