"""BPR join/filter/export distinctions; not independent SQL/browser parity."""
from copy import deepcopy
import json
import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY', 'unit-test-only-not-a-serving-secret')
import django
django.setup()
from django.test import Client

from tests import test_bpr_presentation as fixture
from mta.presentation.bpr import ReadModel
from mta.presentation.bpr_filters import BprPredicate
from mta.presentation.bpr_export import selected_headers
from mta.presentation.context import PublicationUnavailable
from mta.presentation.rrr_export import csv_chunks


class BprBatchTests(unittest.TestCase):
    def test_bpr_config_exposes_canonical_graph_tags_and_types(self):
        from mta.presentation.legacy_ui import bpr_ui_columns
        rows = bpr_ui_columns()
        self.assertEqual(len(rows),19)
        by_code = {row['Col_Code']:row for row in rows}
        self.assertEqual(by_code['dailydatagraph']['Col_Position'],99)
        self.assertEqual(by_code['tags']['Col_Position'],0)
        self.assertEqual(by_code['vn']['Col_Position'],7)
        self.assertEqual(by_code['Norm']['DataType'],'Number')
        self.assertTrue(all(row['Visible'] and 'TagID' not in row for row in rows))
        self.assertTrue(all(type(row['Visible']) is bool for row in rows))

    def setUp(self):
        setup = fixture.BprProjectionTest()
        setup.setUp()
        self.output, self.ancillary = setup.output, setup.ancillary
        self.importer = self.output['ClosingState'][0]['importer']

    def selected(self, group, *items, export=False):
        model = ReadModel(self.output, self.ancillary)
        predicate = BprPredicate({'filters': {group: {'filters': list(items)}}},
                                 self.importer['LocationAttributeData'], export=export)
        return model, predicate.select(list(model.joined(final=export)))

    @staticmethod
    def item(name, value, op='equalto', **extra):
        return dict(attributeName=name, value=value, operator=op, **extra)

    def test_availability_uses_raw_base_and_rationed_owners(self):
        # Base Norm 220 differs from rationed VirtualNorm 440.
        _, rows = self.selected('availabilityFilter', self.item('norm','220'), self.item('virtualnorm','440'))
        self.assertEqual(len(rows), 1)
        _, rows = self.selected('availabilityFilter', self.item('norm','440'))
        self.assertEqual(rows, [])

    def test_pair_predicate_does_not_use_dash_display_or_base_custom_field(self):
        self.importer['SkuLocAttributeData'] = [dict(SKUCode='337',LocCode='AG515802',c1='producer')]
        _, rows = self.selected('customAttributeFilter', self.item('SKULocAttr1','producer'))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['SKULocAttr1'], '-')
        _, rows = self.selected('customAttributeFilter', self.item('SKUAttr1','-'))
        self.assertEqual(rows, [])
        _, rows = self.selected('customAttributeFilter', self.item('SKUAttr1','', 'hasnovalue'))
        self.assertEqual(len(rows), 1)

    def test_parent_type_join_retains_duplicate_locations(self):
        self.output['BPRReports'][0]['BPR_Table'][0]['ParentWhCode'] = 'parent'
        self.importer['LocationAttributeData'] = [dict(WHCode='parent',LocationType='LDC')]*2
        _, rows = self.selected('supplyChainFilter', self.item('forChildren','LDC'))
        self.assertEqual(len(rows), 2)

    def test_tags_are_standard_owned_and_filterable(self):
        self.output['ClosingState'][0]['dbm']['SKULocStandardAttributes'][0]['Tags'] = 'Phase In'
        _, rows = self.selected('availabilityFilter', self.item('pipo,seasonality','Phase In'))
        self.assertEqual(len(rows), 1)

    def test_missing_legacy_columns_are_not_silent_zeroes(self):
        for group, item in [('availabilityFilter',self.item('category','1')),
                ('availabilityFilter',self.item('availability','1')),
                ('coverageFilter',self.item('coverage','1')),
                ('colorFilter',self.item('red','1','greaterthan',type='colorcount')),
                ('colorFilter',self.item('red','1','greaterthan',type='colorage'))]:
            with self.subTest(group=group, item=item):
                with self.assertRaisesRegex(PublicationUnavailable, 'LEG-BPR-FILTER-INVALID-SQL'):
                    self.selected(group,item)

    def test_export_has_trend_colour_count_but_no_btd_alias(self):
        self.output['BTRFinal'][0]['BufferTrendPhysicalInv'] = [dict(SKUCode='337',WhCode='AG515802',RedCount=3)]
        _, rows = self.selected('colorFilter',self.item('red','2','greaterthan',type='colorcount'),export=True)
        self.assertEqual(len(rows),1)
        with self.assertRaisesRegex(PublicationUnavailable, 'missing alias btd'):
            self.selected('colorFilter',self.item('red','2','greaterthan',type='colorage'),export=True)

    def test_export_does_not_square_key_bag_multiplicity(self):
        self.importer['SkuLocAttributeData'] = [dict(SKUCode='337',LocCode='AG515802',c1=value)
                                               for value in ('match','other')]
        model, candidates = self.selected('customAttributeFilter',self.item('SKULocAttr1','match'))
        self.assertEqual(len(model.page(candidates,1,10)),2)
        model, exported = self.selected('customAttributeFilter',self.item('SKULocAttr1','match'),export=True)
        self.assertEqual(len(model.export(exported)),1)

    def test_analytics_excludes_remark_and_trend_multipliers(self):
        self.ancillary['BPRReport_RemarkDetails'] = [dict(SKUCode='337',WhCode='AG515802',
            RemarkDate='2026-06-17',Remark=value) for value in ('first','second')]
        self.output['BTRFinal'][0]['BufferTrendPhysicalInv'] = [dict(SKUCode='337',WhCode='AG515802')]*3
        model = ReadModel(self.output,self.ancillary)
        result = model.analytics(model.candidates())[0]
        self.assertEqual((result['OnHandRed'],result['PipelineYellow']),(1,1))
        self.assertEqual(len(model.page(model.candidates(),1,10)),6)
        self.assertEqual(set(model.analytics([])[0].values()),{0})
        self.assertEqual(len(result),14)

    def test_export_layout_headers_and_csv_raw_nulls(self):
        model = ReadModel(self.output,self.ancillary)
        before = deepcopy(self.output)
        rows = model.export(list(model.joined(final=True)))
        headers = selected_headers(json.dumps({'columns':[
            {'colId':'SKUCode','hide':False}, {'colId':'Remark','hide':False},
            {'colId':'Norm','hide':True}, {'colId':'rh','hide':False}]}))
        self.assertEqual(headers,[('SKUCode','SKUCode'),('Latest Remark','Remark')])
        self.assertEqual(b''.join(csv_chunks(rows,headers)),b'SKUCode,Latest Remark\r\n337,\r\n')
        self.assertEqual(self.output,before)

    def test_http_batch_dispatch_filtering_and_export_ignore_paging(self):
        client = Client()
        payload = dict(name='BPR', reportName='BPR', paginationParameter=dict(pageNumber=9,recordsPerPage=1),
            filters={'productFilter':{'filters':[self.item('sku','337')]}})
        def post(route, authenticated=True):
            return client.post('/api/mta/'+route, json.dumps(payload), content_type='application/json',
                **({'HTTP_X_VECTORFLOW_IDENTITY':'{"id":"unit"}'} if authenticated else {}))
        with patch('mta.presentation.bpr_read.bpr_context', return_value=SimpleNamespace(
                output=self.output,ancillary=self.ancillary)), \
             patch('mta.presentation.views.scoped', side_effect=lambda rows,*a,**k:rows) as scoped, \
             patch('mta.presentation.views.selected_run',return_value=object()), \
             patch('mta.presentation.ui_state.get_layout',return_value='{"columns":[{"colId":"SKUCode"}]}'):
            self.assertEqual(post('GetBPRDataCount').json()['recordCount'],'1')
            self.assertEqual(post('GetBPRData').json()['data'],[])
            analytics = post('GetAnalyticsData')
            self.assertEqual(analytics.status_code,200)
            self.assertEqual(analytics.json()['data'][0]['OnHandRed'],1)
            export = post('GetExportDataAsync')
            self.assertEqual(export.status_code,200)
            self.assertEqual(b''.join(export.streaming_content),b'SKUCode\r\n337\r\n')
            self.assertTrue(all(call.kwargs['preserve_join_multiplicity'] for call in scoped.call_args_list))
            for route in ('GetBPRData','GetBPRDataCount','GetAnalyticsData','GetExportDataAsync'):
                self.assertEqual(post(route,False).status_code,403)
            payload['filters']['productFilter']['filters'][0]['value'] = 'absent'
            self.assertEqual(post('GetBPRDataCount').json()['recordCount'],'0')
            self.assertEqual(set(post('GetAnalyticsData').json()['data'][0].values()),{0})


if __name__ == '__main__':
    unittest.main()
