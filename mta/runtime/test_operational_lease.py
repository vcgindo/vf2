"""Real PostgreSQL worker ownership; persisted daily fixtures use stub calculations."""
from concurrent.futures import ThreadPoolExecutor
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

