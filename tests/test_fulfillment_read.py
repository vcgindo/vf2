from types import SimpleNamespace
import os
import unittest
from unittest.mock import patch

os.environ.setdefault('VF_SECRET_KEY','unit-only')
os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
import django
django.setup()

from mta.presentation.context import PublicationUnavailable
from mta.presentation.fulfillment_filters import predicate
from mta.presentation.fulfillment_read import custom_grid
from mta.presentation.permissions import PermissionCodes


class FulfillmentConsumerTest(unittest.TestCase):
    def test_custom_left_join_omits_identity_without_inventing_nms(self):
        context=SimpleNamespace(nms=[],rows={'summary':[dict(SKUCode='S',WhCode='W',Norm=10,Stock=4,Price=None,RationedQty=6)]},
            output={'ClosingState':[{'importer':{'SiteDescriptionTbl':[]}}]})
        with patch('mta.presentation.fulfillment_read.scope',return_value=(PermissionCodes({'S':2}),PermissionCodes({'W':1}))):
            result=custom_grid(context,{},None)
        self.assertEqual(result['data'],[dict(RN=i,n=10,sk=4,rq=6) for i in (1,2)])
        self.assertEqual(len(result['uiConfig']),46)

    def test_custom_distinct_rows_with_same_native_sort_key_are_not_repaired(self):
        context=SimpleNamespace(nms=[],rows={'summary':[
            dict(SKUCode='S',WhCode='W',Norm=10,Stock=4,Price=None,RationedQty=6),
            dict(SKUCode='T',WhCode='W',Norm=11,Stock=4,Price=None,RationedQty=7)]},
            output={'ClosingState':[{'importer':{'SiteDescriptionTbl':[]}}]})
        with patch('mta.presentation.fulfillment_read.scope',return_value=(None,None)):
            with self.assertRaisesRegex(PublicationUnavailable,'UNORDERED-NMS'):
                custom_grid(context,{},None)
            self.assertEqual(custom_grid(context,{},(0,5))['data'],[])

    def test_coverage_filter_uses_source_label_and_preserves_null_exclusion(self):
        filters={'coverageFilter':{'filters':[dict(attributeName='coverage',value='Gap > 67%')]}}
        select=predicate({'filters':filters},{'LocationAttributeData':[]})
        self.assertEqual(select({'Coverage':'Gap > 67%'},{},{},{}),1)
        self.assertEqual(select({'Coverage':None},{},{},{}),0)
        filters['coverageFilter']['filters'][0]['value']='1'
        self.assertEqual(predicate({'filters':filters},{})({'Coverage':'Gap > 67%'},{},{},{}),0)
