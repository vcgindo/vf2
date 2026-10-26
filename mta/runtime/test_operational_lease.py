"""Real PostgreSQL worker ownership; persisted daily fixtures use stub calculations."""
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path
import unittest
import uuid
import zipfile
from unittest.mock import patch
from django.test import override_settings

from mta.runtime.test_operational_attempts import OperationalAttemptProtocol
from mta.runtime.operational_attempts import fail_attempt,fail_interrupted_attempt,finish_attempt,operational_worker
from mta.runtime.operational_effects import operation,record_file,record_intent
from mta.runtime.operational_lease import operational_run_lease,OperationalLeaseError
from mta.runtime.operational_native import save_population
from mta.application.operational_io import write_file


class PublicationTransactionUnitTests(unittest.TestCase):
    """Cursor protocol witnesses only; native role/locking proof is separate."""
    def setUp(self):
        from types import SimpleNamespace
        from unittest.mock import MagicMock
        from psycopg.pq import TransactionStatus
        from mta.runtime import operational_lease as leases
        self.leases=leases
        self.session=MagicMock(closed=False,autocommit=True)
        self.session.info.backend_pid=41
        self.session.info.transaction_status=TransactionStatus.IDLE
        self.session.execute.return_value.fetchone.return_value=(True,)
        self.lease=leases.OperationalRunLease(uuid.uuid4(),self.session)
        self.attempt=SimpleNamespace(pk=uuid.uuid4(),run_id=self.lease.run_id,
            lease_key=self.lease.key,lease_owner=self.lease.owner,
            business_date=date(2026,10,26),
            run_output_digest='a'*64,action_digest='b'*64,source_digest='c'*64,
            configuration_id='d'*64)
        self.django=SimpleNamespace(in_atomic_block=False,get_autocommit=lambda:True,
                                    settings_dict={'NAME':'fresh_c6_exact'})

    def test_requires_real_context_even_with_unleased_test_flag(self):
        with override_settings(VF_OPERATIONAL_UNLEASED_TESTS=True), \
                patch.object(self.leases,'connection',self.django):
            with self.assertRaisesRegex(OperationalLeaseError,'Actual matching'):
                with self.lease.publication_transaction(self.attempt):
                    self.fail('unleased publication admitted')
        self.session.transaction.assert_not_called()

    def test_outer_django_or_lease_transaction_denies_before_begin(self):
        from psycopg.pq import TransactionStatus
        for kind in ('django_atomic','django_autocommit','lease_transaction','lease_autocommit','worker'):
            with self.subTest(kind=kind):
                self.setUp()
                if kind=='django_atomic':self.django.in_atomic_block=True
                elif kind=='django_autocommit':self.django.get_autocommit=lambda:False
                elif kind=='lease_transaction':self.session.info.transaction_status=TransactionStatus.INTRANS
                elif kind=='lease_autocommit':self.session.autocommit=False
                else:self.attempt.lease_owner=uuid.uuid4()
                token=self.leases._current.set(self.lease)
                try:
                    with patch.object(self.leases,'connection',self.django), self.assertRaises(OperationalLeaseError):
                        with self.lease.publication_transaction(self.attempt):self.fail('invalid owner admitted')
                    self.session.transaction.assert_not_called()
                finally:self.leases._current.reset(token)

    def test_uses_one_lease_transaction_and_rechecks_before_commit(self):
        cursor=self.session.cursor.return_value.__enter__.return_value
        token=self.leases._current.set(self.lease)
        try:
            with patch.object(self.leases,'connection',self.django), \
                    patch.object(self.leases,'_publication_role',return_value={'registration':'exact'}) as role, \
                    patch.object(self.leases,'_publication_locks') as locks, \
                    patch.object(self.leases,'_publication_lock') as held:
                with self.lease.publication_transaction(self.attempt) as actual:
                    self.assertIs(actual,cursor)
                    locks.assert_called_once_with(cursor,self.lease,self.attempt)
                    actual.execute('bounded registrar witness')
                role.assert_called_with(cursor,self.lease,expected={'registration':'exact'})
                held.assert_called_once_with(cursor,self.lease)
            self.session.transaction.assert_called_once_with()
        finally:self.leases._current.reset(token)

    def test_commit_ack_error_is_unknown_not_automatic_retry_or_attempt_failure(self):
        import psycopg
        self.session.transaction.return_value.__exit__.side_effect=psycopg.OperationalError('lost acknowledgement')
        token=self.leases._current.set(self.lease)
        try:
            with patch.object(self.leases,'connection',self.django), \
                    patch.object(self.leases,'_publication_role',return_value={}), \
                    patch.object(self.leases,'_publication_locks'), \
                    patch.object(self.leases,'_publication_lock'), \
                    self.assertRaisesRegex(OperationalLeaseError,'outcome may be unknown'):
                with self.lease.publication_transaction(self.attempt):pass
            self.session.transaction.assert_called_once_with()
        finally:self.leases._current.reset(token)

    def test_lock_check_requires_same_pid_and_database_filter(self):
        from unittest.mock import MagicMock
        for row in ((41,False),(42,True)):
            cursor=MagicMock();cursor.fetchone.return_value=row
            with self.subTest(row=row), self.assertRaisesRegex(OperationalLeaseError,'this PID'):
                self.leases._publication_lock(cursor,self.lease)
            query=cursor.execute.call_args.args[0]
            self.assertIn('database=(SELECT oid',query)
            self.assertIn('pid=pg_backend_pid()',query)

    def test_lease_loss_before_commit_aborts_transaction_without_retry(self):
        cursor=self.session.cursor.return_value.__enter__.return_value
        cursor.fetchone.return_value=(41,False)
        token=self.leases._current.set(self.lease)
        try:
            with patch.object(self.leases,'connection',self.django), \
                    patch.object(self.leases,'_publication_role',return_value={}), \
                    patch.object(self.leases,'_publication_locks'), \
                    self.assertRaisesRegex(OperationalLeaseError,'this PID'):
                with self.lease.publication_transaction(self.attempt):pass
            self.session.transaction.assert_called_once_with()
            self.assertIs(self.session.transaction.return_value.__exit__.call_args.args[0],OperationalLeaseError)
        finally:self.leases._current.reset(token)

    def test_nonmember_issuer_cannot_enter_catalogued_owner(self):
        from unittest.mock import MagicMock
        from mta.mdm import owned_namespace as owned
        from mta.runtime.test_owned_namespace import OwnedNamespaceTests
        fixture=OwnedNamespaceTests();fixture.setUp()
        initial=dict(fixture.database,current_user_oid=11)
        cursor=MagicMock();cursor.fetchone.return_value=(False,)
        with patch.object(self.leases,'connection',self.django), \
                patch.object(owned,'_database_identity',return_value=initial), \
                patch.object(owned,'_registered_identity') as registration, \
                self.assertRaisesRegex(OperationalLeaseError,'cannot enter'):
            self.leases._publication_role(cursor,self.lease)
        registration.assert_not_called()
        cursor.execute.assert_called_once()

    def test_catalogued_owner_role_is_quoted_and_identity_revalidated(self):
        from unittest.mock import MagicMock
        from mta.mdm import owned_namespace as owned
        from mta.runtime.test_owned_namespace import OwnedNamespaceTests
        fixture=OwnedNamespaceTests();fixture.setUp()
        fixture.registration['owner']['name']='owner"catalogued'
        fixture.database['owner']['name']='owner"catalogued'
        initial=dict(fixture.database,current_user_oid=11)
        cursor=MagicMock();cursor.fetchone.side_effect=[(True,),(41,True)]
        with patch.object(self.leases,'connection',self.django), \
                patch.object(owned,'_database_identity',side_effect=[initial,fixture.database]), \
                patch.object(owned,'_registered_identity',return_value=fixture.registration), \
                patch.object(owned,'_catalogue_evidence',return_value=fixture.evidence):
            result=self.leases._publication_role(cursor,self.lease)
        self.assertEqual(result,fixture.registration)
        self.assertEqual(cursor.execute.call_args_list[1].args[0].as_string(),
                         'SET LOCAL ROLE "owner""catalogued"')

    def test_foreign_db_issuer_membership_or_unentered_owner_denies(self):
        from unittest.mock import MagicMock
        from mta.mdm import owned_namespace as owned
        from mta.runtime.test_owned_namespace import OwnedNamespaceTests
        for change in ('database_name','database_oid','issuer','membership','owner_role'):
            fixture=OwnedNamespaceTests();fixture.setUp()
            initial=dict(fixture.database,current_user_oid=11)
            if change=='database_name':initial['name']='foreign'
            elif change=='database_oid':initial['oid']=999
            elif change=='issuer':initial['session_user_oid']=12
            elif change=='membership':fixture.evidence['issuer_roles']=[]
            elif change=='owner_role':fixture.database['current_user_oid']=11
            cursor=MagicMock();cursor.fetchone.side_effect=[(True,),(41,True)]
            with self.subTest(change=change), patch.object(self.leases,'connection',self.django), \
                    patch.object(owned,'_database_identity',side_effect=[initial,fixture.database]), \
                    patch.object(owned,'_registered_identity',return_value=fixture.registration), \
                    patch.object(owned,'_catalogue_evidence',return_value=fixture.evidence), \
                    self.assertRaises(ValueError):
                self.leases._publication_role(cursor,self.lease)

    def _locked_rows(self,*,action=False):
        from mta.serialization import digest
        payload=dict(operation='APPLY',timestamp='2026-10-26T12:00:00')
        actions=[dict(id=1,digest=digest(payload),before='e'*64,after='f'*64)] if action else []
        self.attempt.action_digest=digest(actions)
        self.attempt.source_digest=digest(dict(input='1'*64,output=self.attempt.run_output_digest,
                                               production='2'*64,actions=actions))
        run=('DAILY_CHAIN','SUCCEEDED',self.attempt.business_date,'1'*64,self.attempt.run_output_digest,'2'*64)
        attempt=(self.lease.run_id,'RUNNING',self.attempt.business_date,self.attempt.run_output_digest,
                 self.attempt.action_digest,self.attempt.source_digest,self.attempt.configuration_id,
                 self.lease.key,self.lease.owner)
        return run,attempt,[(1,payload,digest(payload),'e'*64,'f'*64,True)] if action else []

    def test_source_run_attempt_lock_order_and_same_connection_action_identity(self):
        from unittest.mock import MagicMock
        run,attempt,events=self._locked_rows(action=True)
        cursor=MagicMock()
        cursor.fetchone.side_effect=[('native-source','CONSUMED'),run,attempt,
                                    ('native-source','CONSUMED'),(41,True)]
        cursor.fetchall.return_value=events
        self.leases._publication_locks(cursor,self.lease,self.attempt)
        calls=cursor.execute.call_args_list
        self.assertEqual(calls[1].args[1],('fresh-mdm-supplier:native-source',))
        self.assertIn('pg_advisory_xact_lock(hashtextextended(%s,0))',calls[1].args[0])
        self.assertIn('fresh_mta_calculationrun',calls[2].args[0])
        self.assertIn('fresh_mta_operationalattempt',calls[3].args[0])
        self.assertIn('phase_acceptance_id IS NULL ORDER BY id',calls[5].args[0])

    def test_changed_run_capture_worker_or_action_denies_before_yield(self):
        from unittest.mock import MagicMock
        for change in ('run','capture','worker','action','payload','unsealed'):
            run,attempt,events=self._locked_rows(action=True)
            final_capture=('native-source','CONSUMED')
            if change=='run':run=(*run[:4],'9'*64,run[5])
            elif change=='capture':final_capture=('foreign-source','CONSUMED')
            elif change=='worker':attempt=(*attempt[:-1],uuid.uuid4())
            elif change=='action':events=[]
            elif change=='payload':events[0][1]['operation']='SLEEP'
            else:events=[(*events[0][:-1],False)]
            cursor=MagicMock();cursor.fetchall.return_value=events
            cursor.fetchone.side_effect=[('native-source','CONSUMED'),run,attempt,final_capture,(41,True)]
            with self.subTest(change=change), self.assertRaises(OperationalLeaseError):
                self.leases._publication_locks(cursor,self.lease,self.attempt)


class OperationalLeaseProtocol(unittest.TestCase):
    run_day=OperationalAttemptProtocol.run_day
    calculate=OperationalAttemptProtocol.calculate
    start=OperationalAttemptProtocol.start

    def setUp(self):
        OperationalAttemptProtocol.setUp(self)
        flags=override_settings(VF_OPERATIONAL_UNLEASED_TESTS=False)
        flags.enable();self.addCleanup(flags.disable)
        self.calls=len(self.seen)

    def tearDown(self):
        self.assertEqual(len(self.seen),self.calls)

    def test_unleased_start_denied_before_attempt_or_folder(self):
        before=list(Path(self.temp.name).iterdir())
        with self.assertRaisesRegex(OperationalLeaseError,'lease required'):self.start()
        self.assertEqual(list(Path(self.temp.name).iterdir()),before)
        self.assertFalse(self.run.operationalattempt_set.exists())

    def test_live_worker_excludes_second_session_and_self_reclamation(self):
        with operational_run_lease(self.run.pk):
            owner=self.start()
            def contender():
                with operational_run_lease(self.run.pk):raise AssertionError('Second worker admitted')
            with ThreadPoolExecutor(max_workers=1) as pool:
                with self.assertRaisesRegex(OperationalLeaseError,'live worker'):
                    pool.submit(contender).result(timeout=10)
            with self.assertRaisesRegex(ValueError,'prior managed worker'):fail_interrupted_attempt(owner.pk)
            owner.refresh_from_db();self.assertEqual(owner.status,'RUNNING')
            fail_attempt(owner.pk,'test worker finished')

    def test_lost_session_retains_files_then_new_worker_records_interruption(self):
        with operational_run_lease(self.run.pk) as lease:
            owner=self.start()
            with operation(owner,**self.roster[0]) as first:
                write_file(owner.root,'output/kept.csv',b'kept')
                record_file(first,relative_path='output/kept.csv',role='output')
            with self.assertRaisesRegex(OperationalLeaseError,'closed'):
                with operation(owner,**self.roster[1]) as interrupted:
                    write_file(owner.root,'output/partial.csv',b'partial')
                    lease.session.close()
            owner.refresh_from_db();interrupted.refresh_from_db()
            self.assertEqual((owner.status,interrupted.status),('RUNNING','RUNNING'))
        with operational_run_lease(self.run.pk):
            failed=fail_interrupted_attempt(owner.pk)
            self.assertEqual(failed.status,'FAILED')
            first.refresh_from_db();interrupted.refresh_from_db()
            self.assertEqual((first.status,interrupted.status),('SUCCEEDED','FAILED'))
            self.assertEqual(Path(owner.root,'output/partial.csv').read_bytes(),b'partial')
            retry=self.start(retry_of_id=owner.pk)
            self.assertNotEqual(retry.root,owner.root)
            self.assertEqual(retry.source_digest,owner.source_digest)
            fail_attempt(retry.pk,'bounded protocol complete')

    def test_released_worker_cannot_mutate_receipts_populations_or_finish(self):
        with operational_run_lease(self.run.pk):
            owner=self.start()
            with operation(owner,**self.roster[0]) as effect:pass
        actions=[lambda:record_file(effect,relative_path='a',role='output'),
                 lambda:save_population(owner,'empty','BPR/BPRExceptions',[]),
                 lambda:record_intent(effect,alert_name='a',branch='b',stage='c',source_digest='a'*64,
                    recipients='',subject=None,body=None,disposition='DISABLED',reason='disabled',attachments=[]),
                 lambda:finish_attempt(owner),lambda:fail_attempt(owner.pk,'not permitted')]
        for action in actions:
            with self.assertRaises(OperationalLeaseError):action()
        with override_settings(VF_OPERATIONAL_UNLEASED_TESTS=True):
            with self.assertRaisesRegex(OperationalLeaseError,'Managed attempt'):finish_attempt(owner)
        with operational_run_lease(self.run.pk):
            fail_interrupted_attempt(owner.pk)

    def test_legacy_unleased_attempt_is_not_automatically_reclaimed(self):
        with override_settings(VF_OPERATIONAL_UNLEASED_TESTS=True):owner=self.start()
        with operational_run_lease(self.run.pk):
            with self.assertRaisesRegex(ValueError,'prior managed worker'):fail_interrupted_attempt(owner.pk)
        owner.refresh_from_db();self.assertEqual(owner.status,'RUNNING')
        with override_settings(VF_OPERATIONAL_UNLEASED_TESTS=True):fail_attempt(owner.pk,'explicit test cleanup')

    def test_outer_worker_error_is_failed_without_calculation(self):
        with self.assertRaisesRegex(RuntimeError,'between operations'):
            with operational_worker(run_id=self.run.pk,configuration_id=self.config.pk,
                    request_key=uuid.uuid4().hex,owned_root=self.temp.name,
                    expected_output_digest=self.run.output_digest) as owner:
                with operation(owner,**self.roster[0]):pass
                raise RuntimeError('between operations')
        owner.refresh_from_db()
        self.assertEqual(owner.status,'FAILED')
        self.assertEqual(owner.operations.get().status,'SUCCEEDED')
        self.assertIn('between operations',owner.failure)

    def _lose_during_mutation(self,kind):
        from mta.application import operational_io
        from mta.runtime import operational_native
        from mta.runtime.operational_models import OperationalAlertIntent
        with operational_run_lease(self.run.pk) as lease:
            owner=self.start()
            with self.assertRaises(OperationalLeaseError):
                with operation(owner,**self.roster[0]) as effect:
                    if kind=='archive':
                        target=Path(owner.root,'archive.zip')
                        with zipfile.ZipFile(target,'x') as zipped:zipped.writestr('a.csv',b'exact')
                        original=operational_io.zip_members
                        def lose(*args,**kwargs):
                            result=original(*args,**kwargs);lease.session.close();return result
                        with patch.object(operational_io,'zip_members',side_effect=lose):
                            record_file(effect,relative_path='archive.zip',role='output',archive=True)
                    elif kind=='intent':
                        receipt=write_file(owner.root,'attachment.csv',b'exact')
                        original=operational_io.verify_file
                        def lose(*args,**kwargs):
                            result=original(*args,**kwargs);lease.session.close();return result
                        with patch.object(operational_io,'verify_file',side_effect=lose):
                            record_intent(effect,alert_name='lease-fixture',branch='positive',stage='fixture',
                                source_digest='b'*64,recipients='fixture@example.invalid',subject='local',
                                body='local',disposition='LOCAL_READY',reason='',attachments=[receipt])
                    else:
                        original=operational_native.read_population
                        def lose(*args,**kwargs):
                            result=original(*args,**kwargs);lease.session.close();return result
                        with patch.object(operational_native,'read_population',side_effect=lose):
                            save_population(owner,'empty','BPR/BPRExceptions',[])
            self.assertFalse(effect.files.exists())
            self.assertFalse(OperationalAlertIntent.objects.filter(run=self.run).exists())
            self.assertFalse(operational_native.OperationalPopulation.objects.filter(attempt=owner).exists())
            owner.refresh_from_db();self.assertEqual(owner.status,'RUNNING')
        with operational_run_lease(self.run.pk):fail_interrupted_attempt(owner.pk)

    def test_lease_loss_during_archive_read_rolls_back_receipt(self):self._lose_during_mutation('archive')

    def test_lease_loss_during_attachment_check_rolls_back_intent(self):self._lose_during_mutation('intent')

    def test_lease_loss_during_population_readback_rolls_back_rows(self):self._lose_during_mutation('population')

    def test_failure_transition_yields_to_new_owner_after_lease_loss(self):
        from mta.runtime import operational_effects
        original=operational_effects.require_attempt_lease
        fail_phase=False
        future=None
        with ThreadPoolExecutor(max_workers=1) as pool:
            with operational_run_lease(self.run.pk) as lease:
                owner=self.start()
                def reclaim():
                    with operational_run_lease(self.run.pk):return fail_interrupted_attempt(owner.pk).failure
                def checked(value):
                    nonlocal fail_phase,future
                    if fail_phase:
                        fail_phase=False
                        lease.session.close()
                        future=pool.submit(reclaim)
                    return original(value)
                with patch.object(operational_effects,'require_attempt_lease',side_effect=checked):
                    with self.assertRaisesRegex(RuntimeError,'original failure'):
                        with operation(owner,**self.roster[0]):
                            fail_phase=True
                            raise RuntimeError('original failure')
            self.assertIn('Interrupted operational worker',future.result(timeout=10))
        owner.refresh_from_db()
        self.assertEqual(owner.status,'FAILED')
        self.assertIn('Interrupted operational worker',owner.failure)

    def _lose_during_backup_write(self,update):
        from mta.runtime.operational_backup import _save_backup
        from mta.runtime.operational_models import OperationalBackup
        original=OperationalBackup.save
        with operational_run_lease(self.run.pk) as lease:
            owner=self.start()
            with self.assertRaises(OperationalLeaseError):
                with operation(owner,**self.roster[7]) as effect:
                    write_file(owner.root,'backup.dump',b'protocol-only')
                    file=record_file(effect,relative_path='backup.dump',role='postgres-backup')
                    values=dict(database_name='protocol-only',database_system='PostgreSQL',method='protocol-only',
                        snapshot_identity='protocol-only',tool_sha256='a'*64,file=file,logical_digest='b'*64,
                        restore_status='RUNNING')
                    prior=_save_backup(effect,**values) if update else None
                    def lose(instance,*args,**kwargs):
                        result=original(instance,*args,**kwargs);lease.session.close();return result
                    with patch.object(OperationalBackup,'save',new=lose):
                        if update:_save_backup(effect,prior,restore_status='VERIFIED')
                        else:_save_backup(effect,**values)
            rows=list(effect.backups.values_list('restore_status',flat=True))
            self.assertEqual(rows,['RUNNING'] if update else [])
        with operational_run_lease(self.run.pk):fail_interrupted_attempt(owner.pk)

    def test_lease_loss_during_backup_create_rolls_back_receipt(self):self._lose_during_backup_write(False)

    def test_lease_loss_during_backup_status_write_rolls_back_success(self):self._lose_during_backup_write(True)

