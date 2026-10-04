"""Prepared transit admission and parent reader boundary regressions."""
import os
import unittest
from contextlib import ExitStack
from types import SimpleNamespace
from unittest.mock import patch
os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY','unit-only')
import django
django.setup()
from mta.presentation import planning_expedite_transit as subject
from mta.presentation.context import PublicationUnavailable
from mta.presentation.planning_expedite_sql import parent_grid,ExpediteFilters
from mta.runtime.models import ExpediteRow


class TransitAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.run = SimpleNamespace(pk='fixture',kind='LEGACY_UI_FIXTURE',business_date='2026-04-07')
        self.receipt = SimpleNamespace(source_digest='source',recipe_digest='recipe',pick_digest='pick')
        self.stack = ExitStack(); self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(subject.fixture,'binding',return_value=(self.run,'source')))
        self.stack.enter_context(patch.object(subject,'recipe_digest',return_value='recipe'))
        self.stack.enter_context(patch.object(subject,'pick_source',return_value='pick'))
        self.guards = self.stack.enter_context(patch.object(subject,'verify_guards'))
        self.receipts = self.stack.enter_context(patch.object(subject.PlanningExpediteTransitProjection.objects,'filter'))
        self.receipts.return_value.first.return_value = self.receipt

    def test_wrong_binding_rejected_before_receipt(self):
        for pk,kind,day in [('other','LEGACY_UI_FIXTURE','2026-04-07'),('fixture','DAILY_CHAIN','2026-04-07'),('fixture','LEGACY_UI_FIXTURE','2026-06-17')]:
            with self.assertRaisesRegex(PublicationUnavailable,'wrong_fixture'):
                subject.admit(SimpleNamespace(pk=pk,kind=kind,business_date=day))
        self.receipts.assert_not_called()

    def test_receipt_and_pick_identity_are_required(self):
        self.receipts.return_value.first.return_value = None
        with self.assertRaisesRegex(PublicationUnavailable,'receipt_missing_or_changed'): subject.admit(self.run)
        self.receipts.return_value.first.return_value = self.receipt
        for field in ('source_digest','recipe_digest','pick_digest'):
            before = getattr(self.receipt,field);setattr(self.receipt,field,'changed')
            with self.assertRaisesRegex(PublicationUnavailable,'receipt_missing_or_changed'): subject.admit(self.run)
            setattr(self.receipt,field,before)
        self.guards.assert_not_called()

    def test_guard_drift_denied(self):
        self.guards.side_effect = ValueError('changed')
        with self.assertRaisesRegex(PublicationUnavailable,'guards_changed'): subject.admit(self.run)

    def test_unpaged_parent_stays_unavailable_before_any_read(self):
        with self.assertRaisesRegex(PublicationUnavailable,'UNPAGED-SQL156'): parent_grid(self.run,{})
        self.receipts.assert_not_called()

    def test_tags_belong_to_standard_attributes(self):
        filters = ExpediteFilters({},'expedite-parent',ExpediteRow)
        self.assertEqual(filters.column('A','Tags'),('S."Tags"','text'))

    def test_fixture_route_uses_prepared_reader_without_full_context(self):
        from mta.presentation import expedite_read
        with patch.object(expedite_read,'selected_run',return_value=self.run), \
                patch.object(expedite_read,'expedite_context') as context, \
                patch('mta.presentation.planning_expedite_sql.parent_grid',return_value={'data':'prepared'}) as reader:
            self.assertEqual(expedite_read.parent_grid({'filters':{}}),{'data':'prepared'})
            reader.assert_called_once_with(self.run,{'filters':{}})
            context.assert_not_called()
