"""Repair component protocol; parent success is a declared fixture, not O1–O9 acceptance."""
from pathlib import Path
from unittest.mock import patch
import unittest
import uuid
import zipfile
from django.test import override_settings
from django.utils import timezone
from mta.runtime.test_operational_attempts import OperationalAttemptProtocol
from mta.runtime.operational_attempts import start_attempt,finish_attempt,fail_interrupted_attempt
from mta.runtime.operational_effects import operation,record_file,verify_files
from mta.runtime.operational_lease import operational_run_lease,OperationalLeaseError
from mta.runtime.operational_models import OperationalAttempt
from mta.runtime.operational_repair import (
    materialize_repair,bind_repair_file,resolve_operational_file,EXACT,MEMBERS,
)


class OperationalRepairProtocol(unittest.TestCase):
    run_day=OperationalAttemptProtocol.run_day
    calculate=OperationalAttemptProtocol.calculate
    start=OperationalAttemptProtocol.start

    def setUp(self):
        OperationalAttemptProtocol.setUp(self)
        flags=override_settings(VF_OPERATIONAL_UNLEASED_TESTS=False)
        flags.enable();self.addCleanup(flags.disable)
        self.calls=len(self.seen)

    def tearDown(self):self.assertEqual(len(self.seen),self.calls)

    def archive(self,owner,path,payload=b'exact',year=2020):
        target=Path(owner.root,path);target.parent.mkdir(parents=True,exist_ok=True)
        info=zipfile.ZipInfo('report.csv',(year,1,1,0,0,0))
        with zipfile.ZipFile(target,'x') as zipped:zipped.writestr(info,payload)

    def parent(self,*,group='O4',copy=True):
        with operational_run_lease(self.run.pk):
            owner=self.start()
            specification=next(row for row in self.roster if row['group']==group)
            with operation(owner,**specification) as effect:
                self.archive(owner,'output/report.zip')
                original=record_file(effect,relative_path='output/report.zip',role='output',archive=True)
                if copy:
                    from mta.application.operational_io import copy_file
                    copy_file(owner.root,'output/report.zip','download/report.zip')
                    record_file(effect,relative_path='download/report.zip',role='download',archive=True)
            # Declared historical component fixture. Do not claim full roster,
            # producer or backup acceptance from this direct test-only setup.
            OperationalAttempt.objects.filter(pk=owner.pk).update(status='SUCCEEDED',completed_at=timezone.now())
        owner.refresh_from_db()
        Path(owner.root,original.relative_path).unlink()
        return owner,original,specification

    def repair(self,parent,original,*,request_key=None,retry_of_id=None):
        # Parent business/backup completeness is outside this component fixture.
        # The real admission function remains mandatory in production.
        with patch('mta.runtime.operational_attempts._verify_attempt') as admission:
            result=start_attempt(run_id=self.run.pk,configuration_id=self.config.pk,
                request_key=request_key or uuid.uuid4().hex,owned_root=self.temp.name,
                expected_output_digest=self.run.output_digest,repair_of_id=parent.pk,
                repair_file_ids=[original.pk],retry_of_id=retry_of_id)
            admission.assert_called_once_with(parent,missing_file_ids={original.pk})
        return result

    def test_surviving_copy_restores_availability_without_rewriting_original(self):
        parent,original,_=self.parent()
        snapshot=(parent.status,original.sha256,original.size_bytes,parent.root)
        with operational_run_lease(self.run.pk):
            owner=self.repair(parent,original)
            materialize_repair(owner.pk,archive_writer=None)
            finish_attempt(owner)
        owner.refresh_from_db();parent.refresh_from_db();original.refresh_from_db()
        self.assertEqual(owner.status,'SUCCEEDED')
        self.assertEqual((parent.status,original.sha256,original.size_bytes,parent.root),snapshot)
        target=owner.repair_targets.get()
        self.assertEqual(target.equivalence,EXACT)
        self.assertEqual(resolve_operational_file(original).pk,target.replacement_file_id)
        self.assertFalse(Path(parent.root,original.relative_path).exists())
        verify_files(original.operation)

    def _member_equivalent_zip(self, group):
        parent,original,specification=self.parent(group=group,copy=False)
        with operational_run_lease(self.run.pk):
            owner=self.repair(parent,original)
            with operation(owner,**specification) as effect:
                self.archive(owner,original.relative_path,year=2021)
                replacement=record_file(effect,relative_path=original.relative_path,role=original.role,archive=True)
                target=bind_repair_file(owner.pk,original.pk,replacement.pk)
            finish_attempt(owner)
        self.assertEqual(target.equivalence,MEMBERS)
        self.assertNotEqual(original.sha256,replacement.sha256)
        self.assertEqual(resolve_operational_file(original).pk,replacement.pk)

    def test_member_equivalent_zip_keeps_both_container_hashes(self):
        self._member_equivalent_zip('O4')

    def test_approved_bpr_exception_archive_members(self):
        self._member_equivalent_zip('O2')

    def test_approved_parent_norm_archive_members(self):
        self._member_equivalent_zip('O3')

    def test_approved_alert_archive_members(self):
        self._member_equivalent_zip('O7')

    def test_changed_member_content_is_rejected_and_failed_receipts_remain(self):
        parent,original,specification=self.parent(copy=False)
        with operational_run_lease(self.run.pk):
            owner=self.repair(parent,original)
            with self.assertRaisesRegex(ValueError,'member contract'):
                with operation(owner,**specification) as effect:
                    self.archive(owner,original.relative_path,payload=b'changed',year=2021)
                    replacement=record_file(effect,relative_path=original.relative_path,role=original.role,archive=True)
                    bind_repair_file(owner.pk,original.pk,replacement.pk)
        owner.refresh_from_db();parent.refresh_from_db()
        self.assertEqual((owner.status,parent.status),('FAILED','SUCCEEDED'))
        self.assertIsNone(owner.repair_targets.get().replacement_file_id)
        self.assertTrue(Path(owner.root,original.relative_path).exists())
        with self.assertRaisesRegex(ValueError,'absent'):resolve_operational_file(original)

    def test_member_equivalence_is_not_extended_to_other_groups(self):
        parent,original,specification=self.parent(group='O1',copy=False)
        with operational_run_lease(self.run.pk):
            owner=self.repair(parent,original)
            with self.assertRaisesRegex(ValueError,'member contract'):
                with operation(owner,**specification) as effect:
                    self.archive(owner,original.relative_path,year=2021)
                    replacement=record_file(effect,relative_path=original.relative_path,role=original.role,archive=True)
                    bind_repair_file(owner.pk,original.pk,replacement.pk)

    def test_changed_existing_file_is_not_treated_as_missing(self):
        parent,original,_=self.parent()
        Path(parent.root,original.relative_path).write_bytes(b'tampered')
        with operational_run_lease(self.run.pk):
            with self.assertRaisesRegex(ValueError,'bytes differ'):
                start_attempt(run_id=self.run.pk,configuration_id=self.config.pk,request_key=uuid.uuid4().hex,
                    owned_root=self.temp.name,expected_output_digest=self.run.output_digest,
                    repair_of_id=parent.pk,repair_file_ids=[original.pk])
        self.assertFalse(parent.repairs.exists())

    def test_interrupted_repair_retained_then_explicit_retry_completes(self):
        from mta.runtime.operational_repair import stage_surviving_copy
        parent,original,specification=self.parent()
        with operational_run_lease(self.run.pk) as lease:
            first=self.repair(parent,original)
            with self.assertRaises(OperationalLeaseError):
                with operation(first,**specification) as effect:
                    replacement=stage_surviving_copy(effect,original)
                    bind_repair_file(first.pk,original.pk,replacement.pk)
                    lease.session.close()
            first.refresh_from_db();self.assertEqual(first.status,'RUNNING')
        with operational_run_lease(self.run.pk):
            fail_interrupted_attempt(first.pk)
            second=self.repair(parent,original,retry_of_id=first.pk)
            materialize_repair(second.pk,archive_writer=None)
            finish_attempt(second)
        first.refresh_from_db();second.refresh_from_db();parent.refresh_from_db()
        self.assertEqual((first.status,second.status,parent.status),('FAILED','SUCCEEDED','SUCCEEDED'))
        self.assertNotEqual(first.root,second.root)
        self.assertTrue(Path(first.root,original.relative_path).exists())
        self.assertEqual(resolve_operational_file(original).operation.attempt_id,second.pk)
