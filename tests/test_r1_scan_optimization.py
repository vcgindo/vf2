"""R1 join semantics and bounded growth, independent of the large trial.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
from copy import deepcopy
from decimal import Decimal, InvalidOperation
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from mta.planning import projections
from mta.application import production_order_allocation as allocation
from mta.application.r1_order_input import reconcile_order_feed
from mta.domain.virtual_norm import resolve_virtual_norm
from tests.test_production_order_allocation import inputs, order, daily, TODAY
from tests.test_production_order_identity import source, state, feed, opening


class CountedRows(list):
    def __iter__(self):
        for row in super().__iter__():
            self.visits += 1
            yield row

    def __init__(self, rows):
        super().__init__(rows)
        self.visits = 0


def bands_case(n):
    positions = CountedRows([dict(sku_code='A', location_code=str(i),
        stock_quantity=str(i-2), goods_in_transit_quantity=str(i%3)) for i in range(n)])
    prepared = SimpleNamespace(track_a={'foundation':{'hierarchy':[],
        'inventory_positions':positions}}, phase_out_membership=())
    requirements = [dict(sku_code='A', location_code=str(i), effective_norm={'value':'10'},
        requirement=dict(pso='0',pso_threshold='100',due_spike='0',routed_due_spike='0')) for i in range(n)]
    return prepared, requirements, positions


def wide_source(n):
    from tests.test_daily_r1_optimization import order_free_source
    raw=order_free_source()
    def replace(value, location):
        if isinstance(value,dict):return {k:replace(v,location) for k,v in value.items()}
        if isinstance(value,list):return [replace(v,location) for v in value]
        return location if value == 'R1-C' else value
    groups=[raw['foundation'][key] for key in ('locations','sku_locations','inventory_positions','hierarchy')]
    groups += [raw[key] for key in ('policies','stock_openings','routing')]
    for rows in groups:
        template=next(row for row in rows if 'R1-C' in row.values())
        for i in range(1,n):
            row=replace(template,'C'+str(i))
            if 'rationing_priority' in row:row['rationing_priority']=i+10
            rows.append(row)
    return raw


class R1ScanTests(unittest.TestCase):
    def test_inventory_first_occurrence_signed_values_and_linear_row_visits(self):
        for n in (16,32,64):
            prepared,requirements,positions=bands_case(n)
            positions.append(dict(positions[0],stock_quantity='999',goods_in_transit_quantity='999'))
            with patch.object(projections,'calculate_requirement_bands',side_effect=lambda rows,**kw:rows):
                rows=projections._requirement_band_rows(prepared,{'policies':[]},requirements,[],[])
            self.assertEqual([(r.stock,r.goods_in_transit) for r in rows],
                [(Decimal(i-2),Decimal(i%3)) for i in range(n)])
            self.assertEqual(positions.visits,n+1)

    def test_missing_inventory_keeps_failure_after_prior_norm_validation(self):
        prepared,requirements,positions=bands_case(1)
        positions.clear()
        with self.assertRaises(StopIteration):
            projections._requirement_band_rows(prepared,{'policies':[]},requirements,[],[])
        requirements[0]['effective_norm']['value']='invalid'
        with self.assertRaises(InvalidOperation):
            projections._requirement_band_rows(prepared,{'policies':[]},requirements,[],[])

    def test_direct_advance_uses_exact_order_and_destination_white_membership(self):
        prepared,requirements,_=bands_case(1)
        bpp=[dict(order_id='O',destination_location_code='0',colour='white',eligible_for_requirement_band=False)]
        advances=[dict(sku_code='A',source_location_code='0',destination_location_code=None,
            order_id='O',allocation_type='advance-stock',allocated_quantity='2')]
        with patch.object(projections,'calculate_requirement_bands',side_effect=lambda rows,**kw:rows):
            result=projections._requirement_band_rows(prepared,{'policies':[]},requirements,bpp,advances)
            self.assertEqual(result[0].advance_order_blue,Decimal(2))
            advances[0]['order_id']='o'
            result=projections._requirement_band_rows(prepared,{'policies':[]},requirements,bpp,advances)
            self.assertEqual(result[0].advance_order_blue,Decimal(0))

    def test_allocation_many_skus_or_many_locations_linear_key_work_and_exact_qty(self):
        for one_sku in (False,True):
            counts=[]
            for n in (16,32,64):
                stock=[]; facts=[]; orders=[]
                for i in range(n):
                    sku,wh=('A',str(i)) if one_sku else (str(i),'C')
                    facts.append(dict(daily(wh,stock=5),SKUCode=sku))
                    stock.append(dict(SKUCode=sku,WHCode=wh,StockForRationing=5))
                    orders.append(dict(order(i+1,qty=8,wh=wh),SKUCode=sku))
                original=deepcopy((facts,stock,orders))
                with patch.object(allocation,'_k',wraps=allocation._k) as keys:
                    rows=allocation.allocated_orders(**inputs(daily_consumption=facts,
                        stock_calculation=stock,spike_orders=orders))
                counts.append(keys.call_count)
                self.assertEqual([(r['OrderKey'],r['Qty'],r['OrderWiseAllocatedQty']) for r in rows],
                    [(i+1,8,5) for i in range(n)])
                self.assertEqual((facts,stock,orders),original)
            self.assertLessEqual(counts[2],counts[0]*4+20)

    def test_reconciliation_multipart_normalized_identity_and_elephant_duplicates(self):
        value=state(50)
        value['SpikeOrderData']=[opening('A',1,qty=5),opening('A',2,qty=7,part=2),opening('GONE',3)]
        master=dict(SKUCode='R1SKU',WhCode='R1-C',Norm=90,SpikeThreshold=20,
            ElephantOrderCapping=1000,TopmostWhCode='R1-P',TopmostWhNorm=300,RLTTillPlantSupplier=2)
        incoming=[feed('a ',8),feed('NEW',5)]
        raw=source(value,incoming); before=deepcopy(raw)
        result=reconcile_order_feed(raw,[master],'2026-01-15',elephant_orders=[])
        self.assertEqual([(r['OrderKey'],r['Qty'],r['OriginalQty']) for r in result['orders']],
                         [(1,8,5),(2,8,7),(51,5,5)])
        self.assertEqual([r['CustomerOrderId'] for r in result['closure_history']],['GONE'])
        self.assertEqual(raw,before)
        elephant=dict(CustomerOrderID='E',SKUCode='R1SKU',WhCode='R1-C',Qty=2000,
            TopmostWhCode='R1-P',TopmostWhNorm=300,RLTUptoSuppOrPlant=2,
            IntroDate='2026-01-12',CustomerExpectedDate=None,DueDate=None)
        result=reconcile_order_feed(source(state(),[feed('E',2001)]),[master],'2026-01-15',
            elephant_orders=[elephant,deepcopy(elephant)])
        self.assertEqual([r['Qty'] for r in result['elephant_orders']],[2001,2001])
        self.assertEqual(result['orders'],[])

    def test_wide_group_average_is_lazy_and_once_per_actual_group(self):
        from mta.planning.engine import calculate_current_day
        from mta.application import r1_calculation as r1
        raw=wide_source(32)
        # Zero Norm children exercise physical averages; direct demand exercises
        # the same group's average again without changing its arithmetic.
        for rows,field in ((raw['foundation']['sku_locations'],'base_norm'),
                           (raw['stock_openings'],'norm'),(raw['routing'],'norm')):
            for row in rows:
                if row.get('location_code')!='R1-P':row[field]=0
        before=deepcopy(raw)
        with patch('mta.domain.virtual_norm.average_positive_norm',
                   wraps=__import__('mta.domain.virtual_norm',fromlist=['average_positive_norm']).average_positive_norm) as average:
            result=calculate_current_day(raw,defer_pick=True)
        self.assertEqual(len(result['r1_requirement']),33)
        self.assertLessEqual(average.call_count,1)
        self.assertEqual(raw,before)
        from mta.domain.virtual_norm import _PeerNormGroup
        norms=(Decimal(10),)
        group=_PeerNormGroup(norms)
        actual=resolve_virtual_norm(Decimal(0),Decimal(20),kind='CHILD',peer_norms=norms,_peer_group=group)
        self.assertEqual(actual.value,Decimal(10))
        with self.assertRaisesRegex(ValueError,'does not belong'):
            resolve_virtual_norm(Decimal(0),Decimal(20),kind='CHILD',
                peer_norms=(Decimal(11),),_peer_group=group)
        with patch('mta.domain.virtual_norm.average_positive_norm') as average:
            with self.assertRaises(ValueError):
                resolve_virtual_norm(Decimal(-1),Decimal(0),kind='CHILD',_peer_group=group)
            average.assert_not_called()

    def test_static_colour_reference_remains_bound_to_report_producer(self):
        from mta.presentation.native_report_colours import reference
        rows=reference()['rows']
        self.assertEqual(rows,[dict(Color=c,SequenceNo=i) for i,c in
            enumerate(('Black','Red','Yellow','Green','Blue','White','Grey'),1)])
        import json
        from pathlib import Path
        from mta.presentation.context import PublicationUnavailable
        read=Path.read_bytes
        def wrong_pin(path):
            raw=read(path)
            if path.name=='native_report_colours_v1.json':
                value=json.loads(raw);value['source_sha256']='0'*64
                return json.dumps(value).encode()
            return raw
        with patch.object(Path,'read_bytes',new=wrong_pin), self.assertRaisesRegex(
                PublicationUnavailable,'native_report_colour_reference_changed'):
            reference()

    def test_route_reuse_is_bound_to_exact_node_tuple(self):
        from datetime import date
        from mta.domain.r1_current_day import RouteNode, _RouteLookup, route_new_spike_order
        nodes=(RouteNode('C',True,Decimal(10),Decimal(10),'P',1),
               RouteNode('P',False,None,None,None,None))
        other=(nodes[0],RouteNode('X',False,None,None,None,None))
        arguments=dict(business_date=date(2026,1,15),order_id='ONE',sku_code='A',
            source_location_code='C',quantity=Decimal(20),customer_expected_date=None)
        self.assertEqual(route_new_spike_order(**arguments,nodes=nodes),
                         route_new_spike_order(**arguments,nodes=nodes,_route_lookup=_RouteLookup(nodes)))
        with self.assertRaisesRegex(ValueError,'does not belong'):
            route_new_spike_order(**arguments,nodes=nodes,_route_lookup=_RouteLookup(other))



if __name__ == '__main__':
    unittest.main()
