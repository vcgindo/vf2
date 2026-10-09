"""Transaction fixtures, never business-day invocations or timeline receipts."""
import json
from copy import deepcopy
from datetime import date
from pathlib import Path
from unittest.mock import patch

from django.db import DatabaseError, transaction
from django.test import TestCase
from mta.application.r1_importer_master import PRIOR_TABLES, process_importer_master
from mta.application.r1_norm_updates import clear_force_requests
from mta.mdm.daily_input import (bind_capture, select_capture, compose_pair_exclusions,
    capture_prune_candidates, finalize_consumption, install_pair_exclusions)
from mta.mdm.force_capture import native, replace_working_input
from mta.mdm.force_source import (OWNER_SCHEMA, ARTIFACT_SHA, TRIAL_OVERRIDE, HIERARCHY_SUPPLEMENT,
                                  configuration_sha)
from mta.mdm.source import DLL
from mta.mdm.supplier_revisions import source_lock
from mta.runtime.input_storage import save_input, read_input
from mta.runtime.mdm_models import MdmSource, MdmFamilySource, MdmTask, MdmSubTask
from mta.runtime.mdm_force_models import (MdmForceOwner, MdmForceQueue,
    MdmForceConsumed, MdmForceRequested, MdmForceHistory, MdmForceUploadLog)
from mta.runtime.models import CalculationRun
from mta.serialization import digest


class ForceCaptureTests(TestCase):
    def setUp(self):
        self.prior = {'importer': {'ForceNormChange': []},
                      'controls': {'upload_log': []}}
        self.source = MdmSource.objects.create(digest='c' * 64,
            database_name='owned-force-transaction-fixture', dll_digest=DLL, receipt={})
        receipt = dict(schema=OWNER_SCHEMA, artifact_sha256=ARTIFACT_SHA,
            configuration_sha256=configuration_sha(), fixture_override=TRIAL_OVERRIDE,
            hierarchy_supplement=HIERARCHY_SUPPLEMENT,
            root_state_digest=digest(self.prior))
        self.owner = MdmForceOwner.objects.create(source=self.source,
            receipt_digest=digest(receipt), provenance=receipt,
            opening_digest=digest([]), closing_digest=digest([]),
            root_state_digest=digest(self.prior), closing_log_digest=digest([]))
        MdmFamilySource.objects.create(source=self.source, master_id=13,
            digest=digest(receipt), receipt=receipt)
        install_pair_exclusions(self.source, [], provenance={'fixture': 'explicit empty exclusions'})

    def queue(self, norm=201, approved=True, location='DP010290'):
        with source_lock(self.source.pk, deciding=True):
            return MdmForceQueue.objects.create(source=self.source, SKUCode='337',
                WhCode=location, NewNorm=norm, Approved=approved, RequestedBy='901')

    def snapshot(self):
        result = select_capture(self.source, nms_active=False, task_status_log_horizon=7)
        result = compose_pair_exclusions(result, [])
        return capture_prune_candidates(result, self.source, date(2026, 6, 6))

    def bind(self, snapshot, revision='force-test', origin=None):
        raw = {'mdm_input': snapshot, 'profile': {'delivery': {'site_code': 'isolated-force'}}}
        run = CalculationRun.objects.create(kind='DAILY_CHAIN', business_date=date(2026, 6, 6),
            execution_revision=revision, input_digest=digest(raw), input_payload={})
        run.input_payload = save_input(run, raw)
        run.input_manifest_digest = digest(run.input_payload)
        run.save(update_fields=['input_payload', 'input_manifest_digest'])
        capture = bind_capture(run, snapshot, request_digest='d' * 64, origin=origin)
        self.assertEqual(read_input(run), raw)
        return run, capture

    def output(self, rows=(), logs=()):
        return {'ClosingState': [{'importer': {'ForceNormChange': list(rows)},
                                 'controls': {'upload_log': list(logs)}}]}

    def importer_auto_force(self):
        """Minimal retained importer fixture exercising ImportNonNMS auto-force."""
        fixture = json.loads((Path(__file__).parents[1] / 'fixtures' /
                              'r1_importer_master_base.json').read_text())
        payload = deepcopy(fixture)
        payload['import_non_nms'] = True
        payload['prior'] = {name: [] for name in PRIOR_TABLES}
        attribute = deepcopy(fixture['prior']['SkuLocAttributeData'][0])
        attribute.update(SKUCode='337', LocCode='DP010290', NonNMS=0)
        payload['prior']['SkuLocAttributeData'] = [attribute]
        regular = deepcopy(fixture['raw_master'][0])
        regular.update(SKUCode='BASE', WhCode='BASELOC', ParentWhCode='PARENT',
            SKUDescription='Base', WHDescription='Base loc', ParentDescription='Parent')
        non_nms = deepcopy(fixture['raw_master'][1])
        non_nms.update(SKUCode='337', WhCode='DP010290', Norm=99,
            ParentWhCode='PARENT', SKUDescription='Auto', WHDescription='Auto loc',
            ParentDescription='Parent')
        payload['raw_master'] = [regular]
        payload['raw_non_nms'] = [non_nms]
        payload['raw_no_norm'] = []
        result = process_importer_master(payload)
        self.assertEqual(result['outcome'], 'APPLIED')
        expected = [dict(SKUCode='337', WhCode='DP010290', NewNorm=99,
                         Approved=1, RequestedBy=None)]
        self.assertEqual(result['tables']['ForceNormChange'], expected)
        return expected

    def stage(self, task_id, norm, location='DP010290', approved=False):
        task, _ = MdmTask.objects.get_or_create(source=self.source, TaskID=task_id,
            defaults=dict(MasterId='13', Actiontype=2, RequesterId='901', TaskStatus='1'))
        sub, _ = MdmSubTask.objects.get_or_create(source=self.source, TaskID=task_id,
            ApproverId='902', defaults={'TaskStatus': '2' if approved else '1'})
        MdmForceRequested.objects.create(source=self.source, TaskId=task_id,
            SKUCode='337', WhCode=location, NewNorm=norm, RequestedBy='901',
            ActionType=2, Approved=approved, Reverted=False)
        history = MdmForceHistory.objects.create(source=self.source, TaskId=task_id,
            SKUCode='337', WhCode=location, NewNorm=186, ActionType=2,
            ApproverId='902', Status='3' if approved else None)
        return task, sub, history

    def decide(self, task_id, location='DP010290', status='3'):
        from mta.mdm.force_tasks import approve
        with patch('mta.mdm.force_tasks.scopes', return_value=(
                {'337'}, {'dp010290', 'dp020819'})):
            return approve(self.source, dict(taskId=task_id,
                data=[dict(sc='337', wc=location, status=status, comments='owned fixture')]),
                dict(id=902, name='owned reviewer'))

    def test_inactive_capture_preserves_complete_typed_occurrences_and_nulls(self):
        self.queue(); self.queue(); self.queue(None, None, 'DP020819')
        snap = self.snapshot()
        self.assertFalse(snap['nms_active'])
        self.assertEqual([(r['NewNorm'], r['Approved']) for r in snap['force']['rows']],
                         [(201, True), (201, True), (None, None)])
        run, _ = self.bind(snap)
        image = run.input_payload['images']['input/mdm_input/force/rows/values']
        self.assertEqual(image['table'], 'input/force_queue')

    def test_input_replacement_rejects_second_feed_or_wrong_predecessor(self):
        self.queue(); snap = self.snapshot()
        original = deepcopy(self.prior)
        prior = deepcopy(original); day = {'new_force_requests': []}
        replace_working_input(snap, prior, day, None)
        self.assertEqual(prior['importer']['ForceNormChange'], [native(snap['force']['rows'][0])])
        self.assertEqual(original['importer']['ForceNormChange'], [])
        with self.assertRaisesRegex(ValueError, 'second external'):
            replace_working_input(snap, deepcopy(original), {'new_force_requests': [{}]}, None)
        with self.assertRaisesRegex(ValueError, 'does not descend'):
            replace_working_input(snap, prior, day, None)
        wrong_root = deepcopy(original); wrong_root['unrelated'] = 'not the selected opening'
        with self.assertRaisesRegex(ValueError, 'does not descend'):
            replace_working_input(snap, wrong_root, day, None)

    def test_actual_clear_can_remove_unapproved_equal_norm_and_keep_other_pending(self):
        self.queue(201, True); self.queue(201, False); self.queue(75, False, 'DP020819')
        snap = self.snapshot(); run, _ = self.bind(snap)
        state = dict(force_requests=[native(r) for r in snap['force']['rows']],
            raw_master=[], dbm_master=[dict(SKUCode='337', WhCode='DP010290', Norm=201)])
        terminal = clear_force_requests(state, from_ui=True, ignore_master_norm=True,
                                        nms_active=False)['force_requests']
        self.assertEqual(terminal, [native(snap['force']['rows'][2])])
        finalize_consumption(run, output=self.output(terminal))
        self.assertEqual(list(MdmForceQueue.objects.values_list('NewNorm', flat=True)), [75])
        self.assertEqual(list(MdmForceConsumed.objects.order_by('ordinal')
                             .values_list('cleared', flat=True)), [True, True, False])

    def test_failure_rolls_back_all_owners_and_retry_uses_same_image(self):
        queued = self.queue(); snap = self.snapshot(); run, capture = self.bind(snap)
        with self.assertRaisesRegex(RuntimeError, 'publication fault'):
            with transaction.atomic():
                finalize_consumption(run, output=self.output())
                raise RuntimeError('publication fault')
        self.assertTrue(MdmForceQueue.objects.filter(pk=queued.pk).exists())
        self.assertFalse(MdmForceConsumed.objects.exists())
        self.owner.refresh_from_db(); self.assertIsNone(self.owner.last_run_id)
        capture.refresh_from_db(); self.assertEqual(capture.status, 'CAPTURED')
        run.status = 'FAILED'; run.save(update_fields=['status'])
        retry, _ = self.bind(snap, 'force-retry', origin=capture)
        finalize_consumption(retry, output=self.output())
        finalize_consumption(retry, output=self.output())
        self.assertEqual(MdmForceConsumed.objects.filter(run=retry).count(), 1)

    def test_later_same_key_equal_zero_null_decisions_are_not_cleared(self):
        queued = self.queue(); snap = self.snapshot(); run, _ = self.bind(snap)
        for index, value in enumerate((201, 0, None, 222), 1):
            task_id = 'later-' + str(index)
            self.stage(task_id, value); self.decide(task_id)
            queued.refresh_from_db()
            self.assertEqual(queued.revision, index)
            self.assertEqual(queued.NewNorm, 222 if index == 4 else 201)
        finalize_consumption(run, output=self.output())
        queued.refresh_from_db(); self.assertEqual(queued.NewNorm, 222)
        self.assertEqual(MdmForceConsumed.objects.get(run=run).NewNorm, 201)

    def test_later_same_key_ui_generation_supersedes_unmatched_terminal_row(self):
        snap = self.snapshot(); run, _ = self.bind(snap)
        produced = self.importer_auto_force()
        self.stage('post-capture', 77); self.decide('post-capture')
        finalize_consumption(run, output=self.output(produced))
        rows = list(MdmForceQueue.objects.filter(source=self.source)
                    .values('SKUCode', 'WhCode', 'NewNorm', 'Approved', 'RequestedBy'))
        self.assertEqual(rows, [dict(SKUCode='337', WhCode='DP010290',
                                     NewNorm=77, Approved=True, RequestedBy='901')])

    def test_importer_auto_force_publishes_and_anchors_next_capture(self):
        snap = self.snapshot(); run, _ = self.bind(snap)
        produced = self.importer_auto_force()
        output = self.output(produced)
        finalize_consumption(run, output=output)
        self.assertEqual(list(MdmForceQueue.objects.filter(source=self.source)
                             .values('SKUCode', 'WhCode', 'NewNorm', 'Approved',
                                     'RequestedBy')), produced)
        run.status = 'SUCCEEDED'
        run.output_digest = digest(output)
        run.save(update_fields=['status', 'output_digest'])
        next_snapshot = self.snapshot()
        anchor = next_snapshot['force']['anchor']
        self.assertEqual(anchor['run_id'], str(run.pk))
        self.assertEqual(anchor['output_digest'], run.output_digest)
        self.assertEqual(anchor['queue_digest'], digest(produced))
        self.assertEqual(anchor['log_digest'], digest([]))
        prior = {'importer': {'ForceNormChange': deepcopy(produced)},
                 'controls': {'upload_log': []}}
        replace_working_input(next_snapshot, prior, {'new_force_requests': []}, run)
        self.assertEqual(prior['importer']['ForceNormChange'], produced)
        self.assertEqual(prior['controls']['upload_log'], [])

    def test_later_decision_defers_whole_task_completion(self):
        self.queue(); task, sub, _ = self.stage('same-task', 201, approved=True)
        snap = self.snapshot(); run, _ = self.bind(snap)
        self.stage('same-task', 77, location='DP020819')
        self.decide('same-task', location='DP020819')
        finalize_consumption(run, output=self.output())
        sub.refresh_from_db(); task.refresh_from_db()
        self.assertEqual(sub.TaskStatus, '2'); self.assertNotEqual(task.TaskStatus, '7')

    def test_unguarded_mutation_and_sealed_image_change_are_denied(self):
        queued = self.queue(); snap = self.snapshot(); run, _ = self.bind(snap)
        for mutate in (
            lambda: MdmForceQueue.objects.filter(pk=queued.pk).update(NewNorm=99),
            lambda: MdmForceOwner.objects.filter(pk=self.owner.pk).update(
                root_state_digest='0' * 64),
            lambda: MdmForceOwner.objects.filter(pk=self.owner.pk).update(
                closing_log_digest='0' * 64),
        ):
            with self.assertRaises(DatabaseError), transaction.atomic():
                mutate()
        from django.db import connection
        with self.assertRaises(DatabaseError), transaction.atomic(), connection.cursor() as cursor:
            cursor.execute('UPDATE mta_state.input_force_queue SET "NewNorm"=99 WHERE vf_run_id=%s', [run.pk])

    def test_upload_log_and_consumption_receipts_enforce_owned_writers(self):
        with self.assertRaises(DatabaseError), transaction.atomic():
            MdmForceUploadLog.objects.create(source=self.source, SKUCode='337',
                WHCode='DP010290', RequestedBy='unowned',
                ActionTimeStamp='2026-06-06T00:00:00', ActionId=1)
        queued = self.queue(); snap = self.snapshot(); run, _ = self.bind(snap)
        finalize_consumption(run, output=self.output([native(snap['force']['rows'][0])]))
        receipt = MdmForceConsumed.objects.get(run=run, source_pk=queued.pk)
        from mta.mdm.clock import database_now
        with source_lock(self.source.pk, deciding=True):
            event = MdmForceUploadLog.objects.create(source=self.source, SKUCode='337',
                WHCode='DP010290', NewNorm=201, Approved=False, RequestedBy='owned requester',
                ActionTimeStamp=database_now(), ActionId=1)
        for mutate in (
            lambda: MdmForceConsumed.objects.filter(pk=receipt.pk).update(cleared=True),
            lambda: MdmForceConsumed.objects.filter(pk=receipt.pk).delete(),
            lambda: MdmForceUploadLog.objects.filter(pk=event.pk).update(OldNorm=186),
            lambda: MdmForceUploadLog.objects.filter(pk=event.pk).delete(),
        ):
            with self.assertRaises(DatabaseError), transaction.atomic():
                mutate()
        with self.assertRaises(DatabaseError), transaction.atomic():
            MdmForceConsumed.objects.create(source=self.source, run=run,
                source_pk=queued.pk, revision=0, ordinal=99, cleared=False,
                SKUCode='337', WhCode='DP010290', NewNorm=201,
                Approved=True, RequestedBy='901')
        from django.db import connection
        for table in ('fresh_mta_mdmforceuploadlog', 'fresh_mta_mdmforceconsumed'):
            with self.assertRaises(DatabaseError), transaction.atomic(), connection.cursor() as cursor:
                cursor.execute('TRUNCATE TABLE mta.' + table)

    def test_native_upload_timestamp_and_old_norm_are_typed_and_published(self):
        from mta.mdm.clock import database_now
        with source_lock(self.source.pk, deciding=True):
            event = MdmForceUploadLog.objects.create(source=self.source, SKUCode='337',
                WHCode='DP010290', NewNorm=201, Approved=False, RequestedBy='owned requester',
                ActionTimeStamp=database_now(), ActionId=1)
        snap = self.snapshot(); run, _ = self.bind(snap)
        prior = {'importer': {'ForceNormChange': []}, 'controls': {'upload_log': []}}
        replace_working_input(snap, prior, {'new_force_requests': []}, None)
        logs = prior['controls']['upload_log']; logs[0]['OldNorm'] = 186
        finalize_consumption(run, output=self.output(logs=logs))
        event.refresh_from_db(); self.assertEqual(event.OldNorm, 186)
        self.owner.refresh_from_db()
        self.assertEqual(self.owner.closing_log_digest, digest(logs))
        self.assertEqual(self.owner.root_state_digest, digest(self.prior))
