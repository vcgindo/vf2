"""Actual PostgreSQL count over the same independently qualified connector bag."""
from types import SimpleNamespace
from unittest.mock import patch

from django.db import connection
from django.test import TestCase

from mta.presentation import daily_git_count as reader
from mta.presentation.context import PublicationUnavailable
from mta.runtime.test_git_count_cases import fixture, cases


class DailyGitCountTests(TestCase):
    def test_group_grain_nulls_duplicates_and_directional_scope(self):
        data=fixture()
        paths=dict(Transporter=reader.TRANSPORTER_PATH,
            Standard='closing/dbm/SKULocStandardAttributes',
            Rationed='reports/bpr/vf_RationedReqReport',
            LocDesc='closing/importer/SiteDescriptionTbl',
            Loc='closing/importer/LocationAttributeData',
            Pair='closing/importer/SkuLocAttributeData')
        queries={}
        with connection.cursor() as cursor:
            for name, rows in data.items():
                table='counttest_'+name.lower(); fields=list(rows[0])
                cursor.execute('CREATE TEMP TABLE '+table+' ('+','.join('"'+f+'" '+('integer' if f=='Norm' else 'text') for f in fields)+') ON COMMIT DROP')
                cursor.executemany('INSERT INTO '+table+' VALUES ('+','.join(['%s']*len(fields))+')',
                                   [[row.get(f) for f in fields] for row in rows])
                queries[paths[name]]=('SELECT * FROM '+table,[])
        with patch.object(reader,'image_query',side_effect=lambda run,path:queries[path]):
            for case in cases():
                with self.subTest(case=case['id']):
                    self.assertEqual(reader.count(SimpleNamespace(),dict(filters=case.get('filters',{})),set(case['products']),
                                                  set(case['locations'])),case['expected'])

    def test_native_missing_alias_filters_fail_before_reads(self):
        with patch.object(reader,'image_query') as query, self.assertRaises(PublicationUnavailable):
            reader.count(SimpleNamespace(),dict(filters=dict(productFilter=dict(filters=[
                dict(attributeName='p1',operator='equalto',value='A')]))),{'A'},{'P'})
        query.assert_not_called()

    def test_combined_count_uses_transporter_count_but_grid_remains_native_failure(self):
        from mta.presentation import planning_git_sql as grid_reader
        class Codes(set):
            multiplicities={'A':1,'P':1}
        run=SimpleNamespace(kind='DAILY_CHAIN')
        sources=dict(git_master=('SELECT 1::bigint AS rationed_ordinal,1::bigint AS standard_ordinal,'
            "'A'::text AS \"SKUCode\",'L'::text AS \"WhCode\",'P'::text AS \"ParentWhCode\"",[]))
        occurrence={'row':('SELECT 1::bigint AS rationed_ordinal,1::bigint AS standard_ordinal',[])}
        with patch('mta.presentation.daily_preparation.production_branch',return_value=True), \
                patch.object(grid_reader,'admitted_git',return_value=occurrence), \
                patch.object(grid_reader,'admitted_sources',return_value=sources), \
                patch.object(grid_reader,'image_rows',return_value=[{'SKUCode':'A'}]), \
                patch.object(reader,'count',return_value=7) as counted:
            args=dict(resolved_scope=({},None,Codes(['A']),Codes(['P'])))
            self.assertEqual(grid_reader.grid(run,dict(type='child',filters={}),count=True,**args),
                             [dict(locationwise=1,transporterwise=7)])
            counted.assert_called_once()
            with self.assertRaisesRegex(PublicationUnavailable,'207/8120'):
                grid_reader.grid(run,dict(type='child',filters={}),**args)
