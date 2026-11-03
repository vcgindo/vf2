"""Read projections must retain publication validation and full-history fallback."""
import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY','unit-only')
import django
django.setup()
from mta.presentation import btr_calendar_images as calendar


class BtrConsumerProjectionTests(unittest.TestCase):
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
