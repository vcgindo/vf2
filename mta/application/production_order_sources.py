"""Project current computed order/stock/band owners into native allocation inputs."""
from datetime import date
from decimal import Decimal

from mta.application.stage_observation import stage
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
    # Exact part identity validation is kept separate from SQL-style route
    # comparison (_same permits None components here, unlike allocation._k).
    orders_by_key, orders_by_customer = {}, {}
    for item in orders:
        orders_by_key.setdefault(item['OrderKey'], []).append(item)
        orders_by_customer.setdefault(item['CustomerOrderId'], []).append(item)
    def order_key(row):
        if 'order_key' in row:
            matches=[item for item in orders_by_key.get(row['order_key'], ())
                     if item['CustomerOrderId']==row['order_id']]
            if len(matches)!=1:
                raise ValueError('Computed order part differs from its owned closing order')
            return row['order_key']
        matches=orders_by_customer.get(row['order_id'], ())
        if len(matches)!=1:
            raise ValueError('Computed order must identify exactly one owned order part')
        return matches[0]['OrderKey']
    routes=[dict(OrderKey=order_key(row),DestWhCode=row['child_location_code'],
                 SrcWhCode=row['location_code'],DueDate=row['due_date'])
            for row in calculated['r1_order_route']]
    daily=[]
    for name,kind in (('r1_advance_stock_allocation','adv-stock'),('r1_git_advance_allocation','GIT')):
        for row in calculated[name]:
            daily.append(dict(OrderKey=order_key(row),DestWhCode=row['destination_location_code'],
                SrcWhCode=row['source_location_code'],DueDate=today,Qty=_int(row['allocated_quantity']),Type=kind))
    colours=[]
    bpp_by_order = None
    master_routes = None
    for route in routes:
        for order in orders_by_key.get(route['OrderKey'], ()):
            destination=route['SrcWhCode'] if route['DestWhCode'] is None else route['DestWhCode']
            if bpp_by_order is None:
                bpp_by_order = {}
                for row in calculated['r1_order_bpp']:
                    bpp_by_order.setdefault(order_key(row), []).append(row)
            rows=[row for row in bpp_by_order.get(route['OrderKey'], ())
                if _same(row['sku_code'],row['source_location_code'],row['destination_location_code'])==
                    _same(order['SKUCode'],route['SrcWhCode'],destination)]
            # Native BPP UPDATE joins current DBM SKU/destination/parent.
            if master_routes is None:
                master_routes = {_same(m['SKUCode'],m['WhCode'],m['ParentWhCode']) for m in dbm_master}
            qualified=_same(order['SKUCode'],destination,route['SrcWhCode']) in master_routes
            value=_winner([(Decimal(row['bpp']).quantize(Decimal('.01')),row['colour'].title())
                           for row in rows], 'route BPP') if qualified else None
            colours.append(dict(SKUCode=order['SKUCode'],DestWhCode=destination,
                SrcWhCode=route['SrcWhCode'],OrderKey=route['OrderKey'],DueDate=route['DueDate'],
                BPP=value[0] if value else None,OrderColor=value[1] if value else None))
    # Only non-self colour rows supply the self UPDATE, so these references
    # remain unchanged while self rows are updated sequentially below.
    downstream, routes_by_order = {}, {}
    for other in colours:
        if _same(other['DestWhCode']) != _same(other['SrcWhCode']):
            downstream.setdefault((other['OrderKey'], _same(other['DestWhCode'])), []).append(other)
    for route in routes:
        routes_by_order.setdefault(route['OrderKey'], []).append(route)
    # Direct route copies the produced downstream colour; future self is White.
    for row in colours:
        if _same(row['DestWhCode'])!=_same(row['SrcWhCode']):
            continue
        value=_winner([(other['BPP'],other['OrderColor']) for other in
            downstream.get((row['OrderKey'], _same(row['SrcWhCode'])), ())], 'self BPP')
        if value is not None:
            row['BPP'],row['OrderColor']=value
        due=_winner([route['DueDate'] for route in routes_by_order.get(row['OrderKey'], ())
            if _same(route['SrcWhCode'])==_same(row['DestWhCode'])], 'self destination date')
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
    del orders_by_key, orders_by_customer, bpp_by_order, master_routes, downstream, routes_by_order
    with stage('r1_native_order_allocation'):
        return allocated_orders(business_date=today,daily_consumption=daily_consumption,
            stock_calculation=[dict(SKUCode=row['sku_code'],WHCode=row['location_code'],
                                    StockForRationing=_int(row['stock_for_rationing']))
                               for row in calculated['r1_stock_balance']],
            spike_orders=orders,route_original=routes,route_daily=daily,requirement_bands=bands,
            order_colours=colours,
            dbm_master=[dict(SKUCode=row['SKUCode'],WHCode=row['WhCode'],Norm=row['Norm'],RLT=row['RLT'])
                        for row in dbm_master],sku_loc_attributes=attributes)
