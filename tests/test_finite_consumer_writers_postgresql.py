"""Actual finite/Full producer writers on migrated, rolled-back PostgreSQL."""
import os
import unittest
import uuid
from copy import deepcopy
from unittest.mock import patch
if os.environ.get('VF_PHASE_POSTGRES_PROOF')=='1':
    import django
    django.setup()


@unittest.skipUnless(os.environ.get('VF_PHASE_POSTGRES_PROOF')=='1','Owned PostgreSQL required')
class FiniteConsumerWriterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from tests.test_stage_calculation_sources import CalculationSourceTests
        CalculationSourceTests.setUpClass()
        cls.output=CalculationSourceTests.output
        cls.inputs=CalculationSourceTests.phase_inputs
        cls.report_opening=deepcopy(CalculationSourceTests.opening)
        cls.report_opening['production_report_opening']={
            'BOR_OrderAllocationHistory':[],'RRR_OrderAllocationHistory':[]}

    def setUp(self):
        from django.db import connection,transaction
        if connection.settings_dict['NAME']!='VFTEST_Fresh_LifecycleG2_20261024':
            raise RuntimeError('Exclusively owned test database required')
        self.atomic=transaction.atomic();self.atomic.__enter__()
        self.addCleanup(self.rollback)

    def rollback(self):
        from django.db import transaction
        transaction.set_rollback(True);self.atomic.__exit__(None,None,None)

    def owner(self):
        from mta.runtime.models import CalculationRun
        from mta.application.operational_capture import CAPTURE_POLICY
        from mta.runtime.input_storage import save_input
        from mta.runtime.production_daily import input_table
        from mta.serialization import digest
        prior,day,profile=deepcopy(self.inputs)
        profile['operational_sources']=CAPTURE_POLICY
        payload=dict(profile=profile,day=day,opening=dict(identity='finite-consumer-component',
                     opening_date='2037-04-09',state=prior))
        run=CalculationRun.objects.create(kind='DAILY_CHAIN',business_date='2037-04-10',
            input_digest=digest(payload),input_payload={},execution_revision='finite-'+uuid.uuid4().hex)
        run.input_payload=save_input(run,payload,table_selector=input_table)
        run.input_manifest_digest=digest(run.input_payload)
        run.save(update_fields=['input_payload','input_manifest_digest'])
        run.refresh_from_db()
        return run

    def test_complete_actual_full_and_finite_rows_read_back_identically(self):
        from mta.application.operational_capture import capture_rows
        from mta.presentation.fulfillment import routes_for_orders
        from mta.runtime.operational_source import authorize_new_run,write_source,_write_source_rows,_rows
        from mta.presentation.pick_storage import write_pick_bands,_write_pick_rows,selected_bands,_read_rows
        from mta.runtime.report_sources import write_routes,_write_route_rows,read_routes
        from mta.serialization import digest
        calculated=self.output['CalculationOutputs']
        checksum=digest(calculated)
        orders=self.output['ClosingState'][0]['orders']['SpikeOrderData']
        expected_operational=capture_rows(calculated)
        expected_pick=selected_bands(calculated)
        expected_routes=routes_for_orders(calculated,orders)
        results=[]
        for finite in (False,True):
            run=self.owner();authorize_new_run(run)
            if finite:
                op=_write_source_rows(run,expected_operational,calculation_digest=checksum)
                pick=_write_pick_rows(run,expected_pick,provenance={'origin':'production-calculation'},
                                      calculation_digest=checksum)
                routes=_write_route_rows(run,expected_routes)
            else:
                op=write_source(run,calculated,calculation_digest=checksum)
                pick=write_pick_bands(run,calculated,provenance={'origin':'production-calculation'},
                                       calculation_digest=checksum)
                routes=write_routes(run,calculated,orders)
            actual=(_rows(op),_read_rows(run,pick),read_routes(run,routes))
            self.assertEqual(actual,(expected_operational,expected_pick,expected_routes))
            results.append((actual,op.calculation_digest,pick.calculation_digest,routes))
        self.assertEqual(*results)

    def test_late_finite_writer_failure_rolls_all_consumer_rows_back(self):
        from django.db import transaction
        from mta.runtime.operational_source import authorize_new_run,_write_source_rows
        from mta.runtime.operational_source_models import OperationalCalculationSource
        from mta.application.operational_capture import capture_rows
        from mta.presentation.pick_storage import _write_pick_rows,selected_bands
        from mta.runtime.models import PickProjection
        from mta.serialization import digest
        run=self.owner();authorize_new_run(run)
        values=self.output['CalculationOutputs'];checksum=digest(values)
        with self.assertRaisesRegex(ValueError,'injected consumer readback'),transaction.atomic():
            _write_source_rows(run,capture_rows(values),calculation_digest=checksum)
            with patch('mta.presentation.pick_storage._read_rows',side_effect=ValueError('injected consumer readback')):
                _write_pick_rows(run,selected_bands(values),provenance={},calculation_digest=checksum)
        self.assertFalse(OperationalCalculationSource.objects.filter(run=run).exists())
        self.assertFalse(PickProjection.objects.filter(run=run).exists())

    def test_report_sources_and_fresh_histories_match_complete_full_values(self):
        from mta.presentation.production_reports import current,write,_write_report_rows
        from mta.runtime.relational_state import load_image
        from mta.application import production_output_policy
        for expanded in (False,True):
            opening=deepcopy(self.report_opening)
            if expanded:
                opening['production_report_schema']=production_output_policy.SOURCE_SCHEMA
                opening['production_report_policy']['output_contract']=production_output_policy.contract()
            values=current(self.output,opening);before=deepcopy(values)
            results=[]
            for finite in (False,True):
                run=self.owner()
                images=(_write_report_rows(run,values,opening) if finite
                        else write(run,self.output,opening))
                results.append({name:(load_image(run,image),image['producer']) for name,image in images.items()})
            self.assertEqual(*results)
            self.assertEqual(values,before)
            with self.assertRaisesRegex(ValueError,'population roster differs'):
                _write_report_rows(self.owner(),{},opening)
