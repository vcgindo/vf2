"""BPR join/paging unit probes, not replacement synthetic parity evidence."""
from copy import deepcopy
from decimal import Decimal
import unittest

from mta.presentation.bpr import ReadModel
from mta.runtime.relational_state import CATALOG


class BprProjectionTest(unittest.TestCase):
    def setUp(self):
        a = {name:None for name, _ in CATALOG['tables']['BPR/BPR_Table']}
        a.update(SKUCode='337',WhCode='AG515802',Norm=220,Stock=100,GIT=20,
            TechColorSequence=2,EcoColorSequence=3,EcoColor='Yellow',**{'PhaseIn-Out':1})
        vf = {name:None for name,_ in CATALOG['tables']['BPR/vf_RationedReqReport']}
        vf.update(SKUCode='337',WhCode='AG515802',PhysicalInventoryPen='55.00',DispatchPen='45.00',
            PhysicalInventoryColor='Red',DispatchColor='Yellow',PhysicalInventoryColorSequence=2,VirtualNorm=440)
        self.output = dict(BPRReports=[dict(BPR_Table=[a],vf_RationedReqReport=[vf])],
            ClosingState=[dict(importer=dict(SkuAttributeData=[],LocationAttributeData=[],SkuLocAttributeData=[]),
                dbm=dict(SKULocStandardAttributes=[dict(SKUCode='337',WhCode='AG515802',Tags=None)]))],
            BTRFinal=[dict(BufferTrendPhysicalInv=[])])
        self.ancillary = dict(InTransitData=[],BPRReport_RemarkDetails=[])

    def test_requires_explicit_ancillary_populations(self):
        with self.assertRaises(KeyError):
            ReadModel(self.output,{})

    def test_grid_and_count_differ_without_standard_membership(self):
        self.output['ClosingState'][0]['dbm']['SKULocStandardAttributes'] = []
        model = ReadModel(self.output,self.ancillary)
        self.assertEqual(len(model.candidates()),1)
        self.assertEqual(model.count_rows(),[])
        self.assertEqual(len(model.page(model.candidates(),1,10)),1)

    def test_paging_keys_then_rejoining_preserves_duplicate_bags(self):
        self.output['ClosingState'][0]['importer']['SkuLocAttributeData'] = [
            dict(SKUCode='337',LocCode='AG515802')]*2
        model = ReadModel(self.output,self.ancillary)
        self.assertEqual(len(model.candidates()),2)
        self.assertEqual(len(model.count_rows()),2)
        self.assertEqual(len(model.page(model.candidates(),1,1)),2)
        self.assertEqual(len(model.page(model.candidates(),1,2)),4)
        self.assertEqual(model.page(model.candidates(),3,1),[])

    def test_latest_remark_ties_multiply_only_final_and_count(self):
        self.ancillary['BPRReport_RemarkDetails'] = [dict(SKUCode='337',WhCode='AG515802',
            RemarkDate=stamp,Remark=text) for stamp,text in (
            ('2026-06-17T12:00:00','first'),('2026-06-17T12:00:00','tied'),
            ('2026-06-16T12:00:00','older'),(None,'no date'))]
        model = ReadModel(self.output,self.ancillary)
        self.assertEqual(len(model.candidates()),1)
        self.assertEqual(len(model.count_rows()),2)
        self.assertEqual([r['Remark'] for r in model.page(model.candidates(),1,10)],['first','tied'])

    def test_aliases_nulls_and_transit_are_copied_not_recalculated(self):
        self.output['BPRReports'][0]['vf_RationedReqReport'][0]['PhysicalInventoryPen'] = '-99999999.00'
        self.ancillary['InTransitData'] = [dict(SKUCode='337',WhCode='AG515802',
            OrderNo='unit',CreationDate=None,SLT=2,TLT=1,Ageing=1,ETA=None,
            CurrentLocationCode=None,InTransitQty=20,Remark=None)]
        before = deepcopy(self.output)
        model = ReadModel(self.output,self.ancillary)
        row = model.page(model.candidates(),1,10)[0]
        self.assertEqual((row['Norm'],row['vn'],row['EcoPen']),(220,440,Decimal('45.00')))
        self.assertIsNone(row['TechPen'])
        self.assertEqual((row['Req'],row['ParentName'],row['PhaseIn-Out']),(0,'-','Phase Out'))
        self.assertEqual(row['intransit'][0]['qty'],20)
        self.assertEqual(row['intransit'][0]['exeecocolor'],'Yellow')
        self.assertIsNone(row['intransit'][0]['cd'])
        self.assertEqual(self.output,before)

    def test_terminal_empty_transit_is_sql_null_and_availability_is_decimal(self):
        self.output['BTRFinal'][0]['BufferTrendPhysicalInv'] = [dict(SKUCode='337',WhCode='AG515802',
            Availability_01_30='0.00',Availability_31_60='33.33',Availability_61_90=None)]
        model = ReadModel(self.output,self.ancillary)
        row = model.page(model.candidates(),1,10)[0]
        self.assertIsNone(row['intransit'])
        self.assertEqual(row['Availability_31_60'],Decimal('33.33'))
        self.assertIsInstance(row['Availability_01_30'],Decimal)
        self.assertIsNone(row['Availability_61_90'])


if __name__ == '__main__':
    unittest.main()
