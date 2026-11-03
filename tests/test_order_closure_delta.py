"""Closure storage correspondence against the unchanged order producer."""
from copy import deepcopy
import unittest

from mta.row_sequences import RecordRows
from mta.runtime.dated_history_delta import changes,Counts,Fact,Occurrence,source_table
from tests.test_production_order_identity import state,opening,feed,calculate,TODAY,OPENING,TOMORROW


FAMILY='closing/orders/SpikeOrderClosureHistory'


def closure(stamp,**values):
    row=opening()
    del row['OrderKey'];del row['PartId']
    return dict(row,ClosureDate=stamp,**values)


def classify(prior,after,*,today=TODAY,position=1):
    return list(changes(((Occurrence(0,i),r) for i,r in enumerate(prior)),after,
        family=FAMILY,today=today,position=position))


class OrderClosureDeltaTests(unittest.TestCase):
    def test_actual_producer_preserves_all_old_dates_duplicates_and_boolean_conversion(self):
        prior=[closure(stamp) for stamp in (None,TODAY,TOMORROW,OPENING,OPENING)]
        for row in prior:row.update(IsSpike=1,IsElephant=0)
        saved=deepcopy(prior);value=state();value['SpikeOrderClosureHistory']=prior
        value['SpikeOrderData']=[opening('CLOSE',key=18),opening('CLOSE',key=19,part=2)]
        result=calculate(value,[feed('NEW')])
        rows=result['SpikeOrderClosureHistory']
        expected=[dict(r,IsSpike=True,IsElephant=False) for r in prior]
        expected += [dict(closure(TODAY),CustomerOrderId='CLOSE')]*2
        self.assertEqual(rows,expected)
        self.assertEqual(classify(prior,rows),[Fact(Occurrence(1,0),expected[-2]),
            Fact(Occurrence(1,1),expected[-1]),Counts(5,5,2,0,7)])
        self.assertEqual(prior,saved)
        successor=calculate(result,[],today=TOMORROW,prior=TODAY)
        self.assertEqual(classify(rows,successor['SpikeOrderClosureHistory'],today=TOMORROW,position=2),
                         [Counts(7,7,0,0,7)])
        self.assertEqual(source_table(FAMILY),'BPR/SpikeOrderClosureHistory')

    def test_raw_empty_and_nonempty_filtered_feed_keep_original_distinction(self):
        value=state();value['SpikeOrderData']=[opening('OLD')]
        self.assertEqual(calculate(value,[])['SpikeOrderClosureHistory'],[])
        filtered=calculate(value,[feed('OUTSIDE',sku='unregistered')])
        rows=filtered['SpikeOrderClosureHistory']
        self.assertEqual(rows,[closure(TODAY)])
        self.assertEqual(classify([],rows),[Fact(Occurrence(1,0),rows[0]),Counts(0,0,1,0,1)])

    def test_no_other_field_type_order_or_flag_projection_is_permitted(self):
        before=[closure(None),closure(TOMORROW)]
        variants=[list(reversed(before)),before[:1],
            [dict(before[0],Qty=5.0),before[1]],
            [dict(before[0],SKUCode='r1sku'),before[1]],
            [dict(before[0],IsSpike=0),before[1]],
            before+[closure(TOMORROW)],before+[dict(closure(TODAY),IsElephant=0)]]
        for rows in variants:
            with self.subTest(rows=rows),self.assertRaises(ValueError):classify(before,rows)
        with self.assertRaisesRegex(ValueError,'classification flag'):
            classify([dict(before[0],IsSpike=2)],before[:1])

    def test_mature_immutable_reader_boundary_matches_original_list_producer(self):
        prior=[closure(OPENING)]*10001
        value=state();value['SpikeOrderClosureHistory']=prior
        control=calculate(value,[])['SpikeOrderClosureHistory']
        value['SpikeOrderClosureHistory']=RecordRows(len(prior),lambda:iter(prior))
        actual=calculate(value,[])['SpikeOrderClosureHistory']
        self.assertEqual(actual,control)
        self.assertEqual(classify(prior,actual),[Counts(10001,10001,0,0,10001)])


if __name__=='__main__':unittest.main()
