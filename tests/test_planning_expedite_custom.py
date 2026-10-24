"""Prepared reader admission must fail closed without reading broad source bags."""
import os
import unittest
from types import SimpleNamespace
from contextlib import ExitStack
from unittest.mock import patch

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY', 'unit-only')
import django
django.setup()
from mta.presentation import planning_expedite_custom as subject
from mta.presentation.context import PublicationUnavailable


class PlanningExpediteCustomTests(unittest.TestCase):
    def test_full_route_preserves_context_reader_and_wire(self):
        from decimal import Decimal
        from mta.presentation import expedite_read
        from mta.presentation.excess_read import CUSTOM_COLUMNS
        run=SimpleNamespace(kind='DAILY_CHAIN')
        context=SimpleNamespace(rows=[],nms=[],bpr_rows=[],importer={'SiteDescriptionTbl':[]})
        with patch.object(expedite_read,'selected_run',return_value=run), \
                patch.object(expedite_read,'expedite_context',return_value=context) as source, \
                patch('mta.presentation.context.scope',return_value=(set(),set())), \
                patch('mta.presentation.expedite_custom.custom_rows',return_value=[dict(RN=1,tpp=Decimal('3.25'))]) as rows, \
                patch('mta.presentation.planning_expedite_custom_sql.custom_grid',side_effect=AssertionError('Full route changed')):
            self.assertEqual(expedite_read.custom_grid({}),dict(data=[dict(RN=1,tpp=3.25)],
                uiConfig=[dict(header=h,colCode=c,colPosition=p) for h,c,p in CUSTOM_COLUMNS]))
            source.assert_called_once_with(include_master=False,custom=True)
            rows.assert_called_once()

    def setUp(self):
        self.run = SimpleNamespace(pk='daily', kind='DAILY_CHAIN', business_date='2037-04-10')
        self.receipt = SimpleNamespace(source_digest='source', recipe_digest='recipe')
        self.stack=ExitStack();self.addCleanup(self.stack.close)
        def source(run):
            if run.pk!=self.run.pk or run.business_date!=self.run.business_date:
                raise PublicationUnavailable('daily_source_identity_differs')
            return 'source'
        self.stack.enter_context(patch('mta.presentation.daily_preparation.source_digest',side_effect=source))

    def test_admitted_relations_are_run_bounded_without_reconstructing_sources(self):
        with patch('mta.presentation.daily_preparation.production_branch',side_effect=lambda run:run.kind=='DAILY_CHAIN'), \
                patch.object(subject.PlanningExpediteCustomProjection.objects, 'filter') as receipts, \
                patch.object(subject, 'production_recipe_digest', return_value='recipe'), \
                patch.object(subject, 'verify_guards') as guards:
            receipts.return_value.first.return_value = self.receipt
            relations = subject.admitted_expedite_custom(self.run)
            self.assertEqual(set(relations), {'row'})
            for sql, params in relations.values():
                self.assertIn('WHERE run_id=%s', sql)
                self.assertEqual(params, ['daily'])
                self.assertNotIn('JOIN', sql)
            guards.assert_called_once()

    def test_missing_or_changed_receipt_is_unavailable(self):
        with patch('mta.presentation.daily_preparation.production_branch',side_effect=lambda run:run.kind=='DAILY_CHAIN'), \
                patch.object(subject.PlanningExpediteCustomProjection.objects, 'filter') as receipts, \
                patch.object(subject, 'production_recipe_digest', return_value='recipe'), \
                patch.object(subject, 'verify_guards') as guards:
            for value in (None, SimpleNamespace(source_digest='other', recipe_digest='recipe'),
                          SimpleNamespace(source_digest='source', recipe_digest='other')):
                receipts.return_value.first.return_value = value
                with self.assertRaisesRegex(PublicationUnavailable, 'receipt_missing_or_changed'):
                    subject.admitted_expedite_custom(self.run)
            guards.assert_not_called()

    def test_changed_guard_is_unavailable(self):
        with patch('mta.presentation.daily_preparation.production_branch',side_effect=lambda run:run.kind=='DAILY_CHAIN'), \
                patch.object(subject.PlanningExpediteCustomProjection.objects, 'filter') as receipts, \
                patch.object(subject, 'production_recipe_digest', return_value='recipe'), \
                patch.object(subject, 'verify_guards', side_effect=ValueError('drift')):
            receipts.return_value.first.return_value = self.receipt
            with self.assertRaisesRegex(PublicationUnavailable, 'immutable_guards_changed'):
                subject.admitted_expedite_custom(self.run)

    def test_other_run_kind_or_day_is_rejected_before_receipt_read(self):
        with patch('mta.presentation.daily_preparation.production_branch',side_effect=lambda run:run.kind=='DAILY_CHAIN'), \
                patch.object(subject.PlanningExpediteCustomProjection.objects, 'filter') as receipts:
            for pk, kind, day in [('other', 'LEGACY_UI_FIXTURE', '2026-04-07'),
                                  ('fixture', 'DAILY_CHAIN', '2026-04-07'),
                                  ('fixture', 'LEGACY_UI_FIXTURE', '2026-06-17')]:
                with self.assertRaisesRegex(PublicationUnavailable, 'removed_historical_mode|daily_source_identity_differs'):
                    subject.admitted_expedite_custom(SimpleNamespace(pk=pk, kind=kind, business_date=day))
            receipts.assert_not_called()
