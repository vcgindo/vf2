"""Bounded SQL compiler/envelope guards; retained acceptance is separate."""
import json
import os
import re
import unittest
from unittest.mock import patch
from unittest.mock import MagicMock
from types import SimpleNamespace

os.environ.setdefault('VF_SECRET_KEY','unit-only')
os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
import django
django.setup()
from django.test import Client
from mta.presentation.rrr_sql import Filters,like_pattern
from mta.presentation.rrr_filters import sql_like
from mta.presentation.context import PublicationUnavailable


class RrrSqlTest(unittest.TestCase):
    def test_fixture_removes_only_zero_offset_fences(self):
        from mta.presentation import rrr_sql
        from mta.presentation.context import PermissionCodes
        queries=[]
        band=dict(sku_code='a',location_code='x',parent_location_code='p',
            to_black='1',to_red='2',to_yellow='3',to_green='4',to_blue='5')
        for kind in ('DAILY_CHAIN','LEGACY_UI_FIXTURE'):
            cursor=MagicMock();cursor.fetchone.side_effect=[None,(7,)]
            with patch.object(rrr_sql,'image_rows',return_value=[]), \
                patch.object(rrr_sql.hierarchy,'selected_manifest',return_value=None), \
                patch.object(rrr_sql,'rrr_predicate'), \
                patch.object(rrr_sql,'scope',return_value=(PermissionCodes({'a':2}),PermissionCodes({'x':1}))), \
                patch.object(rrr_sql,'read_pick_bands',return_value=[band,band]), \
                patch.object(rrr_sql,'image_query',side_effect=lambda r,p:('SELECT * FROM retained_relation',['run',p])), \
                patch.object(rrr_sql.connection,'cursor') as factory:
                factory.return_value.__enter__.return_value=cursor
                self.assertEqual(rrr_sql.read_rrr(SimpleNamespace(kind=kind),{},paging=(1,5),count=True),7)
            queries.append(cursor.execute.call_args_list)
        self.assertEqual(queries[0][0],queries[1][0])
        before,after=(items[1].args for items in queries)
        self.assertEqual(before[0].count(' OFFSET 0'),5)
        expected=before[0].replace(' OFFSET 0','').replace(' AS MATERIALIZED (',' AS (')
        self.assertEqual(expected,after[0].replace(' AS NOT MATERIALIZED (',' AS ('))
        self.assertEqual(before[1],after[1])

    def test_like_patterns_match_retained_evaluator(self):
        for pattern in ('%Leaf%','B%','[Pp]ro_uct','%Other','[%]','a_b','%'):
            for value in ('B1 Product','Leaf','Leaf  ','Other','%','a_b','acb'):
                self.assertEqual(re.fullmatch(like_pattern(pattern),value,re.I|re.S) is not None,sql_like(value,pattern))

    def test_values_are_parameters_columns_are_allowlisted(self):
        value="Leaf'); DROP TABLE bad; --"
        compiler=Filters({'filters':{'productFilter':{'filters':[
            dict(attributeName='p3',operator='equalto',value=value)]}}})
        query=compiler.compile()
        self.assertNotIn(value,query)
        self.assertEqual(compiler.params,[value])
        with self.assertRaises(PublicationUnavailable): compiler.column('C','SL1; DROP TABLE bad')

    def test_rrr_route_never_calls_full_publication(self):
        client=Client(); payload={'paginationParameter':{'pageNumber':2,'recordsPerPage':7}}
        with patch('mta.presentation.views.selected_run',return_value='explicit-run'), \
             patch('mta.presentation.views.publication',side_effect=AssertionError('whole-run read')), \
             patch('mta.presentation.rrr_sql.read_rrr',return_value=14) as read:
            response=client.post('/api/mta/RRRDataCount',json.dumps(payload),content_type='application/json',
                HTTP_X_VECTORFLOW_IDENTITY='{"id":"unit"}')
            self.assertEqual(response.json()['recordCount'],'14')
            read.assert_called_once_with('explicit-run',payload,paging=(2,7),count=True)
            read.reset_mock()
            self.assertEqual(client.post('/api/mta/RRRDataCount','{}',content_type='application/json').status_code,403)
            read.assert_not_called()
