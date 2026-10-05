import unittest
from parity.planning_order_contract import compare,compare_parent_transit,RUN,SOURCE

class PlanningOrderContractTests(unittest.TestCase):
    def compare(self,a,b,**kw):
        args=dict(run_id=RUN,source_digest=SOURCE,business_date='2026-04-07',kind='parent',family='nil_stock');args.update(kw)
        return compare(a,b,**args)
    def test_only_ties_may_move(self):
        a=[dict(counts=3,label='a'),dict(counts=3,label='b'),dict(counts=1,label=None)]
        self.assertEqual(self.compare(a,[a[1],a[0],a[2]])['status'],'PASS_APPROVED_ORDER_EXCEPTION')
        self.assertEqual(self.compare(a,list(reversed(a)))['status'],'FAIL')
    def test_values_types_nulls_and_duplicates_remain_strict(self):
        a=[dict(counts=3,label=None),dict(counts=3,label=None)]
        for b in (a[:1],[a[0],dict(counts=3,label='')],[a[0],dict(counts=3.0,label=None)]):
            self.assertEqual(self.compare(a,b)['status'],'FAIL')
    def test_unspecified_critical_order_is_scoped(self):
        a=[dict(counts=2,label='a'),dict(counts=9,label='b')]
        self.assertEqual(self.compare(a,a[::-1],family='critical')['status'],'PASS_APPROVED_ORDER_EXCEPTION')
        for kw in (dict(run_id='other'),dict(source_digest='other'),dict(business_date='2026-04-08'),dict(family='pre_post')):
            with self.assertRaises(ValueError):self.compare(a,a,**kw)

    def test_nested_exception_preserves_fields_types_and_duplicates(self):
        args=dict(run_id=RUN,source_digest=SOURCE,business_date='2026-04-07',
                  route='GetPlanningDataGrid',kind='parent',array='expediteDispatchestransit')
        a=[dict(skucode='A',eta='3'),dict(skucode='B',remarks=' '),dict(skucode='A',eta='3')]
        self.assertEqual(compare_parent_transit(a,[a[1],a[0],a[2]],**args)['status'],
                         'PASS_APPROVED_NESTED_ORDER_EXCEPTION')
        for b in (a[:2],[dict(a[0],eta=3),*a[1:]],
                  [dict(a[0],slt=None),*a[1:]], [a[0],dict(a[1],remarks=''),a[2]]):
            self.assertEqual(compare_parent_transit(a,b,**args)['status'],'FAIL')
        for key,value in [('run_id','other'),('source_digest','other'),('business_date','2026-04-08'),
                          ('route','Other'),('kind','child'),('array','createAvailabilityAtParenttransit')]:
            with self.assertRaises(ValueError):compare_parent_transit(a,a,**dict(args,**{key:value}))
