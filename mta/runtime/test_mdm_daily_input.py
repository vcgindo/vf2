"""Focused PostgreSQL proof for frozen occurrence consumption."""
from datetime import date, datetime
from zoneinfo import ZoneInfo
from unittest.mock import patch

from django.db import transaction, connection
from django.test import TestCase

from mta.application.r1_importer_master import RAW_COLUMNS
from mta.mdm.daily_input import (bind_capture, capture_pending_conflicts,
    capture_prune_candidates, compose, compose_pair_exclusions,
    finalize_consumption, select_capture, install_pair_exclusions)
from mta.runtime.mdm_daily_models import (MdmDailyInputCapture,
    MdmDailyInputOccurrence, MdmDailyLocationArchive, MdmDailySkuArchive,
    MdmDailySkuLocAddArchive, MdmDailySkuLocModifyArchive,
    MdmDailySkuLocRemoveArchive, MdmDailyPairExclusion, MdmPairExclusion,
    MdmPairExclusionSource)
from mta.runtime.mdm_models import (MdmLocationApproved, MdmSkuApproved,
    MdmSkuHistory, MdmSource, MdmSkuRequested, MdmSubTask, MdmTask)
from mta.runtime.mdm_skuloc_models import (MdmSkuLocAddApproved,
    MdmSkuLocModifyApproved, MdmSkuLocRemoveApproved)
from mta.runtime.models import CalculationRun
from mta.serialization import digest


class DailyInputConsumptionTests(TestCase):
    def test_finish_run_failure_rolls_queue_history_task_and_output_back(self):
        from mta.application.daily_finalization import FLAG_SEED, POLICY
        from mta.runtime.services import finish_run
        from mta.runtime.models import Checkpoint
        from copy import deepcopy
        approved = MdmSkuApproved.objects.create(source=self.source, SKUCode='APPROVED',
            SKUDescription='Approved', ActionType=2, Approved=True, Reverted=False)
        task = MdmTask.objects.create(source=self.source, TaskID='ROLLBACK', TaskStatus='6',
                                     MasterId='1', Actiontype=2)
        sub = MdmSubTask.objects.create(source=self.source, TaskID='ROLLBACK',
                                       ApproverId='2', TaskStatus='2')
        history = MdmSkuHistory.objects.create(source=self.source, TaskId='ROLLBACK',
            SKUCode='APPROVED', SKUDescription='Approved', Status='3')
        with transaction.atomic():
            snapshot = select_capture(self.source, nms_active=True, task_status_log_horizon=7)
            snapshot = compose_pair_exclusions(snapshot, [])
            snapshot = capture_prune_candidates(snapshot, self.source, date(2026, 10, 6))
            raw = {'mdm_input': snapshot}
            run = CalculationRun.objects.create(input_digest=digest(raw), input_payload=raw,
                kind='DAILY_CHAIN', business_date=date(2026, 10, 6),
                execution_revision='rollback-only-publication-no-calculation')
            bind_capture(run, snapshot, request_digest='e'*64)
        output = {'Lineage': [{'cohort1': {'policy': POLICY}}],
                  'ClosingState': [{'complete': {'ScriptExecutedFlag': deepcopy(FLAG_SEED)}}]}
        def fail_after_write(current, _output):
            self.assertFalse(MdmSkuApproved.objects.filter(pk=approved.pk).exists())
            self.assertEqual(MdmDailyInputCapture.objects.get(run=current).status, 'CONSUMED')
            sub.refresh_from_db(); self.assertEqual(sub.TaskStatus, '4')
            Checkpoint.objects.create(run=current, name='rollback-only-output', rows=[],
                                      row_count=0, digest=digest([]))
            raise ValueError('injected later output failure')
        with patch('mta.runtime.relational_state.save_daily', side_effect=fail_after_write), \
                self.assertRaisesRegex(ValueError, 'injected later output failure'):
            finish_run(run, output, expected_digest=run.input_digest)
        self.assertTrue(MdmSkuApproved.objects.filter(pk=approved.pk).exists())
        self.assertFalse(MdmDailySkuArchive.objects.exists())
        self.assertFalse(Checkpoint.objects.filter(run=run).exists())
        self.assertEqual(MdmDailyInputCapture.objects.get(run=run).status, 'CAPTURED')
        task.refresh_from_db(); sub.refresh_from_db(); history.refresh_from_db()
        self.assertEqual((task.TaskStatus, sub.TaskStatus, history.Status), ('6', '2', '3'))

    def setUp(self):
        self.source = MdmSource.objects.create(digest='a' * 64, database_name='owned',
            dll_digest='b' * 64, receipt={})
        MdmPairExclusionSource.objects.create(source=self.source, digest=digest([]),
            row_count=0, provenance={'kind': 'owned-empty-test-source'})
        self.run = CalculationRun.objects.create(input_digest='c' * 64,
            execution_revision='mdm-daily-test', kind='DAILY_CHAIN',
            business_date=date.fromisoformat('2026-10-06'), input_payload={})

    def _bind(self):
        with transaction.atomic():
            snapshot = select_capture(self.source, nms_active=True,
                                      task_status_log_horizon=7)
            snapshot = compose_pair_exclusions(snapshot, [])
            snapshot = capture_prune_candidates(snapshot, self.source,
                                                date.fromisoformat('2026-10-06'))
            bind_capture(self.run, snapshot, request_digest='d' * 64)
        return snapshot

    def test_success_archives_all_clears_only_approved_and_transitions_task(self):
        approved = MdmSkuApproved.objects.create(source=self.source, SKUCode='APPROVED',
            SKUDescription='Approved', ActionType=2, Approved=True, Reverted=False)
        pending = MdmSkuApproved.objects.create(source=self.source, SKUCode='PENDING',
            SKUDescription='Pending', ActionType=2, Approved=False, Reverted=True,
            ElephantOrderCapping=17, Weight='1.250', Volume='2.500', c7='VALUE')
        task = MdmTask.objects.create(source=self.source, TaskID='TASK', TaskStatus='1',
                                      MasterId='1', Actiontype=2)
        sub = MdmSubTask.objects.create(source=self.source, TaskID='TASK',
                                        ApproverId='2', TaskStatus='2')
        MdmSkuHistory.objects.create(source=self.source, TaskId='TASK', SKUCode='APPROVED',
                                     SKUDescription='Approved', Status='3')
        snapshot = self._bind()
        later = MdmSkuApproved.objects.create(source=self.source, SKUCode='LATER',
            SKUDescription='Later', ActionType=2, Approved=True, Reverted=False)
        with patch('mta.runtime.validation_storage.read_input', return_value={'mdm_input': snapshot}):
            with transaction.atomic(): finalize_consumption(self.run)
        self.assertFalse(MdmSkuApproved.objects.filter(pk=approved.pk).exists())
        self.assertTrue(MdmSkuApproved.objects.filter(pk=pending.pk).exists())
        self.assertTrue(MdmSkuApproved.objects.filter(pk=later.pk).exists())
        capture = MdmDailyInputCapture.objects.get(run=self.run)
        self.assertEqual(capture.status, 'CONSUMED')
        self.assertEqual(capture.occurrences.filter(archived_at__isnull=False).count(), 2)
        self.assertEqual(capture.occurrences.filter(cleared_at__isnull=False).count(), 1)
        archived = MdmDailySkuArchive.objects.get(occurrence__source_pk=pending.pk)
        captured_timestamp = datetime.fromisoformat(
            snapshot['configuration']['run_timestamp'])
        self.assertEqual(archived.Input_Date, captured_timestamp)
        self.assertEqual((archived.SKUCode, archived.ElephantOrderCapping,
                          str(archived.Weight), str(archived.Volume), archived.c7,
                          archived.Approved, archived.Reverted),
                         ('PENDING', 17, '1.250', '2.500', 'VALUE', False, True))
        self.assertFalse(MdmDailySkuArchive.objects.filter(
            occurrence__source_pk=later.pk).exists())
        sub.refresh_from_db(); task.refresh_from_db()
        self.assertEqual((sub.TaskStatus, task.TaskStatus), ('4', '7'))
        self.assertEqual(sub.DBUpdatedDate,
                         captured_timestamp.strftime('%d/%m/%Y %I:%M%p'))
        before = (list(MdmDailySkuArchive.objects.order_by('id').values()),
                  list(MdmSkuApproved.objects.order_by('id').values()),
                  list(capture.occurrences.order_by('id').values()))
        with transaction.atomic():
            finalize_consumption(self.run)
        self.assertEqual(before, (list(MdmDailySkuArchive.objects.order_by('id').values()),
            list(MdmSkuApproved.objects.order_by('id').values()),
            list(capture.occurrences.order_by('id').values())))

    def test_changed_captured_occurrence_aborts_without_clearing(self):
        first = MdmSkuApproved.objects.create(source=self.source, SKUCode='FIRST',
            SKUDescription='Stable', ActionType=2, Approved=True, Reverted=False)
        row = MdmSkuApproved.objects.create(source=self.source, SKUCode='SKU',
            SKUDescription='Before', ActionType=2, Approved=True, Reverted=False)
        snapshot = self._bind()
        MdmSkuApproved.objects.filter(pk=row.pk).update(SKUDescription='After')
        with self.assertRaisesRegex(ValueError, 'changed before consumption'):
            with transaction.atomic():
                with patch('mta.runtime.validation_storage.read_input',
                           return_value={'mdm_input': snapshot}):
                    finalize_consumption(self.run)
        self.assertTrue(MdmSkuApproved.objects.filter(pk=row.pk).exists())
        self.assertTrue(MdmSkuApproved.objects.filter(pk=first.pk).exists())
        self.assertFalse(MdmDailySkuArchive.objects.exists())
        capture = MdmDailyInputCapture.objects.get(run=self.run)
        self.assertEqual(capture.status, 'CAPTURED')
        self.assertFalse(capture.occurrences.exclude(archived_at=None).exists())

    def test_inactive_capture_has_no_queue_rows_but_keeps_task_horizon(self):
        MdmSkuApproved.objects.create(source=self.source, SKUCode='NOT-CAPTURED',
            SKUDescription='Pending', ActionType=2, Approved=True, Reverted=False)
        with transaction.atomic():
            snapshot = select_capture(self.source, nms_active=False,
                                      task_status_log_horizon=9)
        self.assertEqual(snapshot['occurrences'], [])
        self.assertEqual(snapshot['configuration']['task_status_log_horizon'], 9)

    def test_all_delayed_family_queue_shapes_archive_typed_values(self):
        location = MdmLocationApproved.objects.create(source=self.source,
            WHCode='LOC', WHDescription='Location', LocationType='PLANT',
            ActionType=1, Approved=True, Reverted=False, c4='LC4')
        addition = MdmSkuLocAddApproved.objects.create(source=self.source,
            SKUCode='ADD', WhCode='LOC', ParentWhCode='PARENT', Norm=10,
            MinNorm=5, RLT=2, RCP=1, GCP=1, PackSize=12, DBMActive=False,
            StockPercentForRat=91, NormPercentReservation=9, Approved=True,
            SKULocAtt03='ADD3')
        modification = MdmSkuLocModifyApproved.objects.create(source=self.source,
            SKUCode='MOD', WhCode='LOC', ParentWhCode='PARENT',
            SpikeThreshold='1.25', Approved=False, SKULocAtt05='MOD5')
        removal = MdmSkuLocRemoveApproved.objects.create(source=self.source,
            SKUCode='REMOVE', WhCode='LOC', Approved=True)
        snapshot = self._bind()
        with patch('mta.runtime.validation_storage.read_input', return_value={'mdm_input': snapshot}):
            with transaction.atomic(): finalize_consumption(self.run)
        loc_archive = MdmDailyLocationArchive.objects.get(occurrence__source_pk=location.pk)
        add_archive = MdmDailySkuLocAddArchive.objects.get(occurrence__source_pk=addition.pk)
        modify_archive = MdmDailySkuLocModifyArchive.objects.get(occurrence__source_pk=modification.pk)
        remove_archive = MdmDailySkuLocRemoveArchive.objects.get(occurrence__source_pk=removal.pk)
        self.assertEqual((loc_archive.LocationType, loc_archive.c4), ('PLANT', 'LC4'))
        self.assertEqual((add_archive.Norm, add_archive.StockPercentForRat,
                          add_archive.SKULocAtt03), (10, 91, 'ADD3'))
        self.assertEqual((str(modify_archive.SpikeThreshold),
                          modify_archive.SKULocAtt05, modify_archive.Approved),
                         ('1.25', 'MOD5', False))
        self.assertEqual((remove_archive.SKUCode, remove_archive.WhCode),
                         ('REMOVE', 'LOC'))
        self.assertFalse(MdmSkuLocModifyApproved.objects.filter(pk=modification.pk,
                                                                 Approved=True).exists())
        self.assertTrue(MdmSkuLocModifyApproved.objects.filter(pk=modification.pk).exists())
        self.assertEqual(list(MdmDailyPairExclusion.objects.values(
            'SKUCode', 'WhCode')), [{'SKUCode': 'ADD', 'WhCode': 'LOC'}])
        self.assertEqual(list(MdmPairExclusion.objects.values(
            'SKUCode', 'WhCode')), [{'SKUCode': 'ADD', 'WhCode': 'LOC'}])

    def test_pair_exclusion_source_cannot_default_to_empty(self):
        missing = MdmSource.objects.create(digest='9' * 64,
            database_name='missing-exclusions', dll_digest='8' * 64, receipt={})
        with transaction.atomic(), self.assertRaisesRegex(
                ValueError, 'explicit bootstrap required'):
            select_capture(missing, nms_active=False, task_status_log_horizon=7)

    def test_explicit_exclusion_install_is_once_and_preserves_provenance(self):
        source = MdmSource.objects.create(digest='7' * 64,
            database_name='installed-exclusions', dll_digest='8' * 64, receipt={})
        rows = [{'SKUCode': 'A', 'WhCode': 'LOC'}]
        receipt = {'artifact_sha256': '1' * 64, 'source': 'owned-test-opening'}
        owner = install_pair_exclusions(source, rows, provenance=receipt)
        self.assertEqual((owner.digest, owner.row_count, owner.provenance),
                         (digest(rows), 1, receipt))
        with self.assertRaisesRegex(ValueError, 'already installed'):
            install_pair_exclusions(source, [], provenance=receipt)
        self.assertEqual(list(MdmPairExclusion.objects.filter(source=source)
                             .values('SKUCode', 'WhCode')), rows)

    def test_source_rejects_second_live_capture_until_retry_or_consumption(self):
        self._bind()
        with transaction.atomic():
            with self.assertRaisesRegex(ValueError, 'unconsumed daily capture'):
                select_capture(self.source, nms_active=True,
                               task_status_log_horizon=7)

    def test_pending_add_existing_in_composed_master_is_rejected(self):
        MdmTask.objects.create(source=self.source, TaskID='ADD', TaskStatus='1',
                               MasterId='1', Actiontype=1)
        MdmSubTask.objects.create(source=self.source, TaskID='ADD', ApproverId='2',
                                  TaskStatus='1')
        history = MdmSkuHistory.objects.create(source=self.source, TaskId='ADD',
            SKUCode='EXISTING', SKUDescription='Existing', Status=None)
        with transaction.atomic():
            snapshot = select_capture(self.source, nms_active=True,
                                      task_status_log_horizon=7)
            row = dict.fromkeys(RAW_COLUMNS); row['SKUCode'] = 'EXISTING'; row['WhCode'] = 'LOC'
            snapshot = capture_pending_conflicts(snapshot, self.source,
                compose(snapshot, [row], last_run_date='2026-10-05'))
            bind_capture(self.run, snapshot, request_digest='d' * 64)
        with patch('mta.runtime.validation_storage.read_input', return_value={'mdm_input': snapshot}):
            with transaction.atomic(): finalize_consumption(self.run)
        history.refresh_from_db()
        self.assertEqual((history.Status, history.Comments), ('4', 'Already in Vectorflow'))

    def test_archive_prunes_inclusive_fifteen_day_boundary(self):
        prior_run = CalculationRun.objects.create(input_digest='e' * 64,
            execution_revision='prior-archive', kind='DAILY_CHAIN',
            business_date=date.fromisoformat('2026-10-05'), input_payload={}, status='RUNNING')
        prior_capture = MdmDailyInputCapture.objects.create(run=prior_run,
            source=self.source, request_digest='f' * 64, revision_digest='1' * 64,
            sku_revision_digest='2' * 64, location_revision_digest='3' * 64,
            skuloc_revision_digest='4' * 64, sql_digest='5' * 64,
            nms_active=True, status='CAPTURED')
        prior_occurrence = MdmDailyInputOccurrence.objects.create(capture=prior_capture,
            family='sku', queue_kind='approved', source_pk=999, ordinal=0,
            sku_code='OLD', approved=True, reverted=False, action_type=2,
            row_digest='6' * 64)
        old = MdmDailySkuArchive.objects.create(source=self.source,
            occurrence=prior_occurrence,
            Input_Date=datetime(2026, 9, 21, tzinfo=ZoneInfo('Asia/Calcutta')),
            SKUCode='OLD', SKUDescription='Old', ActionType=2,
            Approved=True, Reverted=False)
        with connection.cursor() as cursor:
            cursor.execute("SELECT set_config('fresh.mdm_consuming_run',%s,true)", [str(prior_run.pk)])
        prior_capture.status = 'CONSUMED'
        prior_capture.consumed_at = datetime(2026, 10, 5, tzinfo=ZoneInfo('Asia/Calcutta'))
        prior_capture.save(update_fields=['status', 'consumed_at'])
        prior_run.status = 'SUCCEEDED'; prior_run.save(update_fields=['status'])
        MdmSkuApproved.objects.create(source=self.source, SKUCode='NEW',
            SKUDescription='New', ActionType=2, Approved=True, Reverted=False)
        snapshot = self._bind()
        with patch('mta.runtime.validation_storage.read_input', return_value={'mdm_input': snapshot}):
            with transaction.atomic(): finalize_consumption(self.run)
        self.assertFalse(MdmDailySkuArchive.objects.filter(pk=old.pk).exists())

    def test_completed_task_prunes_at_inclusive_configured_boundary(self):
        task = MdmTask.objects.create(source=self.source, TaskID='EXPIRED',
            PendingSince=datetime(2026, 9, 29, tzinfo=ZoneInfo('Asia/Calcutta')),
            TaskStatus='1', MasterId='1', Actiontype=2)
        sub = MdmSubTask.objects.create(source=self.source, TaskID='EXPIRED',
                                        ApproverId='2', TaskStatus='2')
        history = MdmSkuHistory.objects.create(source=self.source, TaskId='EXPIRED',
            SKUCode='SKU', SKUDescription='Old', Status='3')
        requested = MdmSkuRequested.objects.create(source=self.source, TaskId='EXPIRED',
            SKUCode='SKU', SKUDescription='Old', ActionType=2,
            Approved=False, Reverted=False)
        snapshot = self._bind()
        with patch('mta.runtime.validation_storage.read_input', return_value={'mdm_input': snapshot}):
            with transaction.atomic(): finalize_consumption(self.run)
        for model, pk in ((MdmTask, task.pk), (MdmSubTask, sub.pk),
                          (MdmSkuHistory, history.pk), (MdmSkuRequested, requested.pk)):
            self.assertFalse(model.objects.filter(pk=pk).exists())
