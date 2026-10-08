"""PostgreSQL effect protocol fixtures; no engine or business-date invocation."""
from datetime import date
from pathlib import Path
import tempfile
import unittest
import uuid
from django.test import override_settings

from mta.application import operational_io
from mta.application.operational_input_archive import archive_clock
from mta.runtime.models import CalculationRun
from mta.runtime.operational_models import OperationalConfiguration, OperationalAttempt, OperationalAlertIntent
from mta.runtime.operational_effects import operation, record_file, record_intent
from mta.runtime.operational_native import save_population, read_population, MODELS


class OperationalEffectsProtocol(unittest.TestCase):
    def setUp(self):
        flags=override_settings(VF_OPERATIONAL_UNLEASED_TESTS=True)
        flags.enable();self.addCleanup(flags.disable)
        token = uuid.uuid4().hex
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.run = CalculationRun.objects.create(input_digest=token * 2,
            execution_revision='cohort2-effect-protocol-' + token, business_date=date(2026, 6, 6),
            input_payload={}, status='SUCCEEDED', output_digest='a' * 64)
        self.config = OperationalConfiguration.objects.create(digest=token * 2,
            policy='cohort2-protocol-only', source_digest='b' * 64, bindings={})
        self.owner = self.owner_for('first')

    def owner_for(self, suffix, retry_of=None):
        root = Path(self.temp.name) / suffix
        root.mkdir()
        return OperationalAttempt.objects.create(run=self.run, configuration=self.config,
            request_key=uuid.uuid4().hex, business_date=self.run.business_date,
            run_output_digest=self.run.output_digest, action_digest='c' * 64,
            source_digest='d' * 64, clock=archive_clock(self.run.business_date)['clock'],
            root=str(root), status='RUNNING', retry_of=retry_of)

    def effect(self, owner=None):
        return operation(owner or self.owner, ordinal=0, group='O4', name='InputData',
                         stage='inputs', source_digest='e' * 64)

    def test_file_success_and_tamper_failure_truth(self):
        with self.effect() as effect:
            operational_io.write_file(self.owner.root, 'output/a.csv', b'exact')
            record_file(effect, relative_path='output/a.csv', role='output')
        effect.refresh_from_db()
        self.assertEqual(effect.status, 'SUCCEEDED')
        retry = self.owner_for('bad')
        with self.assertRaisesRegex(ValueError, 'bytes differ'):
            with self.effect(retry) as effect:
                operational_io.write_file(retry.root, 'output/a.csv', b'exact')
                record_file(effect, relative_path='output/a.csv', role='output')
                (Path(retry.root) / 'output/a.csv').write_bytes(b'drift')
        retry.refresh_from_db()
        effect.refresh_from_db()
        self.assertEqual((retry.status, effect.status), ('FAILED', 'FAILED'))
        self.assertEqual((Path(retry.root) / 'output/a.csv').read_bytes(), b'drift')

    def test_typed_duplicates_nulls_empty_and_ordinal_drift(self):
        row = dict(SKUCode='sku', WhCode='loc', Norm=None, Stock=3, GIT=None)
        save_population(self.owner, 'exceptions', 'BPR/BPRExceptions', [row, row])
        save_population(self.owner, 'empty', 'BPR/BPRExceptions', [])
        self.assertEqual(read_population(self.owner, 'exceptions'), [row, row])
        self.assertEqual(read_population(self.owner, 'empty'), [])
        MODELS['BPR/BPRExceptions'].objects.filter(attempt=self.owner, image='exceptions', ordinal=1).update(ordinal=8)
        with self.assertRaisesRegex(ValueError, 'ordinal differs'):
            read_population(self.owner, 'exceptions')

    def test_sku_log_native_columns_round_trip_in_original_order(self):
        from tests.test_operational_upload_logs import row
        from decimal import Decimal
        value = row('UIUploadLogNMSSKUs', ElephantOrderCapping=17,
                    Weight=Decimal('1.125'), Volume=None)
        save_population(self.owner, 'sku-log', 'Importer/UIUploadLogNMSSKUs', [value, value])
        expected = dict(value, Weight='1.125')
        self.assertEqual(read_population(self.owner, 'sku-log'), [expected, expected])
        stored = MODELS['Importer/UIUploadLogNMSSKUs'].objects.get(
            attempt=self.owner, image='sku-log', ordinal=0)
        self.assertEqual(stored.field_25, 17)
        self.assertEqual(stored.field_26, Decimal('1.125'))
        self.assertIsNone(stored.field_27)
        self.assertEqual(stored.field_2, value['SL1'])

    def test_failed_attempt_retained_and_intents_idempotent(self):
        values = dict(alert_name='NoNormParentAlert', branch='main', stage='parent',
            source_digest='f' * 64, recipients='Not-Defined', subject=None, body=None,
            disposition='RECIPIENT_SUPPRESSED', reason='native recipient guard', attachments=[])
        with self.assertRaisesRegex(RuntimeError, 'injected'):
            with self.effect() as effect:
                first = record_intent(effect, **values)
                raise RuntimeError('injected file failure')
        retry = self.owner_for('retry', retry_of=self.owner)
        with self.effect(retry) as effect:
            second = record_intent(effect, **values)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(OperationalAlertIntent.objects.filter(run=self.run).count(), 1)
        self.owner.refresh_from_db()
        self.assertEqual(self.owner.status, 'FAILED')
        self.assertEqual(retry.retry_of_id, self.owner.pk)

    def test_changed_intent_cannot_reuse_identity(self):
        values = dict(alert_name='alert', branch='main', stage='stage', source_digest='f' * 64,
            recipients='fixture@example.invalid', subject='subject', body='body',
            disposition='LOCAL_READY', reason='', attachments=[])
        with self.effect() as effect:
            record_intent(effect, **values)
        retry = self.owner_for('retry', retry_of=self.owner)
        with self.assertRaisesRegex(ValueError, 'different evaluation'):
            with self.effect(retry) as effect:
                record_intent(effect, **{**values, 'body': 'changed'})

    def test_live_capture_commit_immutability_and_no_backfill(self):
        from django.db import transaction, DatabaseError
        from mta.runtime.operational_source import authorize_new_run, write_source, read_source
        from mta.runtime.operational_source_models import OperationalRequirementBand
        from mta.serialization import digest
        from tests.test_operational_capture import calculated
        values = calculated()
        with self.assertRaisesRegex(ValueError, 'production transaction'):
            write_source(self.run, values, calculation_digest=digest(values))
        accepted = self.run
        accepted.status = 'RUNNING'
        accepted.save(update_fields=['status'])
        with self.assertRaisesRegex(ValueError, 'new uncalculated'), transaction.atomic():
            authorize_new_run(accepted)
        self.run = self.capture_run()
        with transaction.atomic():
            authorize_new_run(self.run)
            write_source(self.run, values, calculation_digest=digest(values))
            self.run.status = 'SUCCEEDED'
            self.run.save(update_fields=['status'])
        result = read_source(self.run)
        self.assertEqual(len(result['requirement_bands']), 2)
        with self.assertRaises(DatabaseError), transaction.atomic():
            OperationalRequirementBand.objects.filter(source_id=self.run.pk).update(OrderReqBlack=999)
        self.assertEqual(read_source(self.run), result)
        with self.assertRaisesRegex(ValueError, 'production transaction'), transaction.atomic():
            write_source(self.run, values, calculation_digest=digest(values))

    def test_live_capture_rollback_leaves_no_rows(self):
        from django.db import transaction
        from mta.runtime.operational_source import authorize_new_run, write_source
        from mta.runtime.operational_source_models import OperationalCalculationSource, OperationalRequirementBand
        from mta.serialization import digest
        from tests.test_operational_capture import calculated
        self.run = self.capture_run()
        with transaction.atomic():
            authorize_new_run(self.run)
        values = calculated()
        with self.assertRaisesRegex(RuntimeError, 'rollback'), transaction.atomic():
            write_source(self.run, values, calculation_digest=digest(values))
            raise RuntimeError('rollback')
        self.assertFalse(OperationalCalculationSource.objects.filter(run=self.run).exists())
        self.assertFalse(OperationalRequirementBand.objects.filter(source_id=self.run.pk).exists())

    def capture_run(self, opted_in=True):
        from mta.application.operational_capture import CAPTURE_POLICY
        from mta.serialization import digest
        profile = {'operational_sources': CAPTURE_POLICY} if opted_in else {}
        payload = dict(profile=profile)
        return CalculationRun.objects.create(input_digest=digest(payload),
            execution_revision='capture-protocol-' + uuid.uuid4().hex,
            business_date=date(2026, 6, 6), input_payload=payload, status='RUNNING')

    def test_capture_authorization_requires_persisted_opt_in(self):
        from django.db import transaction
        from mta.runtime.operational_source import authorize_new_run
        owner = self.capture_run(opted_in=False)
        with self.assertRaisesRegex(ValueError, 'Persisted.*opt-in'), transaction.atomic():
            authorize_new_run(owner)
