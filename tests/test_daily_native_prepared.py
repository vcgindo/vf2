"""Focused contracts for the native prepared-layer writers."""
import os
import unittest
from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY', 'unit-only')
import django
django.setup()

from mta.presentation import daily_native_prepared as native
from mta.presentation.context import PublicationUnavailable


class DailyNativePreparedTests(unittest.TestCase):
    def test_dispatch_and_recipe_cover_reconciled_layers(self):
        self.assertEqual(set(native.BUILDERS),
                         {'bpr', 'guided_history', 'guided_dbm', 'guided_chronic'})
        self.assertEqual(native.production_recipe_digest('bpr'),
                         native.production_recipe_digest('bpr'))
        self.assertNotEqual(native.production_recipe_digest('bpr'),
                            native.production_recipe_digest('guided_dbm'))
        build, verify = MagicMock(return_value='build'), MagicMock(return_value='verify')
        with patch.dict(native.BUILDERS, {'bpr': (build, verify)}, clear=True):
            run = object()
            self.assertEqual(native.prepare(run, 'bpr'), 'build')
            self.assertEqual(native.prepare(run, 'bpr', verify_only=True), 'verify')
            build.assert_called_once_with(run)
            verify.assert_called_once_with(run)
            with self.assertRaisesRegex(ValueError, 'unknown_native_prepared_layer'):
                native.prepare(run, 'guided_dbm')

    def test_binding_requires_build_owner_and_initialized_native_chain(self):
        run = SimpleNamespace(pk='run')
        with patch('mta.presentation.daily_preparation.production_branch', return_value=False):
            with self.assertRaisesRegex(PublicationUnavailable,
                                        'daily_publication_build_required'):
                native._binding(run)
        with patch('mta.presentation.daily_preparation.production_branch', return_value=True), \
             patch('mta.presentation.daily_preparation.source_digest', return_value='source'), \
             patch('mta.presentation.native_publication.identity', return_value={'id': 'native'}) as identity:
            self.assertEqual(native._binding(run), 'source')
        identity.assert_called_once_with(run)

    def test_bpr_query_keeps_driving_bag_left_joins_and_source_order(self):
        tables, metadata = {}, {}
        for owner, fields in native.BPR_FIELDS.items():
            table = 'table-' + owner
            physical = []
            observed = []
            for name, kind in fields.items():
                column = 'column-' + name
                db_kind = {'text': 'nvarchar', 'bigint': 'bigint',
                           'numeric': 'numeric'}[kind]
                physical.append((column, db_kind))
                observed.append((name, column, 'unused'))
            tables[table] = physical
            metadata[native.BPR_SOURCES[owner]] = {
                'table': table, 'fields': observed, 'count': 1}
        run = SimpleNamespace(pk='run')
        with patch.object(native, 'CATALOG', {'tables': tables}), \
             patch.object(native, 'image_metadata', side_effect=lambda _r, path: metadata[path]), \
             patch.object(native, 'image_query', side_effect=lambda _r, path: ('SELECT '+path, [path])):
            query, params = native._bpr_insert_query(run)
        self.assertIn('row_number() OVER (ORDER BY A.vf_ordinal,V.vf_ordinal,S.vf_ordinal,C.vf_ordinal,D.vf_ordinal,B.vf_ordinal)-1', query)
        for owner in ('V', 'S', 'C', 'D', 'B'):
            self.assertIn(' LEFT JOIN ' + owner + ' ON ', query)
        self.assertIn('lower(rtrim(A."SKUCode"::text', query)
        self.assertEqual(params[-1], 'run')

    def test_guided_dbm_all_null_native_integer_is_not_coerced(self):
        run = SimpleNamespace(pk='run')
        item = {'table': 'dbm-a', 'count': 2,
                'fields': [('SuggestionGenerationAge', 'age', 'str')]}
        with patch.object(native, 'DBM_SOURCES', {'A': 'a'}), \
             patch.object(native, 'DBM_FIELDS', {'A': {'SuggestionGenerationAge': 'bigint'}}), \
             patch.object(native, 'CATALOG', {'tables': {'dbm-a': [('SuggestionGenerationAge', 'bigint'),
                                                                  ('age', 'bigint')]}}), \
             patch.object(native, 'image_metadata', return_value=item), \
             patch.object(native, 'image_query', return_value=('SELECT NULL', [])), \
             patch.object(native, 'image_field', return_value=[None, None]) as values:
            query, _ = native._dbm_insert_query(run)
            self.assertIn('A."SuggestionGenerationAge"', query)
            self.assertNotIn('COALESCE(A."SuggestionGenerationAge"', query)
            values.return_value = [None, '1']
            with self.assertRaisesRegex(PublicationUnavailable,
                                        'source_field_type_changed'):
                native._dbm_insert_query(run)

    def test_existing_receipt_is_verified_and_reused_without_insert(self):
        run = SimpleNamespace(pk='run')
        receipt = SimpleNamespace(source_digest='source', schema_digest='schema',
                                  row_count=2, rows_digest='rows')
        row_model = MagicMock()
        row_model.objects.filter.return_value.exists.return_value = False
        receipt_model = MagicMock()
        receipt_model.objects.filter.return_value.first.return_value = receipt
        guard = MagicMock()
        with patch.object(native.connection, 'vendor', 'postgresql'), \
             patch.object(native.transaction, 'atomic', return_value=nullcontext()), \
             patch.object(native, '_binding', return_value='source'), \
             patch.object(native, '_lock'), \
             patch.object(native, '_stream_receipt', return_value=(2, 'rows')), \
             patch('mta.presentation.daily_preparation.assert_unchanged'), \
             patch.object(native, 'production_recipe_digest', return_value='recipe'):
            result = native._single_prepare(
                run, layer='bpr', row_model=row_model, receipt_model=receipt_model,
                fields=('ordinal',), insert_query=MagicMock(), schema='schema',
                guard=guard, verify_only=True)
        self.assertEqual(result, {'status': 'PASS', 'source_digest': 'source',
            'recipe_digest': 'recipe', 'rows_digest': 'rows', 'row_count': 2,
            'created': False})
        receipt_model.objects.create.assert_not_called()
        self.assertEqual(guard.call_count, 2)


if __name__ == '__main__':
    unittest.main()
