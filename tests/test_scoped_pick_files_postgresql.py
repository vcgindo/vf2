"""Derived files from real accepted typed BPR; all business fixtures roll back."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from tests import test_prepared_effects_postgresql as prepared_tests


@unittest.skipUnless(os.environ.get('VF_PHASE_POSTGRES_PROOF')=='1','Owned PostgreSQL required')
class ScopedPickFileTests(unittest.TestCase):
    for _name in ('setUp','rollback','owner','accept'):
        locals()[_name]=getattr(prepared_tests.PreparedEffectsPostgresTests,_name)

    def bpr(self, *, captured_root=True, counter=False):
        from mta.temporal.chain import produce_bpr
        from mta.application.native_output_contracts import native_assignments
        from mta.application.stage_calculation_sources import capture_bpr
        from mta.runtime.calculation_effects import _accept_calculation
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name).resolve()
        self.owner(pick_root=self.root if captured_root else None,claim=not counter)
        if counter:
            from tests.test_scope_revisions_postgresql import bind_metadata_counter_owner
            from mta.runtime.scope_execution import _claim
            bind_metadata_counter_owner(self.run,self.source)
            self.attempt=_claim(self.run.pk,scope='UptoBPR',command_key='owned-pick-counter',
                worker_reference='metadata-carrier-not-native',compatibility_digest='a'*64,
                expected_phase='START',expected_receipt_digest='')
        pre=self.accept()
        with native_assignments(True):self.phase=produce_bpr(self.prepared)
        self.sources=capture_bpr(self.phase,{'supplier':self.phase.context.prior['supplier']})
        self.receipt=_accept_calculation(self.attempt.pk,self.attempt.worker_token,
            self.phase,self.sources,parent=pre,compatibility_digest='a'*64)
        self.pre_receipt=pre
        return self.receipt

    def prepare_files(self, **options):
        from mta.runtime.scoped_pick_files import prepare
        return prepare(self.receipt.pk,expected_digest=self.receipt.digest,**options)

    def directory(self, receipt):
        return self.root/str(self.run.pk)/'scope-pick'/str(self.receipt.pk)/str(receipt.directory)

    def test_exact_files_use_persisted_bpr_and_dbm_retains_owner(self):
        from django.db import connection
        from mta.application.complete_daily_batch_files import PICK_NAMES,reports_from_pick_state,sqlcmd_bytes
        from mta.runtime.scoped_pick_files import read,open_file
        from mta.runtime.scoped_actions import calculate_dbm
        from mta.runtime.models import RunPhaseAcceptance
        self.bpr()
        self.assertTrue(self.phase.pick_state['LogisticPickList'])
        self.assertTrue(self.phase.pick_state['PickListDataForTruckFormation'])
        before={r.pk:r.digest for r in RunPhaseAcceptance.objects.filter(run=self.run)}
        expected=reports_from_pick_state(self.phase.pick_state)
        with patch('mta.temporal.chain.produce_bpr',side_effect=AssertionError('BPR replay')):
            receipt=self.prepare_files()
        self.assertEqual(set(receipt.files),set(PICK_NAMES.values()))
        for kind,name in PICK_NAMES.items():
            with open_file(self.receipt.pk,name,expected_digest=self.receipt.digest) as stream:
                self.assertEqual(stream.read(),sqlcmd_bytes(expected[kind]['resultsets']))
        self.assertEqual(self.prepare_files().digest,receipt.digest)
        self.assertEqual({r.pk:r.digest for r in RunPhaseAcceptance.objects.filter(run=self.run)},before)
        # The scope started as UptoBPR; continue through a genuine PostBPR claim.
        from mta.runtime.scope_execution import _setting,_close_attempt,_claim
        with _setting('fresh.scope_worker',self.attempt.worker_token):
            _close_attempt(self.attempt,self.run,'RELEASED',{})
        continuation=_claim(self.run.pk,scope='PostBPR',command_key='pick-files-post-bpr',
            worker_reference='owned-file-component',compatibility_digest='a'*64,
            expected_phase='BPR',expected_receipt_digest=self.receipt.digest)
        dbm=calculate_dbm(continuation.pk,continuation.worker_token,compatibility_digest='a'*64)
        self.assertEqual(read(dbm.pk,expected_digest=dbm.digest).pk,receipt.pk)
        self.run.refresh_from_db();self.capture.refresh_from_db()
        self.assertEqual((self.run.status,self.capture.status),('RUNNING','CAPTURED'))
        self.assertFalse(self.run.output_digest)
        with connection.cursor() as cursor:cursor.execute('SET CONSTRAINTS ALL IMMEDIATE')

    def test_failed_copy_has_no_receipt_and_retry_does_not_replay_business(self):
        from mta.runtime.models import ScopePickFiles,RunPhaseAcceptance
        self.bpr()
        before={r.pk:r.digest for r in RunPhaseAcceptance.objects.filter(run=self.run)}
        from mta.runtime.scoped_pick_files import _copy_file
        calls=[]
        def interrupted(source,target,name):
            calls.append(name)
            if len(calls)==3:raise OSError('injected interrupted third download copy')
            return _copy_file(source,target,name)
        with patch('mta.runtime.scoped_pick_files._copy_file',side_effect=interrupted), \
                self.assertRaisesRegex(OSError,'interrupted third'):
            self.prepare_files()
        self.assertFalse(ScopePickFiles.objects.filter(phase=self.receipt).exists())
        from mta.runtime.scoped_pick_files import read,PickFilesUnavailable
        with self.assertRaisesRegex(PickFilesUnavailable,'not prepared'):
            read(self.receipt.pk,expected_digest=self.receipt.digest)
        with patch('mta.temporal.chain.produce_bpr',side_effect=AssertionError('BPR replay')):
            receipt=self.prepare_files()
        self.assertTrue(receipt.digest)
        self.assertEqual({r.pk:r.digest for r in RunPhaseAcceptance.objects.filter(run=self.run)},before)
        # Both failed and successful private directories survive; only one is registered.
        self.assertEqual(len(list(self.directory(receipt).parent.iterdir())),2)

    def test_missing_corrupt_files_deny_until_exact_same_receipt_repair(self):
        from mta.runtime.scoped_pick_files import read,open_file,PickFilesUnavailable
        from mta.application.complete_daily_batch_files import PICK_NAMES
        self.bpr();receipt=self.prepare_files();directory=self.directory(receipt)
        name=next(iter(PICK_NAMES.values()))
        original=(directory/'download'/name).read_bytes()
        (directory/'download'/name).write_bytes(b'partial')
        with self.assertRaises(PickFilesUnavailable):read(self.receipt.pk,expected_digest=self.receipt.digest)
        with self.assertRaises(PickFilesUnavailable):self.prepare_files()
        (directory/'output'/name).unlink()
        repaired=self.prepare_files(repair=True)
        self.assertEqual((repaired.directory,repaired.digest),(receipt.directory,receipt.digest))
        with open_file(self.receipt.pk,name,expected_digest=self.receipt.digest) as stream:
            self.assertEqual(stream.read(),original)
        self.assertEqual((directory/'output'/name).read_bytes(),original)
        for path in (directory/'download').iterdir():path.unlink()
        (directory/'download').rmdir()
        self.assertEqual(self.prepare_files(repair=True).digest,receipt.digest)
        self.assertEqual((directory/'download'/name).read_bytes(),original)
        with self.assertRaisesRegex(PickFilesUnavailable,'Unknown'):
            open_file(self.receipt.pk,'../other.csv',expected_digest=self.receipt.digest)

    def test_missing_root_wrong_phase_and_raw_receipt_mutations_are_denied(self):
        from django.db import connection,transaction,DatabaseError
        from mta.runtime.models import ScopePickFiles
        from mta.runtime.scoped_pick_files import prepare,PickFilesUnavailable
        self.bpr(captured_root=False)
        with self.assertRaises(PickFilesUnavailable):self.prepare_files()
        with self.assertRaises(PickFilesUnavailable):
            prepare(self.pre_receipt.pk,expected_digest=self.pre_receipt.digest)
        with self.assertRaises(DatabaseError),transaction.atomic():
            ScopePickFiles.objects.create(phase=self.receipt,source_digest=self.receipt.digest,
                recipe_digest='a'*64,files={},digest='b'*64)
        self.assertFalse(ScopePickFiles.objects.exists())

    def test_receipt_is_sql_immutable_and_candidate_links_are_denied(self):
        from django.db import connection,transaction,DatabaseError
        from mta.runtime.models import ScopePickFiles
        from mta.runtime.scoped_pick_files import PickFilesUnavailable,read
        self.bpr();receipt=self.prepare_files()
        for sql,args in (
            ('UPDATE mta.fresh_mta_scopepickfiles SET files=%s WHERE phase_id=%s',['{}',receipt.pk]),
            ('DELETE FROM mta.fresh_mta_scopepickfiles WHERE phase_id=%s',[receipt.pk]),
            ('TRUNCATE mta.fresh_mta_scopepickfiles',[])):
            with self.assertRaises(DatabaseError),transaction.atomic():
                with connection.cursor() as cursor:cursor.execute(sql,args)
        # A captured run cannot redirect files through a symlink into another owner.
        name=next(iter(receipt.files));file=self.directory(receipt)/'download'/name
        other=self.root/'unrelated';other.write_bytes(b'untouched')
        file.unlink();file.symlink_to(other)
        with self.assertRaises(PickFilesUnavailable):read(self.receipt.pk,expected_digest=self.receipt.digest)
        with self.assertRaises(PickFilesUnavailable):self.prepare_files(repair=True)
        self.assertEqual(other.read_bytes(),b'untouched')
        self.assertEqual(ScopePickFiles.objects.get(pk=receipt.pk).digest,receipt.digest)

    def test_disabled_or_replaced_custody_guard_denies_file_readiness(self):
        from django.db import connection,transaction
        from mta.runtime.scoped_pick_files import read,PickFilesUnavailable
        self.bpr();self.prepare_files()
        with connection.cursor() as cursor:cursor.execute('SET CONSTRAINTS ALL IMMEDIATE')
        for sql in (
            'ALTER TABLE mta.fresh_mta_scopepickfiles DISABLE TRIGGER scope_pick_files_immutable',
            'ALTER FUNCTION mta.guard_scope_pick_files() SECURITY DEFINER'):
            with transaction.atomic():
                with connection.cursor() as cursor:cursor.execute(sql)
                with self.assertRaises(PickFilesUnavailable):
                    read(self.receipt.pk,expected_digest=self.receipt.digest)
                transaction.set_rollback(True)
        self.assertTrue(read(self.receipt.pk,expected_digest=self.receipt.digest).digest)
        with transaction.atomic():
            statements=[
                'CREATE SCHEMA scope_pick_spoof',
                'CREATE FUNCTION scope_pick_spoof.guard_scope_pick_files() RETURNS trigger '
                'LANGUAGE plpgsql AS $$ BEGIN RETURN NEW; END $$',
                'DROP TRIGGER scope_pick_files_immutable ON mta.fresh_mta_scopepickfiles',
                'CREATE TRIGGER scope_pick_files_immutable BEFORE INSERT OR UPDATE OR DELETE '
                'ON mta.fresh_mta_scopepickfiles FOR EACH ROW '
                'EXECUTE FUNCTION scope_pick_spoof.guard_scope_pick_files()']
            with connection.cursor() as cursor:
                for sql in statements:cursor.execute(sql)
            with self.assertRaisesRegex(PickFilesUnavailable,'guard coverage'):
                read(self.receipt.pk,expected_digest=self.receipt.digest)
            transaction.set_rollback(True)

    def test_matching_hardlink_is_rejected_and_repair_preserves_other_file(self):
        from mta.runtime.scoped_pick_files import read,PickFilesUnavailable
        self.bpr();receipt=self.prepare_files();name=next(iter(receipt.files))
        download=self.directory(receipt)/'download'/name
        original=download.read_bytes();other=self.root/'other-owner.csv';other.write_bytes(original)
        download.unlink();os.link(other,download)
        with self.assertRaises(PickFilesUnavailable):read(self.receipt.pk,expected_digest=self.receipt.digest)
        with self.assertRaises(PickFilesUnavailable):self.prepare_files(repair=True)
        self.assertEqual(other.read_bytes(),original)

    def test_ancestor_swap_during_repair_cannot_overwrite_another_owner(self):
        from mta.runtime import scoped_pick_files as files
        self.bpr();receipt=self.prepare_files();directory=self.directory(receipt)
        name=next(iter(receipt.files));(directory/'download'/name).write_bytes(b'partial')
        other=self.root/'another-owner';other.mkdir()
        for owner in ('output','download'):
            (other/owner).mkdir()
            for filename in receipt.files:(other/owner/filename).write_bytes(b'other owner untouched')
        replace=os.replace;calls=[]
        def swapped(source,target,**descriptors):
            self.assertIn('src_dir_fd',descriptors);self.assertIn('dst_dir_fd',descriptors)
            if not calls:
                directory.rename(directory.with_name(directory.name+'-moved'))
                directory.symlink_to(other,target_is_directory=True)
            calls.append(source)
            return replace(source,target,**descriptors)
        with patch.object(files.os,'replace',side_effect=swapped),self.assertRaises(files.PickFilesUnavailable):
            self.prepare_files(repair=True)
        self.assertTrue(calls)
        for owner in ('output','download'):
            for filename in receipt.files:
                self.assertEqual((other/owner/filename).read_bytes(),b'other owner untouched')

    def test_pick_metadata_does_not_advance_business_revision(self):
        """Actual PostgreSQL counters; explicit metadata carrier, not native certification."""
        from mta.runtime.scope_revisions import require_current
        self.bpr(counter=True)
        before=require_current(self.run)
        receipt=self.prepare_files()
        self.assertTrue(receipt.digest)
        self.assertEqual(require_current(self.run),before)
