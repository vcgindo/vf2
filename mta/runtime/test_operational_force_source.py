"""Real PostgreSQL capture protocol; calculation is explicitly stubbed."""
from copy import deepcopy
import unittest
import uuid
from unittest.mock import patch
from django.db import DatabaseError, transaction, connection
from django.test import override_settings
from mta.application.operational_capture import CAPTURE_POLICY
from mta.application.timeline_controls import FORCE_CAPTURE_POLICY
from mta.runtime import test_temporal as fixture
from mta.runtime.models import CalculationRun
from mta.runtime.operational_force_source import BINDINGS, read_force_source, write_force_source
from mta.runtime.operational_source_models import OperationalForceSource
from mta.runtime.relational_state import table_sql
from tests.test_operational_capture import calculated


class ForceCaptureProtocol(unittest.TestCase):
    run_day = fixture.TemporalPersistenceTest.run_day

    def setUp(self):
        fixture.TemporalPersistenceTest.setUp(self)
        settings = override_settings(VF_MTA_DAILY_PUBLICATION=False)
        settings.enable()
        self.addCleanup(settings.disable)
        self.profile.update(operational_sources=CAPTURE_POLICY,
                            operational_force_sources=FORCE_CAPTURE_POLICY)
        self.opening['identity'] = 'force-capture-'+uuid.uuid4().hex
        self.populations = dict(ForceNormChange=[dict(SKUCode='S', WhCode='W',
            NewNorm=None, Approved=True, RequestedBy='fixture')]*2,
            DBMMaster=[dict(SKUCode='S', WHCode='W', Norm=12)],
            MasterDataRaw=[dict(SKUCode='S', WhCode='W', Norm=None)])

    def calculate(self, *args):
        result = fixture.TemporalPersistenceTest.calculate(self, *args)
        result['CalculationOutputs'].extend(calculated())
        result['_OperationalForceSources'] = deepcopy(self.populations)
        return result

    def test_typed_readback_retry_immutable_receipt_and_rollback(self):
        run = self.run_day()
        self.assertEqual(read_force_source(run), self.populations)
        calls = len(self.seen)
        self.assertEqual(self.run_day().pk, run.pk)
        self.assertEqual(len(self.seen), calls)
        with transaction.atomic(), self.assertRaisesRegex(ValueError, 'live production'):
            write_force_source(run, self.populations)
        with self.assertRaises(DatabaseError), transaction.atomic():
            OperationalForceSource.objects.filter(run=run).update(rows_digest='0'*64)
        self.opening['identity'] = 'force-failed-'+uuid.uuid4().hex
        self.revision = 'force-failed-'+uuid.uuid4().hex
        with patch('mta.presentation.excess_storage.write_excess', side_effect=RuntimeError('after force capture')):
            with self.assertRaisesRegex(RuntimeError, 'after force capture'):
                self.run_day()
        failed = CalculationRun.objects.get(execution_revision=self.revision)
        self.assertEqual(failed.status, 'FAILED')
        self.assertFalse(OperationalForceSource.objects.filter(run=failed).exists())
        with connection.cursor() as cursor:
            for name, table in BINDINGS.items():
                cursor.execute('SELECT COUNT(*) FROM '+table_sql(table)+
                    ' WHERE vf_run_id=%s AND vf_image=%s', [failed.pk, 'operational/force/'+name])
                self.assertEqual(cursor.fetchone()[0], 0)
        self.revision = 'force-retry-'+uuid.uuid4().hex
        self.assertEqual(read_force_source(self.run_day()), self.populations)

    def test_missing_source_fails_without_partial_capture(self):
        self.populations.pop('ForceNormChange')
        with self.assertRaisesRegex(ValueError, 'All three'):
            self.run_day()
        failed = CalculationRun.objects.get(execution_revision=self.revision)
        self.assertEqual(failed.status, 'FAILED')
        self.assertFalse(OperationalForceSource.objects.filter(run=failed).exists())

    def test_incomplete_positive_rows_are_not_empty_defaults(self):
        self.populations['ForceNormChange'] = [dict(SKUCode='S', WhCode='W')]
        with self.assertRaisesRegex(ValueError, 'required fields'):
            self.run_day()
        failed = CalculationRun.objects.get(execution_revision=self.revision)
        self.assertFalse(OperationalForceSource.objects.filter(run=failed).exists())
