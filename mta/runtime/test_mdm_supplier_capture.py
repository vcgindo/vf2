"""Migration-enabled supplier consumer proofs; no business-day calculation."""
from datetime import date
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.db import DatabaseError, transaction
from django.test import TestCase

from mta.application.r1_supplier_input import process_supplier_validation
from mta.mdm.daily_input import (bind_capture, capture_prune_candidates,
    compose_pair_exclusions, finalize_consumption, install_pair_exclusions,
    select_capture)
from mta.mdm.source import DLL
from mta.mdm.supplier_capture import feeds
from mta.mdm.supplier_source import install
from mta.runtime.input_storage import read_input, save_input
from mta.runtime.mdm_models import MdmSource, MdmTask, MdmSubTask
from mta.runtime.mdm_supplier_models import (MdmSobApproved, MdmSobArchive,
    MdmSobRaw, MdmSupplierConfiguration, MdmSobRequested, MdmSobHistory,
    MdmSupplierTaskRevision)
from mta.runtime.models import CalculationRun
from mta.serialization import digest
from tests.test_nms_supplier_input import approved, fixture


class SupplierCaptureTests(TestCase):
    def setUp(self):
        self.source = MdmSource.objects.create(digest='e' * 64,
            database_name='owned-supplier-test', dll_digest=DLL, receipt={})
        raw, _, _ = fixture()
        install(self.source, raw, moq_format='WithoutDestLoc', upload_log_active=True,
            provenance={'fixture': 'externally authored supplier values',
                'catalogue_sha256': '2ecf4e079807e00d0f809abedde1303640910ca82faeb5b8e56671b22d5de0ff'})
        install_pair_exclusions(self.source, [], provenance={'fixture': 'empty exclusions'})
        self.approved = MdmSobApproved.objects.create(source=self.source, **approved())

    def bind(self, snapshot, revision, origin=None):
        payload = {'mdm_input': snapshot, 'profile': {'delivery': {'site_code': 'isolated-NMS'}}}
        run = CalculationRun.objects.create(input_digest=digest(payload), input_payload={},
            kind='DAILY_CHAIN', business_date=date(2026, 10, 8), execution_revision=revision)
        manifest = save_input(run, payload)
        run.input_payload = manifest
        run.input_manifest_digest = digest(manifest)
        run.save(update_fields=['input_payload', 'input_manifest_digest'])
        capture = bind_capture(run, snapshot, request_digest='f' * 64, origin=origin)
        self.assertEqual(read_input(run), payload)
        return run, capture

    def snapshot(self):
        snapshot = select_capture(self.source, nms_active=True, task_status_log_horizon=7)
        snapshot = compose_pair_exclusions(snapshot, [])
        return capture_prune_candidates(snapshot, self.source, date(2026, 10, 8))

    def producer(self, snapshot):
        master = {'tables': {'SiteDescriptionTbl': [], 'RejectedMaster': [],
            'MasterDataRaw': [], 'MasterData': [dict(SKUCode='337',
                WhCode='DP010290', ParentWhCode='LDC001')]}}
        stages = process_supplier_validation(feeds(snapshot), master, [], '2026-10-08T00:00:00')
        return {'SupplierStages': [dict(stage=name, **stage) for name, stage in stages.items()]}

    def test_failed_publication_retries_identical_typed_capture_once(self):
        snapshot = self.snapshot()
        failed, origin = self.bind(snapshot, 'supplier-failed')
        output = self.producer(snapshot)
        with self.assertRaisesRegex(RuntimeError, 'publication failure'):
            with transaction.atomic():
                finalize_consumption(failed, output=output)
                self.assertEqual(MdmSobArchive.objects.filter(run=failed).count(), 1)
                raise RuntimeError('publication failure')
        self.assertFalse(MdmSobArchive.objects.filter(run=failed).exists())
        self.assertTrue(MdmSobApproved.objects.filter(pk=self.approved.pk).exists())
        failed.status = 'FAILED'
        failed.save(update_fields=['status'])
        later = MdmSobApproved.objects.create(source=self.source,
            **dict(approved(), WhCode='DP020819', SOB=75.5))
        frozen = read_input(failed, components=('mdm_input',))['mdm_input']
        retry, capture = self.bind(frozen, 'supplier-retry', origin)
        self.assertEqual(capture.revision_digest, origin.revision_digest)
        self.assertEqual(self.producer(frozen), output)
        finalize_consumption(retry, output=output)
        finalize_consumption(retry, output=output)
        self.assertEqual(list(MdmSobApproved.objects.filter(source=self.source)
            .values_list('pk', flat=True)), [later.pk])
        self.assertEqual(MdmSobArchive.objects.filter(run=retry).count(), 1)
        self.assertFalse(MdmSobArchive.objects.filter(run=failed).exists())
        self.assertEqual(list(MdmSobRaw.objects.filter(source=self.source).order_by('ordinal')
            .values('SKUCode', 'WHCode', 'SupplierCode', 'SupplierDescription', 'SOB')),
            next(s['tables']['SOBDataRaw'] for s in output['SupplierStages']
                 if s['stage'] == 'ResetFlags.sql'))
        origin.refresh_from_db(); capture.refresh_from_db()
        self.assertEqual((origin.status, capture.status), ('CAPTURED', 'CONSUMED'))

    def test_raw_and_configuration_reject_out_of_boundary_mutation(self):
        for mutate in (
            lambda: MdmSobRaw.objects.filter(source=self.source).update(SOB=50),
            lambda: MdmSobRaw.objects.filter(source=self.source).delete(),
            lambda: MdmSupplierConfiguration.objects.filter(source=self.source).update(moq_format='WithDestLoc'),
        ):
            with self.assertRaises(DatabaseError), transaction.atomic():
                mutate()

    def stage(self, task_id, scalar, *, location='DP010290', approved_row=False):
        task, _ = MdmTask.objects.get_or_create(source=self.source, TaskID=task_id,
            defaults=dict(MasterId='4', Actiontype=1, TaskStatus='1'))
        sub, _ = MdmSubTask.objects.get_or_create(source=self.source, TaskID=task_id,
            ApproverId='902', defaults=dict(TaskStatus='2' if approved_row else '1'))
        MdmSobRequested.objects.create(source=self.source, TaskId=task_id,
            **dict(approved(), WhCode=location, SOB=scalar, Approved=approved_row))
        history = MdmSobHistory.objects.create(source=self.source, TaskId=task_id,
            SKUCode='337', WhCode=location, SupplierCode='LDC001', SOB=20,
            ActionType=1, ApproverId='902', Status='3' if approved_row else '1')
        return task, sub, history

    def decide(self, task_id, *, location='DP010290'):
        from mta.mdm.supplier_tasks import approve
        # Scope expansion has separate real-catalogue API proofs; these tests
        # isolate the decision/capture owner and use the real decision writer.
        with patch('mta.mdm.supplier_tasks.scopes', return_value=(
                {'337'}, {'dp010290', 'dp020819'})):
            approve(self.source, dict(taskId=task_id, data=[dict(sc='337',
                wc=location, spc='LDC001', status='3', comments='owned test')]),
                dict(id=902, name='owned reviewer'))

    def test_same_key_later_approval_archives_frozen_value_and_retains_revision(self):
        snapshot = self.snapshot()
        run, _ = self.bind(snapshot, 'supplier-old-revision')
        self.stage('later-task', 72.5)
        self.decide('later-task')
        self.approved.refresh_from_db()
        self.assertEqual((self.approved.SOB, self.approved.revision), (72.5, 1))
        finalize_consumption(run, output=self.producer(snapshot))
        self.assertEqual(MdmSobArchive.objects.get(run=run).SOB, 12.375)
        self.assertTrue(MdmSobApproved.objects.filter(pk=self.approved.pk, SOB=72.5).exists())
        later = self.snapshot()
        retry, _ = self.bind(later, 'supplier-later-revision')
        finalize_consumption(retry, output=self.producer(later))
        self.assertEqual(MdmSobArchive.objects.get(run=retry).SOB, 72.5)
        self.assertFalse(MdmSobApproved.objects.filter(source=self.source).exists())

    def test_equal_zero_and_null_decisions_each_advance_the_revision(self):
        snapshot = self.snapshot()
        run, _ = self.bind(snapshot, 'supplier-equal-revision')
        for index, scalar in enumerate((12.375, 0, None), 1):
            task_id = 'later-' + str(index)
            self.stage(task_id, scalar)
            self.decide(task_id)
            self.approved.refresh_from_db()
            self.assertEqual((self.approved.SOB, self.approved.revision), (12.375, index))
        finalize_consumption(run, output=self.producer(snapshot))
        self.assertTrue(MdmSobApproved.objects.filter(pk=self.approved.pk, revision=3).exists())

    def test_later_decision_defers_whole_task_then_next_capture_completes(self):
        task, sub, history = self.stage('same-task', 12.375, approved_row=True)
        snapshot = self.snapshot()
        run, _ = self.bind(snapshot, 'supplier-same-task-old')
        self.stage('same-task', 75, location='DP020819')
        self.decide('same-task', location='DP020819')
        before = list(MdmSobHistory.objects.filter(source=self.source).order_by('id').values())
        finalize_consumption(run, output=self.producer(snapshot))
        task.refresh_from_db(); sub.refresh_from_db()
        self.assertEqual((task.TaskStatus, sub.TaskStatus), ('1', '2'))
        self.assertEqual(list(MdmSobHistory.objects.filter(source=self.source).order_by('id').values()), before)
        self.assertFalse(run.mdm_input_capture.task_occurrences.filter(transitioned_at__isnull=False).exists())
        later = self.snapshot()
        next_run, _ = self.bind(later, 'supplier-same-task-new')
        finalize_consumption(next_run, output=self.producer(later))
        task.refresh_from_db(); sub.refresh_from_db()
        self.assertEqual((task.TaskStatus, sub.TaskStatus), ('7', '4'))

    def test_revision_tokens_and_sealed_typed_images_reject_unowned_writes(self):
        snapshot = self.snapshot()
        run, _ = self.bind(snapshot, 'supplier-guarded-image')
        from django.db import connection
        for mutate in (
            lambda: MdmSobApproved.objects.filter(pk=self.approved.pk).update(SOB=99, revision=1),
            lambda: MdmSobApproved.objects.filter(pk=self.approved.pk).update(Approved=False),
            lambda: MdmSupplierTaskRevision.objects.create(source=self.source, master_id=4, task_id='unowned'),
        ):
            with self.assertRaises(DatabaseError), transaction.atomic():
                mutate()
        with self.assertRaises(DatabaseError), transaction.atomic(), connection.cursor() as cursor:
            cursor.execute('UPDATE mta_state.input_supplier_sob SET "SOB"=99 WHERE vf_run_id=%s', [run.pk])

    def test_superseded_supplier_id_does_not_hide_another_master_roster_error(self):
        from mta.mdm.daily_input import _lock_completion_candidates, _lock_prune_candidates
        snapshot = self.snapshot()
        _, capture = self.bind(snapshot, 'supplier-master-qualified')
        for function, key in ((_lock_completion_candidates, 'completion_tasks'),
                              (_lock_prune_candidates, 'prune_tasks')):
            candidate = dict(master_id='1', task_id='same-id', digest='invalid', members={})
            with self.assertRaisesRegex(ValueError, 'roster drift'):
                function({key: [candidate]}, capture, deferred_tasks={(4, 'same-id')})

    def test_retained_token_without_live_task_is_not_a_daily_input_dependency(self):
        from mta.mdm.supplier_revisions import source_lock, bump_task
        with source_lock(self.source.pk, deciding=True):
            bump_task(self.source, 4, 'no-longer-live')
        self.assertTrue(MdmSupplierTaskRevision.objects.filter(source=self.source).exists())
        self.assertEqual(self.snapshot()['supplier']['task_revisions'], [])

    def test_operator_install_requires_pinned_input_and_never_replaces_owners(self):
        from django.core.management import call_command, CommandError
        from io import StringIO
        target = MdmSource.objects.create(digest='7' * 64,
            database_name='owned-command-test', dll_digest=DLL, receipt={})
        raw, _, _ = fixture()
        manifest = dict(schema='fresh-mdm-supplier-install-v1', dll_sha256=DLL,
            source_digest=target.digest, raw=raw, moq_format='WithDestLoc',
            upload_log_active=False, provenance={'fixture': 'operator command proof'})
        with TemporaryDirectory() as folder:
            path = Path(folder) / 'explicit-input.json'
            path.write_text(json.dumps(manifest), encoding='utf-8')
            checksum = hashlib.sha256(path.read_bytes()).hexdigest()
            with self.assertRaisesRegex(CommandError, 'checksum differs'):
                call_command('install_mdm_suppliers', str(path), sha256='wrong',
                    source_digest=target.digest, stdout=StringIO())
            self.assertFalse(MdmSupplierConfiguration.objects.filter(source=target).exists())
            call_command('install_mdm_suppliers', str(path), sha256=checksum,
                source_digest=target.digest, stdout=StringIO())
            with self.assertRaisesRegex(CommandError, 'already installed'):
                call_command('install_mdm_suppliers', str(path), sha256=checksum,
                    source_digest=target.digest, stdout=StringIO())
        self.assertEqual(MdmSupplierConfiguration.objects.get(source=target).moq_format, 'WithDestLoc')
