import copy
import unittest

from mta.application.production_rrr import produce
from mta.presentation.daily_rrr_colour import OUTPUT_FIELDS
from tests import test_daily_rrr_colour as norm_tests


class ProductionRrrTests(unittest.TestCase):
    def inputs(self):
        fixture = norm_tests.DailyRrrColourTests()
        return dict(rationed_report=[fixture.report(PackSize=2, DirectSpikeOverdue=12,
                    SpikeOverdueAtParent=3, ResidualChildrenSnP=4)],
            requirement_bands=[fixture.band(order_req_black=12, order_req_red=3)],
            bpr_master=[dict(SKUCode='A', WHCode='P')], advance_stock_allocations=[],
            allocated_orders=[dict(SKUCode='A', DestWhCode='L', SrcWhCode='P',
                OrderColor='Black', Qty=12, PackSizeWiseAllocatedQty=10),
                dict(SKUCode='A', DestWhCode='L', SrcWhCode='P',
                OrderColor='Red', Qty=3, PackSizeWiseAllocatedQty=2)])

    def test_nonempty_order_and_norm_exact_values(self):
        inputs = self.inputs()
        before = copy.deepcopy(inputs)
        result = produce(**inputs)
        self.assertEqual(inputs, before)
        self.assertEqual([tuple(row) for row in result], [OUTPUT_FIELDS, OUTPUT_FIELDS])
        self.assertEqual(result[0], dict(zip(OUTPUT_FIELDS, (
            'A', 'L', 'P', 'Order', 0, 19, 10, 0, 7, 15,
            12, 3, 0, 0, 0, 12, 1, 10, 2, 0, 0, 0, 'Black', 0))))
        self.assertEqual((result[1]['AllocationFor'], result[1]['RationedQty']), ('Norm',65))

    def test_self_allocation_without_report_keeps_native_nulls(self):
        inputs = self.inputs()
        inputs.update(rationed_report=[], requirement_bands=[], bpr_master=[],
            allocated_orders=[dict(SKUCode='S',DestWhCode='D',SrcWhCode='D',
                                  OrderColor='Black',Qty=7,PackSizeWiseAllocatedQty=4)])
        self.assertEqual(produce(**inputs), [dict(zip(OUTPUT_FIELDS, (
            'S','D','D','Order',0,0,None,None,0,7,7,0,0,0,0,4,None,4,0,0,0,0,'Black',0)))])

    def test_union_collapses_equal_rows_but_sums_all_allocation_occurrences(self):
        inputs = self.inputs()
        inputs['requirement_bands'] *= 2
        inputs['bpr_master'] *= 2
        inputs['allocated_orders'] *= 2
        result = produce(**inputs)
        self.assertEqual(len(result), 2)
        self.assertEqual((result[0]['RationedQty'], result[0]['TOBlack_AllocQty']), (24,20))

    def test_ambiguous_report_update_and_missing_populations_deny(self):
        inputs = self.inputs()
        inputs['rationed_report'].append(dict(inputs['rationed_report'][0], Stock=11))
        with self.assertRaisesRegex(ValueError, 'Ambiguous RRR'):
            produce(**inputs)
        for name in self.inputs():
            inputs = self.inputs()
            inputs[name] = None
            with self.subTest(name=name), self.assertRaises((ValueError,TypeError)):
                produce(**inputs)

    def test_blue_adjustment_uses_pre_update_quantities(self):
        inputs = self.inputs()
        inputs['requirement_bands'][0].update(order_req_black=0, order_req_red=3, order_req_blue=5)
        inputs['allocated_orders'] = [dict(SKUCode='A',DestWhCode='L',SrcWhCode='P',
            OrderColor='Red',Qty=8,PackSizeWiseAllocatedQty=8)]
        order = produce(**inputs)[0]
        self.assertEqual((order['TOR_AllocQty'],order['TOBlue_AllocQty']), (3,5))
