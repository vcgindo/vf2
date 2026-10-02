from datetime import date
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from mta.presentation.context import PublicationUnavailable
from mta.presentation.excess_filters import predicate
from mta.presentation.excess_read import custom_grid, pagination
from mta.presentation.permissions import PermissionCodes


class ExcessConsumerTest(unittest.TestCase):
    def test_custom_preserves_native_nulls_permission_bag_and_integer_paging(self):
        nms = dict(SKUCode='S', WhCode='W', ParentWhCode='P', SKUDescription='SKU', WHDescription='WH',
            MinNorm=1, RLT=3, RCP=1, GCP=2, OCP=3, MinOrderCount=0, PackSize=1, FGRMFlag='FG', DBMActive=True,
            **{p+str(i): None for p in ('SL', 'LL') for i in range(1, 6)})
        report = dict(SKUCode='S', WhCode='W', ReportDate='2026-06-17', Norm=20, Stock=30,
            PhysicalInventoryColor='White', PhysicalInventoryPen='-50.00',
            PipelineInventoryColor='White', PipelineInventoryPen='-50.00')
        context = SimpleNamespace(business_date=date(2026, 6, 17), rows=[report], nms=[nms, nms],
            standards=[dict(SKUCode='S', WhCode='W', Price='2.500')],
            output={'ClosingState':[{'importer':{'SiteDescriptionTbl':[dict(WHCode='P', WHDescription='Parent')]}}]})
        with patch('mta.presentation.excess_read.scope', return_value=(PermissionCodes({'S':2}), PermissionCodes({'W':1}))):
            result = custom_grid(context, {'filters': {'ignored': True}}, (2, 2))
        self.assertEqual([r['RN'] for r in result['data']], [3, 4])
        self.assertEqual(result['data'][0]['Price'], 2.5)
        self.assertIs(result['data'][0]['da'], True)
        self.assertNotIn('sl1', result['data'][0])
        self.assertEqual(len(result['uiConfig']), 46)
        self.assertEqual(pagination({'paginationParameter':{'pageNumber':1, 'recordsPerPage':10000}}), (1,10000))

    def test_filter_gate_and_parent_join_multiplicity(self):
        importer = {'LocationAttributeData':[dict(WHCode='P', LocationType='Depo')]*2}
        groups = {'customAttributeFilter':{'filters':[dict(attributeName='skuattr1', operator='equalto', value='X')]}}
        row = dict(SKUCode='S', WhCode='W', ParentWhCode='P')
        self.assertEqual(predicate({'filters':groups}, importer)(row, {}, {'c1':None}, {}), 1)
        groups['productFilter'] = {'filters':[]}
        self.assertEqual(predicate({'filters':groups}, importer)(row, {}, {'c1':None}, {}), 0)
        groups['customAttributeFilter']['filters'][0].update(operator='notequalto')
        groups['supplyChainFilter'] = {'filters':[dict(attributeName='forchildren', value='Depo')]}
        self.assertEqual(predicate({'filters':groups}, importer)(row, {}, {'c1':None}, {}), 2)

    def test_invalid_source_filter_is_detected_even_without_report_rows(self):
        for group, item in (
            ('availabilityFilter', dict(attributeName='category', value='5')),
            ('colorFilter', dict(attributeName='red', value='0', operator='greaterthan', type='colorcount')),
            ('productFilter', dict(attributeName='p9', value='X', operator='equalto'))):
            with self.assertRaises(PublicationUnavailable):
                predicate({'filters':{group:{'filters':[item]}}}, {'LocationAttributeData':[]})
