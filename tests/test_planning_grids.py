"""Prepared reader admission must fail closed without reading broad source bags."""
import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY', 'unit-only')
import django
django.setup()
from mta.presentation import planning_grids as subject
from mta.presentation.context import PublicationUnavailable


class PlanningGridsTests(unittest.TestCase):
    def setUp(self):
        self.run = SimpleNamespace(pk='fixture', kind='LEGACY_UI_FIXTURE', business_date='2026-04-07')
        self.receipt = SimpleNamespace(source_digest='source', recipe_digest='recipe')

    def test_admitted_relations_are_run_bounded_without_reconstructing_sources(self):
        with patch.object(subject.fixture, 'binding', return_value=(self.run, 'source')), \
                patch.object(subject.PlanningGridProjection.objects, 'filter') as receipts, \
                patch.object(subject, 'recipe_digest', return_value='recipe'), \
                patch.object(subject, 'verify_guards') as guards:
            receipts.return_value.first.return_value = self.receipt
            relations = subject.admitted_grids(self.run)
            self.assertEqual(set(relations), {'excess', 'fulfillment'})
            for sql, params in relations.values():
                self.assertIn('WHERE run_id=%s', sql)
                self.assertEqual(params, ['fixture'])
                self.assertNotIn('JOIN', sql)
            guards.assert_called_once()

    def test_missing_or_changed_receipt_is_unavailable(self):
        with patch.object(subject.fixture, 'binding', return_value=(self.run, 'source')), \
                patch.object(subject.PlanningGridProjection.objects, 'filter') as receipts, \
                patch.object(subject, 'recipe_digest', return_value='recipe'), \
                patch.object(subject, 'verify_guards') as guards:
            for value in (None, SimpleNamespace(source_digest='other', recipe_digest='recipe'),
                          SimpleNamespace(source_digest='source', recipe_digest='other')):
                receipts.return_value.first.return_value = value
                with self.assertRaisesRegex(PublicationUnavailable, 'receipt_missing_or_changed'):
                    subject.admitted_grids(self.run)
            guards.assert_not_called()

    def test_changed_guard_is_unavailable(self):
        with patch.object(subject.fixture, 'binding', return_value=(self.run, 'source')), \
                patch.object(subject.PlanningGridProjection.objects, 'filter') as receipts, \
                patch.object(subject, 'recipe_digest', return_value='recipe'), \
                patch.object(subject, 'verify_guards', side_effect=ValueError('drift')):
            receipts.return_value.first.return_value = self.receipt
            with self.assertRaisesRegex(PublicationUnavailable, 'immutable_guards_changed'):
                subject.admitted_grids(self.run)

    def test_other_run_kind_or_day_is_rejected_before_receipt_read(self):
        with patch.object(subject.fixture, 'binding', return_value=(self.run, 'source')), \
                patch.object(subject.PlanningGridProjection.objects, 'filter') as receipts:
            for pk, kind, day in [('other', 'LEGACY_UI_FIXTURE', '2026-04-07'),
                                  ('fixture', 'DAILY_CHAIN', '2026-04-07'),
                                  ('fixture', 'LEGACY_UI_FIXTURE', '2026-06-17')]:
                with self.assertRaisesRegex(PublicationUnavailable, 'wrong_fixture'):
                    subject.admitted_grids(SimpleNamespace(pk=pk, kind=kind, business_date=day))
            receipts.assert_not_called()
