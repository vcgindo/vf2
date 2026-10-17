"""Finite coordinator/readiness tests; not a claim of daily runtime acceptance."""
import os
import unittest
from contextlib import nullcontext
from datetime import date
from types import SimpleNamespace
from uuid import UUID
from unittest.mock import MagicMock, patch

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY', 'unit-only')
import django
django.setup()
from mta.presentation import daily_publication, planning_summary_daily as daily
from mta.presentation.context import PublicationUnavailable
from mta.runtime.management.commands.prepare_daily_ui import Command


class DailySummaryTests(unittest.TestCase):
    def test_command_calls_complete_reporting_coordinator(self):
        publication=SimpleNamespace(run_id='run',status='READY',seal_digest='seal',layers={})
        summary=SimpleNamespace(pk='summary',status='READY',rows_digest='rows')
        with patch('mta.runtime.management.commands.prepare_daily_ui.prepare_reporting_generation',return_value=(publication,summary)) as prepare:
            Command(stdout=MagicMock()).handle(run_id='run',output_digest='output')
        prepare.assert_called_once_with('run',expected_output_digest='output')

    def test_coordinator_prepares_summary_only_after_base_ready(self):
        run=SimpleNamespace(pk='run')
        publication=SimpleNamespace(run=run,status='INCOMPLETE')
        with patch.object(daily_publication,'prepare',return_value=publication), \
             patch.object(daily,'prepare') as summary:
            with self.assertRaises(PublicationUnavailable):
                daily_publication.prepare_reporting_generation('run',expected_output_digest='output')
            summary.assert_not_called()
            publication.status='READY'
            summary.side_effect=RuntimeError('summary failed')
            with self.assertRaisesRegex(RuntimeError,'summary failed'):
                daily_publication.prepare_reporting_generation('run',expected_output_digest='output')
            summary.assert_called_once_with(run)

    def test_idempotent_prepare_reuses_verified_receipt_without_attempt_or_writes(self):
        identities=dict(source_digest='source',generation_digest='generation',recipe_digest='recipe',business_date=date(2026,4,7))
        receipt=SimpleNamespace(pk='receipt')
        with patch.object(daily,'binding',return_value=(identities,None,{})), \
             patch.object(daily.transaction,'atomic',return_value=nullcontext()), \
             patch.object(daily.connection,'cursor',return_value=MagicMock()), \
             patch.object(daily.PlanningSummaryReceipt.objects,'filter') as query, \
             patch.object(daily.PlanningSummaryAttempt.objects,'create') as attempt, \
             patch.object(daily,'verify') as verify:
            query.return_value.first.return_value=receipt
            self.assertIs(daily._prepare(SimpleNamespace(pk='run')),receipt)
            verify.assert_called_once_with(receipt,identities)
            attempt.assert_not_called()

    def test_missing_summary_is_not_ready(self):
        with patch.object(daily,'binding',return_value=({},None,{})), \
             patch.object(daily.PlanningSummaryReceipt.objects,'filter') as query:
            query.return_value.first.return_value=None
            with self.assertRaisesRegex(PublicationUnavailable,'planning_summary_generation_unavailable'):
                daily.require_ready(SimpleNamespace(pk='run'))

    def test_failed_population_retains_failed_attempt_and_propagates(self):
        run=SimpleNamespace(pk=UUID('00000000-0000-0000-0000-000000000001'))
        attempt=MagicMock()
        with patch.object(daily,'binding',return_value=({},None,{})), \
             patch.object(daily.transaction,'atomic',side_effect=lambda: nullcontext()), \
             patch.object(daily.connection,'cursor',return_value=MagicMock()), \
             patch.object(daily.PlanningSummaryReceipt.objects,'filter') as query, \
             patch.object(daily.PlanningSummaryReceipt.objects,'create',return_value=SimpleNamespace(pk='new')), \
             patch.object(daily.PlanningSummaryAttempt.objects,'create',return_value=attempt), \
             patch.object(daily,'contribution_queries',return_value=[('SELECT 1',[]) ]):
            query.return_value.first.return_value=None
            with self.assertRaisesRegex(RuntimeError,'injected_planning_summary_interruption'):
                daily._prepare(run,fail_after_rows=True)
        self.assertEqual(attempt.status,'FAILED')
        attempt.save.assert_called_once()

    def test_changed_date_or_source_is_not_ready(self):
        identities=dict(source_digest='source',generation_digest='generation',recipe_digest='recipe',business_date=date(2026,4,7))
        for change in ({'source_digest':'other'},{'business_date':date(2026,4,8)}):
            receipt=SimpleNamespace(status='READY',metrics=list(daily.METRICS),**(identities|change))
            with self.assertRaises(PublicationUnavailable):daily.verify(receipt,identities)

if __name__=='__main__':unittest.main()
