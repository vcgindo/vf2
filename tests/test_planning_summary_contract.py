"""Focused unit contract for the prepared Planning overview summary."""
import os
import unittest
import importlib
from contextlib import ExitStack
from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY', 'unit-only')
import django
django.setup()

from django.db import DataError
from django.test import override_settings

from mta.presentation import planning_summary
from mta.presentation.context import PermissionCodes, PublicationUnavailable


class SharedBindingTests(unittest.TestCase):
    def test_direct_dependencies_retain_checks_with_call_local_binding(self):
        run = SimpleNamespace(pk='selected', kind='LEGACY_UI_FIXTURE', business_date=date(2026, 4, 7))
        for module_name, function, model in (
                ('planning_sources', 'admitted_sources', 'PlanningSourceProjection'),
                ('planning_git', 'admitted_git', 'PlanningGitProjection'),
                ('planning_grids', 'admitted_grids', 'PlanningGridProjection'),
                ('planning_expedite_grids', 'admitted_expedite_grids', 'PlanningExpediteGridProjection')):
            module = importlib.import_module('mta.presentation.' + module_name)
            with self.subTest(module=module_name), ExitStack() as stack:
                stack.enter_context(patch('mta.presentation.daily_preparation.production_branch', return_value=False))
                lookup = stack.enter_context(patch.object(getattr(module, model).objects, 'filter'))
                lookup.return_value.first.return_value = SimpleNamespace(source_digest='source', recipe_digest='recipe')
                stack.enter_context(patch.object(module, 'recipe_digest', return_value='recipe'))
                guards = stack.enter_context(patch.object(module, 'verify_guards'))
                original = stack.enter_context(patch.object(module.fixture, 'binding', return_value=(run, 'source')))
                reader = getattr(module, function)
                reader(run, validated_fixture=(run, 'source'))
                original.assert_not_called()
                guards.assert_called_once()
                with self.assertRaises(PublicationUnavailable):
                    reader(run, validated_fixture=(SimpleNamespace(pk='other'), 'source'))
                with self.assertRaises(PublicationUnavailable):
                    reader(run, validated_fixture=(run, 'different-source'))
                reader(run)
                original.assert_called_once()


class ContributionContractTests(unittest.TestCase):
    def setUp(self):
        self.relations = {
            'master': ('SELECT * FROM admitted_master WHERE marker=%s', ['master']),
            'git': ('SELECT * FROM admitted_git WHERE marker=%s', ['git']),
            'expedite': ('SELECT * FROM admitted_expedite WHERE marker=%s', ['expedite']),
            'excess': ('SELECT * FROM admitted_excess WHERE marker=%s', ['excess']),
            'fulfillment': ('SELECT * FROM admitted_fulfillment WHERE marker=%s', ['fulfillment']),
        }

    def queries(self, kind):
        run = SimpleNamespace(pk='run-1', kind=kind, business_date=date(2026, 4, 7))
        if kind == 'LEGACY_UI_FIXTURE':
            return list(planning_summary.contribution_queries(run, self.relations))
        with patch('mta.presentation.selective.image_query', side_effect=[
                ('SELECT * FROM admitted_transporter WHERE marker=%s', ['transporter']),
                ('SELECT * FROM admitted_transit WHERE marker=%s', ['transit'])]):
            return list(planning_summary.contribution_queries(run, self.relations))

    def test_fixture_roster_has_nine_source_metrics_and_declared_zero_git_custom(self):
        queries = self.queries('LEGACY_UI_FIXTURE')
        by_metric = {params[0]: (sql, params) for sql, params in queries}
        self.assertEqual(set(by_metric), set(planning_summary.METRICS) - {'git_custom'})
        self.assertEqual(len(queries), 9)
        self.assertEqual(len(planning_summary.METRICS), 10)

        git_parent = by_metric['git_parent'][0]
        git_child = by_metric['git_child'][0]
        self.assertIn('A.rationed_ordinal=H.rationed_ordinal', git_parent)
        self.assertIn('A.standard_ordinal=H.standard_ordinal', git_parent)
        self.assertIn('WHERE H.grid_eligible', git_parent)
        self.assertIn('A."WhCode" AS location_key', git_parent)
        self.assertIn('A."ParentWhCode" AS location_key', git_child)

        for metric in ('expedite_parent', 'expedite_child'):
            sql = by_metric[metric][0]
            self.assertIn("H.direction='child'", sql)
            self.assertIn("H.branch='dispatch'", sql)
            self.assertIn('H.standard_ordinal IS NOT NULL', sql)
            self.assertIn('H.pair_ordinal IS NOT NULL', sql)
            self.assertIn("lower(rtrim(A.\"PipelineInventoryColor\"::text,' ')) IN ('red','black')", sql)
        self.assertIn('A."WhCode" AS location_key', by_metric['expedite_parent'][0])
        self.assertIn('A."ParentWhCode" AS location_key', by_metric['expedite_child'][0])

        self.assertIn('fresh_mta_excessinventoryrow', by_metric['excess_review'][0])
        self.assertIn('fresh_mta_fulfillmentsummaryrow', by_metric['fulfillment_review'][0])
        self.assertIn('A."ReportDate"=%s', by_metric['excess_custom'][0])
        self.assertNotIn('ReportDate', by_metric['fulfillment_custom'][0])
        self.assertIn('A."ParentWhCode" AS location_key', by_metric['expedite_custom'][0])
        self.assertTrue(all(params[1] == 'raw' for _, params in queries))

    def test_daily_adds_normalized_git_custom_over_two_admitted_source_bags(self):
        queries = self.queries('DAILY_CHAIN')
        by_metric = {params[0]: (sql, params) for sql, params in queries}
        self.assertEqual(set(by_metric), set(planning_summary.METRICS))
        self.assertEqual(len(queries), 10)
        sql, params = by_metric['git_custom']
        self.assertEqual(params[:2], ['git_custom', 'normalized'])
        self.assertEqual(params[2:], ['transporter', 'transit'])
        self.assertIn('admitted_transporter', sql)
        self.assertIn('admitted_transit', sql)
        self.assertIn("lower(rtrim(A.\"SKUCode\"::text,' '))=lower(rtrim(T.\"SKUCode\"::text,' '))", sql)
        self.assertIn("lower(rtrim(A.\"WhCode\"::text,' '))=lower(rtrim(T.\"WhCode\"::text,' '))", sql)


class ResponseContractTests(unittest.TestCase):
    def test_empty_scope_returns_all_ten_counts_as_string_zero_without_database(self):
        response = planning_summary.counts(SimpleNamespace(pk='receipt'),
                                           (PermissionCodes({}), PermissionCodes({'L': 1})))
        self.assertEqual(response, [
            {'category': 'git/wip', 'parentCount': '0', 'childCount': '0', 'custom': '0'},
            {'category': 'expedite', 'parentCount': '0', 'childCount': '0', 'custom': '0'},
            {'category': 'excessInventory', 'reviewCount': '0', 'custom': '0'},
            {'category': 'orderFulfillment', 'reviewCount': '0', 'custom': '0'},
        ])
        self.assertEqual(sum(len(row) - 1 for row in response), 10)

    def test_int32_metrics_reject_overflow(self):
        class Cursor:
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def execute(self, *args): pass
            def fetchall(self): return [('expedite_custom', 2147483648)]

        resolved = (PermissionCodes({'SKU': 1}), PermissionCodes({'LOC': 1}))
        with patch.object(planning_summary.connection, 'cursor', return_value=Cursor()), \
             self.assertRaisesRegex(DataError, 'integer out of range'):
            planning_summary.counts(SimpleNamespace(pk='receipt'), resolved)


class IdentityContractTests(unittest.TestCase):
    def receipt(self, **changes):
        values = dict(pk='receipt-1', source_digest='source-1', generation_digest='generation-1',
                      recipe_digest='recipe-1', business_date=date(2026, 4, 7))
        values.update(changes)
        return SimpleNamespace(**values)

    @override_settings(VF_MTA_PERMISSIONS_SHA256='permissions-1')
    def test_identity_changes_with_actor_weights_generation_source_and_date(self):
        payload = {'product_permissions': [1], 'location_permissions': [2], 'filters': {}}
        resolved = (PermissionCodes({'SKU': 1}), PermissionCodes({'LOC': 1}))
        baseline = planning_summary.identity_value(self.receipt(), payload, 'actor-1', resolved)
        variants = [
            planning_summary.identity_value(self.receipt(), payload, 'actor-2', resolved),
            planning_summary.identity_value(self.receipt(), payload, 'actor-1',
                                            (PermissionCodes({'SKU': 2}), resolved[1])),
            planning_summary.identity_value(self.receipt(generation_digest='generation-2'), payload,
                                            'actor-1', resolved),
            planning_summary.identity_value(self.receipt(source_digest='source-2'), payload,
                                            'actor-1', resolved),
            planning_summary.identity_value(self.receipt(business_date=date(2026, 4, 8)), payload,
                                            'actor-1', resolved),
        ]
        self.assertEqual(len(set([baseline, *variants])), 6)

    @override_settings(VF_MTA_PERMISSIONS_SHA256='permissions-1')
    def test_identity_changes_with_permission_catalogue_signature(self):
        payload = {'product_permissions': [1], 'location_permissions': [2]}
        resolved = (PermissionCodes({'SKU': 1}), PermissionCodes({'LOC': 1}))
        first = planning_summary.identity_value(self.receipt(), payload, 'actor', resolved)
        with override_settings(VF_MTA_PERMISSIONS_SHA256='permissions-2'):
            second = planning_summary.identity_value(self.receipt(), payload, 'actor', resolved)
        self.assertNotEqual(first, second)


class AdmissionContractTests(unittest.TestCase):
    def identities(self):
        return dict(source_digest='source', generation_digest='generation', recipe_digest='recipe',
                    business_date=date(2026, 4, 7))

    def test_missing_receipt_is_unavailable(self):
        run = SimpleNamespace(pk='run')
        manager = planning_summary.PlanningSummaryReceipt.objects
        with patch.object(planning_summary, 'binding', return_value=(self.identities(), {}, {})), \
             patch('mta.presentation.legacy_ui._no_active_filters', return_value=True), \
             patch.object(manager, 'filter') as query:
            query.return_value.first.return_value = None
            with self.assertRaisesRegex(PublicationUnavailable, 'planning_summary_generation_unavailable'):
                planning_summary.admitted(run, {})

    def test_failed_or_changed_receipt_identity_is_unavailable_without_row_read(self):
        base = self.identities()
        for status, source in (('FAILED', 'source'), ('READY', 'changed')):
            receipt = SimpleNamespace(status=status, metrics=list(planning_summary.METRICS),
                                      row_count=0, source_digest=source,
                                      generation_digest='generation', recipe_digest='recipe',
                                      business_date=date(2026, 4, 7))
            with self.subTest(status=status, source=source), \
                 patch.object(planning_summary.PlanningSummaryContribution.objects, 'filter') as rows, \
                 self.assertRaisesRegex(PublicationUnavailable, 'planning_summary_generation_unavailable'):
                planning_summary.verify(receipt, base)
            rows.assert_not_called()


if __name__ == '__main__':
    unittest.main()
