"""Report-mapping unit probes, not engine/legacy synthetic acceptance."""
from copy import deepcopy
from decimal import Decimal
import unittest

from mta.presentation.rrr import pick_rows, selected_rows
from mta.presentation.rrr_types import selected_rrr_response
from mta.runtime.relational_state import CATALOG


class RrrProjectionTest(unittest.TestCase):
    def setUp(self):
        self.row = {name: 0 for name, kind in CATALOG['tables']['BPR/vf_RationedReqReport']}
        self.row.update(SKUCode='337', WhCode='AG515802', ParentWhCode='PARENT',
            SKUName='Retained identity unit probe', WhName='Receiving', ParentWhName='Parent',
            Norm=220, VirtualNorm=220, ParentNorm=440, TechPen='70.00', EcoPen='60.00',
            TechColor='Red', EcoColor='Yellow', TechColorParent='Yellow', EcoColorParent='Green',
            PhysicalInventoryColor='Red', DispatchColor='Yellow', DispatchPen='50.00',
            DispatchColorSequence=3, Req=28, RationedReq=18, AllocatedForDirectOrders=7,
            PackSize=3, ParentPackSize=6, RationedCasePacks=3, LeftoverStock=11, AvgChildrenNorm=40)
        self.band = dict(sku_code='337', location_code='AG515802', parent_location_code='PARENT',
                         to_black='0', to_red='8', to_yellow='10', to_green='0', to_blue='0')
        attrs = {f'c{i}': None for i in range(1,16)}
        self.output = dict(BPRReports=[{'vf_RationedReqReport':[self.row]}],ClosingState=[dict(
            dbm={'SKULocStandardAttributes':[dict(SKUCode='337',WhCode='AG515802')]},
            importer={
                'SkuAttributeData':[dict(SKUCode='337',**attrs,**{f'SL{i}':None for i in range(1,6)})],
                'LocationAttributeData':[dict(WHCode='AG515802',**attrs,**{f'LL{i}':None for i in range(1,6)})],
                'SkuLocAttributeData':[dict(SKUCode='337',LocCode='AG515802',**attrs)]})])

    def test_physical_report_copies_produced_quantities_and_casepacks(self):
        original = deepcopy(self.row)
        row = selected_rows(self.output, [self.band])[0]
        self.assertEqual((row['RReq'],row['RCPs'],row['PackSize']), (18,3,3))
        self.assertEqual((row['torb'],row['torr'],row['toy']), (0,8,10))
        self.assertEqual(row['AllocatedForDirectOrders'],0)
        self.assertEqual(row['EPen'], Decimal('50.00'))
        self.assertEqual(self.row,original)
        wire = selected_rrr_response(row)
        self.assertEqual(wire['PackSize'],'3')  # Selected map's Number entry is PS, not PackSize.
        self.assertEqual(wire['ECol'],'Yellow')
        self.assertEqual(wire['sl1'],'')
        self.assertEqual(wire['SKUAttr1'],'-')
        self.assertNotIn('RN',wire)

    def test_virtual_aliases_are_source_defined_not_recomputed(self):
        band = dict(self.band,parent_location_code='AG515802',to_red='0',to_yellow='0')
        row = pick_rows([self.row],[band])[0]
        self.assertEqual((row['ParentWhCode'],row['ParentNorm']),('AG515802',220))
        self.assertEqual((row['RationedReq'],row['RationedCasePacks'],row['Req']), (0,0,0))
        self.assertEqual((row['AllocatedForDirectOrders'],row['LeftoverParentStock']), (7,11))
        self.assertEqual((row['AvgSiblingsNorm'],row['AvgChildrenNorm']), (40,0))

    def test_attribute_join_bags_null_exclusion_and_band_duplicates(self):
        importer = self.output['ClosingState'][0]['importer']
        importer['SkuLocAttributeData'] *= 2
        self.assertEqual(len(selected_rows(self.output,[self.band,self.band])),8)
        importer['LocationAttributeData'][0]['WHCode'] = None
        self.assertEqual(selected_rows(self.output,[self.band]),[])

    def test_ambiguous_source_and_missing_band_parent_are_rejected(self):
        with self.assertRaisesRegex(ValueError,'unique produced'):
            pick_rows([self.row,self.row],[self.band])
        with self.assertRaisesRegex(ValueError,'parent differs'):
            pick_rows([self.row],[dict(self.band,parent_location_code='UNKNOWN')])


if __name__ == '__main__':
    unittest.main()
