"""Canonical ExcessInventoryDetails current-day report producer.

CollectExcessInventoryDetails.sql SHA256
71bb48766d3af7a739b90c511124f9ad99072066283536fd28a9530f3640b8c4.
Consumes already calculated rationed-report rows; never reruns rationing/DBM.
Historical retention belongs to the caller, not this current-day projection.
"""
from datetime import date
from decimal import Decimal

from mta.presentation.rrr import index, sql_key

PRODUCER_SHA = '71bb48766d3af7a739b90c511124f9ad99072066283536fd28a9530f3640b8c4'
INT_FIELDS = ('Norm','VirtualNorm','Stock','GIT','BlueReq','RequiredQty','ExcessQty')
FIELDS = ('Tags','SKUCode','WhCode','ParentWhCode','Norm','VirtualNorm','Stock','GIT',
          'BlueReq','RequiredQty','PhysicalInventoryPen','PhysicalInventoryColor',
          'PipelineInventoryPen','PipelineInventoryColor','ExcessQty','Amount','ReportDate')


def checked_integer(value, bits=32):
    if value is None:
        return None
    result = int(value)
    if not -(2**(bits-1)) <= result < 2**(bits-1):
        raise OverflowError('Canonical SQL integer conversion overflow')
    return result


def produce(rationed, standards, business_date):
    """SQL inner join bag, white predicate, ABS and destination conversions."""
    business_date = date.fromisoformat(str(business_date))
    standard = index(standards,'SKUCode','WhCode')
    rows = []
    for source in rationed:
        if sql_key(source['PhysicalInventoryColor']) != sql_key('White'):
            continue
        if source['VirtualNorm'] is None or source['Stock'] is None:
            continue
        # SQL INT subtraction and ABS overflow are not repaired/coerced away.
        gap = checked_integer(checked_integer(source['VirtualNorm'])-checked_integer(source['Stock']))
        excess = checked_integer(abs(gap))
        if not excess:
            continue
        for attr in standard.get(sql_key(source['SKUCode'],source['WhCode']),[]):
            row = {name:source[name] for name in ('SKUCode','WhCode','ParentWhCode',
                    'Norm','VirtualNorm','Stock','GIT','BlueReq','PhysicalInventoryColor')}
            row.update(Tags=attr['Tags'],RequiredQty=source['Req'],ExcessQty=excess,
                       PipelineInventoryColor=source['DispatchColor'],ReportDate=business_date.isoformat())
            for name in INT_FIELDS:
                row[name] = checked_integer(row[name])
            for target,field in (('PhysicalInventoryPen','PhysicalInventoryPen'),('PipelineInventoryPen','DispatchPen')):
                row[target] = None if source[field] is None else format(Decimal(str(source[field])),'.2f')
            row['Amount'] = (None if attr['Price'] is None else
                             checked_integer(Decimal(excess)*Decimal(str(attr['Price'])),64))
            rows.append({name:row[name] for name in FIELDS})
    return rows
