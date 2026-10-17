"""Additive Fulfilment transaction proof, not business parity fixtures."""
from datetime import date
from unittest.mock import patch
from django.db import transaction
from django.test import TestCase
from mta.presentation.fulfillment_storage import write_fulfillment, read_fulfillment
from development.fulfillment_storage import publish_existing
from mta.runtime.models import CalculationRun,Checkpoint,FulfillmentProjection,FulfillmentSummaryRow,FulfillmentDetailRow
from mta.serialization import digest
from tests.test_fulfillment_presentation import FulfillmentProducerTest


class FulfillmentProjectionTest(TestCase):
    def setUp(self):
        probe=FulfillmentProducerTest(); probe.setUp()
        self.output=dict(BPRReports=[dict(vf_RationedReqReport=[probe.row,probe.row])],
            ClosingState=[dict(dbm=dict(SKULocStandardAttributes=[probe.attr]),orders=dict(SpikeOrderData=[probe.order]))])
        self.calculated=[dict(capability='r1_order_route',rows=[dict(order_id='unit-order',sku_code='337',
            location_code='AG515802',child_location_code=None,due_date='2026-06-16')])]
        self.run=CalculationRun.objects.create(input_digest='a'*64,input_payload={},business_date=date(2026,6,17),
            kind='DAILY_CHAIN',status='SUCCEEDED',output_digest='b'*64,execution_revision='fulfillment-protocol',
            parity_summary=dict(status='PASS',comparisons={'calculation/routes':'PASS'}))
        Checkpoint.objects.create(run=self.run,name='CalculationOutputs',rows=[],row_count=1,digest=digest(self.calculated))

    def test_readback_duplicates_no_trace_and_source_identity(self):
        write_fulfillment(self.run,self.output,self.calculated)
        with patch('development.validation_storage.evidence_path',side_effect=AssertionError('not HTTP production')):
            rows=read_fulfillment(self.run,output=self.output)
        self.assertEqual((len(rows['summary']),len(rows['details'])),(2,1))
        self.assertEqual(rows['summary'][0],rows['summary'][1])
        self.assertEqual(rows['details'][0]['OrderStatus'],'Over Due')
        FulfillmentDetailRow.objects.filter(run=self.run).update(PendingQty=999)
        with self.assertRaisesRegex(ValueError,'multiplicity drift'):
            read_fulfillment(self.run,output=self.output)

    def test_mid_write_failure_rolls_back_all_projection_tables(self):
        with self.assertRaisesRegex(RuntimeError,'injected'):
            with transaction.atomic():
                with patch('mta.presentation.fulfillment_storage._read',side_effect=RuntimeError('injected')):
                    write_fulfillment(self.run,self.output,self.calculated)
        for model in (FulfillmentProjection,FulfillmentSummaryRow,FulfillmentDetailRow):
            self.assertFalse(model.objects.exists())

    def test_idempotent_restore_and_unaccepted_route_rejection(self):
        first=write_fulfillment(self.run,self.output,self.calculated)
        before=CalculationRun.objects.values().get(pk=self.run.pk)
        with patch('mta.runtime.services.read_outputs',return_value=self.output):
            second=publish_existing(self.run.pk,expected_output_digest='b'*64)
        self.assertEqual(first.created_at,second.created_at)
        self.assertEqual(before,CalculationRun.objects.values().get(pk=self.run.pk))
        self.run.parity_summary['comparisons']['calculation/routes']='FAIL'
        self.run.save(update_fields=['parity_summary'])
        with self.assertRaisesRegex(ValueError,'accepted Fulfilment source'):
            publish_existing(self.run.pk,expected_output_digest='b'*64)
