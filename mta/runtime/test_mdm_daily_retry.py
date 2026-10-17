"""Focused PostgreSQL proof of execute_day's frozen MDM retry wiring."""
from tempfile import TemporaryDirectory
from unittest.mock import patch
import os

from django.test import TransactionTestCase, override_settings

from mta.application.r1_importer_master import RAW_COLUMNS
from mta.runtime.mdm_daily_models import (MdmDailyInputCapture,
    MdmPairExclusionSource)
from mta.runtime.mdm_models import MdmSkuApproved, MdmSource
from mta.runtime.models import CalculationRun
from mta.runtime.temporal import BOUNDARIES
from mta.runtime.temporal import execute_day
from mta.runtime.input_reader import read_input
from mta.serialization import digest


@override_settings(VF_MTA_DAILY_PUBLICATION=False)
class DailyInputRetryTests(TransactionTestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.environment = patch.dict(os.environ,
                                      {'VF_EVIDENCE_ROOT': self.directory.name})
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.source = MdmSource.objects.create(digest='a' * 64,
            database_name='owned-retry', dll_digest='b' * 64, receipt={})
        MdmPairExclusionSource.objects.create(source=self.source, digest=digest([]),
            row_count=0, provenance={'kind': 'owned-empty-retry-source'})
        self.original = MdmSkuApproved.objects.create(source=self.source,
            SKUCode='CAPTURED', SKUDescription='Captured', ActionType=2,
            Approved=True, Reverted=False)
        self.opening = {'identity': 'mdm-retry-wiring',
            'opening_date': '2026-10-05', 'state': {'importer_settings': [
                {'Parameter': 'NMSActive', 'Value': '1'},
                {'Parameter': 'TaskStatusLogHorizon', 'Value': '7'},
                {'Parameter': 'UpdatePWh_RLT_RCP_GCP', 'Value': '0'}]}}
        master = dict.fromkeys(RAW_COLUMNS)
        master.update(SKUCode='BASE', WhCode='LOC')
        self.day = {'business_date': '2026-10-06', 'raw_master': [master]}
        self.profile = {'delivery': {'site_code': 'MDM-RETRY'}}

    def _result(self):
        return {'MajorBoundaries': [{'boundary': name} for name in BOUNDARIES]}

    def test_failed_attempt_retry_reuses_capture_and_retains_later_queue(self):
        # Exercise the same frozen request/remark boundary as the owned daily
        # shell, while calculation and finish remain bounded test doubles.
        self.profile['daily_publication'] = True
        self.opening['state']['supplier'] = {}
        self.profile['daily_publication_config'] = {'bpr_remark_horizon': 90}
        from mta.presentation import ancillary_live, daily_requests
        receipt = {'source': 'explicit-retry-test'}
        ancillary_live.initialize_owner(ancillary_live.BPR,
            provenance_digest=digest(receipt), provenance_receipt=receipt)
        daily_requests.initialize([], provenance=receipt)
        calculations = [RuntimeError('bounded calculation failure'), self._result()]

        def calculate(*_args):
            result = calculations.pop(0)
            if isinstance(result, Exception):
                raise result
            return result

        with patch('mta.runtime.temporal.calculate_day', side_effect=calculate), \
                patch('mta.runtime.temporal.finish_run', side_effect=lambda run, *_a, **_k: run), \
                patch('mta.runtime.temporal.read_outputs'):
            with self.assertRaisesRegex(RuntimeError, 'bounded calculation failure'):
                execute_day(day=self.day, profile=self.profile,
                    execution_revision='mdm-retry-attempt-1', opening=self.opening,
                    mdm_source=self.source)
            failed = CalculationRun.objects.get(execution_revision='mdm-retry-attempt-1')
            failed.refresh_from_db()
            self.assertEqual(failed.status, 'FAILED')
            frozen = read_input(failed)['mdm_input']
            frozen_remarks = read_input(failed)['remark_inputs']
            frozen_requests = read_input(failed)['request_inputs']
            from datetime import datetime, timezone
            ancillary_live.append(ancillary_live.BPR, [dict(SKUCode='BASE',
                WhCode='LOC', Remark='after failure', Username='requester')],
                actor_id='3', timestamp=datetime(2026, 10, 6, tzinfo=timezone.utc))

            later = MdmSkuApproved.objects.create(source=self.source,
                SKUCode='LATER', SKUDescription='Later', ActionType=2,
                Approved=True, Reverted=False)
            retry = execute_day(day=self.day, profile=self.profile,
                execution_revision='mdm-retry-attempt-2', opening=self.opening,
                mdm_retry=failed)

        retry_capture = MdmDailyInputCapture.objects.get(run=retry)
        failed_capture = MdmDailyInputCapture.objects.get(run=failed)
        self.assertEqual(retry_capture.origin_id, failed_capture.pk)
        self.assertEqual(read_input(retry)['mdm_input'], frozen)
        self.assertEqual(read_input(retry)['remark_inputs'], frozen_remarks)
        self.assertEqual(read_input(retry)['request_inputs'], frozen_requests)
        self.assertEqual(ancillary_live.image_rows(retry,
            ancillary_live.PATHS[ancillary_live.BPR]), [])
        self.assertEqual([row['SKUCode'] for row in
            frozen['rows']['sku']['approved']], ['CAPTURED'])
        self.assertTrue(MdmSkuApproved.objects.filter(pk=self.original.pk).exists())
        self.assertTrue(MdmSkuApproved.objects.filter(pk=later.pk).exists())
        failed.refresh_from_db()
        self.assertEqual(failed.status, 'FAILED')

    def _fixture_teardown(self):
        # Immutable production guards prohibit Django's global flush. This
        # uniquely owned test database is disposed by the runner after suite.
        pass
