"""Authenticated MDM request enrichment and approved SKU response adaptation."""
import json
from types import SimpleNamespace
from unittest.mock import patch

import requests
from django.test import SimpleTestCase
from api_gateway.interceptors import mta_interceptor as module


class MdmGatewayTests(SimpleTestCase):
    def forward(self,path,payload,rows=None):
        upstream=requests.Response()
        upstream.status_code=200
        upstream._content=json.dumps({'status':200,'data':rows if rows is not None else [{'SKUCode':'owned'}]}).encode()
        request=SimpleNamespace(COOKIES={'access_token':'owned-test-token'},
            user=SimpleNamespace(id=3,name='Requester',email='owned@fixture.local'),
            data=payload,path='/api/mta/'+path,query_params={},method='POST',FILES={})
        with patch.object(module.User_Application_Product_Permission.objects,'filter') as products, \
                patch.object(module.User_Application_Location_Permission.objects,'filter') as locations, \
                patch.object(module,'getAllUserDetails',return_value=[{'id':2}]), \
                patch.object(module.requests,'request',return_value=upstream) as send:
            products.return_value.values_list.return_value=[4]
            locations.return_value.values_list.return_value=[25]
            result=module.MTA_INTERCEPTOR().forward(request,
                {'mta':{'base_url':'http://owned-test','application_id':2}})
        return result,send.call_args.kwargs['json']

    def test_submit_uses_authenticated_actor_scope_and_eligible_reviewers(self):
        _,body=self.forward('AddMasterData',dict(id=1,all_users=[{'id':999}],
            user={'id':999},product_permissions=[999],location_permissions=[999]))
        self.assertEqual(body['user'],{'id':3,'name':'Requester'})
        self.assertEqual(body['product_permissions'],[4])
        self.assertEqual(body['location_permissions'],[25])
        self.assertEqual(body['all_users'],[{'id':2}])

    def test_only_successful_sku_history_selector_is_wrapped(self):
        result,_=self.forward('GetSkuLoc',{'masterId':1})
        self.assertEqual(json.loads(result.content),
            {'status':200,'data':{'sku':[{'SKUCode':'owned'}],'loc':[]}})
        result,_=self.forward('GetSkuLoc',{'masterId':3})
        self.assertEqual(result.json(),{'status':200,'data':[{'SKUCode':'owned'}]})

    def test_location_history_selector_uses_location_list_only(self):
        result,body=self.forward('GetSkuLoc',{'masterId':2},rows=[{'WHCode':'Location'}])
        self.assertEqual(json.loads(result.content),
            {'status':200,'data':{'sku':[],'loc':[{'WHCode':'Location'}]}})
        self.assertEqual(body['masterId'],2)
        self.assertEqual(body['location_permissions'],[25])
