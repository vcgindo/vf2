"""Real PostgreSQL ownership checks; stub calculations are not parity evidence."""
from copy import deepcopy
from datetime import timedelta
from pathlib import Path
import tempfile
import unittest
import uuid

from django.test import override_settings
from mta.runtime import test_temporal as fixture
from mta.runtime.operational_attempts import (
    register_configuration, configuration_value, start_attempt, finish_attempt,
)
from mta.runtime.operational_effects import operation, record_intent
from mta.runtime.operational_models import OperationalAttempt, OperationalOperation, OperationalAlertIntent
from mta.runtime.operational_native import save_population, MODELS
from mta.serialization import digest


class OperationalAttemptProtocol(unittest.TestCase):
    run_day = fixture.TemporalPersistenceTest.run_day
    calculate = fixture.TemporalPersistenceTest.calculate

    def setUp(self):
        fixture.TemporalPersistenceTest.setUp(self)
        self.revision = 'operational-attempt-' + uuid.uuid4().hex
        self.opening = deepcopy(self.opening)
        self.opening['identity'] = self.revision
        settings = override_settings(VF_MTA_DAILY_PUBLICATION=False,VF_OPERATIONAL_UNLEASED_TESTS=True)
        settings.enable()
        self.addCleanup(settings.disable)
        self.run = self.run_day()
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.roster = [dict(ordinal=i, group='O'+str(i+1), name='protocol-'+str(i),
                            stage='protocol', source_digest=digest(i)) for i in range(9)]
        self.config = register_configuration(source_digest=digest('protocol'),
            bindings={'operation_roster': self.roster}, settings=[], tables=[], alerts=[])

    def start(self, **changes):
        args = dict(run_id=self.run.pk, configuration_id=self.config.pk,
                    request_key=uuid.uuid4().hex, owned_root=self.temp.name,
                    expected_output_digest=self.run.output_digest)
        args.update(changes)
        return start_attempt(**args)

    def fill_operations(self, owner):
        for specification in self.roster:
            with operation(owner, **specification):
                pass

    def test_running_owner_and_failed_retry_lineage(self):
        calls = len(self.seen)
        first = self.start()
        with self.assertRaisesRegex(ValueError, 'running operational attempt'):
            self.start()
        with self.assertRaisesRegex(RuntimeError, 'injected'):
            with operation(first, **self.roster[0]):
                raise RuntimeError('injected I/O interruption')
        first.refresh_from_db()
        self.assertEqual(first.status, 'FAILED')
        with self.assertRaisesRegex(ValueError, 'explicit recovery lineage'):
            self.start()
        second = self.start(retry_of_id=first.pk)
        self.assertNotEqual(first.root, second.root)
        self.assertTrue(Path(first.root).is_dir())
        self.assertEqual(second.retry_of_id, first.pk)
        with self.assertRaisesRegex(RuntimeError, 'again'):
            with operation(second, **self.roster[0]):
                raise RuntimeError('again')
        with self.assertRaisesRegex(ValueError, 'already has a retry'):
            self.start(retry_of_id=first.pk)
        self.assertEqual(len(self.seen), calls)

    def test_no_completion_without_full_roster_and_real_restore(self):
        owner = self.start()
        with self.assertRaisesRegex(ValueError, 'roster'):
            finish_attempt(owner)
        self.fill_operations(owner)
        with self.assertRaisesRegex(ValueError, 'verified operational backup absent'):
            finish_attempt(owner)
        OperationalOperation.objects.filter(attempt=owner, group='O8').update(status='DISABLED')
        with self.assertRaisesRegex(ValueError, 'roster'):
            finish_attempt(owner)
        owner.refresh_from_db()
        self.assertEqual(owner.status, 'RUNNING')
        self.assertIsNone(owner.completed_at)

    def test_completion_rereads_typed_values_and_owner(self):
        owner = self.start()
        row = dict(SKUCode='sku', WhCode='location', Norm=None, Stock=3, GIT=None)
        save_population(owner, 'exceptions', 'BPR/BPRExceptions', [row, row])
        self.fill_operations(owner)
        MODELS['BPR/BPRExceptions'].objects.filter(attempt=owner, ordinal=1).update(field_3=4)
        with self.assertRaisesRegex(ValueError, 'population changed'):
            finish_attempt(owner)
        OperationalAttempt.objects.filter(pk=owner.pk).update(business_date=self.run.business_date+timedelta(days=1))
        with self.assertRaisesRegex(ValueError, 'owner/status/date'):
            finish_attempt(owner)

    def test_configuration_drift_and_inexact_source_denied(self):
        with self.assertRaisesRegex(ValueError, 'Exact completed daily'):
            self.start(expected_output_digest='0'*64)
        # A local copy cannot silently substitute a different configuration body.
        self.config.bindings = {'operation_roster': []}
        with self.assertRaisesRegex(ValueError, 'configuration identity drift'):
            configuration_value(self.config)

    def test_completion_rejects_changed_intent_content(self):
        owner = self.start()
        for specification in self.roster:
            with operation(owner, **specification) as effect:
                if specification['group'] == 'O7':
                    intent = record_intent(effect, alert_name='NoNormParentAlert',
                        branch='no-norm-parent', stage='parent-norm', source_digest=digest('alert'),
                        recipients='Not-Defined', subject=None, body=None,
                        disposition='RECIPIENT_SUPPRESSED', reason='native guard', attachments=[])
        OperationalAlertIntent.objects.filter(pk=intent.pk).update(reason='changed after evaluation')
        with self.assertRaisesRegex(ValueError, 'evaluation content drift'):
            finish_attempt(owner)
