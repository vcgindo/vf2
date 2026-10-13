"""Same-day full-order and Norm RRR projection from owned calculation outputs.

Preserves the source UNION, nullable arithmetic and ambiguous UPDATE denials.
Order allocations must come from the order producer, never an input upload.
"""
from collections import OrderedDict
from decimal import Decimal

from mta.presentation import daily_rrr_colour as norm

VERSION = 'fresh-production-rrr-v1'
COLOURS = ('Black', 'Red', 'Yellow', 'Green', 'White')
REQ = ('TOBlack_ReqQty', 'TOR_ReqQty', 'TOY_ReqQty', 'TOGreen_ReqQty', 'TOBlue_ReqQty')
ALLOC = ('TOBlack_AllocQty', 'TOR_AllocQty', 'TOY_AllocQty', 'TOGreen_AllocQty', 'TOBlue_AllocQty')
ORDER_FIELDS = ('SKUCode', 'DestWhCode', 'SrcWhCode', 'OrderColor', 'Qty', 'PackSizeWiseAllocatedQty')
REPORT_FIELDS = (*norm._REPORT_FIELDS, 'PackSize', 'DirectSpikeOverdue',
                 'SpikeOverdueAtParent', 'ResidualChildrenSnP')


def _sum(values):
    selected = [value for value in values if value is not None]
    return None if not selected else norm._int(sum(selected), 'SUM')


def _signature(row):
    return tuple(norm._sql_key(value) if isinstance(value, str) else value for value in row.values())


def _distinct(rows):
    seen = set()
    for row in rows:
        signature = _signature(row)
        if signature not in seen:
            seen.add(signature)
            yield row


def _unique_update(rows, label):
    values = list(_distinct(rows))
    if len(values) > 1:
        raise ValueError('Ambiguous RRR source UPDATE: ' + label)
    return values[0] if values else None


def _scope(context, bands, capabilities):
    if context != {'producer': VERSION} or set(capabilities) != {'AllocatedOrders'}:
        raise ValueError('Native RRR producer context required')
    if not isinstance(capabilities['AllocatedOrders'], list):
        raise ValueError('Explicit computed AllocatedOrders required')


def produce(*, rationed_report, requirement_bands, bpr_master,
            advance_stock_allocations, allocated_orders):
    """Return all 24 native columns; order rows precede Norm rows in retained order."""
    for name, rows, fields in (
            ('rationed report', rationed_report, REPORT_FIELDS),
            ('requirement bands', requirement_bands, norm._BAND_INPUT_FIELDS),
            ('BPR master', bpr_master, ('SKUCode', 'WHCode')),
            ('allocated orders', allocated_orders, ORDER_FIELDS)):
        if not isinstance(rows, list):
            raise ValueError('Explicit same-run RRR population required: ' + name)
        for row in rows:
            norm._complete(row, fields, name)

    groups = OrderedDict()
    for source in allocated_orders:
        key = norm._key(source['SKUCode'], source['DestWhCode'], source['SrcWhCode'])
        if key is None:
            raise ValueError('Computed allocated-order identity cannot be NULL')
        group = groups.setdefault(key, dict(source=source, rows=[]))
        row = dict(source)
        for field in ('Qty', 'PackSizeWiseAllocatedQty'):
            row[field] = norm._int(row[field], field)
        group['rows'].append(row)

    orders = []
    for band in requirement_bands:
        quantities = [norm._int(band[field], field) for field in norm._BAND_INPUT_FIELDS[-5:]]
        requirement = norm._add(*quantities)
        if requirement is None or requirement <= 0:
            continue
        parent = norm._key(band['sku_code'], band['parent_location_code'])
        if parent is None:
            continue
        for master in bpr_master:
            if norm._key(master['SKUCode'], master['WHCode']) != parent:
                continue
            key = norm._key(band['sku_code'], band['location_code'])
            for report in rationed_report:
                if key is not None and norm._key(report['SKUCode'], report['WhCode']) == key:
                    orders.append(_order(band['sku_code'], band['location_code'],
                        band['parent_location_code'], quantities, report))
    orders = list(_distinct(orders))
    present = {norm._key(row['SKUCode'], row['WhCode'], row['ParentWhCode']) for row in orders}
    for key, group in groups.items():
        if key in present:
            continue
        # First CTE is DISTINCT by colour with window SUM(Qty), then SUM by route.
        quantities = [_sum([row['Qty'] for row in group['rows'] if row['OrderColor'] == colour])
                      for colour in COLOURS]
        # A different colour contributes an explicit zero to each CASE bucket.
        for index, colour in enumerate(COLOURS):
            if any(row['OrderColor'] != colour for row in group['rows']):
                quantities[index] = quantities[index] or 0
        requirement = norm._add(*quantities)
        if requirement is not None and requirement > 0:
            source = group['source']
            orders.append(_order(source['SKUCode'], source['DestWhCode'], source['SrcWhCode'],
                                 quantities, None))

    advances = {}
    for row in advance_stock_allocations:
        if row.get('allocation_type') != 'advance-stock':
            raise ValueError('Explicit stock-only advance producer required')
        key = norm._key(row['sku_code'], row['source_location_code'])
        advances[key] = advances.get(key, 0) + norm._int(row['allocated_quantity'], 'allocated_quantity', False)
    for row in orders:
        key = norm._key(row['SKUCode'], row['WhCode'], row['ParentWhCode'])
        group = groups.get(key)
        if group:
            row['RationedQty'] = _sum([item['PackSizeWiseAllocatedQty'] for item in group['rows']])
            for colour, field in zip(COLOURS, ALLOC):
                row[field] = _sum([item['PackSizeWiseAllocatedQty'] for item in group['rows']
                                   if item['OrderColor'] == colour])
            if norm._key(row['WhCode']) == norm._key(row['ParentWhCode']):
                remaining = norm._sub(row['Stock'], row['RationedQty'])
                row['LeftoverParentStock'] = remaining if remaining is not None and remaining > 0 else 0
        updates = []
        for report in rationed_report:
            if norm._key(report['SKUCode'], report['WhCode']) != norm._key(row['SKUCode'], row['WhCode']):
                continue
            pack = report['PackSize'] if norm._key(row['WhCode']) == norm._key(row['ParentWhCode']) else report['ParentPackSize']
            # Native target is int: decimal quotient converts by truncating toward zero.
            casepacks = None if row['RationedQty'] is None or pack is None else norm._sql_divide(row['RationedQty'], norm._int(pack, 'pack'))
            updates.append(dict(Norm=0, VirtualNorm=norm._add(report['DirectSpikeOverdue'],
                report['SpikeOverdueAtParent'], report['ResidualChildrenSnP']), Stock=report['Stock'],
                GIT=report['GIT'], LeftoverParentStock=report['LeftoverParentStock'], RationedCasePacks=casepacks))
        update = _unique_update(updates, 'rationed report')
        if update is not None:
            row.update(update)
        row['DispatchColor'] = next((colour for colour, field in zip(('Black','Red','Yellow','Green','Blue'), REQ)
            if row[field] is not None and row[field] > 0),
            'White' if norm._add(*(row[field] for field in REQ)) == 0 else None)
        row['AdvAllocDone'] = advances.get(norm._key(row['SKUCode'], row['WhCode']), 0)
        for field in (*REQ, *ALLOC):
            row[field] = row[field] or 0
        row.update(norm._adjust_blue(row))
    normals = norm.norm_rrr_colour_rows(rationed_report=rationed_report,
        requirement_bands=requirement_bands, bpr_master=bpr_master,
        advance_stock_allocations=advance_stock_allocations,
        order_capabilities={'AllocatedOrders': allocated_orders}, context={'producer': VERSION},
        scope_validator=_scope)
    result = []
    for row in _distinct([*orders, *normals]):
        ordered = {field: row[field] for field in norm.OUTPUT_FIELDS}
        for field in norm.OUTPUT_FIELDS[4:]:
            if field != 'DispatchColor':
                ordered[field] = norm._int(ordered[field], field)
        result.append(ordered)
    return result


def _order(sku, location, parent, quantities, report):
    return dict(zip(norm.OUTPUT_FIELDS, (
        sku, location, parent, 'Order', 0, 0,
        None if report is None else report['Stock'],
        None if report is None else report['GIT'],
        None if report is None else report['LeftoverParentStock'],
        norm._add(*quantities), *quantities, 0, None, 0, 0, 0, 0, 0, None, 0)))
