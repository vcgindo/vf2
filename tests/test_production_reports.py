"""Coupled native-source projection without any persisted execution claim."""
from copy import deepcopy
import unittest
from tests import test_h3_daily_integration as coupled
from mta.presentation.production_reports import current
from mta.serialization import storage


class NativeProducerIntegrationTests(unittest.TestCase):
    def test_source_capture_does_not_change_existing_calculation_and_uses_supplier_opening(self):
        frame=coupled.frame();prior=deepcopy(frame['opening']['state'])
        baseline,_=coupled.coupled(frame['profile'],prior,'2037-04-09','2037-04-10')
        day=coupled.supplied_day('2037-04-10')['day'];frozen=coupled.captured(prior,'WithDestLoc')
        day.update(raw_master=coupled.compose(frozen,coupled.nms_master_raw(prior),last_run_date='2037-04-09'),
            exclusions=[],supplier_feeds=coupled.complete_feeds(frozen,prior),
            production_report_policy=dict(bor_history_horizon=90,rrr_history_horizon=90))
        coupled.replace_working_inputs(frozen,prior,day,None)
        with coupled.evidence_mode('production'):
            actual=coupled.calculate_day(prior,'2037-04-09',day,frame['profile'],'component-h4',
                lambda source,**owned:(coupled.calculate_current_day(source,defer_pick=True,**owned),'component-h4'),native_daily=True)
        for name in ('ClosingState','BPRFinal','DBMFinal','BTRFinal','Reports'):
            self.assertEqual(actual[name],baseline[name],name)
        old={item['capability']:item['rows'] for item in baseline['CalculationOutputs']}
        new={item['capability']:item['rows'] for item in actual['CalculationOutputs']}
        self.assertEqual({key:new[key] for key in old},old)
        sources=current(actual,{'supplier':frame['opening']['state']['supplier']})
        self.assertEqual({r['AllocationFor'] for r in sources['RRR_OrderAllocation']},{'Norm','Order'})
        self.assertTrue(sources['BORWithOrderAllocation'])
        from mta.application import production_output_policy as policy
        opening = dict(supplier=frame['opening']['state']['supplier'],
            production_report_schema=policy.SOURCE_SCHEMA,
            production_report_policy={'output_contract': policy.contract()})
        frozen = deepcopy(actual)
        expanded = current(actual, opening)
        self.assertEqual(actual, frozen)
        for name in ('RRR_OrderAllocation', 'AllocatedOrders'):
            self.assertEqual(expanded[name], sources[name])
        self.assertEqual([{k: v for k, v in row.items() if k not in policy.ATTRIBUTES}
                         for row in expanded['BORWithOrderAllocation']], sources['BORWithOrderAllocation'])
        self.assertTrue(all(row[name] is None for row in expanded['BORWithOrderAllocation']
                            for name in policy.ATTRIBUTES))
        self.assertEqual([{k: v for k, v in row.items() if k != 'ParentWhCode'}
                         for row in expanded['BOROARequirement']], sources['BOROARequirement'])
        self.assertTrue(expanded['SupplierDispatchReq'])
        self.assertTrue(all(len(row) == 30 for row in expanded['SupplierDispatchReq']))
        del opening['production_report_policy']['output_contract']
        with self.assertRaises((KeyError, ValueError)):
            current(actual, opening)
        allocated=storage(sources['AllocatedOrders'])
        self.assertEqual(allocated,[
            dict(SKUCode='SUPPLIED-Z9',DestWhCode='OWN-PARENT',SrcWhCode='OWN-ROOT7',OrderKey=3,
                DueDate='2037-04-10',CustomerOrderId='SPIKE',IsSpike=1,Qty=6,OrderWiseAllocatedQty=6,
                BPP='0.00',OrderColor='Green',DueDateAtDest='2037-04-13',PackSizeWiseAllocatedQty=6),
            dict(SKUCode='SUPPLIED-Z9',DestWhCode='OWN-WH8',SrcWhCode='OWN-PARENT',OrderKey=3,
                DueDate='2037-04-16',CustomerOrderId='SPIKE',IsSpike=1,Qty=15,OrderWiseAllocatedQty=9,
                BPP='-100.00',OrderColor='White',DueDateAtDest='2037-04-16',PackSizeWiseAllocatedQty=9)])
        wrong=deepcopy(actual);wrong['CalculationOutputs']=[r for r in wrong['CalculationOutputs'] if r['capability']!='r1_allocated_orders']
        with self.assertRaises(ValueError):current(wrong,{'supplier':prior['supplier']})
