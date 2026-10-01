"""Consumer mechanics only; independent retained SQL evidence is separate."""
import unittest
from mta.presentation.history_native import colour_counts,graph_response,percentage,research_rows,historical_availability
from mta.presentation.permissions import PermissionCodes


def state():
    def trend(wh,parent,colour):
        return dict(SKUCode='337',WhCode=wh,ParentWhCode=parent,Age=1,BRAge=2,
            **{f'D{i}':colour if i==90 else None for i in range(1,91)})
    return dict(BufferTrendPhysicalInv=[trend('AG515802','LDC006','Black'),trend('LDC006','PL001','Green')],
        BufferTrendDispatch=[],SkuAttributeData=[dict(SKUCode='337')],
        LocationAttributeData=[dict(WHCode='AG515802'),dict(WHCode='LDC006')],SkuLocAttributeData=[])


class NativeHistoryTest(unittest.TestCase):
    def test_dotnet_decimal_scale_is_not_fixed_two_places(self):
        for numerator,denominator,expected in ((1,2,'50.0'),(1,4,'25.00'),(0,7,'0'),(7,7,'100'),(1,3,'33.33'),(0,0,'0')):
            self.assertEqual(percentage(numerator,denominator),expected)

    def test_count_joins_preserve_auth_pair_bags_but_historical_has_no_pair_join(self):
        data=state(); data['SkuLocAttributeData']=[dict(SKUCode='337',LocCode='AG515802')]*2
        args=dict(products=PermissionCodes({'337':2}),locations={'AG515802'})
        self.assertEqual(colour_counts(data,'tech',('D90',),**args)[0]['B'],4)
        self.assertEqual(colour_counts(data,'tech',('D90',),with_pair=False,**args)[0]['B'],2)

    def test_no_authorized_population_still_has_requested_dated_zeroes(self):
        counts=colour_counts(state(),'tech',('D89','D90'),products=set(),locations=set())
        self.assertIsNone(counts[0]['B'])
        value=graph_response(counts,[dict(D89='2026-06-16',D90='2026-06-17')])
        self.assertEqual([r['dt'] for r in value['absolute']],['16-06-2026','17-06-2026'])
        self.assertEqual(value['avail'],'0')
        self.assertTrue(all(v=='0' for row in value['percentage'] for k,v in row.items() if k!='dt'))

    def test_historical_wire_integral_double_matches_web_serialization(self):
        value=historical_availability(state(),products=set(),locations=set())[0]
        self.assertTrue(all(type(v) is int and v==0 for v in value.values()))

    def test_selected_child_may_read_parent_and_union_removes_duplicates(self):
        data=state(); data['BufferTrendPhysicalInv'].append(dict(data['BufferTrendPhysicalInv'][0]))
        selected=[dict(SKUCode='337',WhCode='AG515802')]
        master=[dict(SKUCode='337',WhCode='AG515802',ParentWhCode='LDC006')]
        result=research_rows(data,master,selected,products={'337'},locations={'AG515802'})
        self.assertEqual(len(result),2)
        self.assertEqual({r['Type'] for r in result},{'Self','Parent'})
        self.assertTrue(all('D1' not in r for r in result))
        self.assertIsNone(research_rows(data,master,selected,products=set(),locations={'AG515802'}))


if __name__=='__main__': unittest.main()
