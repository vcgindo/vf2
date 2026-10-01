"""Transactional report protocol, not replacement business parity fixtures."""
from datetime import date
from unittest.mock import patch
from django.db import transaction
from django.test import TestCase
from mta.presentation.expedite_storage import write_expedite,read_expedite,publish_existing
from mta.runtime.models import CalculationRun,ExpediteRow,ExpediteProjection
from tests.test_expedite_presentation import ExpediteTest


class ExpediteProjectionTest(TestCase):
    def setUp(self):
        probe=ExpediteTest(); probe.setUp()
        self.output=dict(BPRReports=[dict(vf_RationedReqReport=[probe.parent])],ClosingState=[dict(
            importer=dict(MasterData=[probe.master]),dbm=dict(SKULocStandardAttributes=[probe.standard]*2),
            btr=dict(ExpediteDispatches=[probe.age]))])
        self.mock_pick=patch('mta.presentation.expedite_storage.pick_rows',return_value=[probe.row])
        self.mock_pick.start(); self.addCleanup(self.mock_pick.stop)
        self.run=CalculationRun.objects.create(input_digest='a'*64,input_payload={},execution_revision='expedite-protocol',
            business_date=date(2026,6,17),kind='DAILY_CHAIN',status='SUCCEEDED',output_digest='b'*64,
            parity_summary=dict(status='PASS'))

    def test_readback_and_tamper_rejection_without_trace(self):
        write_expedite(self.run,self.output,bands=[])
        with patch('mta.runtime.validation_storage.evidence_path',side_effect=AssertionError('no trace')):
            rows=read_expedite(self.run,output=self.output,bands=[])
        self.assertEqual(len(rows),2); self.assertEqual(rows[0],rows[1])
        self.assertEqual(rows[0]['BRAge'],12)
        ExpediteRow.objects.filter(run=self.run,ordinal=1).update(RationedQty=99)
        with self.assertRaisesRegex(ValueError,'multiplicity drift'): read_expedite(self.run,output=self.output,bands=[])

    def test_midwrite_failure_rolls_back_receipt_and_rows(self):
        with self.assertRaisesRegex(RuntimeError,'injected'):
            with transaction.atomic():
                with patch('mta.presentation.expedite_storage.read_expedite',side_effect=RuntimeError('injected')):
                    write_expedite(self.run,self.output,bands=[])
        self.assertFalse(ExpediteRow.objects.exists()); self.assertFalse(ExpediteProjection.objects.exists())

    def test_idempotent_publication_does_not_update_accepted_run(self):
        before=CalculationRun.objects.values().get(pk=self.run.pk)
        with patch('mta.runtime.services.read_outputs',return_value=self.output), \
             patch('mta.presentation.expedite_storage.read_pick_bands',return_value=[]):
            first=publish_existing(self.run.pk,expected_output_digest='b'*64)
            second=publish_existing(self.run.pk,expected_output_digest='b'*64)
        self.assertEqual(first.created_at,second.created_at)
        self.assertEqual(before,CalculationRun.objects.values().get(pk=self.run.pk))
        self.output['ClosingState'][0]['btr']['ExpediteDispatches'][0]['BRAge']=0
        with self.assertRaisesRegex(ValueError,'source identity'): read_expedite(self.run,output=self.output,bands=[])

    def test_wrong_identity_rejected(self):
        with self.assertRaisesRegex(ValueError,'accepted source'):
            publish_existing(self.run.pk,expected_output_digest='c'*64)
