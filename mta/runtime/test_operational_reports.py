"""Persisted stub-day report operations with real owned file/ZIP work."""
from copy import deepcopy
from functools import partial
import os
from pathlib import Path
import unittest
import uuid
from unittest.mock import patch

from django.test import override_settings
from mta.application.operational_io import archive_files
from mta.application.operational_norm_reports import REQUIRED_CONFIGURATION
from mta.runtime import test_temporal as fixture
from mta.runtime.operational_attempts import register_configuration, start_attempt, finish_attempt
from mta.runtime.operational_reports import materialize_report_operation, REPORT_OPERATIONS
from mta.runtime.operational_effects import verify_files
from mta.runtime.operational_native import read_population
from mta.runtime.operational_native import OperationalPopulation
from mta.runtime.operational_opening import OPENING_POLICY, OPENING_TABLES, ACTION_TYPES, install_opening, upload_inputs
from mta.runtime.services import read_outputs
from mta.serialization import digest, storage
from tests.test_operational_exceptions import master, daily, processed
from tests.test_operational_norm_reports import reports
from tests.test_operational_bor import requirement, rationed, bor_row
from mta.application.operational_capture import CAPTURE_POLICY, BAND_MAP
from mta.runtime.operational_source_models import OperationalCalculationSource
from mta.runtime.operational_bor import COLOR_SEQUENCE
from mta.runtime.relational_state import CATALOG


class OperationalReportProtocol(unittest.TestCase):
    run_day = fixture.TemporalPersistenceTest.run_day

    def calculate(self, *args):
        result = fixture.TemporalPersistenceTest.calculate(self, *args)
        result['Reports'] = reports(dbm_rows=[['S','W',2,1,'2026-06-06',None]])
        result['CalculationOutputs'].extend([
            dict(capability='r1_requirement_band', rows=[
                {modern:requirement()[native] for native,modern in BAND_MAP}]),
            dict(capability='r1_advance_stock_allocation', rows=[
                dict(sku_code='s ',source_location_code='w ',allocated_quantity=2,allocation_type='advance-stock'),
                dict(sku_code='S',source_location_code='W',allocated_quantity=3,allocation_type='advance-stock')]),
        ])
        rationed_row={name:None for name,_ in CATALOG['tables']['BPR/vf_RationedReqReport']}
        rationed_row.update(rationed())
        rationed_row['LeftoverParentStock']=rationed_row.pop('LeftOverParentStock')
        rationed_row['PhysicalInventoryColor']='Red'
        result['BPRFinal'][0].update(vf_RationedReqReport=[rationed_row])
        return result

    def setUp(self):
        fixture.TemporalPersistenceTest.setUp(self)
        settings = override_settings(VF_MTA_DAILY_PUBLICATION=False,VF_OPERATIONAL_UNLEASED_TESTS=True)
        settings.enable(); self.addCleanup(settings.disable)
        self.profile['delivery']['batch'] = dict(REQUIRED_CONFIGURATION)
        self.profile['force_flags'] = dict(nms_active=False)
        self.profile['operational_sources'] = CAPTURE_POLICY
        self.state['bpr'] = dict(BPRMaster=[master(Norm=100)], DailyConsumption=[daily()])
        self.state['importer'] = dict(MasterData=[processed(), processed(WhCode='P',Norm=0,ParentWhCode='P')],
            SKUDescriptionTbl=[dict(SKUCode='S',SKUDescription='Some, SKU')],
            SiteDescriptionTbl=[dict(WHCode='W',WHDescription='Some, Site')])
        self.state['controls'] = dict(phase_out=[], upload_log=[])
        self.state['supplier'] = dict(SOBData=[], MOQData=[])
        self.opening['identity'] = 'report-protocol-' + uuid.uuid4().hex
        self.run = self.run_day(day={'business_date':'2026-06-06','new_force_requests':[]})
        self.root = Path(os.environ['VF_COHORT2_REPORT_PROOF_ROOT']) / str(self.run.pk)
        self.root.mkdir(parents=True, exist_ok=False)
        self.writer = partial(archive_files, executable=os.environ['VF_COHORT2_ZIP'],
                              tool_sha256=os.environ['VF_COHORT2_ZIP_SHA256'])
        roster = [dict(ordinal=i,group=group,**REPORT_OPERATIONS[group])
                  for i,group in enumerate(('O3','O2','O5','O6','O1'))]
        self.populations = {name:[] for name in OPENING_TABLES}
        self.populations['UIUploadLogActionType'] = deepcopy(ACTION_TYPES)
        self.config = register_configuration(source_digest=digest(REPORT_OPERATIONS),
            bindings={'operation_roster':roster, 'opening_policy':OPENING_POLICY,
                      'opening_input_digest':self.run.input_digest, 'opening_digest':digest(self.populations),
                      'bor_color_sequence':deepcopy(COLOR_SEQUENCE),
                      'upload_log_client_folder':None},
            settings=[dict(ordinal=i,name=name,value=value) for i,(name,value) in enumerate((
                ('UIUploadLogHorizon','7'),('IsMTOEnvironment','0'),
                ('BOROAHistoryHorizon','90'),('RRROAHistoryHorizon','90')))], tables=[], alerts=[])

    def start(self, **changes):
        args = dict(run_id=self.run.pk, configuration_id=self.config.pk,
                    request_key=uuid.uuid4().hex, owned_root=self.root,
                    expected_output_digest=self.run.output_digest)
        args.update(changes)
        return start_attempt(**args)

    def test_real_files_failure_retry_and_no_calculation_replay(self):
        before = deepcopy(read_outputs(self.run))
        calls = len(self.seen)
        failed = self.start()
        install_opening(failed.pk,populations=self.populations)
        def injected(**kwargs):
            raise RuntimeError('injected archive failure')
        with self.assertRaisesRegex(RuntimeError,'injected archive'):
            materialize_report_operation(failed.pk,group='O3',archive_writer=injected)
        failed.refresh_from_db()
        self.assertEqual(failed.status,'FAILED')
        failed_csv = Path(failed.root)/'output/NoNormParentReport.csv'
        self.assertTrue(failed_csv.is_file())
        failed_bytes = failed_csv.read_bytes()
        retry = self.start(retry_of_id=failed.pk)
        install_opening(retry.pk,populations=self.populations)
        for group in ('O3','O2','O5','O6'):
            effect = materialize_report_operation(retry.pk,group=group,archive_writer=self.writer)
            effect.refresh_from_db()
            self.assertEqual(effect.status,'SUCCEEDED')
            verify_files(effect)
        self.assertEqual(retry.operations.count(),4)
        self.assertEqual(sum(effect.files.count() for effect in retry.operations.all()),28)
        self.assertEqual(read_population(retry,'closing/UIUploadLogActionType'),ACTION_TYPES)
        for name in OPENING_TABLES:
            if name.startswith('UIUploadLog') and name != 'UIUploadLogActionType':
                self.assertEqual(read_population(retry,'closing/'+name),[])
        self.assertEqual(len(read_population(retry,'BPRExceptions')),1)
        self.assertEqual(len(read_population(retry,'NoNormAtParentReport')),1)
        self.assertEqual(failed_csv.read_bytes(),failed_bytes)
        self.assertEqual(read_outputs(self.run),before)
        self.assertEqual(len(self.seen),calls)
        with self.assertRaisesRegex(ValueError,'O1–O9'):
            finish_attempt(retry)
        self.assertFalse((Path(retry.root)/'output/DBMNormChange.csv').exists())
        self.assertFalse((Path(retry.root)/'output/NoNormParentReport.csv').exists())
        self.assertTrue((Path(retry.root)/'output/BPRExceptionReport.csv').is_file())

    def test_missing_nonempty_changed_and_repeated_openings_denied(self):
        owner=self.start()
        missing=deepcopy(self.populations);missing.pop('UIUploadLogFNC')
        with self.assertRaisesRegex(ValueError,'opening roster'):
            install_opening(owner.pk,populations=missing)
        populated=deepcopy(self.populations);populated['UIUploadLogFNC']=[{'undeclared':'event'}]
        with self.assertRaisesRegex(ValueError,'empty opening domain'):
            install_opening(owner.pk,populations=populated)
        changed=deepcopy(self.populations);changed['UIUploadLogActionType'][0]['ActionDesc']='changed'
        with self.assertRaisesRegex(ValueError,'exact native upload action'):
            install_opening(owner.pk,populations=changed)
        self.assertFalse(OperationalPopulation.objects.filter(attempt=owner).exists())
        install_opening(owner.pk,populations=self.populations)
        with self.assertRaisesRegex(ValueError,'already installed'):
            install_opening(owner.pk,populations=self.populations)
        from mta.runtime.validation_storage import read_input
        source=read_input(self.run,components=('profile','day'))
        for populated_source in ('nms','force'):
            changed=deepcopy(source)
            if populated_source=='nms':
                changed['profile']['force_flags']['nms_active']=True
            else:
                changed['day']['new_force_requests']=[{'request':'not supported'}]
            with patch('mta.runtime.validation_storage.read_input',return_value=changed):
                with self.assertRaisesRegex(ValueError,'producer requires'):
                    upload_inputs(owner)
        self.assertFalse(owner.operations.exists())

    def test_bor_capture_typed_history_and_missing_capture_denial(self):
        before=deepcopy(read_outputs(self.run)); calls=len(self.seen)
        owner=self.start()
        install_opening(owner.pk,populations=self.populations)
        with patch('mta.runtime.operational_bor.read_source',
                   side_effect=OperationalCalculationSource.DoesNotExist('missing capture')):
            with self.assertRaises(OperationalCalculationSource.DoesNotExist):
                materialize_report_operation(owner.pk,group='O1',archive_writer=self.writer)
        self.assertFalse(owner.operations.exists())
        effect=materialize_report_operation(owner.pk,group='O1',archive_writer=self.writer)
        verify_files(effect)
        expected=storage(bor_row())
        self.assertEqual(read_population(owner,'BORWithOrderAllocation'),[expected])
        self.assertEqual(read_population(owner,'closing/BOR_OrderAllocationHistory'),
                         [{**expected,'ReportDate':'2026-06-06'}])
        self.assertEqual(read_population(owner,'closing/RRR_OrderAllocation'),[])
        self.assertEqual(read_population(owner,'closing/RRR_OrderAllocationHistory'),[])
        output=(Path(owner.root)/'output/BOR_OrderAllocation.csv').read_bytes()
        self.assertEqual(output,(Path(owner.root)/'download/BOR_OrderAllocation.csv').read_bytes())
        self.assertEqual(len(output.splitlines()),2)
        self.assertTrue(output.endswith(b',Black,5\r\n'))
        self.assertEqual(effect.files.count(),2)
        self.assertEqual(read_outputs(self.run),before)
        self.assertEqual(len(self.seen),calls)
