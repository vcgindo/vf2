from copy import deepcopy
import json
from pathlib import Path
from django.test import TransactionTestCase

from mta.runtime.models import CalculationRun, Checkpoint
from mta.runtime.services import execute_current_day, read_outputs
from mta.planning.engine import calculate_current_day


class CurrentDayPersistenceTest(TransactionTestCase):
    def setUp(self):
        self.payload = json.loads(Path('mta/fixtures/r1_raw_current_day.json').read_text())

    def test_atomic_complete_readback_and_idempotency(self):
        run = execute_current_day(self.payload, execution_revision='persistence-test-v1')
        self.assertEqual(read_outputs(run), calculate_current_day(self.payload))
        again = execute_current_day(self.payload, execution_revision='persistence-test-v1')
        self.assertEqual(run.pk, again.pk)
        self.assertEqual(CalculationRun.objects.count(), 1)

    def test_tampered_rows_do_not_pass_retry(self):
        run = execute_current_day(self.payload, execution_revision='persistence-test-v1')
        Checkpoint.objects.filter(run=run, name='r1_requirement').update(rows=[])
        with self.assertRaisesMessage(ValueError, 'storage drift'):
            execute_current_day(self.payload, execution_revision='persistence-test-v1')

    def test_missing_checkpoint_does_not_pass_retry(self):
        run = execute_current_day(self.payload, execution_revision='persistence-test-v1')
        Checkpoint.objects.filter(run=run, name='r1_requirement').delete()
        with self.assertRaisesMessage(ValueError, 'roster'):
            read_outputs(run)

    def test_bad_input_retains_failure_but_no_partial_outputs(self):
        self.payload['rationed_quantity'] = 10
        with self.assertRaises(ValueError):
            execute_current_day(self.payload, execution_revision='persistence-test-v1')
        run = CalculationRun.objects.get()
        self.assertEqual(run.status, 'FAILED')
        self.assertEqual(run.checkpoints.count(), 0)
