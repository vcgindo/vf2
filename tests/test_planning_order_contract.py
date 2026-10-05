import unittest
from parity.planning_order_contract import compare,RUN,SOURCE

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
