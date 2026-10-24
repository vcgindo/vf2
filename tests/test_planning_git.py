"""Prepared reader admission must fail closed without reading broad source bags."""
import os
import unittest
from types import SimpleNamespace
from contextlib import contextmanager,ExitStack
from unittest.mock import patch

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY', 'unit-only')
import django
django.setup()
from mta.presentation import planning_git as subject
from mta.presentation.context import PublicationUnavailable


class PlanningGitTests(unittest.TestCase):
    def test_child_combined_keeps_location_occurrences_separate_from_empty_shipments(self):
        from mta.presentation.planning_git_sql import combined_grid
        row={'g':7,'sc':'001','AgeingOrder':None,'transit':[]}
        rows=[row,dict(row)]
        actual=combined_grid('child',rows,[{'colCode':'g'}])
        self.assertEqual(actual['locationWise']['data'],[row,row])
        self.assertEqual(actual['transporterWise']['data'],[])
        self.assertNotIn('tc',actual['locationWise']['data'][0])
        self.assertEqual(combined_grid('child',[],[])['locationWise']['data'],[])

    def setUp(self):
        self.run = SimpleNamespace(pk='daily-run', kind='DAILY_CHAIN', business_date='2026-04-07')
        self.receipt = SimpleNamespace(source_digest='source', recipe_digest='recipe')

    @contextmanager
    def admitted_daily(self):
        with ExitStack() as stack:
            stack.enter_context(patch('mta.presentation.daily_preparation.production_branch',return_value=True))
            stack.enter_context(patch('mta.presentation.daily_preparation.source_digest',return_value='source'))
            stack.enter_context(patch.object(subject,'production_recipe_digest',return_value='recipe'))
            yield

    def test_admitted_relations_are_run_bounded_without_reconstructing_sources(self):
        with self.admitted_daily(), \
                patch.object(subject.PlanningGitProjection.objects, 'filter') as receipts, \
                patch.object(subject, 'recipe_digest', return_value='recipe'), \
                patch.object(subject, 'verify_guards') as guards:
            receipts.return_value.first.return_value = self.receipt
            relations = subject.admitted_git(self.run)
            self.assertEqual(set(relations), {'row'})
            for sql, params in relations.values():
                self.assertIn('WHERE run_id=%s', sql)
                self.assertEqual(params, ['daily-run'])
                self.assertNotIn('JOIN', sql)
            guards.assert_called_once()

    def test_missing_or_changed_receipt_is_unavailable(self):
        with self.admitted_daily(), \
                patch.object(subject.PlanningGitProjection.objects, 'filter') as receipts, \
                patch.object(subject, 'recipe_digest', return_value='recipe'), \
                patch.object(subject, 'verify_guards') as guards:
            for value in (None, SimpleNamespace(source_digest='other', recipe_digest='recipe'),
                          SimpleNamespace(source_digest='source', recipe_digest='other')):
                receipts.return_value.first.return_value = value
                with self.assertRaisesRegex(PublicationUnavailable, 'receipt_missing_or_changed'):
                    subject.admitted_git(self.run)
            guards.assert_not_called()

    def test_changed_guard_is_unavailable(self):
        with self.admitted_daily(), \
                patch.object(subject.PlanningGitProjection.objects, 'filter') as receipts, \
                patch.object(subject, 'recipe_digest', return_value='recipe'), \
                patch.object(subject, 'verify_guards', side_effect=ValueError('drift')):
            receipts.return_value.first.return_value = self.receipt
            with self.assertRaisesRegex(PublicationUnavailable, 'immutable_guards_changed'):
                subject.admitted_git(self.run)

    def test_unadmitted_run_is_rejected_before_receipt_read(self):
        with patch('mta.presentation.daily_preparation.production_branch',return_value=False), \
                patch.object(subject.PlanningGitProjection.objects,'filter') as receipts:
            with self.assertRaisesRegex(PublicationUnavailable,'removed_historical_mode'):
                subject.admitted_git(self.run)
            with self.assertRaisesRegex(PublicationUnavailable,'wrong_fixture'):
                subject.admitted_git(self.run,validated_fixture=(self.run,'source'))
            receipts.assert_not_called()
