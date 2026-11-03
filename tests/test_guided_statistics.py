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

    def invoke(self):
        with patch.object(subject, 'connection', self.connection):
            subject.refresh_sources(self.run)

    def test_pending_aggregate_refreshes_exact_sources_only(self):
        self.invoke()
        statements = [call.args for call in self.connection.cursor.return_value.__enter__.return_value.execute.call_args_list]
        self.assertEqual(statements, [
            ('ANALYZE mta.fresh_mta_guidedavailabilityhistoryrow',),
            ('ANALYZE mta.fresh_mta_guidedavailabilitysnapshotreference',),
            ('ANALYZE mta.fresh_mta_guidedexcesshistoryrow',),
        ])

    def test_uncommitted_run_is_refused_before_database_work(self):
        self.run.status = 'RUNNING'
        with self.assertRaisesRegex(ValueError, 'committed daily run'):
            self.invoke()
        self.connection.cursor.assert_not_called()

    def test_statistics_failure_propagates_without_retry(self):
        cursor = self.connection.cursor.return_value.__enter__.return_value
        cursor.execute.side_effect = RuntimeError('statistics failed')
        with self.assertRaisesRegex(RuntimeError, 'statistics failed'):
            self.invoke()
        self.assertEqual(cursor.execute.call_count, 1)
        handler = self.connection.connection.add_notice_handler.call_args.args[0]
        self.connection.connection.remove_notice_handler.assert_called_once_with(handler)

    def test_skipped_analyze_warns_and_refuses_preparation(self):
        physical = self.connection.connection
        cursor = self.connection.cursor.return_value.__enter__.return_value

        def skipped(_statement):
            handler = physical.add_notice_handler.call_args.args[0]
            handler(SimpleNamespace(severity_nonlocalized='WARNING',
                                    message_primary='permission denied to analyze, skipping it'))

        cursor.execute.side_effect = skipped
        with self.assertRaisesRegex(ValueError, 'permission denied to analyze'):
            self.invoke()
        self.assertEqual(cursor.execute.call_count, 1)
        physical.remove_notice_handler.assert_called_once_with(physical.add_notice_handler.call_args.args[0])

    def test_no_nonpostgres_fallback(self):
        self.connection.vendor = 'sqlite'
        with self.assertRaisesRegex(ValueError, 'PostgreSQL'):
            self.invoke()
