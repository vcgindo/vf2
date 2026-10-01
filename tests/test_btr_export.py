import json
import os
import unittest
from unittest.mock import patch

os.environ.setdefault('VF_SECRET_KEY', 'unit-only')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
import django
django.setup()
from django.test import Client
from mta.presentation.btr_export import selected_headers


class BtrExportTests(unittest.TestCase):
    def dates(self):
        return [{f'D{i}': None if i == 1 else '2026-06-17' for i in range(1, 91)}]

    def test_saved_dates_null_unpivot_duplicates_and_case(self):
        layout = {'columns': [{'colId': 'D90'}, {'colId': 'SKUCode', 'pinned': 'left'},
                             {'colId': 'D1'}, {'colId': 'D90'}, {'colId': 'Norm', 'hide': True},
                             {'colId': 'd90'}, {'colId': 'unknown'}]}
        self.assertEqual(selected_headers(json.dumps(layout), self.dates()),
                         [('17-06-2026', 'D90'), ('SKUCode', 'SKUCode'), ('', 'D1'), ('17-06-2026', 'D90')])

    def test_default_keeps_ninety_days_and_empty_saved_layout(self):
        result = selected_headers('', self.dates())
        self.assertEqual([code for _, code in result if code.startswith('D')], [f'D{i}' for i in range(1, 91)])
        self.assertEqual(selected_headers('{"columns":[]}', self.dates()), [])

    def test_export_uses_actor_layout_and_ignores_payload_headers_and_page(self):
        request = dict(reportName='BTR', name='tech', Headers=[dict(Field='forged', HeaderName='forged')],
                       user={'id': 'forged'}, paginationParameter={'recordsPerPage': 1})
        with patch('mta.presentation.views.selected_run', return_value='run'), \
             patch('mta.presentation.btr_sql.read_btr', return_value=(iter([{'SKUCode': '337'}, {'SKUCode': '5328'}]), self.dates())) as read, \
             patch('mta.presentation.ui_state.get_layout', return_value='{"columns":[{"colId":"SKUCode"}]}') as layout:
            response = Client().post('/api/mta/GetExportDataAsync', request, content_type='application/json',
                                     HTTP_X_VECTORFLOW_IDENTITY='{"id":"actor"}')
            self.assertEqual(b''.join(response.streaming_content), b'SKUCode\r\n337\r\n5328\r\n')
            read.assert_called_once_with('run', request, paging=None, export=True)
            layout.assert_called_once_with('actor', 'BTRon-hand')
