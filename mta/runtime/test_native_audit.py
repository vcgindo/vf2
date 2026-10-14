"""Rollback-only PostgreSQL proofs for native audit capture and retention."""
from datetime import date, datetime, timedelta
from decimal import Decimal
import uuid
from zoneinfo import ZoneInfo

from django.db import DatabaseError, connection, transaction
from django.test import TestCase
from mta.serialization import digest, storage
from mta.mdm import native_audit as audit
from mta.runtime.native_audit_models import NativeUploadAudit, BINDINGS
from mta.runtime.models import CalculationRun, MdmSource, ProductionInitialization
from mta.runtime.mdm_daily_models import MdmDailyInputCapture
from mta.runtime.input_storage import save_input


def setting(name, value):
    with connection.cursor() as cursor:
        cursor.execute('SELECT set_config(%s,%s,true)', [name,str(value)])


class NativeAuditTests(TestCase):
    def setUp(self):
        self.policy = dict(horizon=7, timezone='Asia/Kolkata', client_folder=None)
        self.profile = dict(delivery=dict(site_code='COMPONENT'), native_upload_audit=self.policy)
        self.source = MdmSource.objects.create(digest='7'*64, database_name='audit-component',
            receipt={'schema':'fresh-production-mdm-source-v1'})
        identity = uuid.uuid4()
        setting('fresh.production_initialization', identity)
        raw = dict(profile=self.profile)
        self.initialized = ProductionInitialization.objects.create(id=identity, source=self.source,
            opening_identity=str(identity), opening_date=date(2026,7,9), input_sha256='7'*64,
            recipe_sha256='7'*64, configuration_digest=digest(self.profile),
            implementation_digest='7'*64, input_digest=digest(raw))
        self.initialized.input_payload = save_input(self.initialized, raw)
        self.initialized.input_manifest_digest = digest(self.initialized.input_payload)
        self.initialized.receipt_digest = '7'*64
        self.initialized.save(update_fields=['input_payload','input_manifest_digest','receipt_digest'])
        setting('fresh.production_initialization','')
        setting('fresh.native_mdm_families',identity)
        self.initial_rows = {}
        zone = ZoneInfo(self.policy['timezone'])
        for name, source, _ in BINDINGS:
            # Cutoff equality expires; one second into the next local day survives.
            self.initial_rows[name] = []
            for stamp in (datetime(2026,7,2,23,59,59,tzinfo=zone),
                          datetime(2026,7,3,0,0,0,tzinfo=zone),
                          datetime(2026,7,3,0,0,0,tzinfo=zone)):
                values = {}
                for field in source._meta.fields:
                    if field.name in ('id','source'):
                        continue
                    if field.name == 'ActionTimeStamp': value = stamp
                    elif field.name == 'ActionId': value = 4
                    elif field.null: value = None
                    elif field.get_internal_type() in ('CharField','TextField'): value = 'A'
                    elif field.get_internal_type() == 'DecimalField': value = Decimal('1.25')
                    elif field.get_internal_type() == 'BooleanField': value = False
                    else: value = 2
                    values[field.name] = value
                row = source.objects.create(source=self.source, **values)
                self.initial_rows[name].append((row.pk, values))
        setting('fresh.native_mdm_families','')
        self.run, self.daily = self.new_run()

    def new_run(self, *, origin=None, predecessor=None, business_date=date(2026,7,10)):
        raw = dict(profile=self.profile)
        run = CalculationRun.objects.create(input_digest=digest(raw), input_payload={},
            execution_revision=str(uuid.uuid4()), kind='DAILY_CHAIN', status='RUNNING',
            business_date=business_date, predecessor=predecessor)
        run.input_payload = save_input(run, raw)
        run.input_manifest_digest = digest(run.input_payload)
        run.save(update_fields=['input_payload','input_manifest_digest'])
        daily = MdmDailyInputCapture.objects.create(run=run, source=self.source,
            origin=origin, request_digest='7'*64, revision_digest='7'*64,
            sku_revision_digest='7'*64, location_revision_digest='7'*64,
            skuloc_revision_digest='7'*64, sql_digest='7'*64, nms_active=True)
        return run, daily

    def consume(self, daily):
        from django.utils import timezone
        setting('fresh.mdm_consuming_run', daily.run_id)
        daily.status = 'CONSUMED'
        daily.consumed_at = timezone.now()
        daily.save(update_fields=['status','consumed_at'])

    def capture(self):
        audit.bind(self.run, self.daily, self.profile)
        return NativeUploadAudit.objects.get(run=self.run)

    def denied(self, call):
        with self.assertRaises(DatabaseError), transaction.atomic():
            call()

    def test_all_eight_tables_exact_rows_duplicates_nulls_and_local_cutoff(self):
        owner = self.capture()
        captured = audit.images(owner, 'FROZEN')
        for name, source, _ in BINDINGS:
            actual = [{k:r[k] for k in audit.fields(source)} for r in captured[name]]
            self.assertEqual(actual, [v for _,v in self.initial_rows[name]])
        self.consume(self.daily)
        audit.finalize(self.run)
        owner.refresh_from_db()
        audit.verify(owner)
        for name, source, _ in BINDINGS:
            rows = audit.images(owner, 'FINAL')[name]
            self.assertEqual([r['retained'] for r in rows], [False,True,True])
            self.assertEqual(list(source.objects.filter(source=self.source).order_by('id')
                .values_list('id',flat=True)), [pk for pk,_ in self.initial_rows[name]][1:])

    def test_late_rollback_keeps_frozen_capture_and_retry_uses_it(self):
        owner = self.capture()
        frozen = storage(audit.images(owner, 'FROZEN'))
        with self.assertRaisesRegex(RuntimeError,'late failure'):
            with transaction.atomic():
                self.consume(self.daily)
                audit.finalize(self.run)
                raise RuntimeError('late failure')
        owner.refresh_from_db()
        self.assertEqual(owner.status,'FROZEN')
        for name, source, model in BINDINGS:
            self.assertEqual(model.objects.filter(capture=owner,stage='FINAL').count(),0)
            self.assertEqual(source.objects.filter(source=self.source).count(),3)
        self.run.status='FAILED'; self.run.save(update_fields=['status'])
        retry, daily = self.new_run(origin=self.daily)
        # A later uncaptured occurrence must survive both retry capture and retention.
        name, source, _ = BINDINGS[0]
        late = source.objects.create(source=self.source, **self.initial_rows[name][0][1])
        audit.bind(retry, daily, self.profile)
        retry_owner = NativeUploadAudit.objects.get(run=retry)
        self.assertEqual(storage(audit.images(retry_owner,'FROZEN')), frozen)
        self.consume(daily)
        audit.finalize(retry)
        self.assertTrue(source.objects.filter(pk=late.pk).exists())
        owner.refresh_from_db(); self.assertEqual(owner.status,'FROZEN')
        self.assertEqual(storage(audit.images(owner,'FROZEN')),frozen)

    def test_immutable_rows_and_empty_statement_denials(self):
        owner = self.capture()
        for _, source, model in BINDINGS:
            self.denied(lambda model=model: model.objects.filter(capture=owner).update(ActionId=1))
            self.denied(lambda model=model: model.objects.filter(pk=-1).delete())
            self.denied(lambda source=source: source.objects.filter(source=self.source).delete())
        self.denied(lambda: NativeUploadAudit.objects.filter(pk=self.run.pk).update(horizon=8))
        # The ORM collector skips DELETE when a parent queryset is empty.
        # Issue the actual empty statement to exercise its database guard.
        self.denied(lambda: self.empty_delete(NativeUploadAudit))
        self.consume(self.daily); audit.finalize(self.run)
        self.denied(lambda: NativeUploadAudit.objects.filter(pk=self.run.pk).update(status='FROZEN'))
        for _, _, model in BINDINGS:
            self.denied(lambda model=model: self.truncate(model))
        self.denied(lambda: self.truncate(NativeUploadAudit))

    def truncate(self, model):
        with connection.cursor() as cursor:
            cursor.execute('TRUNCATE '+connection.ops.quote_name(model._meta.db_table)+' CASCADE')

    def empty_delete(self, model):
        with connection.cursor() as cursor:
            cursor.execute('DELETE FROM '+connection.ops.quote_name(model._meta.db_table)+' WHERE FALSE')

    def test_frozen_live_mutation_is_denied_at_finalize(self):
        self.capture()
        source = BINDINGS[0][1]
        source.objects.filter(source=self.source).update(ActionId=1)
        self.consume(self.daily)
        with self.assertRaisesRegex(ValueError,'occurrence changed'):
            audit.finalize(self.run)

    def test_terminal_force_old_norm_and_own_cumulative_history(self):
        owner = self.capture()
        force = BINDINGS[-1][1]
        setting('fresh.mdm_consuming_run', self.run.pk)
        force.objects.filter(source=self.source).update(OldNorm=13)
        self.consume(self.daily); audit.finalize(self.run)
        self.run.status='SUCCEEDED'; self.run.save(update_fields=['status'])
        rows = audit.read_images(self.run)
        self.assertEqual([r['OldNorm'] for r in rows['full_source_audit']['UIUploadLogFNC']], [13]*3)
        self.assertEqual(len(rows['expired']['UIUploadLogFNC']),1)
        successor, daily = self.new_run(predecessor=self.run, business_date=date(2026,7,11))
        audit.bind(successor, daily, self.profile)
        self.consume(daily); audit.finalize(successor)
        successor.status='SUCCEEDED'; successor.save(update_fields=['status'])
        after = audit.read_images(successor)
        for name, _, _ in BINDINGS:
            self.assertEqual(after['retained'][name],[])
            self.assertEqual(after['full_source_audit'][name],rows['full_source_audit'][name])
            self.assertEqual(after['expired'][name],rows['full_source_audit'][name])
        owner.refresh_from_db()
        self.assertEqual([r['OldNorm'] for r in audit.images(owner,'FROZEN')['UIUploadLogFNC']], [None]*3)
