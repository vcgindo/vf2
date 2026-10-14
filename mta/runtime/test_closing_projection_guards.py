"""Small real-PostgreSQL guard cases; full engine proof is separate."""
from datetime import date
import uuid

from django.db import connection, DatabaseError, transaction
from django.test import TestCase
from django.utils import timezone

from mta.mdm.location_projection import VERSION
from mta.mdm.location_transition import capture_identity, verified_receipt
from mta.runtime.models import (MdmSource, ProductionInitialization, CalculationRun,
    MdmClosingProjectionReceipt, MdmSourceIntegration)
from mta.runtime.mdm_models import MdmFamilySource, MdmLocationAttributes
from mta.runtime.mdm_daily_models import MdmDailyInputCapture
from mta.serialization import digest


def setting(name, value):
    with connection.cursor() as c:
        c.execute('SELECT set_config(%s,%s,true)',[name,str(value)])


class ProjectionGuardFixture(TestCase):
    historical=False
    def setUp(self):
        self.record=None
        if self.historical:
            from mta.mdm.location_transition import registration
            self.record=registration()
            self.assertIsNotNone(self.record)
        self.source=MdmSource.objects.create(**({'pk':self.record['source_id']} if self.record else {}),digest='a'*64,database_name='component',
            receipt={'schema':'fresh-production-mdm-source-v1'})
        identity=uuid.UUID(self.record['initialization_id']) if self.record else uuid.uuid4();setting('fresh.production_initialization',identity)
        self.init=ProductionInitialization.objects.create(id=identity,source=self.source,
            opening_identity=str(identity),opening_date=date(2026,7,1),input_sha256='a'*64,
            recipe_sha256='a'*64,configuration_digest='a'*64,
            implementation_digest='a'*64,input_digest='a'*64)
        for family in (2,3):
            MdmFamilySource.objects.create(source=self.source,master_id=family,digest='a'*64,receipt={})
        self.init.input_manifest_digest='a'*64;self.init.receipt_digest='a'*64
        self.init.save(update_fields=['input_manifest_digest','receipt_digest'])
        setting('fresh.production_initialization','')
        setting('fresh.native_mdm_families',identity)
        for family in range(4,14):
            MdmFamilySource.objects.create(source=self.source,master_id=family,digest='a'*64,
                receipt=dict(schema='fresh-production-mdm-opening-owner-v1',
                    source_digest=self.source.digest,initialization_id=str(identity)))
        seal=dict(schema='fresh-production-mdm-integration-v1',initialization_id=str(identity),
            closing_projection_version=VERSION,adapter_digest='b'*64,source_manifest_digest='c'*64)
        if self.record:
            seal=dict(schema='fresh-production-mdm-integration-v1',initialization_id=str(identity),adapter_digest='a'*64)
        self.seal=MdmSourceIntegration.objects.create(source=self.source,receipt=seal,digest=digest(seal))
        setting('fresh.native_mdm_families','')
        self.parent=None
        if self.record:
            self.parent=CalculationRun.objects.create(pk=self.record['predecessor_id'],
                input_digest='d'*64,input_payload={},execution_revision='synthetic-prefix',
                kind='DAILY_CHAIN',business_date=date(2026,7,2),status='SUCCEEDED',
                output_digest=self.record['predecessor_output_digest'])
        self.run=CalculationRun.objects.create(input_digest='a'*64,execution_revision='guard-fixture',
            input_payload={},kind='DAILY_CHAIN',predecessor=self.parent,
            business_date=date(2026,7,3) if self.record else date(2026,7,1),status='RUNNING')
        self.capture=MdmDailyInputCapture.objects.create(run=self.run,source=self.source,
            request_digest='a'*64,revision_digest='a'*64,sku_revision_digest='a'*64,
            location_revision_digest='a'*64,skuloc_revision_digest='a'*64,sql_digest='a'*64,
            nms_active=False)
        setting('fresh.mdm_consuming_run',self.run.pk)
        self.capture.status='CONSUMED';self.capture.consumed_at=timezone.now()
        self.capture.save(update_fields=['status','consumed_at'])
        setting('fresh.mdm_current_run',self.run.pk)

    def receipt(self, **changes):
        values=dict(run=self.run,version=VERSION,
            transition_id=uuid.UUID(self.record['transition_id']) if self.record else None,source_digest=self.source.digest,
            adapter_digest='b'*64,source_manifest_digest='c'*64,integration_digest=self.seal.digest,
            capture_digest=capture_identity(self.capture))
        values.update(changes)
        return MdmClosingProjectionReceipt.objects.create(**values)

    def denied(self, operation):
        with self.assertRaises(DatabaseError),transaction.atomic():operation()

    def write(self):
        return MdmLocationAttributes.objects.create(source=self.source,owner='BPR',ordinal=1,WHCode='L')

    def seal_receipt(self, receipt):
        receipt.metadata=dict(version=VERSION,partitions=[],sources=[])
        receipt.digest=digest(receipt.metadata);receipt.status='SEALED'
        receipt.save(update_fields=['status','metadata','digest'])

class ClosingProjectionGuardTests(ProjectionGuardFixture):
    def test_fresh_union_and_exact_fields_are_checked_by_database(self):
        for changes in ({'transition_id':uuid.uuid4()},{'version':'unknown'},
                {'source_digest':'d'*64},{'adapter_digest':'d'*64},
                {'source_manifest_digest':'d'*64},{'integration_digest':'d'*64},
                {'status':'SEALED'},{'capture_digest':''}):
            with self.subTest(changes=changes):self.denied(lambda:self.receipt(**changes))
        self.receipt();self.write()

    def test_missing_receipt_and_empty_delete_fail_closed(self):
        self.denied(self.write)
        empty=lambda:MdmLocationAttributes.objects.filter(source=self.source,WHCode='ABSENT').delete()
        self.denied(empty)
        setting('fresh.mdm_current_run','');self.denied(empty)
        setting('fresh.mdm_current_run',self.run.pk)
        receipt=self.receipt();empty();self.write()
        self.seal_receipt(receipt);self.denied(empty)

    def test_wrong_run_marker_cannot_reuse_pending_receipt(self):
        self.receipt();setting('fresh.mdm_consuming_run',uuid.uuid4())
        self.denied(self.write)

    def test_sealed_receipt_is_immutable_and_old_run_cannot_be_rewritten(self):
        receipt=self.receipt();self.seal_receipt(receipt)
        self.assertEqual(verified_receipt(self.run,self.source).pk,receipt.pk)
        self.denied(lambda:MdmClosingProjectionReceipt.objects.filter(pk=receipt.pk).update(digest='d'*64))
        self.denied(lambda:MdmClosingProjectionReceipt.objects.filter(pk=receipt.pk).delete())
        def truncate():
            with connection.cursor() as c:c.execute('TRUNCATE mta.fresh_mta_mdmclosingprojectionreceipt')
        self.denied(truncate)
        self.run.status='SUCCEEDED';self.run.save(update_fields=['status'])
        self.denied(self.write)

    def test_late_transaction_rollback_restores_both_rows_and_receipt(self):
        with self.assertRaisesRegex(RuntimeError,'late'),transaction.atomic():
            receipt=self.receipt();self.write();self.seal_receipt(receipt)
            raise RuntimeError('late')
        self.assertFalse(MdmClosingProjectionReceipt.objects.exists())
        self.assertFalse(MdmLocationAttributes.objects.filter(source=self.source).exists())
        self.receipt();self.write()

    def test_fresh_successor_requires_same_sealed_parent_identity(self):
        parent=CalculationRun.objects.create(input_digest='d'*64,execution_revision='wrong-parent',
            input_payload={},kind='DAILY_CHAIN',business_date=date(2026,6,30),status='SUCCEEDED')
        self.run.predecessor=parent;self.run.save(update_fields=['predecessor'])
        self.denied(self.receipt)


class HistoricalProjectionGuardTests(ProjectionGuardFixture):
    historical=True

    def test_exact_bridge_accepts_only_its_activation(self):
        for changes in ({'transition_id':None},{'transition_id':uuid.uuid4()},
                {'adapter_digest':'d'*64},{'source_manifest_digest':'d'*64},
                {'integration_digest':'d'*64},{'source_digest':'d'*64}):
            with self.subTest(changes=changes):self.denied(lambda:self.receipt(**changes))
        receipt=self.receipt();self.write();self.seal_receipt(receipt)
        self.assertEqual(verified_receipt(self.run,self.source).transition_id,receipt.transition_id)
        from mta.runtime.receipt_integrity import source_receipts
        encoded=source_receipts(self.run)
        self.assertEqual(encoded['MdmClosingProjectionReceipt'][0]['transition_id'],str(receipt.transition_id))
        self.assertEqual(len(digest(encoded)),64)
        from mta.mdm.location_transition import run_identity,V1
        self.assertEqual(run_identity(self.parent,self.source),dict(version=V1))
        self.assertFalse(MdmClosingProjectionReceipt.objects.filter(run=self.parent).exists())

    def test_wrong_date_parent_and_old_binary_are_denied(self):
        empty=lambda:MdmLocationAttributes.objects.filter(source=self.source,WHCode='ABSENT').delete()
        self.denied(empty)
        for values in (dict(business_date=date(2026,7,2)),dict(business_date=date(2026,7,5)),
                dict(predecessor=None),dict(business_date=date(2026,7,4))):
            with self.subTest(values=values),transaction.atomic():
                CalculationRun.objects.filter(pk=self.run.pk).update(**values)
                self.denied(self.receipt)
                transaction.set_rollback(True)
        self.receipt();empty()

    def test_application_cannot_mint_change_delete_or_truncate_registration(self):
        statements=("INSERT INTO mta.native_location_transition(record) VALUES('{}')",
            "UPDATE mta.native_location_transition SET record='{}'",
            'DELETE FROM mta.native_location_transition','TRUNCATE mta.native_location_transition')
        for sql in statements:
            with self.subTest(sql=sql):
                def attempt():
                    with connection.cursor() as c:c.execute(sql)
                self.denied(attempt)
