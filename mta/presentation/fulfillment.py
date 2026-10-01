"""CollectOrderFulfillmentData.sql report projections, not order calculation.

The inputs are the day's already-produced rationed rows, standard attributes,
orders and original routes. No aggregate-to-order reconstruction or legacy fix.
"""
from collections import defaultdict
from datetime import date
from decimal import Decimal
from mta.presentation.excess import checked_integer
from mta.presentation.rrr import index,sql_key

PRODUCER_SHA='b6ae768bd632c831050453f7702a2016bf8db11bc69a2a05088f31c030d3d3b1'
SUMMARY_FIELDS=('Coverage','Tags','SKUCode','WhCode','ParentWhCode','VirtualNorm','Norm','Stock','GIT',
    'RationedQty','NormReq','SpikeReq','RelPSOAndCNR','TotalReq','Gap','PhysicalInventoryPen',
    'PhysicalInventoryColor','PipelineInventoryPen','PipelineInventoryColor','Price','TotalSnP')
DETAIL_FIELDS=('OrderNo','SKUCode','WhCode','Introdate','PendingQty','DueDate','Customer','Price','OrderStatus')


def routes_for_orders(calculated,orders):
    populations=[r['rows'] for r in calculated if r['capability']=='r1_order_route']
    if len(populations)!=1:
        raise ValueError('Exactly one produced original-route population required')
    by_id=index(orders,'CustomerOrderId')
    result=[]
    for route in populations[0]:
        candidates=by_id.get(sql_key(route['order_id']),[])
        if 'order_key' in route:
            candidates=[r for r in candidates if r['OrderKey']==int(route['order_key'])]
        if len(candidates)!=1:
            raise ValueError('Original-route OrderKey mapping is absent or ambiguous')
        order=candidates[0]
        if 'sku_code' in route and sql_key(route['sku_code'])!=sql_key(order['SKUCode']):
            raise ValueError('Produced route SKU differs from its order')
        result.append(dict(OrderKey=order['OrderKey'],SrcWhCode=route['location_code'],
                           DestWhCode=route['child_location_code'],DueDate=route['due_date']))
    return result


def amount(quantity,price):
    if quantity is None or price is None:
        return None
    return checked_integer(Decimal(checked_integer(quantity,64))*Decimal(str(price)),64)


def produce_summary(rationed,standards):
    standard=index(standards,'SKUCode','WhCode')
    result=[]
    copies=('SKUCode','WhCode','ParentWhCode','VirtualNorm','Norm','Stock','GIT','NormReq','RelPSOAndCNR',
            'PhysicalInventoryPen','PhysicalInventoryColor')
    aliases={'RationedQty':'RationedReq','SpikeReq':'ResidualSnP','TotalReq':'Req',
             'PipelineInventoryPen':'DispatchPen','PipelineInventoryColor':'DispatchColor','TotalSnP':'SnPToNetOff'}
    for source in rationed:
        if source['VirtualNorm'] is None or source['VirtualNorm']<=0:
            continue
        for attr in standard.get(sql_key(source['SKUCode'],source['WhCode']),[]):
            row={name:source[name] for name in copies}
            row.update({target:source[name] for target,name in aliases.items()})
            row.update(Tags=attr['Tags'],Price=amount(source['Req'],attr['Price']),
                Gap=None if source['Req'] is None or source['RationedReq'] is None else
                    checked_integer(source['Req']-source['RationedReq']))
            gap,total=row['Gap'],row['TotalReq']
            row['Coverage']=None
            if gap is not None and total is not None:
                lower=Decimal('33.33')*total/100
                upper=Decimal('66.67')*total/100
                row['Coverage']=('Gap < 33%' if gap<lower else
                    '33% <= Gap <= 67%' if gap>=lower and gap<=upper else
                    'Gap > 67%' if gap>upper else None)
            for name in ('VirtualNorm','Norm','Stock','GIT','RationedQty','NormReq','SpikeReq','RelPSOAndCNR','TotalReq','TotalSnP'):
                row[name]=checked_integer(row[name])
            for name in ('PhysicalInventoryPen','PipelineInventoryPen'):
                row[name]=None if row[name] is None else format(Decimal(str(row[name])),'.2f')
            result.append({name:row[name] for name in SUMMARY_FIELDS})
    return result


def produce_details(orders,routes,standards,business_date):
    today=date.fromisoformat(str(business_date))
    standard=index(standards,'SKUCode','WhCode')
    by_order=defaultdict(list)
    for route in routes:
        if route['OrderKey'] is not None and route['DueDate'] is not None and date.fromisoformat(route['DueDate'])<=today:
            by_order[route['OrderKey']].append(route)
    result=[]
    for order in orders:
        selected=by_order.get(order['OrderKey'],[])
        latest=max((r['DueDate'] for r in selected),default=None)
        selected=[r for r in selected if r['DueDate']==latest] or [None]
        for attr in standard.get(sql_key(order['SKUCode'],order['WhCode']),[]):
            for route in selected:
                due=None if route is None else route['DueDate']
                status=('Others' if order['DueDate'] is None else
                        'Due' if due==str(business_date) else
                        'Over Due' if due is not None and due<str(business_date) else None)
                source=None if route is None else route['SrcWhCode']
                result.append(dict(OrderNo=order['CustomerOrderId'],SKUCode=order['SKUCode'],
                    WhCode=order['WhCode'] if source is None else source,Introdate=order['IntroDate'],
                    PendingQty=checked_integer(order['Qty']),DueDate=due,Customer=None,
                    Price=amount(order['Qty'],attr['Price']),OrderStatus=status))
    return result
