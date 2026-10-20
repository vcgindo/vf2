"""Approved generated identity order, actual routing/allocation and own carry."""
from copy import deepcopy
import json,os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock,patch

os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY','order-identity-unit-only')
import django
django.setup()
from mta.domain.order_closing import TABLES,order_stages
from mta.domain.order_identity import CONTRACT,QUALIFICATION,MAX_KEY,next_keys
from mta.application.r1_order_input import reconcile_order_feed
from mta.application.r1_input import prepare_r1_current_day, prepare_owned_order_current_day
from mta.application.r1_calculation import calculate_r1_requirements
from mta.runtime import relational_state as typed
from mta.serialization import storage
from mta.temporal.chain import calculation_order_rows
from mta.planning.engine import calculate_current_day

TODAY='2026-01-15';OPENING='2026-01-14';TOMORROW='2026-01-16'


def feed(oid,qty=5,wh='R1-C',sku='R1SKU',ced=None):
    return dict(OrderID=oid,SKUCode=sku,WhCode=wh,Qty=qty,CustomerExpDate=ced)


def opening(oid='OLD',key=19,qty=5,spike=False,wh='R1-C',part=1):
    return dict(OrderKey=key,CustomerOrderId=oid,PartId=part,IsSpike=spike,IsElephant=False,
        OriginalQty=qty,Qty=qty,SKUCode='R1SKU',WhCode=wh,CustomerExpectedDate=None,
        FirstServicingWhCode='R1-P' if spike else None,DueDate='2026-01-17' if spike else None,
        IntroDate='2026-01-12')


def state(counter=50,levels=2):
    value={name:[] for name in TABLES}
    nodes=[('R1-C',90,'R1-P',2,1),('R1-P',300,None,4,0)] if levels==2 else [
        ('R1-C',90,'R1-P',2,2),('R1-P',300,'R1-R',4,1),('R1-R',1000,None,6,0)]
    value.update(BPRMaster=[dict(SKUCode='R1SKU',WHCode=w,Norm=n) for w,n,p,r,l in nodes],
        DBMMaster=[dict(SKUCode='R1SKU',WhCode=w,Norm=n,ParentWhCode=p,RLT=r) for w,n,p,r,l in nodes],
        AdditionalMasterData=[dict(SKUCode='R1SKU',WhCode=w,WhLevel=l,SpikeThreshold=20,ElephantOrderCapping=1000)
                              for w,n,p,r,l in nodes],
        OrderIdentity=[dict(Seed=1,Increment=1,LastValue=counter)],
        LastBatchRunTbl=[dict(LastRunDate=OPENING+'T00:00:00')],IntermediateTables={})
    return value


def calculate(value,rows,today=TODAY,prior=OPENING):
    return list(order_stages(today,prior,value,'PRESENT',rows))[-1][1]


def source(value,rows):
    return dict(opening_date=OPENING,opening_identity='own-component-order-opening',feed_status='PRESENT',feed_rows=rows,
        opening_orders=value['SpikeOrderData'],closure_history=value['SpikeOrderClosureHistory'],
        identity_last_value=value['OrderIdentity'][0]['LastValue'])


def payload(rows,counter=91,retained=None):
    value=json.loads((Path(__file__).resolve().parents[1]/'mta/fixtures/r1_order_mixed_identity.json').read_text())
    value['order_input'].update(feed_rows=rows,opening_orders=[] if retained is None else retained,
        closure_history=[],identity_last_value=counter)
    # This is an explicit finite allocation boundary override, not a new policy.
    for row in value['stock_openings']:
        if row['location_code']=='R1-P':row['stock']=250
        if row['location_code']=='R1-C':row['stock']=90
    for row in value['foundation']['inventory_positions']:
        if row['location_code']=='R1-P':row['stock_quantity']=250
        if row['location_code']=='R1-C':row['stock_quantity']=90
    return value


class GeneratedIdentityTests(unittest.TestCase):
    def test_multiple_ordinary_preserved_filter_ordinals_not_customer_sku_qty_sort(self):
        rows=[feed('IGNORED',sku='outside'),feed('Z',7),feed('A',3),feed('M',5)]
        value=state();before=deepcopy(value);raw=deepcopy(rows)
        result=calculate(value,rows)
        self.assertEqual([(r['CustomerOrderId'],r['OrderKey'],r['Qty']) for r in result['SpikeOrderData']],
                         [('Z',51,7),('A',52,3),('M',53,5)])
        self.assertEqual(result['OrderIdentity'],[dict(Seed=1,Increment=1,LastValue=53)])
        self.assertEqual(value,before);self.assertEqual(rows,raw)
        reversed_result=calculate(value,list(reversed(rows)))
        self.assertEqual([(r['CustomerOrderId'],r['OrderKey']) for r in reversed_result['SpikeOrderData']], [('M',51),('A',52),('Z',53)])

    def test_multiple_spike_and_interleaved_subsets_ordinary_then_spike(self):
        for rows in ([feed('Z-S',25),feed('A-S',35)],
                     [feed('Z-S',25),feed('Z-O',7),feed('A-S',35),feed('A-O',3)]):
            result=calculate(state(),rows)
            expected=[r['OrderID'] for r in rows if r['Qty']<=18]+[r['OrderID'] for r in rows if r['Qty']>18]
            self.assertEqual([r['CustomerOrderId'] for r in result['SpikeOrderData']],expected)
            self.assertEqual([r['OrderKey'] for r in result['SpikeOrderData']],list(range(51,51+len(expected))))
            for row in result['SpikeOrderData']:
                if row['IsSpike']:
                    self.assertEqual((row['FirstServicingWhCode'],row['DueDate']),('R1-P','2026-01-17'))
            reverse=calculate(state(),list(reversed(rows)))
            self.assertEqual([r['CustomerOrderId'] for r in reverse['SpikeOrderData']],
                list(reversed([r['OrderID'] for r in rows if r['Qty']<=18]))+list(reversed([r['OrderID'] for r in rows if r['Qty']>18])))

    def test_hierarchy_resolution_order_does_not_replace_spike_feed_identity_order(self):
        rows=[feed('P-FIRST',70,wh='R1-P'),feed('C-SECOND',25)]
        result=calculate(state(levels=3),rows)
        self.assertEqual([(r['CustomerOrderId'],r['OrderKey'],r['FirstServicingWhCode'],r['DueDate']) for r in result['SpikeOrderData']],
            [('P-FIRST',51,'R1-R','2026-01-19'),('C-SECOND',52,'R1-P','2026-01-17')])
        self.assertEqual([r['CustomerOrderId'] for r in result['NewSpikeOrders']],['P-FIRST','C-SECOND'])

    def test_retained_keys_parts_amendment_closure_promotion_and_deleted_counter_not_reused(self):
        value=state(91)
        value['SpikeOrderData']=[opening('KEEP',19,spike=True),opening('KEEP',23,spike=True,part=2),opening('CLOSE',70),opening('PROMOTE',71)]
        result=calculate(value,[feed('NEW-O'),feed('KEEP',8),feed('PROMOTE',25),feed('NEW-S',35)])
        self.assertEqual([(r['CustomerOrderId'],r['PartId'],r['OrderKey']) for r in result['SpikeOrderData']],
            [('KEEP',1,19),('KEEP',2,23),('NEW-O',1,92),('PROMOTE',1,93),('NEW-S',1,94)])
        self.assertEqual([r['Qty'] for r in result['SpikeOrderData'][:2]],[8,8])
        self.assertEqual([r['OriginalQty'] for r in result['SpikeOrderData'][:2]],[5,5])
        self.assertEqual([r['CustomerOrderId'] for r in result['SpikeOrderClosureHistory']],['CLOSE'])
        self.assertEqual(result['OrderIdentity'][0]['LastValue'],94)

    def test_existing_per_level_anti_join_without_wh_is_preserved_not_deduplicated(self):
        result=calculate(state(levels=3),[feed('SAME',70,wh='R1-P'),feed('SAME',25)])
        self.assertEqual([(r['WhCode'],r['OrderKey']) for r in result['SpikeOrderData']],[('R1-C',51)])
        value=state();value['BPRMaster'].append(dict(SKUCode='R1SKU',WHCode='R1-D',Norm=90))
        value['DBMMaster'].append(dict(value['DBMMaster'][0],WhCode='R1-D'))
        value['AdditionalMasterData'].append(dict(value['AdditionalMasterData'][0],WhCode='R1-D'))
        simultaneous=calculate(value,[feed('SAME',25),feed('SAME',25,wh='R1-D')])
        self.assertEqual([(r['WhCode'],r['OrderKey']) for r in simultaneous['SpikeOrderData']],[('R1-C',51),('R1-D',52)])

    def test_declared_duplicate_master_feed_and_elephant_errors_remain_atomic(self):
        for issue in ('duplicate-feed','duplicate-key','duplicate-master','elephant','counter-drift'):
            value=state();rows=[feed('O')]
            if issue=='duplicate-feed':rows=[feed('O'),feed('o ',3)]
            if issue=='duplicate-key':value['SpikeOrderData']=[opening(key=19),opening('OTHER',key=19)]
            if issue=='duplicate-master':value['BPRMaster'].append(deepcopy(value['BPRMaster'][0]))
            if issue=='elephant':rows=[feed('E',1001)]
            if issue=='counter-drift':value['SpikeOrderData']=[opening(key=51)]
            before=deepcopy(value);raw=deepcopy(rows)
            with self.assertRaises(ValueError):calculate(value,rows)
            self.assertEqual(value,before);self.assertEqual(rows,raw)

    def test_counter_capacity_before_assignment_and_exhausted_counter_inactive_carry(self):
        self.assertEqual(list(next_keys(MAX_KEY-2,2)),[MAX_KEY-1,MAX_KEY])
        for rows in ([feed('A'),feed('B')],[feed('A',25),feed('B',35)],[feed('A'),feed('B',25)]):
            value=state(MAX_KEY-1);before=deepcopy(value)
            with self.assertRaisesRegex(ValueError,'identity exhausted'):calculate(value,rows)
            self.assertEqual(value,before)
        value=state(MAX_KEY);value['SpikeOrderData']=[opening(key=MAX_KEY)]
        result=calculate(value,[])
        self.assertEqual(result['OrderIdentity'],value['OrderIdentity'])
        self.assertEqual(result['SpikeOrderData'],value['SpikeOrderData'])
        with self.assertRaises(ValueError):calculate(value,[feed('NEW')])
        for invalid in (True,0,MAX_KEY+1):
            with self.assertRaises(ValueError):next_keys(invalid,0)

    def test_single_ordinary_single_spike_empty_and_missing_keep_established_behavior(self):
        ordinary=calculate(state(),[feed('ONE')])
        self.assertEqual((ordinary['SpikeOrderData'][0]['OrderKey'],ordinary['OrderIdentity'][0]['LastValue']),(51,51))
        spike=calculate(state(),[feed('ONE',25)])
        self.assertEqual((spike['SpikeOrderData'][0]['OrderKey'],spike['OrderIdentity'][0]['LastValue']),(51,51))
        value=state();value['SpikeOrderData']=[opening()]
        for status in ('PRESENT','MISSING'):
            final=list(order_stages(TODAY,OPENING,value,status,[]))[-1][1]
            self.assertEqual(final['SpikeOrderData'],value['SpikeOrderData'])
            self.assertEqual(final['OrderIdentity'],value['OrderIdentity'])


class ConnectedIdentityTests(unittest.TestCase):
    def test_simultaneous_customer_parts_reach_calculation_and_consumer_projection(self):
        value=state(91)
        for table,field in (('BPRMaster','WHCode'),('DBMMaster','WhCode'),('AdditionalMasterData','WhCode')):
            value[table].append(dict(value[table][0],**{field:'R1-D'}))
        closing=calculate(value,[feed('SAME',25),feed('SAME',25,wh='R1-D')])
        raw=payload([]);raw.pop('order_input')
        # Explicit second same-level location in this finite source-boundary case.
        raw['foundation']['locations'].append({'location_code':'R1-D'})
        for rows in (raw['foundation']['sku_locations'],raw['foundation']['inventory_positions'],
                     raw['foundation']['hierarchy'],raw['policies'],raw['stock_openings'],raw['routing']):
            original=next(row for row in rows if 'R1-C' in row.values())
            rows.append({key:'R1-D' if value=='R1-C' else deepcopy(value) for key,value in original.items()})
        raw['policies'][-1]['rationing_priority']=2
        raw['orders']=calculation_order_rows(closing)
        self.assertEqual([r['order_id'] for r in raw['orders']],['92','93'])
        prepared=prepare_owned_order_current_day(raw,closing)
        self.assertEqual(prepared.order_part_identity,{
            '92':dict(order_id='SAME',order_key=92,part_id=1),
            '93':dict(order_id='SAME',order_key=93,part_id=1)})
        outputs=calculate_current_day(raw,defer_pick=True,_owned_order_closing=closing)
        routes=outputs['r1_order_route']
        self.assertEqual({(r['order_id'],r['order_key'],r['part_id']) for r in routes},
                         {('SAME',92,1),('SAME',93,1)})
        remaining=outputs['r1_order_remaining']
        self.assertEqual([(r['order_id'],r['order_key']) for r in remaining],[('SAME',92),('SAME',93)])
        self.assertEqual([r['OrderKey'] for r in closing['SpikeOrderData']],[92,93])
        drift=deepcopy(raw);drift['orders'][0]['outstanding_quantity']=1
        with self.assertRaisesRegex(ValueError,'projection drift'):prepare_owned_order_current_day(drift,closing)
        seeded=deepcopy(raw);seeded['order_part_identity']=prepared.order_part_identity
        with self.assertRaises(ValueError):prepare_r1_current_day(seeded)

    def test_separate_feed_computed_keys_reach_actual_tied_allocation_priority(self):
        for rows in ([feed('Z',25),feed('A',35)],[feed('A',35),feed('Z',25)]):
            raw=payload(rows)
            prepared=prepare_r1_current_day(raw)
            self.assertEqual([v['order_id'] for v in prepared.order_part_identity.values()],[r['OrderID'] for r in rows])
            self.assertEqual(list(prepared.order_part_identity),['92','93'])
            _,_,stock,git,trace=calculate_r1_requirements(prepared,raw)
            self.assertTrue(stock)
            self.assertEqual(stock[0]['order_id'],'92')
            self.assertTrue(all(row['order_id']=='92' for row in stock))
            self.assertEqual(prepared.order_part_identity[stock[0]['order_id']]['order_id'],rows[0]['OrderID'])

    def test_retained_keys_keep_priority_before_generated_and_mixed_subsets(self):
        raw=payload([feed('NEW-S',35),feed('NEW-O'),feed('OLD',25)],
                    retained=[opening('OLD',key=19,qty=25,spike=True)])
        prepared=prepare_r1_current_day(raw)
        self.assertEqual(prepared.order_part_identity,{
            '19':dict(order_id='OLD',order_key=19,part_id=1),
            '92':dict(order_id='NEW-O',order_key=92,part_id=1),
            '93':dict(order_id='NEW-S',order_key=93,part_id=1)})
        _,_,stock,_,_=calculate_r1_requirements(prepared,raw)
        self.assertTrue(stock);self.assertEqual({r['order_id'] for r in stock},{'19'})

    def test_owned_single_and_inactive_connection_preserves_existing_outputs(self):
        for rows in ([],[feed('ONE')],[feed('ONE',25)]):
            closing=calculate(state(91),rows)
            raw=payload(rows);raw.pop('order_input');raw['orders']=calculation_order_rows(closing)
            self.assertEqual(calculate_current_day(raw,defer_pick=True),
                calculate_current_day(raw,defer_pick=True,_owned_order_closing=closing))

    def test_actual_daily_order_closing_keys_reach_unchanged_allocation_sort(self):
        rows=[feed('Z',25),feed('A',35)]
        closing=calculate(state(91),rows)
        raw=payload(rows);raw.pop('order_input')
        raw['orders']=calculation_order_rows(closing)
        prepared=prepare_r1_current_day(raw)
        _,_,stock,git,trace=calculate_r1_requirements(prepared,raw)
        self.assertTrue(stock);self.assertEqual({row['order_id'] for row in stock},{'Z'})
        self.assertEqual([r['OrderKey'] for r in closing['SpikeOrderData']],[92,93])

    def test_typed_identity_closing_reconstruction_then_next_date_uses_own_counter(self):
        value=state(91);rows=[feed('O1'),feed('S1',25),feed('O2'),feed('S2',35)]
        closing=calculate(value,rows);own=deepcopy(closing)
        run=SimpleNamespace(pk='fc11f6b1-dc49-4fce-98c0-cdf4b6a3a49e')
        for name in ('SpikeOrderData','SpikeOrderClosureHistory','NewSpikeOrders','ElephantOrders','OrderIdentity'):
            path='closing/orders/'+name;records=[]
            with patch.object(typed,'bulk',side_effect=lambda query,values:records.extend(values)):
                meta=typed.save_image(run,path,path,storage(closing[name]))
            cursor=MagicMock();cursor.fetchmany.side_effect=[[tuple(r[2:]) for r in records],[]]
            with patch.object(typed.connection,'chunked_cursor') as context:
                context.return_value.__enter__.return_value=cursor
                own[name]=typed.load_image(run,meta)
            self.assertEqual(own[name],storage(closing[name]))
            self.assertEqual(cursor.execute.call_args.args[1],[run.pk,path])
        next_rows=[*rows,feed('S3',25),feed('O3')]
        successor=calculate(own,next_rows,TOMORROW,TODAY)
        self.assertEqual([(r['CustomerOrderId'],r['OrderKey']) for r in successor['SpikeOrderData']],
            [('O1',92),('O2',93),('S1',94),('S2',95),('O3',96),('S3',97)])
        self.assertEqual(successor['OrderIdentity'][0]['LastValue'],97)

    def test_explicit_empty_counter_and_no_counter_compatibility_boundary(self):
        value=state()
        masters=[dict(SKUCode='R1SKU',WhCode='R1-C',Norm=90,SpikeThreshold=20,ElephantOrderCapping=1000)]
        imported=reconcile_order_feed(source(value,[feed('A'),feed('B')]),masters,TODAY)
        self.assertEqual([r['OrderKey'] for r in imported['orders']],[51,52])
        unbound=source(value,[feed('A')]);del unbound['identity_last_value']
        self.assertIsNone(reconcile_order_feed(unbound,masters,TODAY)['orders'][0]['OrderKey'])
        raw=payload([feed('A',25),feed('B',35)]);del raw['order_input']['identity_last_value']
        with self.assertRaisesRegex(ValueError,'explicit owned counter'):prepare_r1_current_day(raw)

    def test_contract_qualification_and_native_preflight_allow_exhausted_inactive_counter(self):
        self.assertEqual(QUALIFICATION,'APPROVED_PRODUCTION_CONTRACT_CHANGE')
        self.assertEqual(CONTRACT,'preserved-feed-row-ordinary-before-spike-v1')
        from tests.production_daily_fixture import initialized_input
        from tests.initialization_input_fixture import encoded
        from mta.runtime import production_preflight as preflight
        value=initialized_input();value['opening']['state']['orders']['OrderIdentity'][0]['LastValue']=MAX_KEY
        raw,sha,args=encoded(value);report=preflight.initialization(raw,sha,**args)
        self.assertFalse(any(issue['code']=='ORDER_IDENTITY_REQUIRED' for issue in report['issues']))
        self.assertFalse(report['production_ready'])


if __name__=='__main__':unittest.main()
