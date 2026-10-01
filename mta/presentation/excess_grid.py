"""Selected Planning inventory-grid joins and legacy presentation aliases.

The selected adminbpr configuration has no enabled dynamic *Attr columns.
Descriptions and attribute rows are inputs, not inferred from display labels.
"""
from collections import Counter, defaultdict


def inventory_grid_membership(rows, locations, skus, location_attrs, sku_attrs, sku_locations, *, include_location_type=False, left_sku_location=False):
    """INNER descriptions/attributes, LEFT parent description; keep multiplicity."""
    by_location, by_sku = defaultdict(list), defaultdict(list)
    for attr in location_attrs:
        by_location[attr['WHCode']].append(attr)
    for attr in sku_attrs:
        by_sku[attr['SKUCode']].append(attr)
    result = []
    memberships = Counter(sku_locations)
    for row in rows:
        sku, wh = row['SKUCode'], row['WHCode']
        multiplicity = memberships[(sku, wh)]
        if left_sku_location:
            multiplicity = max(1, multiplicity)
        if sku not in skus or wh not in locations or not multiplicity:
            continue
        for sa in by_sku[sku]:
            for la in by_location[wh]:
                joined = {**row, 'SKUName': skus[sku], 'WHName': locations[wh],
                               **{field:sa.get(field) for field in ('ElephantOrderCapping','Volume','Weight')},
                               'ParentWHName': locations.get(row.get('ParentWhCode')),
                               **({'LocationType': la.get('LocationType')} if include_location_type else {}),
                               **{f'sl{i}': sa.get(f'sl{i}') for i in range(1, 6)},
                               **{f'll{i}': la.get(f'll{i}') for i in range(1, 6)}}
                result.extend(dict(joined) for _ in range(multiplicity))
    return result


EXCESS_COLUMNS = (
    ('Tags', 't', 1), ('SKU code', 'sc', 2), ('SKU Description', 'sd', 3),
    ('Location', 'wcd', 4), ('Parent location', 'pl', 5), ('Norm', 'n', 6),
    ('Virtual Norm', 'vn', 7), ('Stock', 'st', 8), ('GIT', 'g', 10),
    ('Required Quantity', 'rq', 12), ('On-hand Inventory Pen', 'pip', 9),
    ('Pipeline Inventory Pen', 'pin', 11), ('Excess Inventory Value', 'am', 13),
    ('Business', 'sl1', 14), ('Category', 'sl2', 15), ('Family', 'sl3', 16),
    ('Zone', 'll1', 19), ('Location Group', 'll2', 20), ('WH Type', 'll3', 21),
)
EXCESS_ALIASES = {
    't': 'Tags', 'sc': 'SKUCode', 'sd': 'SKUName', 'wc': 'WHCode',
    'wcd': 'WHName', 'pl': 'ParentWHName', 'n': 'Norm', 'vn': 'VirtualNorm',
    'st': 'Stock', 'g': 'GIT', 'br': 'BlueReq', 'rq': 'Requirement',
    'pip': 'PhysicalPen', 'pic': 'PhysicalColor', 'pin': 'PipelinePen',
    'plc': 'PipelineColor', 'am': 'Amount',
    **{f'{prefix}{i}': f'{prefix}{i}' for prefix in ('sl', 'll') for i in range(1, 6)},
}


def excess_grid_rows(rows):
    """Assign ROW_NUMBER before API pagination, WH descending / SKU ascending.

    Equal SQL keys have no specified tie-break. Keep their input order; callers
    must not claim deterministic tie parity when duplicate attributes differ.
    """
    ordered = sorted(rows, key=lambda r: r['SKUCode'].rstrip().casefold())
    ordered.sort(key=lambda r: r['WHCode'].rstrip().casefold(), reverse=True)
    return [dict(rn=index, **{alias: row.get(field) for alias, field in EXCESS_ALIASES.items()})
            for index, row in enumerate(ordered, 1)]


def excess_grid_config():
    return [dict(header=header, colCode=code, colPosition=position)
            for header, code, position in EXCESS_COLUMNS]
