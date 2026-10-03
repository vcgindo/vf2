"""PostgreSQL transaction protocol; fixtures are not report parity evidence."""
import hashlib
import json
import tempfile
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

from django.test import TestCase

from mta.presentation.excess import produce, PRODUCER_SHA
from mta.presentation.excess_history import OPENING, TERMINAL_ID, TERMINAL_DIGEST, run_identity, publish_history
from mta.presentation.excess_storage import inputs, write_excess
from mta.runtime.models import CalculationRun, ExcessProjection, ExcessInventoryRow
from mta.serialization import digest
from tests.test_excess_presentation import ExcessProducerTest


class ExcessHistoryTransactionTests(TestCase):
    def setUp(self):
        probe = ExcessProducerTest()
        probe.setUp()
        self.output = dict(BPRReports=[dict(vf_RationedReqReport=[probe.row])],
            ClosingState=[dict(dbm=dict(SKULocStandardAttributes=[probe.attr]))])
        self.runs = []
        for i in range(12):
            values = dict(input_digest=str(i).zfill(64), input_payload={},
                execution_revision='excess-history-protocol', kind='DAILY_CHAIN', status='SUCCEEDED',
                business_date=date(2026, 6, 6) + timedelta(days=i),
                output_digest=TERMINAL_DIGEST if i == 11 else str(i).zfill(64),
                predecessor=self.runs[-1] if self.runs else None, parity_summary={'status': 'PASS'})
            if i == 11:
                values['id'] = TERMINAL_ID
            self.runs.append(CalculationRun.objects.create(**values))
        projections = []
        for run in self.runs:
            source = inputs(self.output, run.business_date)
            rows = produce(**source)
            projections.append(dict(run_id=str(run.pk), producer_sha256=PRODUCER_SHA,
                source_digest=digest(source), rows_digest=digest(rows), row_count=len(rows)))
        self.manifest = dict(version='fresh-excess-history-v1', opening=OPENING, retention_days=90,
            producer_sha256=PRODUCER_SHA, runs=list(map(run_identity, self.runs)), projections=projections)
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.receipt = Path(self.directory.name) / 'protocol-only.json'
        self.receipt.write_text(json.dumps(dict(self.manifest, status='PASS_EXCESS_HISTORY')))
        self.manifest['comparison_sha256'] = hashlib.sha256(self.receipt.read_bytes()).hexdigest()
        write_excess(self.runs[-1], self.output)

    def test_middle_failure_rolls_back_new_days_preserving_existing_terminal(self):
        calls = 0
        def fail(run, output):
            nonlocal calls
            calls += 1
            receipt = write_excess(run, output)
            if calls == 6:
                raise RuntimeError('middle-history-failure')
            return receipt
        with patch('mta.presentation.excess_history.native_output', return_value=self.output), \
             patch('mta.presentation.excess_history.write_excess', side_effect=fail):
            with self.assertRaisesMessage(RuntimeError, 'middle-history-failure'):
                publish_history(TERMINAL_ID, self.manifest, self.receipt)
        self.assertEqual([str(pk) for pk in ExcessProjection.objects.values_list('run_id', flat=True)],
                         [str(self.runs[-1].pk)])
        self.assertEqual(ExcessInventoryRow.objects.count(), 1)

    def test_idempotent_complete_history_preserves_run_and_projection_metadata(self):
        before = list(CalculationRun.objects.order_by('business_date').values())
        terminal_before = ExcessProjection.objects.values().get(run=self.runs[-1])
        with patch('mta.presentation.excess_history.native_output', return_value=self.output):
            publish_history(TERMINAL_ID, self.manifest, self.receipt)
            first = list(ExcessProjection.objects.order_by('run_id').values())
            publish_history(TERMINAL_ID, self.manifest, self.receipt)
        self.assertEqual(first, list(ExcessProjection.objects.order_by('run_id').values()))
        self.assertEqual(before, list(CalculationRun.objects.order_by('business_date').values()))
        self.assertEqual(terminal_before, ExcessProjection.objects.values().get(run=self.runs[-1]))
        self.assertEqual(ExcessProjection.objects.count(), 12)
