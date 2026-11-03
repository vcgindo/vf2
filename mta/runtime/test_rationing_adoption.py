"""Rollback-only maintenance-role proof, not a complete application upgrade."""
from datetime import date
from contextlib import contextmanager
import uuid

from django.db import connection, transaction
from django.test import TestCase

from mta.serialization import digest
from mta.runtime.test_rationing_cut_guards import RationingCutGuardTests as Fixture
from mta.runtime.models import CalculationRun
from mta.runtime.ingestion_models import InitializationCertification, IngestionRevisionState


class RationingAdoptionTests(TestCase):
    seal_initialization = Fixture.seal_initialization
    new_run = Fixture.new_run
    tearDown = Fixture.tearDown
    constraints = Fixture.constraints

    def setUp(self):
        with connection.cursor() as cursor:
            cursor.execute('SELECT rolsuper FROM pg_roles WHERE rolname=session_user')
            self.assertEqual(cursor.fetchone(), (True,))
            cursor.execute('SET LOCAL ROLE vectorflow_mta_owner')
        Fixture.setUp(self)

    @contextmanager
    def provisioner(self):
        with connection.cursor() as cursor:
            cursor.execute('RESET ROLE')
        try:
            yield
        finally:
            with connection.cursor() as cursor:
                cursor.execute('SET LOCAL ROLE vectorflow_mta_owner')

    def certify_metadata(self):
        # Just the original watch/immutability participants; no native or
        # business certification is claimed by this rollback-owned fixture.
        state = IngestionRevisionState.objects.create(initialization=self.owner)
        with connection.cursor() as cursor:
            cursor.execute('SELECT oid FROM pg_database WHERE datname=current_database()')
            oid = cursor.fetchone()[0]
        InitializationCertification.objects.create(initialization=self.owner,
            contract='IR1_METADATA_ONLY_ANCHOR', database_name=connection.settings_dict['NAME'],
            database_oid=oid, namespace=uuid.uuid4(), source_digest=self.source.digest,
            content_digest=self.owner.input_digest, configuration_digest=self.owner.configuration_digest,
            schema_digest='1'*64, guard_digest='2'*64, release_digest='3'*64,
            receipt_digest='4'*64, populations={'fixture': 'NO_NATIVE_OR_BUSINESS_CERTIFICATION'})
        return state

    def legacy_day(self, rows, *, predecessor=None, day=date(2026, 7, 10)):
        from mta.runtime.rationing_reader import IMAGE
        from mta.runtime.relational_state import save_image
        from mta.runtime.mdm_daily_models import MdmDailyInputCapture
        from django.utils import timezone
        run = self.new_run(predecessor=predecessor, business_date=day)
        item = save_image(run, IMAGE, IMAGE, rows)
        with connection.cursor() as cursor:
            cursor.execute("SELECT set_config('fresh.mdm_consuming_run',%s,true)", [str(run.pk)])
        MdmDailyInputCapture.objects.filter(run=run).update(status='CONSUMED', consumed_at=timezone.now())
        run.production_manifest = dict(version=3, images={IMAGE: item})
        run.production_digest = digest(run.production_manifest)
        run.status = 'SUCCEEDED'
        run.save(update_fields=['production_manifest', 'production_digest', 'status'])
        return run, item

    def preserved(self):
        with connection.cursor() as cursor:
            cursor.execute('SELECT to_jsonb(I),to_jsonb(C),to_jsonb(S) FROM '
                'mta.fresh_mta_productioninitialization I '
                'JOIN mta.fresh_mta_initializationcertification C ON C.initialization_id=I.id '
                'JOIN mta.fresh_mta_ingestionrevisionstate S ON S.initialization_id=I.id WHERE I.id=%s',
                [self.owner.pk])
            owner = cursor.fetchone()
            cursor.execute('SELECT to_jsonb(R) FROM mta.fresh_mta_calculationrun R ORDER BY id')
            return owner, cursor.fetchall()

    def test_populated_adoption_preserves_prefix_epochs_and_next_day(self):
        from tests.test_rationing_delta import row
        from mta.runtime.rationing_adoption import adopt
        from mta.runtime.rationing_audit import audit_cut, audit_image
        from mta.runtime.rationing_reader import read_cut
        from mta.runtime.rationing_writer import write_day
        self.seal_initialization()
        first, first_item = self.legacy_day([row('2026-07-10')])
        rows = [row('2026-07-10'), row('2026-07-11'), row('2026-07-11')]
        last, last_item = self.legacy_day(rows, predecessor=first, day=date(2026, 7, 11))
        self.certify_metadata()
        before = self.preserved()
        with self.assertRaisesMessage(ValueError, 'trusted provisioning session'):
            adopt(self.owner)
        with self.provisioner():
            receipt = adopt(self.owner)
            self.constraints()
            repeat = adopt(self.owner)
        self.assertEqual(receipt['status'], 'ADOPTED')
        self.assertEqual(repeat['status'], 'EXISTING')
        self.assertEqual(receipt['root_digest'], repeat['root_digest'])
        self.assertEqual(self.preserved(), before)
        self.assertEqual(audit_cut(read_cut(receipt['cut_id']))['count'], 3)
        from mta.runtime.relational_state import load_image
        self.assertEqual(load_image(first, first_item), [row('2026-07-10')])
        self.assertEqual(load_image(last, last_item), rows)
        with connection.cursor() as cursor:
            cursor.execute('SET CONSTRAINTS state_cut_complete DEFERRED')
        run = self.new_run(predecessor=last, business_date=date(2026, 7, 12))
        before_epoch = IngestionRevisionState.objects.get(pk=self.owner.pk).operational_epoch
        item = write_day(run, rows+[row('2026-07-12')])
        Fixture.accept_storage_fixture(self, run, item)
        self.assertGreater(IngestionRevisionState.objects.get(pk=self.owner.pk).operational_epoch, before_epoch)
        audited = audit_image(run, item)
        self.assertEqual((audited['cuts'], audited['facts'], audited['count']), (2, 4, 4))

    def test_unused_initialized_opening_adopts_without_revision_or_reinitialization(self):
        from tests.test_rationing_delta import row
        from mta.runtime.rationing_adoption import adopt
        from mta.runtime.rationing_reader import read_cut
        from mta.runtime.rationing_audit import audit_cut
        self.raw['opening']['state']['btr']['RationingHistory'] = [row(None)]
        self.owner.input_digest = digest(self.raw)
        self.owner.save(update_fields=['input_digest'])
        self.seal_initialization()
        self.certify_metadata()
        before = self.preserved()
        with self.provisioner():
            receipt = adopt(self.owner)
            self.constraints()
        self.assertIsNone(receipt['source_run'])
        self.assertEqual(self.preserved(), before)
        self.assertEqual(audit_cut(read_cut(receipt['cut_id']))['facts'], 1)

    def test_active_or_ambiguous_prefix_refuses_without_anchor(self):
        from tests.test_rationing_delta import row
        from mta.runtime.rationing_adoption import adopt
        from mta.runtime.state_cut_models import OperationalStateCut
        self.seal_initialization()
        with transaction.atomic():
            self.new_run()
            with self.provisioner(), self.assertRaisesMessage(ValueError, 'unfinished calculation'):
                adopt(self.owner)
            transaction.set_rollback(True)
        self.legacy_day([row('2026-07-10')])
        self.legacy_day([row('2026-07-11')], day=date(2026, 7, 11))
        with self.provisioner(), self.assertRaisesMessage(ValueError, 'one exact accepted terminal prefix'):
            adopt(self.owner)
        self.assertFalse(OperationalStateCut.objects.exists())
