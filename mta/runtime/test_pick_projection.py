"""Storage/transaction probes only; not replacement synthetic parity inputs."""
from copy import deepcopy
from datetime import date
import os
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.db import transaction
from django.test import TransactionTestCase

from mta.presentation.pick_storage import read_pick_bands, write_pick_bands
from development.pick_storage import restore_pick_bands
from mta.runtime.models import CalculationRun, Checkpoint, PickBand, PickProjection
from development.validation_storage import persist_trace
from mta.serialization import digest


class PickProjectionTest(TransactionTestCase):
    available_apps = ['mta.runtime', 'django.contrib.contenttypes']

    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        environment = patch.dict(os.environ, VF_EVIDENCE_ROOT=self.directory.name)
        environment.start()
        self.addCleanup(environment.stop)
        self.row = dict(sku_code='337', location_code='AG515802', parent_location_code='AG515802',
                        to_black='0', to_red='0', to_yellow='0', to_green='0', to_blue='0')
        self.rows = [self.row, deepcopy(self.row)]
        self.calculated = [dict(capability='r1_ration_bifurcation', rows=self.rows)]
        self.run = CalculationRun.objects.create(input_digest='a'*64, input_payload={},
            execution_revision='storage-protocol-only', kind='DAILY_CHAIN',
            business_date=date(2026,6,17), status='SUCCEEDED', output_digest='b'*64,
            parity_summary=dict(status='PASS', sha256='c'*64, comparisons={'calculation/bifurcation':'PASS'}))
        Checkpoint.objects.create(run=self.run, name='CalculationOutputs',
            **persist_trace(self.run, 'CalculationOutputs', self.calculated))

    def write(self):
        with transaction.atomic():
            return write_pick_bands(self.run, self.calculated, provenance={'origin':'protocol-test'})

    def test_duplicate_rows_wire_identity_and_no_trace_on_read(self):
        self.write()
        with patch('development.validation_storage.evidence_path', side_effect=AssertionError('no trace read')):
            self.assertEqual(read_pick_bands(self.run), self.rows)
        self.assertEqual(list(self.run.pick_bands.values_list('ordinal', flat=True).order_by('ordinal')), [0,1])

    def test_mutation_and_missing_ordinal_fail_readback(self):
        self.write()
        self.run.pick_bands.filter(ordinal=1).update(to_blue=1)
        with self.assertRaisesMessage(ValueError, 'typed values/multiplicity'):
            read_pick_bands(self.run)
        self.run.pick_bands.filter(ordinal=1).delete()
        with self.assertRaisesMessage(ValueError, 'population/order'):
            read_pick_bands(self.run)

    def test_mid_write_failure_rolls_back_receipt_and_all_rows(self):
        with patch('mta.presentation.pick_storage._read_rows', side_effect=RuntimeError('injected readback failure')):
            with self.assertRaisesMessage(RuntimeError, 'injected readback'):
                self.write()
        self.assertEqual(PickProjection.objects.count(), 0)
        self.assertEqual(PickBand.objects.count(), 0)
        self.run.refresh_from_db()
        self.assertEqual(self.run.status, 'SUCCEEDED')
        self.assertEqual(self.run.checkpoints.count(), 1)

    def test_explicit_restore_is_idempotent_and_preserves_run(self):
        before = CalculationRun.objects.values().get(pk=self.run.pk)
        with patch('mta.runtime.services.read_outputs', return_value={}):
            first = restore_pick_bands(self.run.pk, expected_output_digest='b'*64)
            second = restore_pick_bands(self.run.pk, expected_output_digest='b'*64)
            self.assertEqual(first.created_at, second.created_at)
            with self.assertRaisesMessage(ValueError, 'explicit Pick calculation'):
                restore_pick_bands(self.run.pk, expected_output_digest='d'*64)
        self.assertEqual(CalculationRun.objects.values().get(pk=self.run.pk), before)
        self.assertEqual(read_pick_bands(self.run), self.rows)

    def test_changed_evidence_cannot_publish_rows(self):
        self.run.checkpoints.update(evidence_sha256='0'*64)
        with patch('mta.runtime.services.read_outputs', return_value={}):
            with self.assertRaisesMessage(ValueError, 'evidence file drift'):
                restore_pick_bands(self.run.pk, expected_output_digest='b'*64)
        self.assertFalse(PickProjection.objects.exists())

    def test_unaccepted_overall_status_cannot_publish_even_if_bands_pass(self):
        for status in (None, 'DIVERGENCE', 'NOT_VERIFIED'):
            self.run.parity_summary['status'] = status
            self.run.save(update_fields=['parity_summary'])
            with self.assertRaisesMessage(ValueError, 'explicit Pick calculation'):
                restore_pick_bands(self.run.pk, expected_output_digest='b'*64)
        self.assertFalse(PickProjection.objects.exists())

    def test_reject_wire_type_change_and_missing_producer(self):
        self.rows[0]['to_blue'] = 0
        with self.assertRaisesMessage(ValueError, 'wire value'):
            self.write()
        self.calculated.clear()
        with self.assertRaisesMessage(ValueError, 'one produced'):
            self.write()
        self.assertFalse(PickProjection.objects.exists())
