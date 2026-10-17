"""Relational report protocol checks, not synthetic engine acceptance."""
from datetime import date
from unittest.mock import patch
from django.db import transaction
from django.test import TestCase

from mta.presentation.excess_storage import read_excess, write_excess
from development.excess_storage import publish_existing
from mta.runtime.models import CalculationRun, ExcessInventoryRow, ExcessProjection
from tests.test_excess_presentation import ExcessProducerTest


class ExcessProjectionTest(TestCase):
    def setUp(self):
        probe = ExcessProducerTest()
        probe.setUp()
        self.output = dict(BPRReports=[dict(vf_RationedReqReport=[probe.row,dict(probe.row)])],
            ClosingState=[dict(dbm=dict(SKULocStandardAttributes=[probe.attr]))])
        self.run = CalculationRun.objects.create(input_digest='a'*64,input_payload={},
            execution_revision='excess-storage-protocol',kind='DAILY_CHAIN',status='SUCCEEDED',
            business_date=date(2026,6,17),output_digest='b'*64,parity_summary={'status':'PASS'})

    def test_typed_population_roundtrip_and_no_evidence_read(self):
        receipt = write_excess(self.run,self.output)
        with patch('development.validation_storage.evidence_path',side_effect=AssertionError('not production')):
            rows = read_excess(self.run,output=self.output)
        self.assertEqual(receipt.row_count,2)
        self.assertEqual(rows[0],rows[1])
        self.assertEqual((rows[0]['ExcessQty'],rows[0]['Amount'],rows[0]['PhysicalInventoryPen']),(7,12,'-3.18'))

    def test_row_and_source_tampering_rejected(self):
        write_excess(self.run,self.output)
        ExcessInventoryRow.objects.filter(run=self.run,ordinal=1).update(Amount=999)
        with self.assertRaisesMessage(ValueError,'values/types/multiplicity'):
            read_excess(self.run,output=self.output)
        self.output['ClosingState'][0]['dbm']['SKULocStandardAttributes'][0]['Price']='2.000'
        with self.assertRaisesMessage(ValueError,'source identity'):
            read_excess(self.run,output=self.output)

    def test_mid_write_failure_rolls_back_all_added_report_rows(self):
        with self.assertRaisesMessage(RuntimeError,'injected'):
            with transaction.atomic():
                with patch('mta.presentation.excess_storage.read_excess',side_effect=RuntimeError('injected')):
                    write_excess(self.run,self.output)
        self.assertFalse(ExcessProjection.objects.exists())
        self.assertFalse(ExcessInventoryRow.objects.exists())
        self.run.refresh_from_db()
        self.assertEqual(self.run.status,'SUCCEEDED')

    def test_explicit_publication_is_idempotent_without_run_mutation(self):
        before = CalculationRun.objects.values().get(pk=self.run.pk)
        with patch('mta.runtime.services.read_outputs',return_value=self.output):
            first = publish_existing(self.run.pk,expected_output_digest='b'*64)
            second = publish_existing(self.run.pk,expected_output_digest='b'*64)
        self.assertEqual(first.created_at,second.created_at)
        self.assertEqual(CalculationRun.objects.values().get(pk=self.run.pk),before)
        self.assertEqual(ExcessInventoryRow.objects.count(),2)

    def test_unaccepted_or_wrong_run_cannot_publish(self):
        with self.assertRaisesMessage(ValueError,'accepted source'):
            publish_existing(self.run.pk,expected_output_digest='c'*64)
        self.run.parity_summary={'status':'DIVERGENCE'}
        self.run.save(update_fields=['parity_summary'])
        with self.assertRaisesMessage(ValueError,'accepted source'):
            publish_existing(self.run.pk,expected_output_digest='b'*64)
        self.assertFalse(ExcessProjection.objects.exists())
