"""Read projections must retain publication validation and full-history fallback."""
import os
import unittest
from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY','unit-only')
import django
django.setup()
from mta.presentation import btr_calendar_images as calendar


class BtrConsumerProjectionTests(unittest.TestCase):
    def test_sql_requests_current_colour_only_for_a_colour_age_predicate(self):
        from mta.presentation import btr_sql,btr_reporting
        from mta.presentation.context import PermissionCodes
        for kind in (None,'colorcount','colorage'):
            payload={'name':'tech'}
            if kind:
                payload['filters']={'colorFilter':{'filters':[{'attributeName':'green','type':kind,
                                                              'operator':'greaterthan','value':'0'}]}}
            calls=[]
            def relation(run,path,**kwargs):
                calls.append((path,kwargs.get('required_fields')))
                return 'SELECT * FROM owned_test_relation',[]
            cursor=MagicMock();cursor.__enter__.return_value=cursor;cursor.fetchone.return_value=(0,)
            with patch.object(btr_reporting,'selected_generation',return_value=None), \
                    patch.object(btr_sql,'image_rows',return_value=[]), \
                    patch.object(btr_sql,'image_query',side_effect=relation), \
                    patch.object(btr_sql.hierarchy,'selected_manifest',return_value=None), \
                    patch.object(btr_sql,'scope',return_value=(PermissionCodes({'S':1}),PermissionCodes({'W':1}))), \
                    patch.object(btr_sql.connection,'cursor',return_value=cursor):
                for export in (False,True):
                    calls.clear()
                    btr_sql.read_btr(SimpleNamespace(business_date=date(2026,4,9)),payload,
                                     paging=(1,10),count=not export,export=export)
                    colours=[fields for path,fields in calls if path.startswith('closing/btr/BufferTrend')]
                    self.assertTrue(colours)
                    self.assertTrue(all(('D90' in fields)==(kind=='colorage') for fields in colours))

    def test_current_colour_only_and_scalar_counts_use_authenticated_roster(self):
        for name, fields, colour in (
                ('BPPTrendPhysicalInv', ['SKUCode','WhCode'], False),
                ('BufferTrendPhysicalInv', ['Age','D90'], True),
                ('BufferTrendDispatch', ['BlackCount','D90'], True)):
            item={'table':'BTR/'+name,'image':'closing/btr/'+name}
            run=SimpleNamespace()
            with patch('mta.presentation.btr_page_dates.roster_query',return_value=('sql',[])) as roster, \
                    patch.object(calendar,'_trend_query',side_effect=AssertionError('unneeded full history')):
                self.assertEqual(calendar.published_query(run,item,required_fields=fields),('sql',[]))
                roster.assert_called_once_with(run,item,current_colour=colour)

    def test_history_levels_and_all_fields_keep_complete_relation(self):
        for name, fields in (('BPPTrendPhysicalInv',['D90']),('BufferTrendDispatch',['D89','D90']),
                            ('BufferTrendPhysicalInv',None)):
            item={'table':'BTR/'+name,'image':'closing/btr/'+name}
            run=SimpleNamespace()
            with patch.object(calendar,'published_directory',return_value={'checked':True}) as owner, \
                    patch.object(calendar,'_trend_query',return_value=('full',[])) as full:
                self.assertEqual(calendar.published_query(run,item,required_fields=fields),('full',[]))
                owner.assert_called_once_with(run,item)
                full.assert_called_once_with(run,{'checked':True},name)

    def test_invalid_fields_fail_and_roster_does_not_bypass_owner(self):
        item={'table':'BTR/BufferTrendDispatch','image':'closing/btr/BufferTrendDispatch'}
        for fields in ([], ['foreign']):
            with self.assertRaisesRegex(ValueError,'projection fields'):
                calendar.published_query(SimpleNamespace(),item,required_fields=fields)
        with patch.object(calendar,'published_directory',side_effect=ValueError('unsealed owner')):
            with self.assertRaisesRegex(ValueError,'unsealed owner'):
                calendar.published_query(SimpleNamespace(),item,required_fields=['D90'])
