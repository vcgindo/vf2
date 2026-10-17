from datetime import date
from unittest.mock import patch
from django.db import transaction
from django.test import TestCase
from mta.presentation.pick_post_storage import write_pick_post, read_pick_post
from development.pick_post_storage import publish_existing
from mta.runtime.models import CalculationRun,PickPostRow,PickPostProjection
from tests.test_expedite_charts import PickPostTest


class PickPostProjectionTest(TestCase):
    def setUp(self):
        case=PickPostTest(); case.setUp()
        self.rows=[case.row,case.row]
        self.output={'BPRReports':[dict(vf_RationedReqReport=[])]}
        mock=patch('mta.presentation.pick_post_storage.pick_rows',return_value=self.rows)
        mock.start(); self.addCleanup(mock.stop)
        self.run=CalculationRun.objects.create(input_digest='a'*64,input_payload={},execution_revision='post-report-protocol',
            business_date=date(2026,6,17),kind='DAILY_CHAIN',status='SUCCEEDED',output_digest='b'*64,parity_summary=dict(status='PASS'))

    def test_readback_multiplicity_and_tamper_guard(self):
        write_pick_post(self.run,self.output,bands=[])
        with patch('development.validation_storage.evidence_path',side_effect=AssertionError('no trace')):
            rows=read_pick_post(self.run,output=self.output,bands=[])
        self.assertEqual(len(rows),2); self.assertEqual(rows[0],rows[1])
        PickPostRow.objects.filter(run=self.run,ordinal=1).update(PostPipelineInventoryColor='Green')
        with self.assertRaisesRegex(ValueError,'multiplicity drift'): read_pick_post(self.run,output=self.output,bands=[])

    def test_midwrite_rollback(self):
        with self.assertRaisesRegex(RuntimeError,'injected'):
            with transaction.atomic(),patch('mta.presentation.pick_post_storage.read_pick_post',side_effect=RuntimeError('injected')):
                write_pick_post(self.run,self.output,bands=[])
        self.assertFalse(PickPostProjection.objects.exists()); self.assertFalse(PickPostRow.objects.exists())

    def test_idempotent_publication_preserves_run(self):
        before=CalculationRun.objects.values().get(pk=self.run.pk)
        with patch('mta.runtime.services.read_outputs',return_value=self.output),patch('mta.presentation.pick_post_storage.read_pick_bands',return_value=[]):
            first=publish_existing(self.run.pk,expected_output_digest='b'*64)
            second=publish_existing(self.run.pk,expected_output_digest='b'*64)
        self.assertEqual(first.created_at,second.created_at)
        self.assertEqual(before,CalculationRun.objects.values().get(pk=self.run.pk))
        self.rows[0]=dict(self.rows[0],RationedReq=8)
        with self.assertRaisesRegex(ValueError,'source identity'): read_pick_post(self.run,output=self.output,bands=[])
