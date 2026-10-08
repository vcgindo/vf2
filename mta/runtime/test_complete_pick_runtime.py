"""Pick file/storage protocol tests; stub day outputs are not business parity."""
from pathlib import Path
from unittest.mock import patch
from django.test import SimpleTestCase, TransactionTestCase, override_settings

from mta.runtime import test_temporal as temporal_protocol
from mta.runtime.models import CalculationRun
from mta.runtime.services import read_outputs
from mta.application.complete_daily_batch_files import PICK_NAMES, reports_from_pick_state, sqlcmd_bytes
from mta.domain.remaining_capabilities import calculate_pick_list_state
from mta.serialization import storage
from tests.test_pick_stage_state import fixture


class CompletePickReplayUnitTests(SimpleTestCase):
    def test_completed_retry_restores_from_own_rows_without_calculation(self):
        from mta.runtime.temporal import replay_completed
        run = type('Run', (), {'pk': 'owned-run'})()
        complete = {'LogisticPickList': [{'owned': 1}],
                    'PickListDataForTruckFormation': []}
        with patch('mta.runtime.temporal.read_outputs',
                   return_value={'ClosingState': [{'complete': complete}]}), \
                patch('mta.application.complete_daily_batch_files.write_run_pick_files') as write:
            self.assertIs(replay_completed(run, complete_pick=True,
                                           pick_output_root='owned-root'), run)
        write.assert_called_once_with('owned-run', complete, 'owned-root')

    def test_failed_or_unreadable_retry_cannot_restore_files(self):
        from mta.runtime.temporal import replay_completed
        run = type('Run', (), {'pk': 'failed-run'})()
        with patch('mta.runtime.temporal.read_outputs', side_effect=ValueError('Run is not complete')), \
                patch('mta.application.complete_daily_batch_files.write_run_pick_files') as write, \
                self.assertRaisesMessage(ValueError, 'Run is not complete'):
            replay_completed(run, complete_pick=True, pick_output_root='owned-root')
        write.assert_not_called()


@override_settings(VF_MTA_DAILY_PUBLICATION=False)
class CompletePickRuntimeTests(TransactionTestCase):
    available_apps = temporal_protocol.TemporalPersistenceTest.available_apps
    calculate = temporal_protocol.TemporalPersistenceTest.calculate
    run_day = temporal_protocol.TemporalPersistenceTest.run_day
    _fixture_teardown = temporal_protocol.TemporalPersistenceTest._fixture_teardown

    def setUp(self):
        temporal_protocol.TemporalPersistenceTest.setUp(self)
        self.profile['complete_pick'] = {'policy': 'canonical-tied-order-v1'}
        state = storage(calculate_pick_list_state(fixture()))
        self.state['complete'] = {name: state[name] for name in
                                 ('LogisticPickList', 'PickListDataForTruckFormation')}

    def test_pick_files_retry_from_own_typed_state(self):
        run = self.run_day(evidence_mode='production', pick_output_root=self.directory.name)
        state = read_outputs(run)['ClosingState'][0]['complete']
        self.assertEqual(state, self.state['complete'])
        reports = reports_from_pick_state(state)
        for kind, name in PICK_NAMES.items():
            expected = sqlcmd_bytes(reports[kind]['resultsets'])
            for folder in ('output', 'download'):
                self.assertEqual((Path(self.directory.name)/str(run.pk)/folder/name).read_bytes(), expected)
        target = Path(self.directory.name)/str(run.pk)/'download'/PICK_NAMES['logistic']
        target.unlink()
        again = self.run_day(evidence_mode='production', pick_output_root=self.directory.name)
        self.assertEqual(again.pk, run.pk)
        self.assertEqual(len(self.seen), 1)
        self.assertEqual(target.read_bytes(), sqlcmd_bytes(reports['logistic']['resultsets']))

    def test_initial_opening_collision_restores_files_without_calculation(self):
        run = self.run_day(evidence_mode='production', pick_output_root=self.directory.name)
        target = Path(self.directory.name)/str(run.pk)/'output'/PICK_NAMES['remaining_summary']
        expected = target.read_bytes()
        target.unlink()
        # Simulate the concurrent-start window: the broad digest lookup did not
        # observe the row, while the unique opening key did.
        with patch.object(CalculationRun.objects, 'filter') as candidates:
            candidates.return_value.first.return_value = None
            again = self.run_day(evidence_mode='production', pick_output_root=self.directory.name)
        self.assertEqual(again.pk, run.pk)
        self.assertEqual(len(self.seen), 1)
        self.assertEqual(target.read_bytes(), expected)

    def test_file_failure_prevents_completed_run_and_preserves_failed_attempt(self):
        with patch('mta.application.complete_daily_batch_files.write_run_pick_files',
                   side_effect=OSError('deliberate Pick file failure')):
            with self.assertRaisesMessage(OSError, 'deliberate Pick file failure'):
                self.run_day(evidence_mode='production', pick_output_root=self.directory.name)
        run = CalculationRun.objects.get(execution_revision=self.revision)
        self.assertEqual(run.status, 'FAILED')
        self.assertFalse(run.production_manifest)
        with self.assertRaises(ValueError):
            self.run_day(evidence_mode='production', pick_output_root=self.directory.name)
        self.assertEqual(CalculationRun.objects.filter(execution_revision=self.revision).count(), 1)

    def test_partial_files_are_isolated_from_previously_completed_run(self):
        import shutil
        import uuid
        completed = self.run_day(evidence_mode='production', pick_output_root=self.directory.name)
        folder = Path(self.directory.name)/str(completed.pk)
        before = {p.relative_to(folder).as_posix():p.read_bytes() for p in folder.rglob('*.csv')}
        self.revision = 'pick-partial-'+str(uuid.uuid4())
        original = shutil.copyfile
        calls = []
        def fail_second(source, target, *args, **kwargs):
            calls.append(str(target))
            if len(calls)==2:
                raise OSError('deliberate second-file failure')
            return original(source,target,*args,**kwargs)
        with patch('mta.application.complete_daily_batch_files.shutil.copyfile', side_effect=fail_second):
            with self.assertRaisesMessage(OSError, 'deliberate second-file failure'):
                self.run_day(evidence_mode='production', pick_output_root=self.directory.name)
        failed = CalculationRun.objects.get(execution_revision=self.revision)
        self.assertEqual(failed.status,'FAILED')
        self.assertFalse(failed.production_manifest)
        self.assertTrue(list((Path(self.directory.name)/str(failed.pk)).rglob('*.csv')))
        self.assertEqual({p.relative_to(folder).as_posix():p.read_bytes() for p in folder.rglob('*.csv')},before)
        with self.assertRaises(ValueError):
            read_outputs(failed)
