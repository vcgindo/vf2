"""HTTP adapter unit checks, not synthetic-engine or legacy-parity evidence."""
from datetime import date
import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

os.environ.setdefault('VF_SECRET_KEY', 'test-only-not-a-serving-credential')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
import django
django.setup()
from django.test import Client, override_settings
from mta.presentation.context import PublicationUnavailable, publication, scope
from mta.presentation.permissions import PermissionCodes

IDENTITY = {'HTTP_X_VECTORFLOW_IDENTITY': '{"id":1,"name":"unit-client"}'}
CATALOGUE = {
    'products': {'records': [dict(id=71001,level_1='B1 Product',level_2=None,level_3=None),
        dict(id=71002,level_1='B1 Product',level_2='Selected',level_3='Leaf')],
        'attributes': [dict(code='337',level_1='B1 Product',level_2='Selected',level_3='Leaf')]},
    'locations': {'records': [dict(id=72001,level_1='B1 Location',level_2=None,level_3=None),
        dict(id=72003,level_1='B1 Location',level_2='Receiving',level_3='Leaf')],
        'attributes': [dict(code='AG515802',level_1='B1 Location',level_2='Receiving',level_3='Leaf')]},
}
ATTRIBUTES = {
    'SkuAttributeData':[dict(SKUCode='337',SL1='B1 Product',SL2='Selected',SL3='Leaf')],
    'LocationAttributeData':[dict(WHCode='AG515802',LL1='B1 Location',LL2='Receiving',LL3='Leaf')],
}


class PresentationTest(unittest.TestCase):
    def test_location_types_preserves_deployed_text_distinct_and_null_rule(self):
        context = SimpleNamespace(output={'ClosingState':[{'importer':{'LocationAttributeData':[
            {'LocationType':'Depot'}, {'LocationType':None}, {'LocationType':''}, {'LocationType':'Depot'}
        ]}}]})
        with patch('mta.presentation.views.selected_run', return_value=object()) as load, \
             patch('mta.presentation.selective.image_field', return_value=['Depot',None,'','Depot']), \
             patch('mta.presentation.views.publication', side_effect=AssertionError('metadata must not reconstruct publication')):
            self.assertEqual(self.client.get('/api/mta/LocationType').status_code,403)
            load.assert_not_called()
            response = self.client.get('/api/mta/LocationType', **IDENTITY)
            self.assertEqual(response.status_code,200)
            self.assertEqual(response.json()['data'],'[{"lt":"Depot"},{"lt":""}]')
        context.output['ClosingState'][0]['importer']['LocationAttributeData']=[]
        with patch('mta.presentation.views.selected_run', return_value=object()), \
             patch('mta.presentation.selective.image_field', return_value=[]):
            self.assertEqual(self.client.get('/api/mta/LocationType', **IDENTITY).json()['data'],'[]')

    def setUp(self):
        self.client = Client()

    def post(self, path, payload, **headers):
        return self.client.post('/api/mta/' + path, json.dumps(payload), content_type='application/json', **headers)

    def test_no_gateway_identity_reaches_no_publication(self):
        with patch('mta.presentation.views.publication', side_effect=AssertionError('must not read')):
            for path in ('DBMData','DBMDataCount','GetBTRData','GetBTRDataCount','DailyDataGraph'):
                self.assertEqual(self.post(path, {}).status_code, 403)
            self.assertEqual(self.post('DBMData', {}, HTTP_X_VECTORFLOW_IDENTITY='[]').status_code, 403)

    def test_insight_wire_nulls_and_chronic_numbers_after_scope(self):
        context=SimpleNamespace(state=ATTRIBUTES, dbm={}, nms=[])
        payload=dict(product_permissions=[71001],location_permissions=[72001])
        row=dict(SKUCode='337',WHCode='AG515802',skucode='337',PhysicalInventoryPen='100.00',
            PipelineInventoryPen='66.67',RLT=3,skudesc=None)
        with patch('mta.presentation.insight_read.insight_context',return_value=context), \
             patch('mta.presentation.context.permission_catalogue',return_value=CATALOGUE), \
             patch('mta.presentation.views.insights.chronic_grid',return_value=[row]), \
             patch('mta.presentation.views.insights.joined_rows',return_value=[]):
            response=self.post('ChronicUnavailabilityGridViewData',payload,**IDENTITY)
            self.assertEqual(response.status_code,200)
            self.assertEqual(response.json()['data'],[dict(skucode='337',PhysicalInventoryPen=100.0,
                PipelineInventoryPen=66.67,RLT=3)])
            self.assertIsNone(self.post('DBMNormSuggestionPie',payload,**IDENTITY).json()['data'])
            payload['product_permissions']=[]
            self.assertIsNone(self.post('ChronicUnavailabilityGridViewData',payload,**IDENTITY).json()['data'])

    def test_history_routes_use_selected_readers_without_whole_publication(self):
        run = object()
        payload = dict(product_permissions=[71001], location_permissions=[72001],
                       data=[dict(SKUCode='337', WhCode='AG515802')])
        with patch('mta.presentation.views.selected_run', return_value=run), \
             patch('mta.presentation.views.publication', side_effect=AssertionError('whole publication')), \
             patch('mta.presentation.research_read.read_research', return_value=[{'Type':'Parent'}]) as research, \
             patch('mta.presentation.research_read.read_historical_availability', return_value=[{'availability_01_30':0}]) as historical:
            self.assertEqual(self.post('GetResearchInsightData', payload, **IDENTITY).json()['data'], [{'Type':'Parent'}])
            research.assert_called_once_with(run, payload)
            response = self.client.generic('GET', '/api/mta/GetHistroricalAvailabilityBPRData', json.dumps(payload),
                                           content_type='application/json', **IDENTITY)
            self.assertEqual(response.json()['data'], [{'availability_01_30':0}])
            historical.assert_called_once_with(run, payload)

    def test_graph_uses_explicit_selected_run_without_whole_publication(self):
        run = object()
        payload = dict(product_permissions=[71001], location_permissions=[72001], days=12,
                       bufferTrendType='eco', filters={'productFilter': {'filters': []}})
        with patch('mta.presentation.views.publication', side_effect=AssertionError('whole publication forbidden')), \
             patch('mta.presentation.views.selected_run', return_value=run), \
             patch('mta.presentation.buffer_trends_sql.read_graph', return_value={'native':'graph'}) as graph:
            response = self.post('GetBufferTrendGraphData', payload, **IDENTITY)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()['data'], {'native':'graph'})
            graph.assert_called_once_with(run, payload)

    def test_missing_publication_never_chooses_latest_run(self):
        with override_settings(VF_MTA_PUBLISHED_RUN='', VF_MTA_PUBLISHED_DIGEST=''):
            with patch('mta.presentation.context.CalculationRun.objects.filter', side_effect=AssertionError('no latest')):
                with self.assertRaisesRegex(PublicationUnavailable, 'explicit_publication_identity_required'):
                    publication()

    def test_method_body_and_config_contracts(self):
        self.assertEqual(self.client.get('/api/mta/DBMData', **IDENTITY).status_code, 405)
        self.assertEqual(self.post('DBMData', [], **IDENTITY).status_code, 400)
        response = self.client.get('/api/mta/GetUIConfig?reportName=NormSuggestion', **IDENTITY)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.json()), {'recordCount','data','status','msg','errorCount','error','conflictErrorCount','conflictError'})
        self.assertTrue(any(row['Col_Code'] == 'NewNormValue' for row in response.json()['data']))

    def test_explicit_permission_expansion_and_missing_scope_denial(self):
        with patch('mta.presentation.context.permission_catalogue', return_value=CATALOGUE):
            products, locations = scope(dict(product_permissions=[71001],location_permissions=[72001]), attributes=ATTRIBUTES)
            self.assertEqual(products, {'337'})
            self.assertEqual(locations, {'AG515802'})
            self.assertEqual(scope({},attributes=ATTRIBUTES), (set(),set()))
            with self.assertRaises(PublicationUnavailable):
                scope(dict(product_permissions=[999],location_permissions=[72001]),attributes=ATTRIBUTES)
            with self.assertRaises(ValueError):
                scope(dict(product_permissions=[True],location_permissions=[72001]),attributes=ATTRIBUTES)

    def test_historical_permission_memberships_do_not_override_produced_nulls(self):
        from copy import deepcopy
        produced = deepcopy(ATTRIBUTES)
        produced['SkuAttributeData'][0]['SL1'] = None
        with patch('mta.presentation.context.permission_catalogue', return_value=CATALOGUE):
            products, locations = scope(dict(product_permissions=[71001],location_permissions=[72001]),attributes=produced)
            self.assertEqual(products,set())
            self.assertEqual(locations,{'AG515802'})
            self.assertEqual(CATALOGUE['products']['attributes'][0]['code'],'337')

    def test_grid_count_scope_pagination_and_duplicate_multiplicity(self):
        rows = [dict(SKUCode='337',LocCode='AG515802',LocName='',PWhCode='',RN=i,NewNormValue='220')
                for i in (1,2)]
        rows.append(dict(SKUCode='5328',LocCode='AG515802',LocName='',PWhCode='',RN=3,NewNormValue='220'))
        payload = dict(product_permissions=[71001], location_permissions=[72001],
                       paginationParameter=dict(pageNumber=2,recordsPerPage=1))
        # Canonical DBM CTES own these attributes; Importer is deliberately empty.
        with patch('mta.presentation.views.dbm_context', return_value=SimpleNamespace(dbm=ATTRIBUTES,
             output={'ClosingState':[{'importer':{}}]})), \
             patch('mta.presentation.views.dbm_rows', return_value=rows), \
             patch('mta.presentation.context.permission_catalogue', return_value=CATALOGUE):
            count = self.post('DBMDataCount', payload, **IDENTITY).json()
            grid = self.post('DBMData', payload, **IDENTITY).json()
            self.assertEqual(count['recordCount'], '2')
            self.assertEqual(len(grid['data']), 1)
            self.assertEqual(grid['data'][0]['RN'], 2)
            self.assertEqual(grid['data'][0]['NewNormValue'], '220')
            self.assertNotIn('WHCode', grid['data'][0])
            # Deployed GetDBMData scalar FOR JSON maps an empty result to NULL.
            self.assertIsNone(self.post('DBMData', {}, **IDENTITY).json()['data'])

    def test_history_forbidden_pair_is_not_loaded(self):
        with patch('mta.presentation.context.permission_catalogue', return_value=CATALOGUE), \
             patch('mta.presentation.views.dbm_context', side_effect=AssertionError('denied')):
            response = self.post('DailyDataGraph', dict(SKUCode='337',WHCode='AG515802'), **IDENTITY)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()['data'], [])

    def test_history_authorized_pair_uses_own_graph_and_unmodified_envelope(self):
        context=SimpleNamespace(dbm={'own':'committed-state'},output={'ClosingState':[{'importer':ATTRIBUTES}]})
        graph=[dict(StockData=[dict(stk=1,dt='2026-06-17',git=None)],NormData=[],MasterData=[],
            MonitoringData=[],NormChangeHistoryData=[],SuggestionHistoryData=[],RunDate='2026-06-17',horizonValue=90)]
        payload=dict(SKUCode='337',WHCode='AG515802',product_permissions=[71001],location_permissions=[72001])
        with patch('mta.presentation.context.permission_catalogue',return_value=CATALOGUE), \
             patch('mta.presentation.views.dbm_context',return_value=context), \
             patch('mta.presentation.views.daily_graph',return_value=graph) as read:
            result=self.post('DailyDataGraph',payload,**IDENTITY)
            self.assertEqual(result.status_code,200); self.assertEqual(result.json()['data'],graph)
            read.assert_called_once_with(context.dbm,'337','AG515802')
            read.reset_mock(); payload['WHCode']='FORBIDDEN'
            self.assertEqual(self.post('DailyDataGraph',payload,**IDENTITY).json()['data'],[])
            read.assert_not_called()

    def test_last_date_is_explicit_selected_business_date(self):
        with patch('mta.presentation.views.selected_run', return_value=SimpleNamespace(business_date=date(2026,6,17))), \
             patch('mta.presentation.views.publication', side_effect=AssertionError('date must not reconstruct publication')):
            self.assertEqual(self.client.get('/api/mta/GetLastRunDate', **IDENTITY).json()['data'],
                             [dict(formatted='17 Jun 2026',rawDate='2026-06-17')])

    def test_imported_consumers_keep_registered_bytes_or_proven_adaptation(self):
        root = Path(__file__).resolve().parents[1]
        manifest = json.loads((root/'baseline/consumer-reuse.json').read_text())
        adaptations = manifest.get('accepted_adaptations', {})
        self.assertEqual(set(adaptations), {'mta/presentation/btr.py', 'mta/presentation/dbm.py',
                                           'mta/presentation/insights.py', 'mta/presentation/legacy_ui.py'})
        for name, expected in manifest['outputs'].items():
            if name in adaptations:
                record = adaptations[name]
                self.assertEqual(record['from_sha256'], expected, name)
                report = {'mta/presentation/btr.py': 'BTR', 'mta/presentation/dbm.py': 'DBM',
                          'mta/presentation/insights.py': 'Guided',
                          'mta/presentation/legacy_ui.py': 'Guided'}[name]
                self.assertTrue(record['scope'].startswith('F3.2 ' + report), name)
                self.assertEqual(len(record['evidence_sha256']), 64, name)
                expected_acceptance = ('PASS_CANONICAL_CHRONIC_CONFIG' if name.endswith('/legacy_ui.py') else
                                       'PASS_PROJECTED_SCOPED_FILTER_VALUES' if report == 'Guided'
                                       else 'PASS_SELECTED_FILTER_CONTRACT_ONLY')
                self.assertIn(expected_acceptance, record['acceptance'], name)
                expected = record['sha256']
            actual = (root/name).read_bytes().replace(b'\r\n', b'\n')
            self.assertEqual(hashlib.sha256(actual).hexdigest(), expected, name)

    def test_excess_wire_contract_and_invalid_filters_are_explicit(self):
        context=SimpleNamespace(run=None,business_date=date(2026,6,17),
                                output={'ClosingState':[{'importer':ATTRIBUTES}]})
        context.storage_output=context.output
        payload=dict(category='excessInventory',type='parent',product_permissions=[71001],
            location_permissions=[72001],paginationParameter=dict(pageNumber=1,recordsPerPage=50))
        context.rows = []
        with patch('mta.presentation.views.publication',side_effect=AssertionError('whole publication forbidden')), \
             patch('mta.presentation.excess_read.excess_context',return_value=context), \
             patch('mta.presentation.views.excess_rows',return_value=[dict(SKUCode='337',WHCode='AG515802',Amount=12)]), \
             patch('mta.presentation.context.permission_catalogue',return_value=CATALOGUE):
            response=self.post('GetPlanningDataGrid',payload,**IDENTITY).json()
            self.assertIsInstance(response['data']['data'],list)
            self.assertEqual(response['data']['data'][0]['am'],12)
            self.assertEqual(self.post('GetPlanningDataGridCount',payload,**IDENTITY).json()['data'],1)
            payload['filters']={'availabilityFilter':{'filters':[{'attributeName':'category','value':'1'}]}}
            self.assertEqual(self.post('GetPlanningDataGrid',payload,**IDENTITY).status_code,503)

    def test_fulfillment_count_grid_and_nested_detail_wire_types(self):
        context=SimpleNamespace(run=None,business_date=date(2026,6,17),output={'ClosingState':[{'importer':ATTRIBUTES}]})
        context.storage_output=context.output
        payload=dict(category='orderFulfillment',type='parent',product_permissions=[71001],location_permissions=[72001],
                     paginationParameter=dict(pageNumber=1,recordsPerPage=50))
        detail=dict(WhCode='AG515802',SKUCode='337',Introdate='2026-06-01',OrderNo='unit',PendingQty=5,DueDate=None,Price=None)
        context.rows={'summary':[],'details':[detail]}
        with patch('mta.presentation.views.publication',side_effect=AssertionError('whole publication forbidden')), \
             patch('mta.presentation.fulfillment_read.fulfillment_context',return_value=context), \
             patch('mta.presentation.views.fulfillment_rows',return_value=[dict(SKUCode='337',WHCode='AG515802',Gap=5,Price=12)]), \
             patch('mta.presentation.context.permission_catalogue',return_value=CATALOGUE):
            response=self.post('GetPlanningDataGrid',payload,**IDENTITY).json()
            grid=response['data']['data']
            self.assertIsInstance(grid,list)
            self.assertEqual(grid[0]['p'],'12')
            self.assertEqual(grid[0]['transit'][0]['p'],0)
            self.assertEqual(grid[0]['transit'][0]['dd'],'-')
            self.assertEqual(self.post('GetPlanningDataGridCount',payload,**IDENTITY).json()['data'],1)
            payload['product_permissions']=[]
            self.assertEqual(self.post('GetPlanningDataGridCount',payload,**IDENTITY).json()['data'],0)

    def test_fulfillment_graph_reads_persisted_projection_and_applies_native_scope(self):
        from copy import deepcopy
        importer=deepcopy(ATTRIBUTES)
        importer['SkuAttributeData'][0].update(SL4=None,SL5=None)
        importer['LocationAttributeData'][0].update(LL4=None,LL5=None)
        importer.update(SKUDescriptionTbl=[dict(SKUCode='337',SKUDescription='Retained SKU')],
                        SiteDescriptionTbl=[dict(WHCode='AG515802',WHDescription='Retained location')])
        context=SimpleNamespace(run=object(),output={'ClosingState':[{'importer':importer}]})
        context.storage_output=context.output
        reports=dict(summary=[dict(SKUCode='337',WhCode='AG515802',Coverage='Gap > 67%')],details=[])
        context.rows=reports
        payload=dict(category='orderFulfillment',product_permissions=[71001],location_permissions=[72001])
        with patch('mta.presentation.views.publication',side_effect=AssertionError('whole publication forbidden')), \
             patch('mta.presentation.fulfillment_read.fulfillment_context',return_value=context) as read, \
             patch('mta.presentation.context.permission_catalogue',return_value=CATALOGUE):
            response=self.post('GetPlanningDataGraph',payload,**IDENTITY)
            self.assertEqual(response.status_code,200)
            charts=response.json()['data']['data']
            self.assertEqual(charts['maxSkuWithGap']['data'][0]['greater'],'1')
            self.assertEqual(charts['maxSkuWithGap']['uiconfig'][0]['colPosition'],0)
            read.assert_called_once_with()
            payload['product_permissions']=[]
            denied=self.post('GetPlanningDataGraph',payload,**IDENTITY).json()['data']['data']
            self.assertTrue(all(not section['data'] for section in denied.values()))

    def test_expedite_count_direction_and_unavailable_detail_contract(self):
        context=SimpleNamespace(run=object(),output={'ClosingState':[{'importer':ATTRIBUTES}]})
        context.storage_output=context.output
        payload=dict(category='expedite',type='child',product_permissions=[71001],location_permissions=[72001])
        with patch('mta.presentation.views.publication',return_value=context), \
             patch('mta.presentation.views.read_expedite',return_value=['persisted']) as read, \
             patch('mta.presentation.views.expedite_counts',return_value=dict(expediteDispatches=2,createAvailabilityAtParent=0)) as count, \
             patch('mta.presentation.context.permission_catalogue',return_value=CATALOGUE):
            response=self.post('GetPlanningDataGridCount',payload,**IDENTITY)
            self.assertEqual(response.status_code,200)
            self.assertEqual(response.json()['data'],dict(expediteDispatches=2,createAvailabilityAtParent=0))
            read.assert_called_once_with(context.run,output=context.output)
            self.assertEqual(count.call_args.args,(context.output,['persisted'],'child'))
            self.assertEqual(count.call_args.kwargs['locations'],{'AG515802'})
            self.assertEqual(self.post('GetPlanningDataGrid',payload,**IDENTITY).status_code,503)
            payload['filters']={'availabilityFilter':{'filters':[dict(attributeName='Stock',value=1)]}}
            self.assertEqual(self.post('GetPlanningDataGridCount',payload,**IDENTITY).status_code,503)

    def test_expedite_chart_native_scope_and_source_flaw_unavailable(self):
        context=SimpleNamespace(run=object(),output={'ClosingState':[{'importer':ATTRIBUTES}]})
        context.storage_output=context.output
        payload=dict(category='expedite',type='parent',product_permissions=[71001],location_permissions=[72001])
        with patch('mta.presentation.views.publication',return_value=context), \
             patch('mta.presentation.views.read_expedite',return_value=['report']) as report, \
             patch('mta.presentation.views.read_pick_post',return_value=['post']) as post, \
             patch('mta.presentation.views.expedite_chart_queries',return_value={'native':'queries'}) as query, \
             patch('mta.presentation.views.expedite_chart_response',return_value={'data':'response'}) as response, \
             patch('mta.presentation.context.permission_catalogue',return_value=CATALOGUE):
            result=self.post('GetPlanningDataGraph',payload,**IDENTITY)
            self.assertEqual(result.status_code,200); self.assertEqual(result.json()['data'],{'data':'response'})
            report.assert_called_once_with(context.run,output=context.output)
            post.assert_called_once_with(context.run,output=context.output)
            self.assertEqual(query.call_args.args,(context.output,['report'],['post'],'parent'))
            self.assertEqual(query.call_args.kwargs['products'],{'337'})
            response.side_effect=ValueError('Legacy Expedite receiving LogisticsLocation depends on unordered critical rows')
            unavailable=self.post('GetPlanningDataGraph',payload,**IDENTITY)
            self.assertEqual(unavailable.status_code,503)
            self.assertIn('LEG-EXPEDITE-UNORDERED-LABEL',unavailable.json()['error'])
            response.side_effect=None
            payload['product_permissions']=[]
            self.assertEqual(self.post('GetPlanningDataGraph',payload,**IDENTITY).status_code,200)
            self.assertEqual(query.call_args.kwargs['products'],set())


if __name__ == '__main__':
    unittest.main()
