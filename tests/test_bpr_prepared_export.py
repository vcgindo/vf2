"""Prepared BPR export dispatch, SQL boundary and bounded iterator contracts.

PostgreSQL value/order differential coverage lives in test_bpr_prepared; these
unit tests do not claim to execute the generated PostgreSQL query.
"""
from contextlib import contextmanager
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
import json
import os
import unittest

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY', 'unit-only')
import django
django.setup()
from django.test import Client, override_settings

from mta.presentation import bpr_prepared as prepared
from mta.presentation.bpr import ReadModel
from mta.presentation.bpr_export import selected_headers
from mta.presentation.bpr_filters import BprPredicate
from mta.presentation.context import PermissionCodes
from mta.presentation.rrr_export import csv_chunks
from tests import test_bpr_presentation as fixture


class PreparedExportTests(unittest.TestCase):
    def setUp(self):
        source = fixture.BprProjectionTest()
        source.setUp()
        self.output, self.ancillary = source.output, source.ancillary
        self.importer = self.output['ClosingState'][0]['importer']

    def test_export_is_final_bag_without_key_selection_or_pagination(self):
        payload = {'paginationParameter': {'pageNumber': 999, 'recordsPerPage': 1},
            'filters': {'colorFilter': {'filters': [dict(attributeName='black/red',
                operator='greaterthan', value='2', type='colorcount')]}}}
        with patch.object(prepared, '_prepared_query', return_value=('SELECT * FROM retained', ['prepared'])), \
             patch.object(prepared, 'image_query', return_value=('SELECT * FROM trend', ['trend'])), \
             patch.object(prepared, 'scope', return_value=(PermissionCodes({'337': 2}), PermissionCodes({'AG515802': 3}))):
            query, values = prepared._build(SimpleNamespace(pk='run'), payload, self.importer,
                                            self.ancillary, paging=(999, 1), export=True)
        self.assertIn(' FROM prepared R JOIN P ', query)
        self.assertIn('LEFT JOIN latest_remarks RM', query)
        self.assertIn('LEFT JOIN T ON', query)
        self.assertIn('T."BlackCount"::numeric>%s', query)
        self.assertIn('T."RedCount"::numeric>%s', query)
        self.assertNotIn('selected_counts', query)
        self.assertNotIn('generate_series', query)
        self.assertNotIn(' LIMIT ', query)
        self.assertNotIn(' OFFSET ', query)
        self.assertEqual(values[:6], ['prepared', '337', '337', 'AG515802', 'AG515802', 'AG515802'])
        self.assertEqual(values[6], 'trend')
        self.assertEqual(values[-2:], [2, 2])
        self.assertIn('NULLIF(R."v_physicalinventorypen",-99999999.00) DESC NULLS LAST', query)
        self.assertTrue(query.endswith('RM.ordinal,T.vf_ordinal'))

    def test_export_only_predicates_retain_canonical_failure_boundaries(self):
        payload = {'filters': {'colorFilter': {'filters': [dict(attributeName='Red',
            operator='greaterthan', value='2', type='colorcount')]}}}
        BprPredicate(payload, [], export=True)
        with self.assertRaisesRegex(ValueError, 'missing column'):
            BprPredicate(payload, [])
        payload['filters']['colorFilter']['filters'][0]['type'] = 'colorage'
        with self.assertRaisesRegex(ValueError, 'missing alias btd'):
            BprPredicate(payload, [], export=True)

    def test_canonical_export_parent_predicate_is_a_multiplicity_not_a_boolean(self):
        from mta.presentation.views import bpr_selected
        self.output['BPRReports'][0]['BPR_Table'][0]['ParentWhCode'] = 'parent'
        self.importer['LocationAttributeData'] = [dict(WHCode='parent', LocationType='LDC')]*2
        payload = {'filters': {'supplyChainFilter': {'filters': [
            dict(attributeName='forChildren', value='LDC')]}}}
        with patch('mta.presentation.bpr_read.bpr_context', return_value=SimpleNamespace(
                run=SimpleNamespace(kind='LEGACY_UI_FIXTURE'), output=self.output, ancillary=self.ancillary)), \
             patch('mta.presentation.views.scope', return_value=(
                PermissionCodes({'337': 1}), PermissionCodes({'AG515802': 1}))):
            model, selected = bpr_selected(payload, mode='export')
        self.assertEqual(len(model.export(selected)), 2)

    def test_primed_batches_match_complete_oracle_csv_and_close_on_exhaustion(self):
        self.importer['SkuLocAttributeData'] = [dict(SKUCode='337', LocCode='AG515802')]*2
        self.ancillary['BPRReport_RemarkDetails'] = [dict(SKUCode='337', WhCode='AG515802',
            RemarkDate='2026-04-07T12:00:00', Remark=value) for value in ('first', 'tied')]
        model = ReadModel(self.output, self.ancillary)
        expected = model.export(list(model.joined(final=True))) * 151
        names = list(expected[0])
        records = [tuple(row[name] for name in names) for row in expected]
        cursor = MagicMock()
        cursor.description = [(name,) for name in names]
        cursor.fetchmany.side_effect = [records[:500], records[500:], []]
        connection = MagicMock()
        connection.cursor.return_value.__enter__.return_value.fetchone.return_value = ('on',)
        connection.chunked_cursor.return_value.__enter__.return_value = cursor
        events = []
        @contextmanager
        def verification(_run):
            events.append('enter')
            try:
                yield
            finally:
                events.append('exit')
        with patch.object(prepared, 'connection', connection), patch.object(prepared.transaction, 'atomic'), \
             patch('mta.presentation.report_verification.verification_scope', verification):
            rows = prepared._primed_export(prepared._export_rows('run', 'SELECT export', [], {}, False))
            self.assertEqual(events, ['enter'])
            self.assertEqual(cursor.fetchmany.call_count, 1)
            layout = json.dumps({'columns': [{'colId': 'SKUCode'}, {'colId': 'Remark'}]})
            headers = selected_headers(layout)
            self.assertEqual(b''.join(csv_chunks(rows, headers)), b''.join(csv_chunks(expected, headers)))
            self.assertEqual(events, ['enter', 'exit'])
            self.assertEqual(cursor.fetchmany.call_args_list, [unittest.mock.call(500)]*3)
            cursor.fetchall.assert_not_called()
            connection.chunked_cursor.return_value.__exit__.assert_called_once()

    def test_close_before_consumption_closes_the_primed_cursor_and_verification(self):
        closed = []
        def source():
            try:
                yield {'row': 1}
                yield {'row': 2}
            finally:
                closed.append(True)
        rows = prepared._primed_export(source())
        rows.close()
        rows.close()
        self.assertEqual(closed, [True])
        self.assertEqual(list(rows), [])

    def test_close_releases_cursor_transaction_and_verification_before_first_csv_chunk(self):
        cursor = MagicMock()
        cursor.description = [('SKUCode',)]
        cursor.fetchmany.return_value = [('first',), ('second',)]
        connection = MagicMock()
        connection.cursor.return_value.__enter__.return_value.fetchone.return_value = ('on',)
        connection.chunked_cursor.return_value.__enter__.return_value = cursor
        events = []
        @contextmanager
        def verification(_run):
            events.append('enter')
            try:
                yield
            finally:
                events.append('exit')
        with patch.object(prepared, 'connection', connection), \
             patch.object(prepared.transaction, 'atomic') as atomic, \
             patch('mta.presentation.report_verification.verification_scope', verification):
            rows = prepared._primed_export(prepared._export_rows('run', 'SELECT export', [], {}, False))
            self.assertEqual(events, ['enter'])
            rows.close()
            rows.close()
            self.assertEqual(events, ['enter', 'exit'])
            self.assertEqual(cursor.fetchmany.call_count, 1)
            connection.chunked_cursor.return_value.__exit__.assert_called_once()
            atomic.return_value.__exit__.assert_called_once()

    @override_settings(VF_MTA_DAILY_PUBLICATION=True)
    def test_export_rejects_changed_receipt_before_opening_query_cursor(self):
        run = SimpleNamespace(pk='run', kind='DAILY_CHAIN')
        with patch('mta.presentation.daily_preparation.production_branch', return_value=True), \
             patch('mta.presentation.selective.image_rows', return_value=[]), \
             patch('mta.presentation.hierarchy.selected_manifest', return_value=None), \
             patch('mta.presentation.daily_preparation.source_digest', return_value='accepted'), \
             patch('mta.presentation.daily_preparation.ancillary_rows', return_value=self.ancillary), \
             patch('mta.presentation.logistics_live.serving_transit_rows', return_value=[]), \
             patch.object(prepared.BprPreparedProjection.objects, 'filter') as receipt, \
             patch.object(prepared, '_export_rows') as stream:
            receipt.return_value.first.return_value = SimpleNamespace(source_digest='changed')
            with self.assertRaisesRegex(ValueError, 'receipt_missing_or_changed'):
                prepared.read_bpr(run, {}, export=True)
            stream.assert_not_called()

    def test_priming_surfaces_query_failure_before_http_stream_construction(self):
        def source():
            raise ValueError('query failed')
            yield
        with self.assertRaisesRegex(ValueError, 'query failed'):
            prepared._primed_export(source())

    def test_export_validation_and_iteration_share_one_live_verification_scope(self):
        events = []
        @contextmanager
        def verification(_run):
            events.append('enter')
            try:
                yield
            finally:
                events.append('exit')
        def validate(*args, **kwargs):
            self.assertEqual(events, ['enter'])
            events.append('validate')
            def rows():
                try:
                    events.append('fetch')
                    yield {'SKUCode': 'first'}
                    yield {'SKUCode': 'second'}
                finally:
                    events.append('cursor-close')
            return rows()
        with patch('mta.presentation.report_verification.verification_scope', verification), \
             patch.object(prepared, '_read_bpr', side_effect=validate):
            rows = prepared.read_bpr('run', {}, export=True)
            self.assertEqual(events, ['enter', 'validate', 'fetch'])
            rows.close()
            self.assertEqual(events, ['enter', 'validate', 'fetch', 'cursor-close', 'exit'])

    @override_settings(VF_BPR_PREPARED=True)
    def test_native_export_keeps_layout_full_rows_and_closes_before_first_chunk(self):
        model = ReadModel(self.output, self.ancillary)
        expected = model.export(list(model.joined(final=True)))
        layout = json.dumps({'columns': [{'colId': 'SKUCode'}, {'colId': 'Remark'}]})
        payload = {'reportName': 'BPR', 'paginationParameter': {'pageNumber': 99, 'recordsPerPage': 1}}
        for consume in (True, False):
            closed = []
            def source():
                try:
                    yield from deepcopy(expected)
                finally:
                    closed.append(True)
            rows = prepared._primed_export(source())
            with patch('mta.presentation.native_publication.enabled', return_value=True), \
                 patch('mta.presentation.views.selected_run', return_value='run'), \
                 patch('mta.presentation.ui_state.get_layout', return_value=layout), \
                 patch.object(prepared, 'read_bpr', return_value=rows) as read, \
                 patch('mta.presentation.views.bpr_selected', side_effect=AssertionError('old full read')):
                response = Client().post('/api/mta/GetExportDataAsync', json.dumps(payload),
                    content_type='application/json', HTTP_X_VECTORFLOW_IDENTITY='{"id":"unit"}')
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response['Content-Disposition'], 'attachment')
                read.assert_called_once_with('run', payload, export=True)
                if consume:
                    self.assertEqual(b''.join(response.streaming_content),
                                     b''.join(csv_chunks(expected, selected_headers(layout))))
                response.close()
            self.assertEqual(closed, [True])


if __name__ == '__main__':
    unittest.main()
