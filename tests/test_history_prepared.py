"""Boundaries for exact prepared Research and Buffer Trends memberships."""
import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY', 'unit-only')
import django
django.setup()
from django.test import override_settings

from mta.presentation import buffer_trends_sql, history_preparation, history_prepared_sql, research_read
from mta.presentation.context import PublicationUnavailable


RUN_ID = history_preparation.RUN_ID


class HistoryPreparationShapeTest(unittest.TestCase):
    def setUp(self):
        self.run = SimpleNamespace(pk=RUN_ID)
        self.image = patch.object(history_preparation, 'image_query',
                                  side_effect=lambda run, path: ('SELECT * FROM source_' + path.replace('/','_'), []))
        self.image.start()

    def tearDown(self):
        self.image.stop()

    def test_availability_has_physical_sku_location_inner_grain_without_pair(self):
        sql, params = history_preparation.availability_query(self.run)
        self.assertEqual(params, [])
        self.assertIn('FROM physical JOIN sa ON', sql)
        self.assertIn(' JOIN la ON ', sql)
        self.assertNotIn('sla', sql)
        self.assertNotIn('SkuLocAttributeData', sql)

    def test_graph_has_distinct_family_and_left_pair_occurrences(self):
        sql, params = history_preparation.graph_query(self.run)
        self.assertEqual(params, [])
        self.assertIn("'physical' AS \"family\"", sql)
        self.assertIn("'dispatch' AS \"family\"", sql)
        self.assertEqual(sql.count(' LEFT JOIN sla ON '), 2)
        self.assertEqual(sql.count(' JOIN sa ON '), 2)
        self.assertEqual(sql.count(' JOIN la ON '), 2)

    def test_research_reference_expands_exact_owner_and_parent_directions(self):
        sql, params = history_preparation.research_history_query(self.run)
        self.assertEqual(params, [])
        self.assertEqual(sql.count('SELECT DISTINCT'), 2)
        self.assertEqual(sql.count('UNION ALL'), 3)
        self.assertNotIn(' OR ', sql)
        self.assertIn('physical."WhCode"', sql)
        self.assertIn('physical."ParentWhCode"', sql)
        self.assertNotIn(' FROM R ', sql)
        self.assertIn('"SKUCode" IS NOT NULL', sql)
        self.assertIn('"WhCode" IS NOT NULL', sql)

    def test_null_only_selected_keys_return_without_invalid_values_sql(self):
        with patch.object(history_prepared_sql, 'image_metadata') as metadata, \
             patch.object(history_prepared_sql, 'image_query') as query:
            self.assertEqual(history_prepared_sql._source_rows(
                self.run, 'path', history_prepared_sql.ResearchPreparedMasterReference,
                {None}, source_field='rationed_ordinal'), [])
            metadata.assert_not_called()
            query.assert_not_called()


class HistoryPreparedAdmissionTest(unittest.TestCase):
    def setUp(self):
        self.run = SimpleNamespace(pk=RUN_ID, kind='LEGACY_UI_FIXTURE')

    @override_settings(VF_HISTORY_REPORTS_PREPARED=False)
    def test_disabled_flag_is_non_opted_fallback_without_receipt_query(self):
        with patch.object(history_prepared_sql.HistoryPreparedProjection.objects, 'filter') as query:
            query.return_value.first.return_value = None
            self.assertIsNone(history_prepared_sql.admitted(self.run))
            query.assert_not_called()

    @override_settings(VF_HISTORY_REPORTS_PREPARED=True)
    def test_enabled_flag_requires_prepared_receipt(self):
        with patch.object(history_prepared_sql.HistoryPreparedProjection.objects, 'filter') as query:
            query.return_value.first.return_value = None
            with self.assertRaisesRegex(PublicationUnavailable, 'receipt_missing_or_changed'):
                history_prepared_sql.admitted(self.run)

    @override_settings(VF_HISTORY_REPORTS_PREPARED=True)
    def test_present_non_ready_receipt_fails_closed(self):
        receipt = SimpleNamespace(status='BUILDING', source_digest='source', dimension_digest='dimensions',
                                  recipe_digest='recipe', research_master_count=0,
                                  research_history_count=0, availability_count=0, graph_count=0)
        with patch.object(history_prepared_sql.HistoryPreparedProjection.objects, 'filter') as query, \
             patch.object(history_prepared_sql.fixture, 'binding', return_value=(self.run, 'source')), \
             patch.object(history_prepared_sql, 'source_signatures', return_value='dimensions'), \
             patch.object(history_prepared_sql, 'verify_guards'), \
             patch.object(history_prepared_sql, 'recipe_digest', return_value='recipe'):
            query.return_value.first.return_value = receipt
            with self.assertRaisesRegex(PublicationUnavailable, 'receipt_missing_or_changed'):
                history_prepared_sql.admitted(self.run)

    @override_settings(VF_HISTORY_REPORTS_PREPARED=True)
    def test_ready_receipt_still_denies_run_source_recipe_and_guard_drift(self):
        receipt = SimpleNamespace(status='READY', source_digest='source',
                                  dimension_digest='dimensions', recipe_digest='recipe')
        for changed in ('run', 'source', 'dimensions', 'recipe', 'guards'):
            with self.subTest(changed=changed), \
                 patch.object(history_prepared_sql.HistoryPreparedProjection.objects, 'filter') as query, \
                 patch.object(history_prepared_sql.fixture, 'binding', return_value=(
                     SimpleNamespace(pk='wrong') if changed == 'run' else self.run,
                     'changed' if changed == 'source' else 'source')), \
                 patch.object(history_prepared_sql, 'source_signatures',
                              return_value='changed' if changed == 'dimensions' else 'dimensions'), \
                 patch.object(history_prepared_sql, 'recipe_digest',
                              return_value='changed' if changed == 'recipe' else 'recipe'), \
                 patch.object(history_prepared_sql, 'verify_guards',
                              side_effect=ValueError('changed') if changed == 'guards' else None) as guards:
                query.return_value.first.return_value = receipt
                with self.assertRaises(PublicationUnavailable):
                    history_prepared_sql.admitted(self.run)
                guards.assert_called_once()


class HistoryPreparedBranchTest(unittest.TestCase):
    def setUp(self):
        self.run = SimpleNamespace(pk=RUN_ID, kind='LEGACY_UI_FIXTURE')

    def test_selected_parent_lookup_preserves_native_history_expansion(self):
        payload = {'data': [{'SKUCode': '337', 'WhCode': 'A'}]}
        masters = [{'SKUCode': '337', 'WhCode': 'A', 'ParentWhCode': 'P'},
                   {'SKUCode': '337', 'WhCode': 'A', 'ParentWhCode': None}]
        with patch.object(history_prepared_sql, '_attributes', return_value=({}, None)), \
             patch.object(history_prepared_sql, 'scope', return_value=({'337'}, {'A'})), \
             patch.object(history_prepared_sql, '_source_rows', side_effect=[masters, [], []]) as rows, \
             patch.object(history_prepared_sql.history_native, 'research_rows', return_value=[]) as assemble:
            self.assertEqual(history_prepared_sql.read_research(self.run, payload), [])
            self.assertEqual(rows.call_args_list[0].args[3], {('337', 'a')})
            for call in rows.call_args_list[1:]:
                self.assertEqual(call.args[3], {('337', 'a'), ('337', 'p'), None})
            self.assertIs(assemble.call_args.args[1], masters)

    def test_research_and_availability_use_prepared_only_after_admission(self):
        payload = {'data':[{'SKUCode':'337','WhCode':'A'}]}
        with patch.object(history_prepared_sql, 'admitted', return_value=object()), \
             patch.object(history_prepared_sql, 'read_research', return_value=['research']) as selected, \
             patch.object(history_prepared_sql, 'read_historical_availability', return_value=['availability']) as availability:
            self.assertEqual(research_read.read_research(self.run, payload), ['research'])
            self.assertEqual(research_read.read_historical_availability(self.run, {}), ['availability'])
            selected.assert_called_once_with(self.run, payload)
            availability.assert_called_once_with(self.run, {})

    def test_buffer_graph_passes_live_filters_scope_and_dates_to_prepared_reader(self):
        attributes = {'SkuAttributeData':[], 'LocationAttributeData':[]}
        dates = [{'D90':'2026-04-07'}]
        def rows(run, path):
            return dates if path.endswith('BufferTrendDates') else attributes[path.rsplit('/',1)[1]]
        with patch.object(buffer_trends_sql, 'image_rows', side_effect=rows), \
             patch.object(buffer_trends_sql.hierarchy, 'selected_manifest', return_value=None), \
             patch.object(buffer_trends_sql, 'scope', return_value=({'337'},{'A'})), \
             patch.object(history_prepared_sql, 'admitted', return_value=object()), \
             patch.object(history_prepared_sql, 'read_graph', return_value={'prepared':True}) as prepared:
            self.assertEqual(buffer_trends_sql.read_graph(self.run, {'days':1}), {'prepared':True})
            kwargs = prepared.call_args.kwargs
            self.assertEqual(kwargs['columns'], ('D90',))
            self.assertEqual(kwargs['where'], 'TRUE')
            self.assertEqual(kwargs['attributes'], attributes)
            self.assertEqual(kwargs['dates'], dates)

    @override_settings(VF_HISTORY_REPORTS_PREPARED=True)
    def test_buffer_batches_only_named_request_images_and_keeps_live_scope(self):
        for family, history in (('eco', 'BufferTrendDispatch'), ('tech', 'BufferTrendPhysicalInv')):
            paths = ['closing/btr/' + name for name in ('SkuAttributeData', 'LocationAttributeData',
                'BufferTrendDates', 'SkuLocAttributeData', history)]
            metadata = {path: object() for path in paths}
            attributes = {'SkuAttributeData': [{'SKUCode':'x', 'SL1':None}],
                          'LocationAttributeData': [{'WHCode':'A', 'LL1':None}]}
            dates = [{'D90':'2026-04-07'}]
            def rows(run, path, *, metadata):
                self.assertIs(metadata, items[path])
                return dates if path.endswith('BufferTrendDates') else attributes[path.rsplit('/',1)[1]]
            items = metadata
            with self.subTest(family=family), \
                 patch.object(history_prepared_sql.fixture, 'image_metadata_batch', return_value=metadata) as batch, \
                 patch.object(buffer_trends_sql, 'image_rows', side_effect=rows) as images, \
                 patch.object(buffer_trends_sql.hierarchy, 'selected_manifest', return_value=None), \
                 patch.object(buffer_trends_sql, 'scope', return_value=({'x'},{'A'})) as scope, \
                 patch.object(history_prepared_sql, 'admitted', return_value=object()) as admission, \
                 patch.object(history_prepared_sql, 'read_graph', return_value={'prepared':True}) as prepared:
                payload = {'days':1, 'bufferTrendType':family}
                self.assertEqual(buffer_trends_sql.read_graph(self.run, payload), {'prepared':True})
                batch.assert_called_once_with(self.run, paths)
                self.assertEqual(images.call_count, 3)
                scope.assert_called_once_with(payload, attributes=attributes)
                admission.assert_called_once_with(self.run)
                self.assertIs(prepared.call_args.kwargs['metadata'], metadata)

    @override_settings(VF_HISTORY_REPORTS_PREPARED=True)
    def test_buffer_batch_failure_does_not_fall_back(self):
        with patch.object(history_prepared_sql.fixture, 'image_metadata_batch',
                          side_effect=PublicationUnavailable('fixture_source_manifest_changed')), \
             patch.object(buffer_trends_sql, 'image_rows') as images:
            with self.assertRaisesRegex(PublicationUnavailable, 'source_manifest_changed'):
                buffer_trends_sql.read_graph(self.run, {'days':1})
            images.assert_not_called()

    def test_prepared_graph_keeps_bare_black_or_red_precedence(self):
        captured = {}
        class Cursor:
            description = None
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def execute(self, sql, params): captured.update(sql=sql, params=params)
            def fetchall(self): return [(0, 'D90', *((0,) * 6))]
        filters = SimpleNamespace(children=[], params=['7','7'])
        class Codes(set):
            def __init__(self, value):
                super().__init__((value,)); self.multiplicities = {value:1}
        with patch.object(history_prepared_sql, 'image_query', return_value=('SELECT * FROM source', [])), \
             patch.object(history_prepared_sql, '_dimension_ctes', return_value=([], [])), \
             patch.object(history_prepared_sql.connection, 'cursor', return_value=Cursor()):
            history_prepared_sql.read_graph(self.run, {}, columns=('D90',), filters=filters,
                where='A."BlackCount">%s OR A."RedCount">%s', attributes={}, manifest=None,
                products=Codes('337'), locations=Codes('A'),
                dates=[{'D90':'2026-04-07'}])
        self.assertIn('WHERE A."BlackCount">%s OR A."RedCount">%s', captured['sql'])
        self.assertNotIn('WHERE (A."BlackCount"', captured['sql'])

    def test_grouped_empty_graph_keeps_requested_days_and_null_counts(self):
        class Cursor:
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def execute(self, *args): pass
            def fetchall(self): return []
        from mta.presentation.context import PermissionCodes
        columns = ('D89', 'D90')
        with patch.object(history_prepared_sql, 'image_query', return_value=('SELECT * FROM source', [])), \
                patch.object(history_prepared_sql, '_dimension_ctes', return_value=([], [])), \
                patch.object(history_prepared_sql.connection, 'cursor', return_value=Cursor()), \
                patch.object(history_prepared_sql.history_native, 'graph_response', side_effect=lambda rows,dates:rows):
            result = history_prepared_sql.read_graph(self.run, {}, columns=columns,
                filters=SimpleNamespace(children=[], params=[]), where='FALSE', attributes={},
                manifest=None, products=PermissionCodes({'S':1}), locations=PermissionCodes({'W':1}), dates=[])
        self.assertEqual(result, [dict(D=column, **{alias:None for alias,_ in
            history_prepared_sql.history_native.COLOURS}) for column in columns])


if __name__ == '__main__':
    unittest.main()
