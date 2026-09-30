from copy import deepcopy
import json
from pathlib import Path
from unittest.mock import patch
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

    def test_raw_file_source_and_generated_lineage_roundtrip(self):
        payload=json.loads(Path('mta/fixtures/r1_gulfoil_common_selected.json').read_text())
        run=execute_current_day(payload,execution_revision='file-source-test-v1')
        output=read_outputs(run)
        self.assertEqual(run.input_payload,payload)
        self.assertEqual(output['r1_gulfoil_adapter'][0]['source'],payload)
        self.assertTrue(output['r1_order_route'])

    def test_calculation_uses_durable_snapshot_not_caller_object(self):
        original=deepcopy(self.payload)
        def calculate(snapshot):
            self.payload['rationed_quantity']=999
            self.assertEqual(snapshot,original)
            return calculate_current_day(snapshot)
        with patch('mta.runtime.services.calculate_current_day',side_effect=calculate):
            run=execute_current_day(self.payload,execution_revision='snapshot-test-v1')
        self.assertEqual(run.input_payload,original)
        self.assertEqual(read_outputs(run),calculate_current_day(original))
