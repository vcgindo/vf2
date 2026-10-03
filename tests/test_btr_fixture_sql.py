"""Fixture planner choices must leave normal BTR predicates and bags intact."""
import os
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

os.environ.setdefault('VF_SECRET_KEY', 'unit-only')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
import django
django.setup()
from mta.presentation import btr_sql
from mta.presentation.context import PermissionCodes


class BtrFixtureSqlTests(unittest.TestCase):
    def test_fixture_only_planner_controls_preserve_count_query(self):
        queries=[]
        for kind in ('DAILY_CHAIN', 'LEGACY_UI_FIXTURE'):
            fixture=kind=='LEGACY_UI_FIXTURE'
            cursor=MagicMock()
            cursor.fetchone.side_effect=[('on',),(7,),('on',),(7,)] if fixture else [(7,),(7,)]
            with patch.object(btr_sql,'image_rows',return_value=[]), \
                patch.object(btr_sql.hierarchy,'selected_manifest',return_value=None), \
                patch.object(btr_sql,'BtrPredicate'), \
                patch.object(btr_sql,'scope',return_value=(PermissionCodes({'a':2}),PermissionCodes({'x':1}))), \
                patch.object(btr_sql,'image_query',side_effect=lambda r,p:('SELECT * FROM retained_relation',['run',p])), \
                patch.object(btr_sql.transaction,'atomic'), \
                patch.object(btr_sql.connection,'cursor') as factory:
                factory.return_value.__enter__.return_value=cursor
                result=btr_sql.read_btr(SimpleNamespace(kind=kind,business_date=SimpleNamespace(isoformat=lambda:'2026-04-07')),{},paging=(1,5),count=True)
                self.assertEqual(result,{'TechCount':'7','EcoCount':'7'})
            calls=[call.args for call in cursor.execute.call_args_list]
            queries.append([args for args in calls if args[0].startswith('WITH ')])
            self.assertEqual(sum(args[0]=='SET LOCAL enable_nestloop = off' for args in calls),2 if fixture else 0)
            self.assertEqual(sum(args[0].startswith('SELECT set_config') for args in calls),2 if fixture else 0)
        for before,after in zip(*queries):
            self.assertEqual(before[0],after[0].replace(' AS NOT MATERIALIZED (',' AS ('))
            self.assertEqual(before[1],after[1])
