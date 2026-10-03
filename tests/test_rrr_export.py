import json
import os
import unittest
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault('VF_SECRET_KEY','unit-only')
os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
import django
django.setup()
from django.test import Client
from mta.presentation.rrr_export import csv_chunks, selected_headers


class RrrExportTest(unittest.TestCase):
    def test_deployed_csvhelper_escaping_and_types(self):
        # Witness captured from deployed CsvHelper.dll20101c39...; no BOM,
        # CRLF, leading/trailing spaces quoted, decimal scale retained.
        rows=[{'a':' spaces ','b':'a,b'},{'a':'say "hi"','b':'x\ny'},
              {'a':Decimal('3.0000'),'b':3.0},{'a':True,'b':None}]
        value=b''.join(csv_chunks(rows,[('head','a'),('head2','b')]))
        self.assertEqual(value,b'head,head2\r\n" spaces ","a,b"\r\n"say ""hi""","x\ny"\r\n3.0000,3\r\nTrue,\r\n')
        self.assertEqual(b''.join(csv_chunks([{}],[])),b'\r\n\r\n')

    def test_saved_order_hiding_duplicates_and_exact_field_case(self):
        layout=json.dumps({'columns':[{'colId':'SKUName'}, {'colId':'SKUCode','pinned':'left'},
            {'colId':'Norm','hide':True},{'colId':'skuName'}, {'colId':'SKUName'},
            {'colId':'unknown'},{'colId':'WhCode','hide':None}]})
        self.assertEqual(selected_headers(layout,('SKUName','SKUCode','WhCode')),
            [('SKUName','SKUName'),('SKUCode','SKUCode'),('SKUName','SKUName'),('To Location','WhCode')])

    def test_invalid_layout_falls_back_valid_empty_layout_does_not(self):
        self.assertEqual(selected_headers('bad-json',('SKUCode',)),[('SKUCode','SKUCode')])
        self.assertEqual(selected_headers('{"columns":[]}',('SKUCode',)),[])

    def test_export_ignores_grid_pagination_uses_gateway_identity(self):
        client=Client()
        payload={'reportName':'RRR','paginationParameter':{'recordsPerPage':1},'user':{'id':'forged'}}
        with patch('mta.presentation.views.selected_run',return_value='selected-run'), \
             patch('mta.presentation.rrr_sql.read_rrr',return_value=[{'SKUCode':'337'},{'SKUCode':'6408'}]) as read, \
             patch('mta.presentation.ui_state.get_layout',return_value='{"columns":[{"colId":"SKUCode"}]}') as layout:
            response=client.post('/api/mta/GetExportDataAsync',json.dumps(payload),content_type='application/json',
                HTTP_X_VECTORFLOW_IDENTITY='{"id":"authenticated"}')
            self.assertEqual(response.status_code,200)
            self.assertEqual(response['Content-Type'],'text/csv')
            self.assertEqual(response['Content-Disposition'],'attachment')
            self.assertEqual(b''.join(response.streaming_content),b'SKUCode\r\n337\r\n6408\r\n')
            read.assert_called_once_with('selected-run',payload,paging=None)
            layout.assert_called_once_with('authenticated','RRR')
        self.assertEqual(client.post('/api/mta/GetExportDataAsync','{}',content_type='application/json').status_code,403)

    def test_no_fallback_for_other_export_family(self):
        response=Client().post('/api/mta/GetExportDataAsync',json.dumps({'reportName':'BOR'}),
            content_type='application/json',HTTP_X_VECTORFLOW_IDENTITY='{"id":"authenticated"}')
        self.assertEqual(response.status_code,503)
        self.assertEqual(response.json()['error'],'selected_report_export_not_connected')
