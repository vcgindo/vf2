"""Focused binding/guard proofs. Test carriers roll back; no day is calculated."""
import os
import unittest
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY', 'unit-only')
import django
django.setup()
from django.db import connection, transaction, DatabaseError
from mta.mdm import daily_source, integration_source, supplier_capture
from mta.serialization import digest


class ClosingBindingTests(unittest.TestCase):
    def test_nms_raw_projection_preserves_native_values_and_nulls_other_fields(self):
        from mta.mdm.daily_input import nms_master_raw
        from mta.application.r1_importer_master import RAW_COLUMNS
        # Extra populated NMS fields must not leak past SQL's explicit NULLs.
        first = dict.fromkeys(RAW_COLUMNS, 'must-not-leak')
        first.update(SKUCode='S', WhCode='L', Norm=17, Weight=None)
        second = {**first, 'SKUCode': 'T', 'Norm': 23}
        prior = {'consumer_context': {'NMSAllItems': [first, second, deepcopy(first)]}}
        before = deepcopy(prior)
        result = nms_master_raw(prior)
        self.assertEqual([(r['SKUCode'], r['Norm']) for r in result],
                         [('S', 17), ('T', 23), ('S', 17)])
        self.assertEqual(result[0], result[2])
        self.assertIsNone(result[0]['Weight'])
        for field in ('SKUDescription', 'WHDescription', 'ParentDescription',
                      'PackSize', 'MOQ', 'SpikeThreshold', 'PSOThreshold',
                      'FGRMFlag', 'StockPercentForRationing', 'NormPercentReservation',
                      *(f'{prefix}{i:02}' for prefix in ('SKUAtt', 'LocAtt', 'SKULocAtt')
                        for i in range(1, 16))):
            self.assertIsNone(result[0][field], field)
        self.assertEqual(prior, before)
        with self.assertRaises(KeyError):
            nms_master_raw({'consumer_context': {}})
        self.assertEqual(nms_master_raw({'consumer_context': {'NMSAllItems': []}}), [])

    def test_active_intake_keeps_selected_predecessor_and_clears_opposite_format(self):
        raw = dict(SOBDataRaw=[], MOQDataRaw1=[dict(SKUCode='S', SupplierCode='P',
            SupplierDescription=None, MOQ=11)], MOQDataRaw2=[{'old_opposite_format': True}])
        queues = {name: [] for name in supplier_capture.QUEUES}
        prior = dict(complete={**deepcopy(raw), **queues}, importer_settings=[
            dict(Parameter='NMSMOQInputDataFormat', Value='WithoutDestLoc')])
        supplier = dict(raw=deepcopy(raw), queues=queues, moq_format='WithoutDestLoc')
        supplier['digest'] = digest(supplier)
        snapshot = dict(nms_active=True, supplier=supplier,
            rows={'location': {'descriptions': [], 'approved': []}})
        before = deepcopy((snapshot, prior))
        result = supplier_capture.complete_feeds(snapshot, prior)
        self.assertEqual(result['MOQDataRaw2'], [])
        self.assertEqual(result['MOQDataRaw1'][0]['MOQ'], 11)
        self.assertEqual((snapshot, prior), before)
        prior['complete']['MOQDataRaw1'][0]['MOQ'] = 12
        with self.assertRaisesRegex(ValueError, 'own raw predecessor'):
            supplier_capture.complete_feeds(snapshot, prior)

    def test_production_supplier_raw_retains_nulls_and_duplicate_occurrences(self):
        raw = dict(SOBDataRaw=[{'x': None}, {'x': None}], MOQDataRaw1=[{'x': 0}], MOQDataRaw2=[])
        output = {'ClosingState': [{'complete': deepcopy(raw)}]}
        self.assertEqual(supplier_capture.terminal_raw(output), raw)
        output['SupplierStages'] = [{'stage': 'ResetFlags.sql', 'tables': deepcopy(raw)}]
        self.assertEqual(supplier_capture.terminal_raw(output), raw)
        output['SupplierStages'][0]['tables']['SOBDataRaw'].pop()
        with self.assertRaisesRegex(ValueError, 'differs'):
            supplier_capture.terminal_raw(output)

    def test_missing_raw_owner_cannot_be_treated_as_empty(self):
        with self.assertRaisesRegex(ValueError, 'Complete terminal'):
            supplier_capture.terminal_raw({'ClosingState': [{'complete': {'SOBDataRaw': []}}]})

    def test_complete_current_root_binds_only_complete_daily_owners(self):
        families = {str(i): {'owners': [str(i)]} for i in (1, 2, 3)}
        receipt = dict(schema=daily_source.SCHEMA, adapter_sha256=daily_source.adapter_digest(),
            artifact_sha256='a'*64, artifact_schema='test', families=families,
            configuration=daily_source.configuration_digest())
        source = SimpleNamespace(receipt=receipt, digest=digest(receipt), dll_digest=daily_source.DLL)
        rows = [SimpleNamespace(master_id=i, receipt=families[str(i)], digest=digest(families[str(i)]))
                for i in (2, 3)] + [SimpleNamespace(master_id=i) for i in range(4, 14)]
        owner = SimpleNamespace(provenance={'schema': integration_source.DAILY_OWNER_SCHEMA})
        from contextlib import ExitStack
        with ExitStack() as stack:
            stack.enter_context(patch.object(integration_source, 'installed_binding', return_value=None))
            stack.enter_context(patch.object(daily_source.MdmFamilySource.objects, 'filter', return_value=rows))
            for family in integration_source.CAPTURES:
                stack.enter_context(patch('mta.mdm.' + family + '_source.require_installed', return_value=owner))
            check = lambda: daily_source.require_binding(source, artifact_sha256='a'*64, artifact_schema='test')
            self.assertIs(check(), source)
            rows.pop(9)  # incomplete Seasonality group
            with self.assertRaisesRegex(ValueError, 'Complete shared'):
                check()


@unittest.skipUnless(os.environ.get('VF_MDM_CLOSING_PG_PROOF') == '1', 'owned PostgreSQL proof only')
class AcceptedClosingPostgresTests(unittest.TestCase):
    def setUp(self):
        from tests.mdm_proof_resources import assert_owned_mdm_proof
        assert_owned_mdm_proof(self, connection)
        self.tx = transaction.atomic()
        self.tx.__enter__()
        self.addCleanup(self.rollback)
        from mta.runtime.models import CalculationRun
        from mta.runtime.mdm_models import MdmSource
        self.source = MdmSource.objects.create(digest='a'*64, dll_digest=daily_source.DLL,
            database_name='rollback-only-guard-test', receipt={})
        self.run = CalculationRun.objects.create(kind='DAILY_CHAIN', business_date='2026-06-06',
            input_digest='rollback-only-test', execution_revision='guard-test-no-calculation',
            input_payload={}, status='RUNNING', output_digest='b'*64)
        self.capture(self.run, 'CONSUMED')
        self.run.status = 'SUCCEEDED'
        self.run.save(update_fields=['status'])
        self.p = dict(schema=integration_source.DAILY_OWNER_SCHEMA, family='season',
            source_digest=self.source.digest, run_id=str(self.run.pk), output_digest=self.run.output_digest,
            capture_digest='c'*64)
        from mta.runtime.mdm_season_models import MdmSeasonOwner
        self.owner = MdmSeasonOwner.objects.create(source=self.source, provenance=self.p,
            receipt_digest=digest(self.p), root_state_digest='d'*64, closing_queue_digest=digest([]),
            closing_current_digest=digest([]), last_run=self.run)
        self.row = dict(SKUCode='SKU', WhCode='WH', StartDate='2026-06-06',
            EndDate='2026-06-20', TargetNorm=300, DeltaNormPercentage=None, UpperLowerCap=None,
            BuildupDuration=1, ActivateDBM=False, OrigNorm=100, NewNorm=300, Type=1,
            Status=1, Comment=None, LastProcessedOn='2026-06-06')

    def rollback(self):
        transaction.set_rollback(True)
        self.tx.__exit__(None, None, None)

    def capture(self, run, status):
        from mta.runtime.mdm_daily_models import MdmDailyInputCapture
        from django.utils import timezone
        captured = MdmDailyInputCapture.objects.create(run=run, source=self.source, status='CAPTURED',
            request_digest='c'*64, revision_digest='c'*64, sku_revision_digest='c'*64,
            location_revision_digest='c'*64, skuloc_revision_digest='c'*64, sql_digest='c'*64, nms_active=True)
        if status == 'CONSUMED':
            with connection.cursor() as cursor:
                cursor.execute("SELECT set_config('fresh.mdm_consuming_run',%s,true)", [str(run.pk)])
            captured.status, captured.consumed_at = status, timezone.now()
            captured.save(update_fields=['status', 'consumed_at'])
            with connection.cursor() as cursor:
                cursor.execute("SELECT set_config('fresh.mdm_consuming_run','',true)")
        return captured

    def guc(self, value=None, key='fresh.season_closing_bind'):
        with connection.cursor() as cursor:
            cursor.execute('SELECT set_config(%s,%s,true)',
                [key, value if value is not None else f'{self.source.pk}:{self.run.pk}'])

    def insert(self, ordinal=1):
        from mta.runtime.mdm_season_models import MdmSeasonCurrent
        return MdmSeasonCurrent.objects.create(source=self.source, ordinal=ordinal, **self.row)

    def denied(self, callback):
        with self.assertRaises(DatabaseError), transaction.atomic():
            callback()

    def test_exact_binding_then_receipt_closes_bootstrap_and_is_retained(self):
        from mta.runtime.mdm_models import MdmFamilySource
        self.denied(self.insert)
        self.guc('foreign:' + str(self.run.pk))
        self.denied(self.insert)
        self.guc()
        self.insert(1)
        self.insert(2)  # preserve equal business rows at distinct ordinals
        family = MdmFamilySource.objects.create(source=self.source, master_id=10,
            receipt=self.p, digest=digest(self.p))
        self.guc()
        self.denied(lambda: self.insert(3))
        self.denied(lambda: MdmFamilySource.objects.filter(pk=family.pk).delete())
        self.denied(lambda: MdmFamilySource.objects.filter(pk=family.pk).update(receipt={}))

    def test_pending_capture_and_successful_successor_deny_old_binding(self):
        from mta.runtime.models import CalculationRun
        for status, captured in (('RUNNING', 'CAPTURED'), ('SUCCEEDED', 'CONSUMED')):
            with transaction.atomic():
                next_run = CalculationRun.objects.create(kind='DAILY_CHAIN', business_date='2026-06-07',
                    input_digest=status, execution_revision='guard-test', input_payload={},
                    status='RUNNING', predecessor=self.run)
                self.capture(next_run, captured)
                next_run.status = status
                next_run.save(update_fields=['status'])
                self.guc()
                self.denied(self.insert)
                transaction.set_rollback(True)

    def test_normal_consumption_still_inserts_without_new_capability(self):
        from mta.runtime.models import CalculationRun
        next_run = CalculationRun.objects.create(kind='DAILY_CHAIN', business_date='2026-06-07',
            input_digest='normal-consumption', execution_revision='guard-test', input_payload={},
            status='RUNNING', predecessor=self.run)
        self.capture(next_run, 'CAPTURED')
        self.guc(str(next_run.pk), key='fresh.mdm_consuming_run')
        self.insert()

    def test_supplier_raw_accepted_binding_closes_after_family_receipt(self):
        from mta.runtime.mdm_supplier_models import MdmSupplierConfiguration, MdmSobRaw
        from mta.runtime.mdm_models import MdmFamilySource
        p = {**self.p, 'family': 'supplier'}
        MdmSupplierConfiguration.objects.create(source=self.source, moq_format='WithoutDestLoc',
            upload_log_active=True, provenance=p, receipt_digest=digest(p))
        insert = lambda: MdmSobRaw.objects.create(source=self.source, ordinal=1,
            SKUCode='SKU', WHCode='WH', SupplierCode='SUP', SupplierDescription=None, SOB=100)
        self.denied(insert)
        self.guc(key='fresh.supplier_closing_bind')
        row = insert()
        family = MdmFamilySource.objects.create(source=self.source, master_id=4,
            receipt={'closing_binding_digest': digest(p)}, digest='e'*64)
        self.denied(insert)
        self.denied(lambda: type(row).objects.filter(pk=row.pk).update(SOB=99))
        self.denied(lambda: MdmFamilySource.objects.filter(pk=family.pk).delete())
