"""Prepared chart admission fails closed before aggregate reads."""
import os
import unittest
import inspect
import json
from contextlib import ExitStack
from types import SimpleNamespace
from unittest.mock import patch
os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY','unit-only')
import django
django.setup()
from mta.presentation import planning_expedite_charts as subject
from mta.presentation.context import PublicationUnavailable


class ChartAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.run=SimpleNamespace(pk='fixture',kind='LEGACY_UI_FIXTURE',business_date='2026-04-07')
        self.receipt=SimpleNamespace(source_digest='source',recipe_digest='recipe',pick_digest='pick')
        self.stack=ExitStack();self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(subject.fixture,'binding',return_value=(self.run,'source')))
        self.stack.enter_context(patch.object(subject,'recipe_digest',return_value='recipe'))
        self.stack.enter_context(patch.object(subject,'pick_source',return_value='pick'))
        self.guards=self.stack.enter_context(patch.object(subject,'verify_guards'))
        self.receipts=self.stack.enter_context(patch.object(subject.PlanningExpediteChartProjection.objects,'filter'))
        self.receipts.return_value.first.return_value=self.receipt

    def test_wrong_run_kind_or_day_is_denied_before_read(self):
        for pk,kind,day in [('other','LEGACY_UI_FIXTURE','2026-04-07'),('fixture','DAILY_CHAIN','2026-04-07'),('fixture','LEGACY_UI_FIXTURE','2026-06-17')]:
            with self.assertRaisesRegex(PublicationUnavailable,'wrong_fixture'):
                subject.admit(SimpleNamespace(pk=pk,kind=kind,business_date=day))
        self.receipts.assert_not_called()

    def test_all_source_identities_and_receipt_are_required(self):
        self.receipts.return_value.first.return_value=None
        with self.assertRaisesRegex(PublicationUnavailable,'receipt_missing_or_changed'):subject.admit(self.run)
        self.receipts.return_value.first.return_value=self.receipt
        for field in ('source_digest','recipe_digest','pick_digest'):
            before=getattr(self.receipt,field);setattr(self.receipt,field,'changed')
            with self.assertRaisesRegex(PublicationUnavailable,'receipt_missing_or_changed'):subject.admit(self.run)
            setattr(self.receipt,field,before)
        self.guards.assert_not_called()

    def test_changed_guards_are_denied(self):
        self.guards.side_effect=ValueError('changed')
        with self.assertRaisesRegex(PublicationUnavailable,'guards_changed'):subject.admit(self.run)

    def test_valid_receipt_requires_guards(self):
        subject.admit(self.run)
        self.guards.assert_called_once()

    def test_fixture_graph_uses_prepared_reader_without_full_context(self):
        from mta.presentation import views
        with patch.object(subject.fixture,'enabled',return_value=True), \
                patch.object(views,'selected_run',return_value=self.run), \
                patch('mta.presentation.planning_expedite_chart_sql.queries',return_value={'tables':'prepared'}) as reader, \
                patch('mta.presentation.expedite_read.expedite_context') as context, \
                patch.object(views,'expedite_chart_response',return_value={'data':'formatted'}) as formatter:
            payload=dict(category='expedite',type='parent',filters={})
            result=inspect.unwrap(views.planning_graph)(None,payload)
            self.assertEqual(json.loads(result.content)['data'],{'data':'formatted'})
            reader.assert_called_once_with(self.run,payload,'parent')
            formatter.assert_called_once_with({'tables':'prepared'},'parent',receiving_own_label=True)
            context.assert_not_called()

    def test_child_label_ambiguity_remains_unavailable(self):
        from mta.presentation import views
        with patch.object(subject.fixture,'enabled',return_value=True), \
                patch.object(views,'selected_run',return_value=self.run), \
                patch('mta.presentation.planning_expedite_chart_sql.queries',return_value={}), \
                patch.object(views,'expedite_chart_response',side_effect=ValueError('Legacy Expedite receiving LogisticsLocation depends on unordered critical rows')) as formatter:
            with self.assertRaisesRegex(PublicationUnavailable,'LEG-EXPEDITE-UNORDERED-LABEL'):
                inspect.unwrap(views.planning_graph)(None,dict(category='expedite',type='child',filters={}))
            formatter.assert_called_once_with({},'child',receiving_own_label=False)


if __name__=='__main__':unittest.main()
