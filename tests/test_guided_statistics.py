"""Planner maintenance must not rebuild reports or alter execution settings."""
import os
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY', 'unit-only')
import django
django.setup()
from mta.runtime import guided_statistics as subject


class GuidedStatisticsTests(unittest.TestCase):
    def setUp(self):
        self.run = SimpleNamespace(pk='run', kind='DAILY_CHAIN', status='SUCCEEDED')
        self.connection = MagicMock(vendor='postgresql')
        self.receipts = MagicMock()
        self.receipts.filter.return_value.exists.return_value = False

    def invoke(self):
        with patch.object(subject, 'connection', self.connection), \
                patch.object(subject.ReportAggregateReceipt, 'objects', self.receipts):
            return subject.refresh_pending(self.run)

    def test_pending_aggregate_refreshes_exact_sources_only(self):
        self.assertTrue(self.invoke())
        statements = [call.args for call in self.connection.cursor.return_value.__enter__.return_value.execute.call_args_list]
        self.assertEqual(statements, [
            ('ANALYZE mta.fresh_mta_guidedavailabilityhistoryrow',),
            ('ANALYZE mta.fresh_mta_guidedavailabilitysnapshotreference',),
            ('ANALYZE mta.fresh_mta_guidedexcesshistoryrow',),
        ])
        self.receipts.filter.assert_called_once_with(run=self.run)

    def test_sealed_receipt_reuse_does_not_refresh_or_write(self):
        self.receipts.filter.return_value.exists.return_value = True
        self.assertFalse(self.invoke())
        self.connection.cursor.assert_not_called()

    def test_uncommitted_run_is_refused_before_database_work(self):
        self.run.status = 'RUNNING'
        with self.assertRaisesRegex(ValueError, 'committed daily run'):
            self.invoke()
        self.receipts.filter.assert_not_called()
        self.connection.cursor.assert_not_called()

    def test_statistics_failure_propagates_without_retry(self):
        cursor = self.connection.cursor.return_value.__enter__.return_value
        cursor.execute.side_effect = RuntimeError('statistics failed')
        with self.assertRaisesRegex(RuntimeError, 'statistics failed'):
            self.invoke()
        self.assertEqual(cursor.execute.call_count, 1)

    def test_no_nonpostgres_fallback(self):
        self.connection.vendor = 'sqlite'
        with self.assertRaisesRegex(ValueError, 'PostgreSQL'):
            self.invoke()
        self.receipts.filter.assert_not_called()
