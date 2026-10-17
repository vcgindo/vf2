"""Supplier execute_day routing proof, with only the real supplier calculation.

The wider day calculator/output publisher are bounded test doubles. This does
not execute or qualify a business day; capture, typed storage, retry routing,
supplier validation and application consumption are production code.
"""
from unittest.mock import patch
from tempfile import TemporaryDirectory
import os
import uuid

from django.db import transaction
from django.test import TransactionTestCase, override_settings

from mta.application.r1_importer_master import RAW_COLUMNS
from mta.application.r1_supplier_input import process_supplier_validation
from mta.mdm.daily_input import finalize_consumption, install_pair_exclusions
from mta.mdm.source import DLL
from mta.mdm.supplier_source import install
from mta.runtime.mdm_daily_models import MdmDailyInputCapture
from mta.runtime.mdm_models import MdmSource
from mta.runtime.mdm_supplier_models import MdmSobApproved, MdmSobArchive, MdmSobRaw
from mta.runtime.models import CalculationRun
from mta.runtime.temporal import BOUNDARIES
from development.temporal import execute_day
from mta.runtime.input_reader import read_input
from mta.serialization import digest
from tests.test_nms_supplier_input import approved, fixture


@override_settings(VF_MTA_DAILY_PUBLICATION=False)
class SupplierRetryRoutingTests(TransactionTestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        environment = patch.dict(os.environ, {'VF_EVIDENCE_ROOT': self.directory.name})
        environment.start()
        self.addCleanup(environment.stop)
        self.identity = str(uuid.uuid4())
        self.source = MdmSource.objects.create(digest=digest(self.identity),
            database_name='owned-supplier-routing', dll_digest=DLL, receipt={})
        install_pair_exclusions(self.source, [], provenance={'fixture': self.identity})
        self.opening = {'identity': self.identity, 'opening_date': '2026-10-05',
            'state': {'importer_settings': [
                {'Parameter': 'NMSActive', 'Value': '1'},
                {'Parameter': 'TaskStatusLogHorizon', 'Value': '7'},
                {'Parameter': 'UpdatePWh_RLT_RCP_GCP', 'Value': '0'}]}}
        master = dict.fromkeys(RAW_COLUMNS)
        master.update(SKUCode='BASE', WhCode='LOC')
        self.day = {'business_date': '2026-10-06', 'raw_master': [master]}
        self.profile = {'delivery': {'site_code': 'SUPPLIER-RETRY'}}

    def _fixture_teardown(self):
        # Retain this owned proof: immutable production guards prohibit flush.
        pass

    def test_failed_attempt_retry_reuses_capture_and_retains_later_queue(self):
        raw, _, _ = fixture()
        install(self.source, raw, moq_format='WithoutDestLoc', upload_log_active=True,
                provenance={'fixture': 'explicit supplier retry routing'})
        first = MdmSobApproved.objects.create(source=self.source, **approved())
        self.opening['state']['importer_settings'].append(
            {'Parameter': 'NMSMOQInputDataFormat', 'Value': 'WithoutDestLoc'})
        master = {'tables': {'SiteDescriptionTbl': [], 'RejectedMaster': [],
            'MasterDataRaw': [], 'MasterData': [dict(SKUCode='337',
                WhCode='DP010290', ParentWhCode='LDC001')]}}
        seen = []

        def calculate(_prior, _date, day, *_args):
            seen.append(day['supplier_feeds'])
            stages = process_supplier_validation(day['supplier_feeds'], master, [],
                                                  '2026-10-06T00:00:00')
            result = {'MajorBoundaries': [{'boundary': name} for name in BOUNDARIES]}
            result['SupplierStages'] = [dict(stage=name, **value)
                                       for name, value in stages.items()]
            return result

        def publish(run, result, **_kwargs):
            with transaction.atomic():
                finalize_consumption(run, output=result)
                if len(seen) == 1:
                    raise RuntimeError('bounded supplier publication failure')
            return run

        with patch('mta.runtime.temporal.calculate_day', side_effect=calculate), \
                patch('mta.runtime.temporal.finish_run', side_effect=publish):
            with self.assertRaisesRegex(RuntimeError, 'bounded supplier publication failure'):
                execute_day(day=self.day, profile=self.profile, opening=self.opening,
                    mdm_source=self.source, execution_revision=self.identity + '-failed')
            failed = CalculationRun.objects.get(execution_revision=self.identity + '-failed')
            self.assertEqual(failed.status, 'FAILED')
            self.assertFalse(MdmSobArchive.objects.filter(run=failed).exists())
            self.assertTrue(MdmSobApproved.objects.filter(pk=first.pk).exists())
            frozen = read_input(failed)['mdm_input']
            later = MdmSobApproved.objects.create(source=self.source,
                **dict(approved(), WhCode='DP020819', SOB=75.5))
            retry = execute_day(day=self.day, profile=self.profile, opening=self.opening,
                mdm_retry=failed, execution_revision=self.identity + '-retry')

        self.assertEqual(seen[0], seen[1])
        self.assertEqual(read_input(retry)['mdm_input'], frozen)
        old = MdmDailyInputCapture.objects.get(run=failed)
        new = MdmDailyInputCapture.objects.get(run=retry)
        self.assertEqual((old.status, new.status, new.origin_id),
                         ('CAPTURED', 'CONSUMED', old.pk))
        self.assertEqual(list(MdmSobApproved.objects.filter(source=self.source)
            .values_list('pk', flat=True)), [later.pk])
        self.assertEqual(MdmSobArchive.objects.filter(run=retry).count(), 1)
        self.assertEqual(MdmSobRaw.objects.get(source=self.source,
            SKUCode='337', WHCode='DP010290', SupplierCode='LDC001').SOB, first.SOB)
