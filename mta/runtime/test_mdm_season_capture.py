"""Owned transaction fixtures, not business-day invocations or parity receipts."""
from copy import deepcopy
from datetime import date
from unittest.mock import patch
from django.db import DatabaseError, transaction
from django.db.models import F
from django.test import TestCase

from mta.application.r1_seasonality import REQUEST_FIELDS, SEASON_FIELDS
from mta.mdm.daily_input import (bind_capture, select_capture, compose_pair_exclusions,
    capture_prune_candidates, finalize_consumption, install_pair_exclusions)
from mta.mdm.season_capture import native, replace_working_input
from mta.mdm.season_source import OWNER_SCHEMA, ARTIFACT_SHA, SUPPLEMENT, configuration_sha
from mta.mdm.source import DLL
from mta.mdm.supplier_revisions import source_lock
from mta.runtime.input_storage import save_input, read_input
from mta.runtime.mdm_models import (MdmSource, MdmFamilySource, MdmTask, MdmSubTask,
                                    MdmDraft, MdmDraftMaster)
from mta.runtime.mdm_season_models import (MdmSeasonOwner, MdmSeasonQueue,
    MdmSeasonCurrent, MdmSeasonConsumed, MdmSeasonRequested, MdmSeasonHistory,
    MdmDraftSeason)
from mta.runtime.models import CalculationRun
from mta.serialization import digest, storage


def request(**changes):
    return dict(SKUCode='6120', WhCode='DP010290', StartDate='2026-06-06',
        EndDate='2026-06-20', TargetNorm=201, DeltaNormPercentage=None,
        UpperLowerCap=None, BuildupDuration=6, ActivateDBM=False, Approved=True, **changes)


def season():
    row = {k: v for k, v in request().items() if k != 'Approved'}
    row.update(OrigNorm=186, NewNorm=201, Type=1, Status=4,
               Comment='transaction fixture', LastProcessedOn='2026-06-06')
    return row


class SeasonCaptureTests(TestCase):
    def setUp(self):
        self.prior = dict(control_aux={'season_requests': []}, dbm={'Seasonality': []},
                          controls={'seasonality': []})
        self.source = MdmSource.objects.create(digest='e' * 64, dll_digest=DLL,
            database_name='owned-season-transaction-fixture', receipt={})
        receipt = dict(schema=OWNER_SCHEMA, artifact_sha256=ARTIFACT_SHA,
            configuration_sha256=configuration_sha(), supplement=SUPPLEMENT,
            root_state_digest=digest(self.prior), eligibility_digest=digest([]))
        self.owner = MdmSeasonOwner.objects.create(source=self.source, provenance=receipt,
            receipt_digest=digest(receipt), root_state_digest=digest(self.prior),
            closing_queue_digest=digest([]), closing_current_digest=digest([]))
        for mid in (10, 11, 12):
            MdmFamilySource.objects.create(source=self.source, master_id=mid,
                digest=digest(receipt), receipt=receipt)
        install_pair_exclusions(self.source, [], provenance={'fixture': 'explicit empty exclusions'})

    def queue(self, **changes):
        values = request(); values.update(changes)
        with source_lock(self.source.pk, deciding=True):
            return MdmSeasonQueue.objects.create(source=self.source, **values)

    def snapshot(self):
        result = select_capture(self.source, nms_active=False, task_status_log_horizon=7)
        result = compose_pair_exclusions(result, [])
        return capture_prune_candidates(result, self.source, date(2026, 6, 6))

    def bind(self, snapshot, revision='season-test', origin=None):
        raw = dict(mdm_input=snapshot, profile={'delivery': {'site_code': 'isolated-season'}})
        run = CalculationRun.objects.create(kind='DAILY_CHAIN', business_date=date(2026, 6, 6),
            execution_revision=revision, input_digest=digest(raw), input_payload={})
        run.input_payload = save_input(run, raw)
        run.input_manifest_digest = digest(run.input_payload)
        run.save(update_fields=['input_payload', 'input_manifest_digest'])
        captured = bind_capture(run, snapshot, request_digest='d' * 64, origin=origin)
        self.assertEqual(read_input(run), raw)
        return run, captured

    def output(self, queue=(), current=()):
        return {'ClosingState': [dict(control_aux={'season_requests': list(queue)},
                                     dbm={'Seasonality': list(current)})]}

    def publish_fixture(self):
        snap = self.snapshot(); run, _ = self.bind(snap)
        finalize_consumption(run, output=self.output(current=[season()]))
        run.status = 'SUCCEEDED'; run.output_digest = 'f' * 64
        run.save(update_fields=['status', 'output_digest'])
        return run

    def test_typed_capture_preserves_nulls_duplicates_and_inactive_gate(self):
        self.queue(); self.queue(); self.queue(TargetNorm=None, Approved=None)
        snap = self.snapshot(); run, _ = self.bind(snap)
        self.assertFalse(snap['nms_active'])
        self.assertEqual([r['TargetNorm'] for r in snap['season']['rows']], [201, 201, None])
        self.assertEqual(run.input_payload['images']['input/mdm_input/season/rows/values']['table'], 'input/season_queue')

    def test_replacement_is_full_and_checks_predecessor_and_second_feed(self):
        self.queue(); snap = self.snapshot(); prior = deepcopy(self.prior)
        day = {'control_requests': {'season_requests': []}}
        replace_working_input(snap, prior, day, None)
        self.assertEqual(prior['control_aux']['season_requests'], [native(snap['season']['rows'][0], REQUEST_FIELDS)])
        self.assertEqual(self.prior['control_aux']['season_requests'], [])
        self.assertTrue(day['seasonality_input_validation'])
        with self.assertRaisesRegex(ValueError, 'does not descend'):
            replace_working_input(snap, prior, day, None)
        with self.assertRaisesRegex(ValueError, 'second external'):
            replace_working_input(snap, deepcopy(self.prior), {'control_requests': {'season_requests': [{}]}}, None)

    def test_failure_rolls_back_and_frozen_retry_is_idempotent(self):
        row = self.queue(); snap = self.snapshot(); run, capture = self.bind(snap)
        with self.assertRaisesRegex(RuntimeError, 'publication fault'):
            with transaction.atomic():
                finalize_consumption(run, output=self.output(current=[season()]))
                raise RuntimeError('publication fault')
        self.assertTrue(MdmSeasonQueue.objects.filter(pk=row.pk).exists())
        self.assertFalse(MdmSeasonCurrent.objects.exists())
        self.assertFalse(MdmSeasonConsumed.objects.exists())
        run.status = 'FAILED'; run.save(update_fields=['status'])
        retry, _ = self.bind(snap, 'season-retry', capture)
        finalize_consumption(retry, output=self.output(current=[season()]))
        finalize_consumption(retry, output=self.output(current=[season()]))
        self.assertEqual(MdmSeasonConsumed.objects.count(), 1)
        self.assertEqual(MdmSeasonCurrent.objects.count(), 1)

    def test_later_add_revision_survives_older_consumption(self):
        row = self.queue(); snap = self.snapshot(); run, _ = self.bind(snap)
        with source_lock(self.source.pk, deciding=True):
            MdmSeasonQueue.objects.filter(pk=row.pk).update(TargetNorm=210, revision=F('revision') + 1)
        finalize_consumption(run, output=self.output(current=[season()]))
        row.refresh_from_db(); self.assertEqual(row.TargetNorm, 210)
        self.assertEqual(MdmSeasonConsumed.objects.get().TargetNorm, 201)

    def test_later_status_is_preserved_on_same_generation(self):
        self.publish_fixture()
        snap = self.snapshot(); run, _ = self.bind(snap, 'second')
        with source_lock(self.source.pk, deciding=True):
            MdmSeasonCurrent.objects.filter(source=self.source).update(Status=23,
                Comment='later stop', revision=F('revision') + 1)
        finalize_consumption(run, output=self.output(current=[season()]))
        self.assertEqual(MdmSeasonCurrent.objects.get().Status, 23)
        self.owner.refresh_from_db()
        self.assertEqual(self.owner.closing_current_digest, digest([season()]))

    def test_late_status_cannot_transfer_to_captured_add_replacement(self):
        predecessor = self.publish_fixture(); self.queue()
        snap = self.snapshot(); run, _ = self.bind(snap, 'collision')
        with source_lock(self.source.pk, deciding=True):
            MdmSeasonCurrent.objects.filter(source=self.source).update(Status=23,
                Comment='later stop', revision=F('revision') + 1)
        with self.assertRaisesRegex(ValueError, 'conflicts with captured ADD'), transaction.atomic():
            finalize_consumption(run, output=self.output(current=[season()]))
        self.owner.refresh_from_db(); self.assertEqual(self.owner.last_run_id, predecessor.pk)
        self.assertEqual(MdmSeasonCurrent.objects.get().Status, 23)
        self.assertEqual(MdmSeasonQueue.objects.count(), 1)

    def test_guards_reject_unowned_writes_and_calculation_value_changes(self):
        self.publish_fixture()
        for mutation in (
                lambda: MdmSeasonQueue.objects.create(source=self.source, **request()),
                lambda: MdmSeasonCurrent.objects.all().update(Status=23),
                lambda: MdmSeasonCurrent.objects.all().delete()):
            with self.assertRaises(DatabaseError), transaction.atomic():
                mutation()
        with self.assertRaises(DatabaseError), transaction.atomic(), source_lock(self.source.pk, deciding=True):
            MdmSeasonCurrent.objects.all().update(NewNorm=999, revision=F('revision') + 1)

    def test_add_decision_zero_null_fallback_and_pending_completion(self):
        from mta.mdm.season_tasks import approve
        queued = self.queue()
        MdmTask.objects.create(source=self.source, TaskID='add11', MasterId='11', Actiontype=1,
            TaskStatus='1', RequesterId='4')
        MdmSubTask.objects.create(source=self.source, TaskID='add11', ApproverId='5', TaskStatus='1')
        values = request(); values.pop('Approved'); values.update(TargetNorm=0, EndDate=None)
        MdmSeasonRequested.objects.create(source=self.source, **values, Approved=False,
            Reverted=False, TaskId='add11', ActionType=2)
        MdmSeasonHistory.objects.create(source=self.source, **values, TaskId='add11', ActionType=2, ApproverId='5')
        with patch('mta.mdm.season_tasks.scopes', return_value=({'6120'}, {'dp010290'})):
            approve(self.source, dict(taskId='add11', data=[dict(sc='6120', wc='DP010290',
                status='3', comments='approved transaction fixture')]), dict(id=5, name='reviewer'))
        queued.refresh_from_db()
        self.assertEqual((queued.TargetNorm, queued.EndDate), (201, date(2026, 6, 20)))
        self.assertEqual(MdmSubTask.objects.get().TaskStatus, '2')
        snap = self.snapshot(); run, _ = self.bind(snap)
        finalize_consumption(run, output=self.output(current=[season()]))
        self.assertEqual(MdmSubTask.objects.get().TaskStatus, '4')
        self.assertEqual(MdmTask.objects.get().TaskStatus, '7')

    def submission(self, master_id, data, action=None):
        from mta.mdm.season_tasks import submit
        from mta.runtime.mdm_skuloc_models import MdmSkuLocPair
        from mta.runtime.mdm_season_models import MdmSeasonEligibility
        from django.db import connection
        if not MdmSkuLocPair.objects.filter(source=self.source).exists():
            MdmSkuLocPair.objects.create(source=self.source, owner='Importer', ordinal=1,
                SKUCode='6120', LocCode='DP010290', PackSize=1,
                StockPercentForRationing=100, NormPercentReservation=0, NonNMS=False)
        if not MdmSeasonEligibility.objects.filter(source=self.source).exists():
            with connection.cursor() as cursor:
                cursor.execute("SELECT set_config('fresh.season_eligibility_source',%s,true)", [str(self.source.pk)])
            MdmSeasonEligibility.objects.create(source=self.source, ordinal=1,
                SKUCode='6120', WhCode='DP010290', Norm=186)
            with connection.cursor() as cursor:
                cursor.execute("SELECT set_config('fresh.season_eligibility_source','',true)")
        payload = dict(id=master_id, TaskId='', data=data, all_users=[], action=action)
        with patch('mta.mdm.season_tasks._submission_scopes', return_value=({'6120'}, {'dp010290'})), \
                patch('mta.mdm.season_tasks._approvers', return_value=[dict(id=5, name='reviewer')]):
            return submit(self.source, payload, dict(id=4, name='requester'), 2 if master_id == 10 else 1)

    def decide(self, task_id, status='3'):
        from mta.mdm.season_tasks import approve
        with patch('mta.mdm.season_tasks.scopes', return_value=({'6120'}, {'dp010290'})):
            return approve(self.source, dict(taskId=task_id, data=[dict(sc='6120', wc='DP010290',
                status=status, comments='focused fixture')]), dict(id=5, name='reviewer'))

    def test_absolute_submission_preserves_duplicates_and_row_header_action_split(self):
        row = dict(sc='6120', wc='DP010290', sd='2026-06-06', ed='2026-06-20', tn='201', bd='6')
        result = self.submission(11, [row, row])
        self.assertEqual(result['status'], 200)
        self.assertEqual(MdmSeasonRequested.objects.count(), 2)
        self.assertEqual(list(MdmSeasonRequested.objects.values_list('ActionType', 'ActivateDBM')), [(2, False), (2, False)])
        self.assertEqual(MdmTask.objects.get().Actiontype, 1)
        self.assertEqual(list(MdmSeasonHistory.objects.values_list('ActivateDBM', flat=True)), [None, None])
        self.decide(result['taskId'])
        self.assertEqual(MdmSeasonQueue.objects.count(), 2)
        self.assertEqual(list(MdmSeasonQueue.objects.values_list('TargetNorm', flat=True)), [201, 201])

    def test_percentage_rejection_does_not_install_approved_input(self):
        row = dict(sc='6120', wc='DP010290', sd='2026-06-06', ed='2026-06-20', dnp='20', ulc='200', bd='6')
        result = self.submission(12, [row]); self.decide(result['taskId'], '4')
        self.assertFalse(MdmSeasonQueue.objects.exists())
        r = MdmSeasonRequested.objects.get()
        self.assertEqual((r.DeltaNormPercentage, r.UpperLowerCap, r.Approved, r.Reverted), (20, 200, False, True))
        self.assertEqual(MdmSubTask.objects.get().TaskStatus, '6')

    def test_status_approval_changes_only_native_fields_and_completes_immediately(self):
        from mta.mdm.season_tasks import _effect
        from mta.runtime.mdm_season_models import MdmSeasonStatusRequested, MdmSeasonStatusHistory
        self.publish_fixture()
        before = storage(MdmSeasonCurrent.objects.values(*SEASON_FIELDS).get())
        result = self.submission(10, [dict(sc='6120', wc='DP010290')], 'stop')
        self.assertEqual(MdmSeasonStatusHistory.objects.get().Status1, 4)
        self.decide(result['taskId'])
        after = storage(MdmSeasonCurrent.objects.values(*SEASON_FIELDS).get())
        self.assertEqual({k: v for k, v in after.items() if k not in ('Status', 'Comment')},
                         {k: v for k, v in before.items() if k not in ('Status', 'Comment')})
        self.assertEqual(after['Status'], 23)
        self.assertEqual(MdmSeasonStatusHistory.objects.get().ApproverBy, '5')
        self.assertEqual(MdmSubTask.objects.get().TaskStatus, '4')
        self.assertIsNone(MdmSubTask.objects.get().DBUpdatedDate)
        # A focused native status writer fixture, not a third business day.
        requested = MdmSeasonStatusRequested.objects.get()
        requested.Status1 = -1; requested.Comment = 'Resumed on transaction fixture'
        with source_lock(self.source.pk, deciding=True):
            _effect(self.source, 10, [requested])
        self.assertEqual(MdmSeasonCurrent.objects.get().Status, -1)

    def test_denied_decision_leaves_requested_history_and_queue_unchanged(self):
        from mta.mdm.season_tasks import approve
        from mta.mdm.task_reads import TaskDenied
        result = self.submission(11, [dict(sc='6120', wc='DP010290', sd='2026-06-06',
                                         ed='2026-06-20', tn='201', bd='6')])
        with patch('mta.mdm.season_tasks.scopes', return_value=(set(), set())), self.assertRaises(TaskDenied):
            approve(self.source, dict(taskId=result['taskId'], data=[dict(sc='6120', wc='DP010290',
                status='3', comments='denied')]), dict(id=5, name='reviewer'))
        self.assertIsNone(MdmSeasonHistory.objects.get().Status)
        self.assertFalse(MdmSeasonRequested.objects.get().Approved)
        self.assertFalse(MdmSeasonQueue.objects.exists())

    def test_draft_details_match_native_master_specific_projection(self):
        from mta.mdm import drafts
        actor = dict(id=5, name='requester')
        values = dict(RowId=1, Error='row error', SKUCode='6120', WhCode='DP010290',
            StartDate='2026-06-06', EndDate='2026-06-20', TargetNorm='201',
            DeltaNormPercentage='20', NewNorm='205', OriginalNorm='186',
            UpperLowerCap='200', BuildupDuration='6', Type='1', Status='4',
            Comment='native draft', Warning='row warning', CurrentNorm='186',
            IsSelected='true')
        for master_id in (10, 11, 12):
            with self.subTest(master_id=master_id):
                draft_id = f'season-{master_id}'
                MdmDraft.objects.create(source=self.source, DraftId=draft_id, Userid='5')
                MdmDraftMaster.objects.create(source=self.source, DraftId=draft_id,
                    MasterId=master_id, GridState='{}', Status='1')
                MdmDraftSeason.objects.create(source=self.source, DraftId=draft_id, **values)
                row = drafts.details(self.source, draft_id, actor,
                    dict(pageNumber=1, recordsPerPage=20))[0]['DataMaster'][0]
                if master_id == 10:
                    self.assertEqual(set(row), {'sc', 'wc', 'sd', 'ed', 'tn', 'dnp',
                        'ulc', 'bd', 'nn', 'onm', 'tp', 'sts', 'cmt', 'IsSelected',
                        'error', 'warning'})
                    self.assertEqual((row['sc'], row['IsSelected'], row['error']),
                                     ('6120', 'true', 'row error'))
                else:
                    self.assertEqual(set(row), {'RowId', 'DraftId', 'Error', 'SKUCode',
                        'WhCode', 'StartDate', 'EndDate', 'TargetNorm',
                        'DeltaNormPercentage', 'NewNorm', 'OriginalNorm', 'UpperLowerCap',
                        'BuildupDuration', 'Type', 'Status', 'Comment', 'Warning',
                        'CurrentNorm', 'IsSelected'})
                    self.assertEqual((row['SKUCode'], row['IsSelected'], row['Error']),
                                     ('6120', 'true', 'row error'))
