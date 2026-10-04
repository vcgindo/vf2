import copy
import unittest
from parity.btr_benchmark_contract import compare,MANIFEST


class BtrBenchmarkContractTests(unittest.TestCase):
    def check(self,a,b,**kwargs):
        return compare(a,b,manifest_sha256=kwargs.get('manifest',MANIFEST),business_date=kwargs.get('date','2026-04-07'),route=kwargs.get('route','GetBTRData'))

    def test_only_alias_permutation_is_qualified_and_bodies_are_untouched(self):
        a={'data':{'tech':[{'Category':'DN|BR|BR','D90':'1.00'}]}}
        b={'data':{'tech':[{'Category':'BR|DN|BR','D90':'1.00'}]}}
        old=copy.deepcopy((a,b));r=self.check(a,b)
        self.assertEqual(r['status'],'PASS_WITH_APPROVED_CATEGORY_ORDER')
        self.assertEqual(len(r['category_order_exceptions']),1)
        self.assertEqual((a,b),old)
        self.assertFalse(r['exact_response_equal'])

    def test_duplicate_loss_case_whitespace_and_type_changes_fail(self):
        for altered in ('DN|BR','dn|BR|BR','DN| BR|BR',None,0):
            self.assertEqual(self.check({'data':{'eco':[{'Category':'DN|BR|BR'}]}},
                                       {'data':{'eco':[{'Category':altered}]}})['status'],'FAIL')

    def test_other_fields_and_row_order_remain_strict(self):
        a={'data':{'tech':[{'Category':'DN|BR','D90':'1'},{'Category':'BR','D90':'2'}]}}
        for b in ({'data':{'tech':list(reversed(a['data']['tech']))}},
                  {'data':{'tech':[{'Category':'BR|DN','D90':'1.0'},a['data']['tech'][1]]}},
                  {'data':{'tech':[{'Category':'BR|DN','D90':1},a['data']['tech'][1]]}}):
            self.assertEqual(self.check(a,b)['status'],'FAIL')

    def test_missing_rows_fields_and_other_category_paths_fail(self):
        for a,b in [({'Category':'A|B'},{'Category':'B|A'}),
                    ({'data':{'tech':[{'Category':''}]}},{'data':{'tech':[]}}),
                    ({'data':{'tech':[{'Category':''}]}},{'data':{'tech':[{}]}})]:
            self.assertEqual(self.check(a,b)['status'],'FAIL')

    def test_scope_does_not_transfer_to_normal_runs_other_dates_or_reports(self):
        for override in ({'manifest':'0'*64},{'date':'2026-06-17'},{'route':'GetBPRData'}):
            with self.assertRaises(ValueError):self.check({}, {},**override)

    def test_unchanged_response_is_strict(self):
        self.assertEqual(self.check({'data':None},{'data':None})['status'],'PASS_STRICT')
