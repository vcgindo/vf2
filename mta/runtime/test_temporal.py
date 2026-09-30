"""Persistence protocol tests; stub outputs here are NOT business parity inputs."""
from copy import deepcopy
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.test import TransactionTestCase
from mta.runtime.models import CalculationRun, RunCommand, Checkpoint
from mta.runtime.services import read_outputs
from mta.runtime.temporal import BOUNDARIES, execute_day, record_command
from mta.runtime.validation_storage import export_run
from parity.output_archive import OutputArchive


class TemporalPersistenceTest(TransactionTestCase):
    available_apps=['mta.runtime','django.contrib.contenttypes']
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.environment = patch.dict(os.environ, {'VF_EVIDENCE_ROOT': self.directory.name})
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.profile = {'delivery': {'site_code': 'VECTORFLOW-DEMO'}}
        self.state = {'dbm': {
            'DBMMaster': [{'SKUCode': '337', 'WhCode': 'AG515802', 'Norm': 220}],
            'Suggestions': [{'SKUCode': '337', 'WhCode': 'AG515802', 'NewNorm': 250}],
            'NormAcceptanceTbl': [], 'NormsInSleepModeTbl': []}}
        self.opening = dict(identity='persistence-protocol-only', opening_date='2026-06-05', state=self.state)
        self.seen = []

    def calculate(self, prior, opening_date, day, profile, identity, calculate, exceptions):
        self.seen.append(deepcopy(prior))
        return dict(ClosingState=[prior], DBMFinal=[prior['dbm']], Lineage=[],
                    MajorBoundaries=[dict(boundary=name, state={}) for name in BOUNDARIES])

    def run_day(self, index=0, **kwargs):
        options = dict(day={'business_date': f'2026-06-{6+index:02d}'},
                       profile=self.profile, execution_revision='protocol-test')
        options.update(kwargs)
        if 'predecessor' not in options:
            options['opening'] = self.opening
        with patch('mta.runtime.temporal.calculate_day', side_effect=self.calculate):
            return execute_day(**options)

    def action(self, run, operation='APPLY', **kwargs):
        options = dict(operation=operation, selected=[['337', 'AG515802']],
                       timestamp='2026-06-06T12:00:00+05:30', actor='protocol-test', idempotency_key='action-1')
        options.update(kwargs)
        return record_command(run, **options)

    def test_next_day_consumes_own_closing_and_command_without_mutating_previous(self):
        first = self.run_day()
        before = read_outputs(first)
        event = self.action(first)
        self.assertEqual(self.action(first).pk, event.pk)
        second = self.run_day(1, predecessor=first)
        self.assertEqual(second.predecessor_id, first.pk)
        self.assertEqual(self.seen[-1]['dbm']['NormAcceptanceTbl'], [dict(
            SKUCode='337', WhCode='AG515802', AcceptanceDate='2026-06-06', OldNorm=220, NewNorm=250)])
        self.assertEqual(read_outputs(first), before)
        self.assertEqual(read_outputs(second)['Lineage'][0]['run_id'], str(first.pk))
        self.assertEqual(read_outputs(second)['Lineage'][0]['commands'][0]['id'], event.pk)
        self.assertEqual(self.run_day(1, predecessor=first).pk, second.pk)
        self.assertEqual(CalculationRun.objects.count(), 2)

    def test_sleep_effect_and_same_key_different_payload_rejected(self):
        first = self.run_day()
        self.action(first, 'SLEEP')
        with self.assertRaisesMessage(ValueError, 'different command facts'):
            self.action(first)
        self.run_day(1, predecessor=first)
        self.assertEqual(self.seen[-1]['dbm']['Suggestions'], [])
        self.assertEqual(self.seen[-1]['dbm']['NormsInSleepModeTbl'], [dict(
            SKUCode='337', WhCode='AG515802', StartDate='2026-06-06')])

    def test_action_and_implicit_fork_rejected_after_consumption(self):
        first = self.run_day()
        self.run_day(1, predecessor=first)
        with self.assertRaisesMessage(ValueError, 'already been consumed'):
            self.action(first)
        with self.assertRaisesMessage(ValueError, 'no implicit timeline fork'):
            self.run_day(2, predecessor=first)

    def test_command_tamper_prevents_next_day(self):
        first = self.run_day()
        event = self.action(first)
        RunCommand.objects.filter(pk=event.pk).update(after_digest='0'*64)
        with self.assertRaisesMessage(ValueError, 'Command output drift'):
            self.run_day(1, predecessor=first)
        self.assertEqual(CalculationRun.objects.count(), 1)

    def test_same_opening_cannot_silently_start_another_timeline(self):
        first = self.run_day()
        self.assertEqual(self.run_day().pk, first.pk)
        with self.assertRaisesMessage(ValueError, 'Opening already used'):
            self.run_day(1)
        self.assertEqual(CalculationRun.objects.count(), 1)

    def test_actions_cannot_be_backdated_or_consumed_before_their_date(self):
        first = self.run_day()
        with self.assertRaisesMessage(ValueError, 'Command date precedes'):
            self.action(first, timestamp='2026-06-05T12:00:00+05:30')
        self.action(first, timestamp='2026-06-08T12:00:00+05:30')
        with self.assertRaisesMessage(ValueError, 'Command date precedes'):
            self.action(first, timestamp='2026-06-07T12:00:00+05:30', idempotency_key='action-2')
        with self.assertRaisesMessage(ValueError, 'Command date outside'):
            self.run_day(1, predecessor=first)
        self.run_day(2, predecessor=first)

    def test_changed_durable_input_cannot_receive_calculated_outputs(self):
        def corrupt(*args):
            output = self.calculate(*args)
            CalculationRun.objects.filter(pk=args[4]).update(input_payload={'changed':True})
            return output
        with patch('mta.runtime.temporal.calculate_day', side_effect=corrupt):
            with self.assertRaisesMessage(ValueError, 'Input snapshot changed'):
                execute_day(day={'business_date':'2026-06-06'}, profile=self.profile,
                            execution_revision='drift-test', opening=self.opening)
        run=CalculationRun.objects.get()
        self.assertEqual(run.status,'FAILED')
        self.assertEqual(run.checkpoints.count(),0)

    def test_input_snapshot_and_predecessor_site_are_enforced(self):
        first = self.run_day()
        self.state['dbm']['DBMMaster'][0]['Norm'] = 999
        with self.assertRaisesMessage(ValueError, 'another site'):
            self.run_day(1, predecessor=first, profile={'delivery': {'site_code': 'ANOTHER'}})
        self.run_day(1, predecessor=first)
        self.assertEqual(self.seen[-1]['dbm']['DBMMaster'][0]['Norm'], 220)

    def test_incomplete_boundary_roster_is_durable_failed_not_publication(self):
        def incomplete(*args):
            output = self.calculate(*args)
            output['MajorBoundaries'].pop()
            return output
        with patch('mta.runtime.temporal.calculate_day', side_effect=incomplete):
            with self.assertRaisesMessage(ValueError, 'Incomplete daily boundary roster'):
                execute_day(day={'business_date': '2026-06-06'}, profile=self.profile,
                            execution_revision='bad-roster', opening=self.opening)
        run = CalculationRun.objects.get()
        self.assertEqual(run.status, 'FAILED')
        self.assertEqual(run.checkpoints.count(), 0)

    def test_validation_boundaries_are_external_and_exactly_verified(self):
        run = self.run_day()
        self.assertNotIn('MajorBoundaries', read_outputs(run))
        checkpoint = run.checkpoints.get(name='MajorBoundaries')
        self.assertEqual(checkpoint.rows, [])
        self.assertEqual(checkpoint.row_count, 8)
        manifest = export_run(run, Path(self.directory.name) / 'export')
        archive = OutputArchive(manifest)
        self.assertEqual([r['boundary'] for r in archive.iter_rows('MajorBoundaries')], list(BOUNDARIES))
        self.assertEqual(archive['ClosingState'], read_outputs(run)['ClosingState'])
        archive.verify(run.output_digest)
        Checkpoint.objects.filter(pk=checkpoint.pk).update(evidence_sha256='0'*64)
        with self.assertRaisesMessage(ValueError, 'evidence file drift'):
            export_run(run, Path(self.directory.name) / 'tampered-export')

    def test_atomic_failure_keeps_unpublished_trace_but_no_checkpoint_or_action(self):
        create = Checkpoint.objects.create
        def fail_trace(**fields):
            if fields['name'] == 'MajorBoundaries':
                raise RuntimeError('injected after external trace write')
            return create(**fields)
        with patch('mta.runtime.services.Checkpoint.objects.create', side_effect=fail_trace):
            with self.assertRaisesMessage(RuntimeError, 'after external trace'):
                self.run_day()
        run = CalculationRun.objects.get()
        self.assertEqual(run.status, 'FAILED')
        self.assertEqual(run.checkpoints.count(), 0)
        self.assertEqual(run.commands.count(), 0)
        self.assertEqual(run.output_digest, '')
        self.assertTrue((Path(self.directory.name) / str(run.pk) / 'MajorBoundaries.jsonl.gz').is_file())
