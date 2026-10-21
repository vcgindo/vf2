"""Retained order fixtures with explicit finite Elephant boundary overrides."""
from copy import deepcopy
from datetime import date
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

from tests.test_production_order_identity import state, feed, opening, calculate, payload, TODAY, OPENING, TOMORROW
from mta.domain.elephant_orders import acceptance, apply_due_dates, ACTION
from mta.domain.order_identity import MAX_KEY, ELEPHANT_CONTRACT
from mta.application.r1_input import calculation_order_rows, prepare_owned_order_current_day
from mta.application.r1_calculation import calculate_r1_requirements
from mta.runtime import relational_state as typed
from mta.runtime.temporal import command_states
from mta.serialization import storage, digest


def elephant(oid='E', qty=25, due=None, **changes):
    return dict(CustomerOrderID=oid, SKUCode='R1SKU', WhCode='R1-C', Qty=qty,
        TopmostWhCode='R1-C', TopmostWhNorm=90, RLTUptoSuppOrPlant=2,
        IntroDate='2026-01-12', CustomerExpectedDate='2026-01-17', DueDate=due, **changes)


def elephant_state(counter=50):
    value = state(counter)
    for row in value['BPRMaster']:
        row['ParentWhCode'] = 'R1-P' if row['WHCode'] == 'R1-C' else None
    for row in value['AdditionalMasterData']:
        row.update(TopmostWhCode=row['WhCode'], TopmostWhNorm=90 if row['WhCode']=='R1-C' else 300,
                   RLTTillPlantSupplier=2, ElephantOrderCapping=20)
    return value


class ElephantProducerTests(unittest.TestCase):
    def test_not_null_width_and_computed_topmost_domains_deny_before_state_change(self):
        for name,bad in (('Qty',None),('TopmostWhNorm',None),('RLTUptoSuppOrPlant',None),
                         ('TopmostWhCode',None),('IntroDate',None),('CustomerOrderID','A'*51)):
            value=elephant_state();value['ElephantOrders']=[dict(elephant(),**{name:bad})]
            before=deepcopy(value)
            with self.assertRaises(ValueError):calculate(value,[])
            self.assertEqual(value,before)
        for name in ('TopmostWhCode','TopmostWhNorm','RLTTillPlantSupplier'):
            value=elephant_state();value['AdditionalMasterData'][0][name]=None
            with self.assertRaises(ValueError):calculate(value,[feed('NEW-E',25)])

    def test_new_whole_quantity_then_manual_due_date_and_own_next_opening(self):
        value = elephant_state()
        first = calculate(value, [feed('E', 25, ced='2026-01-17')])
        self.assertEqual(first['SpikeOrderData'], [])
        self.assertEqual(first['NewSpikeOrders'], [])
        self.assertEqual(first['ElephantOrders'], [dict(elephant(),IntroDate=TODAY)])
        action = apply_due_dates(first,[dict(OrderID='E',SKUCode='R1SKU',WhCode='R1-C',DueDate='2026-01-20')])
        next_day = calculate(action, [], TOMORROW, TODAY)
        row = next_day['SpikeOrderData'][0]
        self.assertEqual((row['OrderKey'],row['PartId'],row['IsSpike'],row['IsElephant'],row['Qty']),
                         (51,1,True,True,25))
        self.assertEqual((row['DueDate'],row['FirstServicingWhCode'],row['IntroDate']),
                         ('2026-01-20','R1-P',TOMORROW))
        self.assertEqual(next_day['ElephantOrders'], [])
        self.assertEqual(first['ElephantOrders'][0]['DueDate'], None)

    def test_amendment_retains_ced_and_intro_refreshes_topology_declassifies_same_day(self):
        value = elephant_state();value['ElephantOrders']=[elephant()]
        value['AdditionalMasterData'][0].update(TopmostWhCode='R1-P',TopmostWhNorm=300,RLTTillPlantSupplier=7)
        amended=calculate(value,[feed('E',30,ced='2026-01-30')])['ElephantOrders'][0]
        self.assertEqual((amended['Qty'],amended['CustomerExpectedDate'],amended['IntroDate']),
                         (30,'2026-01-17','2026-01-12'))
        self.assertEqual((amended['TopmostWhCode'],amended['TopmostWhNorm'],amended['RLTUptoSuppOrPlant']),('R1-P',300,7))
        ordinary=calculate(value,[feed('E',17)])
        self.assertEqual(ordinary['ElephantOrders'],[])
        self.assertFalse(ordinary['SpikeOrderData'][0]['IsSpike'])
        spike=calculate(value,[feed('E',20)])
        self.assertEqual(spike['ElephantOrders'],[])
        self.assertTrue(spike['SpikeOrderData'][0]['IsSpike'])
        self.assertFalse(spike['SpikeOrderData'][0]['IsElephant'])

    def test_simultaneous_accepted_ordinals_precede_ordinary_and_spike_feed(self):
        for ids in (['Z','A'],['A','Z']):
            value=elephant_state();value['ElephantOrders']=[elephant(oid,due='2026-01-17') for oid in ids]
            # Explicit cap1000 for these new ordinary/Spike candidates.
            value['AdditionalMasterData'][0]['ElephantOrderCapping']=1000
            result=calculate(value,[feed(ids[0],25),feed('S',35),feed(ids[1],25),feed('O')])
            self.assertEqual([(r['CustomerOrderId'],r['OrderKey']) for r in result['SpikeOrderData']],
                             [(ids[0],51),(ids[1],52),('O',53),('S',54)])
            self.assertEqual([r['IsElephant'] for r in result['SpikeOrderData']],[True,True,False,False])

    def test_duplicate_acceptances_use_same_preinsert_part_max_and_distinct_keys(self):
        value=elephant_state();value['SpikeOrderData']=[opening('E',part=3,spike=True)]
        value['ElephantOrders']=[elephant(due='2026-01-17'),elephant(due='2026-01-17')]
        result=calculate(value,[])
        self.assertEqual([(r['PartId'],r['OrderKey']) for r in result['SpikeOrderData']],[(3,19),(4,51),(4,52)])
        self.assertEqual(result['OrderIdentity'][0]['LastValue'],52)

    def test_cap_null_and_promoted_ordinary_use_established_classification(self):
        value=elephant_state();value['AdditionalMasterData'][0]['ElephantOrderCapping']=None
        result=calculate(value,[feed('E',1)])
        self.assertEqual(result['ElephantOrders'][0]['Qty'],1)
        value=elephant_state();value['SpikeOrderData']=[opening('E')]
        value['AdditionalMasterData'][0]['SpikeThreshold']=100
        ordinary=calculate(value,[feed('E',25)])
        self.assertEqual(ordinary['ElephantOrders'],[])
        self.assertEqual(ordinary['SpikeOrderData'][0]['OrderKey'],19)
        promoted=calculate(value,[feed('E',95)])
        self.assertEqual(promoted['SpikeOrderData'],[])
        self.assertEqual(promoted['ElephantOrders'][0]['Qty'],95)

    def test_raw_empty_retains_missing_master_removes_and_due_dated_failed_join_deletes(self):
        value=elephant_state();value['ElephantOrders']=[elephant()]
        self.assertEqual(calculate(value,[])['ElephantOrders'],value['ElephantOrders'])
        absent=calculate(value,[feed('OTHER',1)])
        self.assertEqual(absent['ElephantOrders'],[])
        self.assertEqual(absent['SpikeOrderData'][0]['CustomerOrderId'],'OTHER')
        value['ElephantOrders'][0]['DueDate']='2026-01-17'
        value['AdditionalMasterData'][0]['TopmostWhCode']='UNMATCHED'
        result=calculate(value,[])
        self.assertEqual(result['ElephantOrders'],[])
        self.assertEqual(result['SpikeOrderData'],[])
        self.assertEqual(result['SpikeOrderClosureHistory'],[])

    def test_acceptance_and_combined_identity_overflow_are_atomic(self):
        for counter,rows in ((MAX_KEY,[feed('E',25)]),(MAX_KEY-1,[feed('E',25),feed('O')])):
            value=elephant_state(counter);value['ElephantOrders']=[elephant(due='2026-01-17')]
            before=deepcopy(value)
            with self.assertRaisesRegex(ValueError,'identity exhausted'):calculate(value,rows)
            self.assertEqual(value,before)
        value=elephant_state();value['ElephantOrders']=[elephant(due='2026-01-17')]
        value['SpikeOrderData']=[opening('E',part=MAX_KEY)]
        with self.assertRaisesRegex(ValueError,'PartId overflow'):calculate(value,[])

    def test_persisted_ordinals_reach_actual_tied_allocation(self):
        for ids in (['Z','A'],['A','Z']):
            value=elephant_state(91);value['ElephantOrders']=[dict(elephant(oid,due='2026-01-17'),CustomerExpectedDate=None) for oid in ids]
            closing=calculate(value,[])
            raw=payload([]);raw.pop('order_input');raw['orders']=calculation_order_rows(closing)
            prepared=prepare_owned_order_current_day(raw,closing)
            _,_,stock,_,_=calculate_r1_requirements(prepared,raw)
            self.assertTrue(stock)
            self.assertEqual({row['order_id'] for row in stock},{ids[0]})
            self.assertEqual([r['OrderKey'] for r in closing['SpikeOrderData']],[92,93])


class ElephantActionTests(unittest.TestCase):
    def test_joined_target_duplicates_null_clear_past_date_and_conflicting_bag(self):
        value=elephant_state();value['ElephantOrders']=[elephant(),elephant()]
        action=dict(OrderID='e ',SKUCode='r1sku',WhCode='r1-c',DueDate='2020-01-01')
        result=apply_due_dates(value,[action,deepcopy(action)])
        self.assertEqual([r['DueDate'] for r in result['ElephantOrders']],['2020-01-01']*2)
        cleared=apply_due_dates(result,[dict(action,DueDate='   ')])
        self.assertEqual([r['DueDate'] for r in cleared['ElephantOrders']],[None,None])
        for selected in ([],[action,dict(action,DueDate=None)]):
            with self.assertRaises(ValueError):apply_due_dates(value,selected)
        self.assertEqual(value['ElephantOrders'],[elephant(),elephant()])

    def test_mixed_action_domain_chain_global_dates_and_drift(self):
        base=dict(dbm={'NormAcceptanceTbl':[]},orders={'ElephantOrders':[elephant()]})
        acted=apply_due_dates(base['orders'],[dict(OrderID='E',SKUCode='R1SKU',WhCode='R1-C',DueDate='2026-01-17')])
        payload=dict(operation=ACTION,selected=[],timestamp=TODAY+'T12:00:00',actor='proof')
        meta=dict(table='BPR/ElephantOrders')
        event=SimpleNamespace(pk=1,payload=payload,digest=digest(payload),before_digest=digest(base['orders']),
            after_digest=digest(acted),state_manifest={'ElephantOrders':meta})
        run=SimpleNamespace(business_date=date.fromisoformat(TODAY),commands=MagicMock())
        run.commands.order_by.return_value=[event]
        with patch.object(typed,'load_image',return_value=acted['ElephantOrders']):
            result,receipts=command_states(run,base,through_date=date.fromisoformat(TOMORROW))
            self.assertEqual(result,dict(base,orders=acted));self.assertEqual([r['id'] for r in receipts],[1])
            with self.assertRaisesRegex(ValueError,'outside'):command_states(run,base,through_date=date.fromisoformat(OPENING))
            event.after_digest='0'*64
            with self.assertRaisesRegex(ValueError,'output drift'):command_states(run,base)

    def test_elephant_rows_roundtrip_through_owned_typed_codec(self):
        run=SimpleNamespace(pk='fc11f6b1-dc49-4fce-98c0-cdf4b6a3a49e');rows=[elephant(),elephant()]
        records=[]
        with patch.object(typed,'bulk',side_effect=lambda query,values:records.extend(values)):
            meta=typed.save_image(run,'action/1/ElephantOrders','closing/orders/ElephantOrders',rows)
        cursor=MagicMock();cursor.fetchmany.side_effect=[[tuple(r[2:]) for r in records],[]]
        with patch.object(typed.connection,'chunked_cursor') as context:
            context.return_value.__enter__.return_value=cursor
            self.assertEqual(typed.load_image(run,meta),storage(rows))
        self.assertEqual(ELEPHANT_CONTRACT,'persisted-elephant-ordinal-before-feed-ordinary-spike-v1')


if __name__=='__main__':unittest.main()
