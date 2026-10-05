"""Focused contracts for the opt-in RRR prepared-membership boundary."""
import os
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from django.test import override_settings

os.environ.setdefault('VF_SECRET_KEY', 'unit-only')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
import django
django.setup()

from mta.presentation.context import PermissionCodes, PublicationUnavailable
from mta.presentation import rrr_preparation, rrr_prepared_sql, rrr_sql


class RrrPreparedTests(unittest.TestCase):
    def setUp(self):
        prepared = override_settings(VF_RRR_PREPARED=True)
        prepared.enable()
        self.addCleanup(prepared.disable)
    def test_rrr_reader_uses_opt_in_relation_and_keeps_fallback_explicit(self):
        run = SimpleNamespace(pk='fixture', kind='LEGACY_UI_FIXTURE')
        with patch.object(rrr_prepared_sql, 'admitted_relation', return_value=('SELECT member', ['fixture'])), \
             patch.object(rrr_prepared_sql, 'read_prepared', return_value=['prepared']) as prepared, \
             patch.object(rrr_sql, 'image_rows', side_effect=AssertionError('fallback read')):
            self.assertEqual(rrr_sql.read_rrr(run, {}, paging=(1, 5)), ['prepared'])
            prepared.assert_called_once_with(run, {}, paging=(1, 5), count=False,
                                             relation='SELECT member', relation_params=['fixture'])
        with patch.object(rrr_prepared_sql, 'admitted_relation', return_value=None), \
             patch.object(rrr_sql, 'image_rows', return_value=[]), \
             patch.object(rrr_sql.hierarchy, 'selected_manifest', return_value=None), \
             patch.object(rrr_sql, 'rrr_predicate'), \
             patch.object(rrr_sql, 'scope', return_value=(PermissionCodes({'sku': 1}), PermissionCodes({'loc': 1}))), \
             patch.object(rrr_sql, 'read_pick_bands', return_value=[]):
            self.assertEqual(rrr_sql.read_rrr(run, {}, paging=(1, 5)), [])

    def test_membership_query_retains_every_exact_inner_and_left_ordinal(self):
        run = SimpleNamespace(pk='fixture')
        with patch.object(rrr_preparation, 'image_query',
                          side_effect=lambda selected, path: ('SELECT * FROM ' + path.replace('/', '_'), [path])):
            query, params = rrr_preparation.membership_query(run, 'VALUES (%s,%s)', [0, 'sku'])
        for expression in ('R.vf_ordinal', 'S.vf_ordinal', 'B.vf_ordinal',
                           'C.vf_ordinal', 'D.vf_ordinal', 'sla.vf_ordinal'):
            self.assertIn(expression, query)
        self.assertIn('LEFT JOIN B sla ON', query)
        self.assertIn('K.column1 AS "band_ordinal"', query)
        self.assertEqual(params[-2:], [0, 'sku'])

    def test_preparation_guards_distinct_positions_without_global_parentnorm_denial(self):
        cursor = MagicMock()
        cursor.fetchone.return_value = None
        with patch.object(rrr_preparation, 'image_query', return_value=('SELECT positions', ['source'])):
            rrr_preparation.validate_positions(cursor, SimpleNamespace(), 'VALUES (%s,%s,%s,%s)',
                                               [0, 'sku', 'loc', 'parent'])
        self.assertEqual(cursor.execute.call_count, 1)
        guard_sql = cursor.execute.call_args.args[0]
        self.assertIn('SELECT DISTINCT column2,column3,column4 FROM K', guard_sql)
        self.assertIn('HAVING count(R.vf_ordinal)<>1', guard_sql)
        self.assertNotIn('ParentNorm', guard_sql)
        cursor = MagicMock(); cursor.fetchone.return_value = ('bad', 'position')
        with patch.object(rrr_preparation, 'image_query', return_value=('SELECT positions', [])):
            with self.assertRaisesRegex(ValueError, 'unique produced'):
                rrr_preparation.validate_positions(cursor, SimpleNamespace(), 'VALUES (0)', [])

    def test_prepared_grid_denies_parentnorm_only_after_returned_membership(self):
        run = SimpleNamespace(pk='fixture', kind='LEGACY_UI_FIXTURE')
        cursor = MagicMock()
        cursor.description = [('ParentNorm',)]
        cursor.fetchall.return_value = [(None,)]
        attributes = {'SkuAttributeData': [], 'LocationAttributeData': []}
        with patch.object(rrr_prepared_sql, 'image_rows', side_effect=lambda run, path: attributes[path.rsplit('/', 1)[1]]), \
             patch.object(rrr_prepared_sql.hierarchy, 'selected_manifest', return_value=None), \
             patch.object(rrr_prepared_sql, 'rrr_predicate'), \
             patch.object(rrr_prepared_sql, 'scope', return_value=(PermissionCodes({'sku': 1}), PermissionCodes({'loc': 1}))), \
             patch.object(rrr_prepared_sql, 'image_query',
                          side_effect=lambda run, path: ('SELECT * FROM retained_source', [path])), \
             patch.object(rrr_prepared_sql.connection, 'cursor') as factory:
            factory.return_value.__enter__.return_value = cursor
            with self.assertRaisesRegex(ValueError, 'ParentNorm NULL conversion'):
                rrr_prepared_sql.read_prepared(
                    run, {'filters': {}}, paging=(1, 5), count=False,
                    relation='SELECT * FROM prepared WHERE run_id=%s', relation_params=['fixture'])

    def test_existing_receipt_mismatch_fails_closed_instead_of_falling_back(self):
        run = SimpleNamespace(pk='fixture', kind='LEGACY_UI_FIXTURE', business_date='2026-04-07')
        receipt = SimpleNamespace(source_digest='wrong', dimension_digest='dimension',
                                  pick_digest='pick', recipe_digest=rrr_preparation.recipe_digest())
        queryset = MagicMock(); queryset.first.return_value = receipt
        with patch.object(rrr_prepared_sql.RrrPreparedProjection.objects, 'filter', return_value=queryset), \
             patch.object(rrr_prepared_sql.fixture, 'binding', return_value=(run, 'source')), \
             patch.object(rrr_prepared_sql, 'source_signatures', return_value=('dimension', 'pick')), \
             patch.object(rrr_prepared_sql, 'verify_guards'):
            with self.assertRaisesRegex(PublicationUnavailable, 'receipt_missing_or_changed'):
                rrr_prepared_sql.admitted_relation(run)

    def test_configured_fixture_requires_receipt(self):
        run = SimpleNamespace(pk='fixture', kind='LEGACY_UI_FIXTURE', business_date='2026-04-07')
        queryset = MagicMock(); queryset.first.return_value = None
        with patch.object(rrr_prepared_sql.RrrPreparedProjection.objects, 'filter', return_value=queryset), \
             patch.object(rrr_prepared_sql.fixture, 'binding', side_effect=AssertionError('no admission work')):
            with self.assertRaisesRegex(PublicationUnavailable, 'receipt_required'):
                rrr_prepared_sql.admitted_relation(run)

    @override_settings(VF_RRR_PREPARED=False)
    def test_explicitly_disabled_reader_keeps_native_fallback_without_table_query(self):
        with patch.object(rrr_prepared_sql.RrrPreparedProjection.objects, 'filter',
                          side_effect=AssertionError('disabled preparation queried')):
            self.assertIsNone(rrr_prepared_sql.admitted_relation(SimpleNamespace(pk='fixture',kind='LEGACY_UI_FIXTURE')))

    def test_prepared_count_scopes_and_filters_at_membership_boundary(self):
        run = SimpleNamespace(pk='fixture', kind='LEGACY_UI_FIXTURE')
        cursor = MagicMock(); cursor.fetchone.return_value = (7,)
        attributes = {'SkuAttributeData': [], 'LocationAttributeData': []}
        with patch.object(rrr_prepared_sql, 'image_rows', side_effect=lambda run, path: attributes[path.rsplit('/', 1)[1]]), \
             patch.object(rrr_prepared_sql.hierarchy, 'selected_manifest', return_value=None), \
             patch.object(rrr_prepared_sql, 'rrr_predicate'), \
             patch.object(rrr_prepared_sql, 'scope', return_value=(PermissionCodes({'sku': 2}), PermissionCodes({'loc': 3}))), \
             patch.object(rrr_prepared_sql, 'image_query',
                          side_effect=lambda run, path: ('SELECT * FROM retained_source', [path])), \
             patch.object(rrr_prepared_sql.connection, 'cursor') as factory:
            factory.return_value.__enter__.return_value = cursor
            result = rrr_prepared_sql.read_prepared(
                run, {'filters': {}}, paging=(1, 5), count=True,
                relation='SELECT * FROM prepared WHERE run_id=%s', relation_params=['fixture'])
        self.assertEqual(result, 7)
        sql, params = cursor.execute.call_args.args
        self.assertIn('JOIN R ON R.vf_ordinal=H.rationed_ordinal', sql)
        self.assertIn('JOIN S ON S.vf_ordinal=A.standard_ordinal', sql)
        self.assertIn('JOIN B ON B.vf_ordinal=A.pair_ordinal', sql)
        self.assertIn('JOIN C ON C.vf_ordinal=A.sku_ordinal', sql)
        self.assertIn('JOIN D ON D.vf_ordinal=A.location_ordinal', sql)
        self.assertEqual(params.count('sku'), 2)
        self.assertEqual(params.count('loc'), 3)


if __name__ == '__main__':
    unittest.main()
