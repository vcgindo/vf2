"""Canonical report boundary units; not substitute synthetic parity data."""
from copy import deepcopy
import unittest
from mta.presentation.fulfillment import produce_summary,produce_details,routes_for_orders
from mta.presentation.fulfillment_charts import chart_queries,chart_response,SECTIONS
from mta.presentation.permissions import PermissionCodes


class FulfillmentProducerTest(unittest.TestCase):
    def setUp(self):
        self.row=dict(SKUCode='337',WhCode='AG515802',ParentWhCode=None,VirtualNorm=220,Norm=220,
            Stock=12,GIT=1,NormReq=207,RelPSOAndCNR=0,PhysicalInventoryPen='94.55',PhysicalInventoryColor='Red',
            RationedReq=3,ResidualSnP=0,Req=10,DispatchPen='94.09',DispatchColor='Red',SnPToNetOff=0)
        self.attr=dict(SKUCode='337',WhCode='AG515802',Tags=None,Price='1.250')
        self.order=dict(OrderKey=7,CustomerOrderId='unit-order',SKUCode='337',WhCode='AG515802',
                        DueDate='2026-06-16',IntroDate='2026-06-01',Qty=10)
        self.routes=[dict(OrderKey=7,SrcWhCode='AG515802',DestWhCode=None,DueDate='2026-06-16')]

    def test_summary_signed_gap_coverage_price_and_no_mutation(self):
        before=deepcopy((self.row,self.attr))
        row=produce_summary([self.row],[self.attr])[0]
        self.assertEqual((row['Gap'],row['Coverage'],row['Price']),(7,'Gap > 67%',12))
        self.assertEqual((self.row,self.attr),before)
        row=produce_summary([dict(self.row,RationedReq=11)],[self.attr])[0]
        self.assertEqual((row['Gap'],row['Coverage']),(-1,'Gap < 33%'))
        row=produce_summary([dict(self.row,RationedReq=0,Req=0)],[self.attr])[0]
        self.assertEqual(row['Coverage'],'33% <= Gap <= 67%')

    def test_summary_positive_virtual_norm_inner_bags_and_nulls(self):
        self.assertEqual(produce_summary([dict(self.row,VirtualNorm=0)],[self.attr]),[])
        self.assertEqual(len(produce_summary([self.row]*2,[self.attr]*3)),6)
        row=produce_summary([dict(self.row,Req=None)],[self.attr])[0]
        self.assertIsNone(row['Gap']); self.assertIsNone(row['Coverage']); self.assertIsNone(row['Price'])

    def test_details_max_eligible_date_ties_and_independent_order_null_status(self):
        routes=self.routes+[dict(self.routes[0],SrcWhCode='PL002'),dict(self.routes[0],DueDate='2026-06-20')]
        rows=produce_details([self.order],routes,[self.attr],'2026-06-17')
        self.assertEqual(len(rows),2)
        self.assertEqual({r['WhCode'] for r in rows},{'AG515802','PL002'})
        self.assertTrue(all(r['OrderStatus']=='Over Due' and r['PendingQty']==10 and r['Customer'] is None for r in rows))
        row=produce_details([dict(self.order,DueDate=None)],self.routes,[self.attr],'2026-06-17')[0]
        self.assertEqual(row['OrderStatus'],'Others')
        row=produce_details([self.order],[],[self.attr],'2026-06-17')[0]
        self.assertIsNone(row['OrderStatus']); self.assertIsNone(row['DueDate'])
        self.assertEqual(row['WhCode'],'AG515802')

    def test_route_identity_must_not_guess_between_order_parts(self):
        route=dict(order_id='unit-order',sku_code='337',location_code='AG515802',child_location_code=None,due_date='2026-06-16')
        calculated=[dict(capability='r1_order_route',rows=[route])]
        self.assertEqual(routes_for_orders(calculated,[self.order]),self.routes)
        with self.assertRaisesRegex(ValueError,'ambiguous'):
            routes_for_orders(calculated,[self.order,dict(self.order,OrderKey=8)])
        calculated[0]['rows'][0]['order_key']=8
        self.assertEqual(routes_for_orders(calculated,[self.order,dict(self.order,OrderKey=8)])[0]['OrderKey'],8)


class FulfillmentChartTest(unittest.TestCase):
    def setUp(self):
        self.importer=dict(SKUDescriptionTbl=[dict(SKUCode='337',SKUDescription='Retained SKU')],
            SiteDescriptionTbl=[dict(WHCode='AG515802',WHDescription="O'Brien")],
            SkuAttributeData=[dict(SKUCode='337',**{f'SL{i}':None for i in range(1,6)})],
            LocationAttributeData=[dict(WHCode='AG515802',**{f'LL{i}':None for i in range(1,6)})])
        self.output={'ClosingState':[{'importer':self.importer}]}
        self.reports=dict(summary=[dict(SKUCode='337',WhCode='AG515802',Coverage='Gap > 67%')],
            details=[dict(SKUCode='337',WhCode='AG515802',OrderStatus='Over Due',OrderNo='unit',PendingQty=7)])

    def test_count_and_sum_preserve_permission_description_and_attribute_bags(self):
        self.importer['SiteDescriptionTbl']*=2
        self.importer['LocationAttributeData']*=3
        queries=chart_queries(self.output,self.reports,products=PermissionCodes({'337':2}),
                              locations=PermissionCodes({'AG515802':3}))
        self.assertEqual([r['counts'] for r in queries['location_orders']],[12]*3)
        self.assertEqual([r['counts'] for r in queries['location_gap']],[12]*3)
        self.assertEqual(queries['sku_orders'][0]['counts'],42)
        self.assertEqual(queries['location_orders'][0]['Details'],'OBrien')
        response=chart_response(queries)
        self.assertEqual(response['data']['maximumOverdueOrders']['data'][0]['overdue'],'12')
        self.assertTrue(all(c['colPosition']==0 for section in response['data'].values() for c in section['uiconfig']))

    def test_null_sum_denial_and_overflow_are_not_repaired(self):
        self.reports['details'][0]['PendingQty']=None
        queries=chart_queries(self.output,self.reports,products=None,locations=None)
        self.assertIsNone(queries['sku_orders'][0]['counts'])
        self.assertEqual(chart_response(queries)['data']['categorizationOfPendingQuantity']['data'][0]['overdue'],'')
        self.assertTrue(all(not rows for rows in chart_queries(self.output,self.reports,products=set(),locations=None).values()))
        self.reports['details'][0]['PendingQty']=2**31
        with self.assertRaises(OverflowError):
            chart_queries(self.output,self.reports,products=None,locations=None)

    def test_source_description_group_first_three_rows_without_demo_resorting(self):
        queries={s[0]:[] for s in SECTIONS}
        def row(detail,band,count):
            return dict(Details=detail,OrderStatus=band,counts=count,**{f'll{i}':None for i in range(1,6)})
        queries['location_orders']=[row('A','Over Due',7),row('B','Over Due',6),
            row('B','Due',6),row('A','Over Due',5),row('A','Due',4),row('A','Others',3)]
        data=chart_response(queries)['data']['maximumOverdueOrders']['data']
        self.assertEqual([r['location'] for r in data],['A','B'])
        self.assertEqual((data[0]['overdue'],data[0]['due'],data[0]['others']),('5','4','0'))
        queries['location_orders'][0]['Details']=None
        with self.assertRaisesRegex(ValueError,'Legacy Fulfilment NULL'):
            chart_response(queries)


if __name__=='__main__':
    unittest.main()
