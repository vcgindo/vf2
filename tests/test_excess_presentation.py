"""Excess report unit boundaries; not replacement full synthetic evidence."""
from copy import deepcopy
import unittest
from mta.presentation.excess import produce
from mta.presentation.excess_views import chart_queries,chart_response,joined_rows
from mta.presentation.permissions import PermissionCodes


class ExcessProducerTest(unittest.TestCase):
    def setUp(self):
        self.row = dict(SKUCode='337',WhCode='AG515802',ParentWhCode=None,Norm=220,
            VirtualNorm=220,Stock=227,GIT=10,BlueReq=0,Req=0,PhysicalInventoryPen='-3.18',
            PhysicalInventoryColor='White',DispatchPen='-7.73',DispatchColor='White')
        self.attr = dict(SKUCode='337',WhCode='AG515802',Tags=None,Price='1.750')

    def test_source_values_bigint_truncation_and_no_mutation(self):
        before = deepcopy((self.row,self.attr))
        result = produce([self.row],[self.attr],'2026-06-17')
        self.assertEqual(result[0]['ExcessQty'],7)
        self.assertEqual(result[0]['Amount'],12)
        self.assertEqual(result[0]['PhysicalInventoryPen'],'-3.18')
        self.assertEqual((self.row,self.attr),before)

    def test_inner_join_null_and_duplicate_bags(self):
        self.assertEqual(len(produce([self.row]*2,[self.attr]*3,'2026-06-17')),6)
        self.assertEqual(produce([dict(self.row,SKUCode=None)],[self.attr],'2026-06-17'),[])
        self.assertEqual(produce([self.row],[],'2026-06-17'),[])
        result = produce([self.row],[dict(self.attr,Price=None)],'2026-06-17')
        self.assertIsNone(result[0]['Amount'])

    def test_white_nonzero_predicate_is_not_positive_norm_gate(self):
        self.assertEqual(produce([dict(self.row,PhysicalInventoryColor='Blue')],[self.attr],'2026-06-17'),[])
        self.assertEqual(produce([dict(self.row,Stock=220)],[self.attr],'2026-06-17'),[])
        row = produce([dict(self.row,Norm=0,VirtualNorm=0,Stock=8,PhysicalInventoryColor='white ')],
                      [self.attr],'2026-06-17')[0]
        self.assertEqual((row['Norm'],row['ExcessQty']),(0,8))

    def test_source_overflow_is_not_repaired(self):
        with self.assertRaises(OverflowError):
            produce([dict(self.row,Stock=-2147483648,VirtualNorm=0)],[self.attr],'2026-06-17')


class ExcessConsumerTest(unittest.TestCase):
    def setUp(self):
        self.attributes={'SKUCode':'337',**{f'SL{i}':None for i in range(1,6)}}
        self.location={'WHCode':'AG515802',**{f'LL{i}':None for i in range(1,6)}}
        self.importer=dict(SKUDescriptionTbl=[dict(SKUCode='337',SKUDescription='-ND- retained')],
            SiteDescriptionTbl=[dict(WHCode='AG515802',WHDescription="O'Brien")],
            SkuAttributeData=[self.attributes],LocationAttributeData=[self.location],
            SkuLocAttributeData=[dict(SKUCode='337',LocCode='AG515802')])
        self.output={'ClosingState':[{'importer':self.importer}]}
        self.row=dict(SKUCode='337',WhCode='AG515802',ParentWhCode=None,Amount=7,
            ReportDate='2026-06-17',RequiredQty=0,PhysicalInventoryPen='-5.25',
            PipelineInventoryPen=None,PhysicalInventoryColor='White',PipelineInventoryColor='White')

    def queries(self,rows=None,**scope):
        return chart_queries(self.output,[self.row] if rows is None else rows,'2026-06-17',
            products=scope.get('products'),locations=scope.get('locations'))

    def test_chart_description_and_permission_bags_aggregate_before_attribute_join(self):
        self.importer['SiteDescriptionTbl']*=2
        self.importer['LocationAttributeData']*=3
        charts=self.queries(products=PermissionCodes({'337':2}),locations=PermissionCodes({'AG515802':3}))
        self.assertEqual(len(charts['location_count']),3)
        self.assertEqual([r['counts'] for r in charts['location_count']],[12]*3)
        self.assertEqual([r['counts'] for r in charts['location_value']],[84]*3)
        self.assertEqual(charts['location_count'][0]['Details'],'OBrien')
        self.assertEqual(charts['sku_count'][0]['Details'],'337 retained')
        self.assertEqual(charts['sku_count'][0]['counts'],6)

    def test_chart_groups_before_replacing_description_and_retains_null_sum(self):
        self.importer['SiteDescriptionTbl'].append(dict(WHCode='AG515802',WHDescription='OBrien'))
        charts=self.queries([dict(self.row,Amount=None)])
        self.assertEqual(len(charts['location_value']),2)
        self.assertTrue(all(r['counts'] is None for r in charts['location_value']))
        response=chart_response(self.output,[dict(self.row,Amount=None)],'2026-06-17',products=None,locations=None)
        self.assertEqual(response['data']['topTenLocationsWithExcessInventoryValue']['data'][0]['SumOfAmount'],'')
        self.assertTrue(all(c['colPosition']==0 for section in response['data'].values() for c in section['uiconfig']))

    def test_chart_denial_date_guard_and_no_silent_bigint_widening(self):
        self.assertTrue(all(not rows for rows in self.queries(products=set()).values()))
        self.assertTrue(all(not rows for rows in self.queries([dict(self.row,ReportDate='2026-06-16')]).values()))
        with self.assertRaises(OverflowError):
            self.queries([dict(self.row,Amount=2**63-1),self.row])

    def test_grid_keeps_parent_and_inner_description_multiplicity(self):
        self.importer['SKUDescriptionTbl']*=2
        self.importer['SkuLocAttributeData']*=3
        rows=joined_rows(self.output,[self.row],'2026-06-17')
        self.assertEqual(len(rows),6)
        self.assertIsNone(rows[0]['ParentWHName'])
        self.assertEqual(rows[0]['PhysicalPen'],-5.25)
        self.assertEqual(joined_rows(self.output,[self.row],'2026-06-16'),[])


if __name__=='__main__':
    unittest.main()
