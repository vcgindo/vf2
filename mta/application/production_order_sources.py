"""Project current computed order/stock/band owners into native allocation inputs."""
from datetime import date
from decimal import Decimal

from mta.application.operational_bor import _int
from mta.application.r1_importer_master import _sql_key
from mta.application.production_order_allocation import allocated_orders


def _same(*values):
    return tuple(_sql_key(value) if value is not None else None for value in values)


def _winner(values, label):
    if not values:
        return None
    if any(value != values[0] for value in values[1:]):
        raise ValueError('Native order source has differing update winners: '+label)
    return values[0]


def produce(*, today, calculated, orders, dbm_master, attributes, daily_consumption):
    required=('r1_order_route','r1_order_bpp','r1_advance_stock_allocation',
              'r1_git_advance_allocation','r1_stock_balance','r1_order_allocation_bands')
    if any(not isinstance(calculated.get(name),list) for name in required):
        raise ValueError('Complete same-run order source capabilities required')
    def order_key(row):
        if 'order_key' in row:
            matches=[item for item in orders if item['OrderKey']==row['order_key']
                     and item['CustomerOrderId']==row['order_id']]
            if len(matches)!=1:
                raise ValueError('Computed order part differs from its owned closing order')
            return row['order_key']
        matches=[item['OrderKey'] for item in orders if item['CustomerOrderId']==row['order_id']]
        if len(matches)!=1:
            raise ValueError('Computed order must identify exactly one owned order part')
        return matches[0]
    routes=[dict(OrderKey=order_key(row),DestWhCode=row['child_location_code'],
                 SrcWhCode=row['location_code'],DueDate=row['due_date'])
            for row in calculated['r1_order_route']]
    daily=[]
    for name,kind in (('r1_advance_stock_allocation','adv-stock'),('r1_git_advance_allocation','GIT')):
        for row in calculated[name]:
            daily.append(dict(OrderKey=order_key(row),DestWhCode=row['destination_location_code'],
                SrcWhCode=row['source_location_code'],DueDate=today,Qty=_int(row['allocated_quantity']),Type=kind))
    colours=[]
    for route in routes:
        for order in orders:
            if order['OrderKey']!=route['OrderKey']:
                continue
            destination=route['SrcWhCode'] if route['DestWhCode'] is None else route['DestWhCode']
            rows=[row for row in calculated['r1_order_bpp'] if order_key(row)==route['OrderKey']
                and _same(row['sku_code'],row['source_location_code'],row['destination_location_code'])==
                    _same(order['SKUCode'],route['SrcWhCode'],destination)]
            # Native BPP UPDATE joins the current DBM master on SKU/destination/parent.
            qualified=any(_same(master['SKUCode'],master['WhCode'],master['ParentWhCode'])==
                _same(order['SKUCode'],destination,route['SrcWhCode']) for master in dbm_master)
            value=_winner([(Decimal(row['bpp']).quantize(Decimal('.01')),row['colour'].title())
                           for row in rows], 'route BPP') if qualified else None
            colours.append(dict(SKUCode=order['SKUCode'],DestWhCode=destination,
                SrcWhCode=route['SrcWhCode'],OrderKey=route['OrderKey'],DueDate=route['DueDate'],
                BPP=value[0] if value else None,OrderColor=value[1] if value else None))
    # Direct route copies the produced downstream colour; future self is White.
    for row in colours:
        if _same(row['DestWhCode'])!=_same(row['SrcWhCode']):
            continue
        value=_winner([(other['BPP'],other['OrderColor']) for other in colours
            if other['OrderKey']==row['OrderKey'] and _same(row['SrcWhCode'])==_same(other['DestWhCode'])
            and _same(other['DestWhCode'])!=_same(other['SrcWhCode'])], 'self BPP')
        if value is not None:
            row['BPP'],row['OrderColor']=value
        due=_winner([route['DueDate'] for route in routes if route['OrderKey']==row['OrderKey']
            and _same(route['SrcWhCode'])==_same(row['DestWhCode'])], 'self destination date')
        if due is not None and date.fromisoformat(due)>date.fromisoformat(today):
            row['BPP'],row['OrderColor']=Decimal('-1.00'),'White'
    bands=[]
    seen=set()
    for row in calculated['r1_order_allocation_bands']:
        grain=_same(row['SKUCode'],row['WhCode'])
        if row['ParentWhCode'] is None or grain in seen:
            raise ValueError('Native allocation capture requires the unique computed grain and a producer-owned parent')
        seen.add(grain)
        bands.append({field: value if field in ('SKUCode','WhCode','ParentWhCode') else _int(value)
                      for field,value in row.items()})
    return allocated_orders(business_date=today,daily_consumption=daily_consumption,
        stock_calculation=[dict(SKUCode=row['sku_code'],WHCode=row['location_code'],
                                StockForRationing=_int(row['stock_for_rationing']))
                           for row in calculated['r1_stock_balance']],
        spike_orders=orders,route_original=routes,route_daily=daily,requirement_bands=bands,
        order_colours=colours,
        dbm_master=[dict(SKUCode=row['SKUCode'],WHCode=row['WhCode'],Norm=row['Norm'],RLT=row['RLT'])
                    for row in dbm_master],sku_loc_attributes=attributes)
