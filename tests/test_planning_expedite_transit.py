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
        self.run = SimpleNamespace(pk='daily',kind='DAILY_CHAIN',business_date='2037-04-10')
        self.receipt = SimpleNamespace(source_digest='source',recipe_digest='recipe',pick_digest='pick')
        self.stack = ExitStack(); self.addCleanup(self.stack.close)
        self.stack.enter_context(patch('mta.presentation.daily_preparation.production_branch',side_effect=lambda run:run.kind=='DAILY_CHAIN'))
        self.source=self.stack.enter_context(patch('mta.presentation.daily_preparation.source_digest',return_value='source'))
        self.stack.enter_context(patch.object(subject,'production_recipe_digest',return_value='recipe'))
        self.stack.enter_context(patch.object(subject,'pick_binding',return_value='pick'))
        self.guards = self.stack.enter_context(patch.object(subject,'verify_guards'))
        self.receipts = self.stack.enter_context(patch.object(subject.PlanningExpediteTransitProjection.objects,'filter'))
        self.receipts.return_value.first.return_value = self.receipt

    def test_wrong_binding_rejected_before_receipt(self):
        for pk,kind,day in [('other','LEGACY_UI_FIXTURE','2026-04-07'),('daily','OTHER','2037-04-10'),('daily','LEGACY_UI_FIXTURE','2026-06-17')]:
            with self.assertRaisesRegex(PublicationUnavailable,'removed_historical_mode'):
                subject.admit(SimpleNamespace(pk=pk,kind=kind,business_date=day))
        self.source.assert_not_called()
        self.source.side_effect=PublicationUnavailable('daily_source_identity_differs')
        with self.assertRaisesRegex(PublicationUnavailable,'daily_source_identity_differs'):subject.admit(self.run)
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

    def test_retained_recipe_keeps_exact_source_and_pick_admission(self):
        self.receipt.recipe_digest=subject.RETAINED_PRODUCTION_RECIPE
        subject.admit(self.run)
        for field in ('source_digest','pick_digest'):
            previous=getattr(self.receipt,field);setattr(self.receipt,field,'different')
            with self.assertRaisesRegex(PublicationUnavailable,'receipt_missing_or_changed'):subject.admit(self.run)
            setattr(self.receipt,field,previous)

    def test_native_recipe_tracks_real_builder_instead_of_historical_fixture(self):
        from mta.presentation import planning_expedite_transit_preparation as preparation
        def changed_builder(run):return ('SELECT changed_native_contract',[])
        before=preparation.production_recipe_digest()
        with patch.object(preparation,'base_query',changed_builder),patch.object(preparation,'match_query',changed_builder):
            self.assertEqual(preparation.production_recipe_digest(),before)
        with patch.object(preparation,'production_base_query',changed_builder):
            self.assertNotEqual(preparation.production_recipe_digest(),before)
        with patch.object(preparation,'prepared_production_match',changed_builder):
            self.assertNotEqual(preparation.production_recipe_digest(),before)

    def test_unpaged_parent_uses_complete_same_relation_and_order(self):
        from mta.presentation import planning_expedite_sql as reader
        with patch.object(reader,'selected_parent',return_value=('SELECT source_rows', ['fixture'])) as selected, \
                patch.object(reader.transaction,'atomic'), patch.object(reader.connection,'cursor') as cursor, \
                patch.object(reader,'transit_rows',return_value=[]) as transit:
            c=cursor.return_value.__enter__.return_value
            c.fetchone.side_effect=[('on',),None]
            c.description=[('branch',),('rn',),('sc',)]
            c.fetchall.return_value=[('dispatch',1,'001'),('availability',1,'002')]
            result=parent_grid(self.run,{})
            statements=[args.args for args in c.execute.call_args_list]
            query,params=next(item for item in statements if 'SELECT * FROM numbered' in item[0])
            self.assertNotIn('rn BETWEEN',query)
            self.assertTrue(query.endswith(' ORDER BY branch,rn'))
            self.assertEqual(params,['fixture'])
            self.assertEqual(result['data']['expediteDispatches'],[{'rn':'1','sc':'001'}])
            self.assertEqual(result['data']['createAvailabilityAtParent'],[{'rn':'1','sc':'002'}])
            self.assertEqual(transit.call_count,2)

    def test_tags_belong_to_standard_attributes(self):
        filters = ExpediteFilters({},'expedite-parent',ExpediteRow)
        self.assertEqual(filters.column('A','Tags'),('S."Tags"','text'))

    def test_paged_daily_route_uses_prepared_reader_without_full_context(self):
        from mta.presentation import expedite_read
        with patch.object(expedite_read,'selected_run',return_value=self.run), \
                patch('mta.presentation.logistics_live.enabled',return_value=True), \
                patch.object(expedite_read,'expedite_context') as context, \
                patch('mta.presentation.planning_expedite_sql.parent_grid',return_value={'data':'prepared'}) as reader:
            payload=dict(filters={},paginationParameter=dict(pageNumber=1,recordsPerPage=25))
            self.assertEqual(expedite_read.parent_grid(payload),{'data':'prepared'})
            reader.assert_called_once_with(self.run,payload)
            context.assert_not_called()

    def test_unpaged_public_route_keeps_explicit_legacy_denial(self):
        from mta.presentation import expedite_read
        with patch.object(expedite_read,'selected_run',return_value=self.run), \
                patch('mta.presentation.logistics_live.enabled',return_value=True), \
                patch.object(expedite_read,'expedite_context',return_value=SimpleNamespace()), \
                patch('mta.presentation.planning_expedite_sql.parent_grid') as reader:
            with self.assertRaisesRegex(PublicationUnavailable,'LEG-EXPEDITE-PARENT-UNPAGED-SQL156'):
                expedite_read.parent_grid(dict(filters={}))
            reader.assert_not_called()
