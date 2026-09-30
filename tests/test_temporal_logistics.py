"""Input-mapping contract tests, not replacement synthetic parity artifacts."""
from copy import deepcopy
import unittest

from mta.temporal.chain import producer_owned_logistics
from mta.planning.projections import _pick_rows


class TemporalLogisticsTest(unittest.TestCase):
    def inputs(self):
        logistics = dict(vehicle=dict(name='trial',weight_capacity=100,volume_capacity=100),
            items=[dict(sku_code='337',location_code='AG515802',to_location='AG515802',
                        from_location='LDC006',weight=999,volume=999,pack_size=999,logistics_location='stale')])
        importer = dict(SkuAttributeData=[dict(SKUCode='337',Weight=2,Volume=3)],
            LocationAttributeData=[dict(WHCode='AG515802',LogisticsLocation=None)],
            SkuLocAttributeData=[dict(SKUCode='337',LocCode='AG515802',PackSize=7)])
        return logistics, importer

    def test_producer_attributes_replace_profile_without_mutation(self):
        logistics, importer = self.inputs()
        before = deepcopy((logistics,importer))
        row = producer_owned_logistics(logistics,importer)['items'][0]
        self.assertEqual((row['weight'],row['volume'],row['pack_size'],row['logistics_location']),(2,3,999,None))
        self.assertEqual((logistics,importer),before)

    def test_sql_null_predicate_does_not_invent_a_dimension_or_exclude_zero(self):
        logistics, importer = self.inputs()
        for weight,volume,count in ((None,None,0),(None,3,1),(2,None,1),(0,0,1)):
            importer['SkuAttributeData'][0].update(Weight=weight,Volume=volume)
            rows=producer_owned_logistics(logistics,importer)['items']
            self.assertEqual(len(rows),count)
            if rows:self.assertEqual((rows[0]['weight'],rows[0]['volume']),(weight,volume))

    def test_inner_join_absence_and_sql_identity_matching(self):
        logistics, importer = self.inputs()
        importer['LocationAttributeData'][0]['WHCode']='ag515802 '
        self.assertEqual(len(producer_owned_logistics(logistics,importer)['items']),1)
        importer['LocationAttributeData']=[]
        self.assertEqual(producer_owned_logistics(logistics,importer)['items'],[])

    def test_duplicate_candidates_and_join_rows_remain_rows(self):
        logistics, importer = self.inputs()
        logistics['items'] *= 2
        importer['SkuAttributeData'] *= 2
        self.assertEqual(len(producer_owned_logistics(logistics,importer)['items']),4)

    def test_existing_pick_reads_produced_values_and_null_location_fallback(self):
        logistics, importer = self.inputs()
        source=producer_owned_logistics(logistics,importer)
        rows=[dict(sku_code='337',location_code='AG515802',parent_location_code='LDC006',
                   to_black=1,to_red=0,to_yellow=0,to_green=0,to_blue=0)]
        actual=_pick_rows(rows,source,remaining=True)
        self.assertEqual(len(actual),1)
        self.assertEqual(actual[0]['logistics_location'],'AG515802')
        self.assertEqual(actual[0]['remaining_quantity'],'1')
        importer['SkuAttributeData'][0].update(Weight=None,Volume=None)
        self.assertEqual(_pick_rows(rows,producer_owned_logistics(logistics,importer),remaining=True),[])
