"""Deployed parent Expedite grid projection over admitted terminal facts.

No calculation, publication or route selection occurs here. Nonempty transit
requires its separate consumer port; it must not silently become empty.
"""
from decimal import Decimal
from itertools import product
from copy import deepcopy

from mta.presentation.permissions import permission_multiplicity
from mta.presentation.rrr import index, sql_key


def parent_filter(payload, importer):
    """Same Commons expressions as Excess, with the parent query's own joins."""
    from mta.presentation.context import PublicationUnavailable
    from mta.presentation.dbm_filters import STANDARD_GROUPS
    from mta.presentation.excess_filters import predicate
    payload = deepcopy(payload)
    groups = payload.get('filters') or {}
    if any(groups.get(name) is not None for name in STANDARD_GROUPS):
        if any(i.get('attributeName', '').lower() == 'norm'
               for i in (groups.get('availabilityFilter') or {}).get('filters', [])):
            raise PublicationUnavailable('LEG-EXPEDITE-PARENT-FILTER-SQL209: ambiguous norm')
        supply = groups.get('supplyChainFilter')
        if supply:
            # Commons emits this as sqlJoinFilter; parent never appends it.
            supply['filters'] = [i for i in supply['filters'] if i.get('attributeName', '').lower() != 'forchildren']
    try:
        return predicate(payload, importer)
    except PublicationUnavailable as exc:
        raise PublicationUnavailable('LEG-EXPEDITE-PARENT-FILTER-INVALID-SQL:'+str(exc).partition(':')[2]) from exc


def parent_transit_rows(nms, remarks, pick, selected, *, availability=False):
    """Reference for the deployed cte_intransit/cte_avilatparentintransit.

    `selected` is the complete filtered/scoped CTE, before paging. Dispatch
    LEFT joins that CTE through remarks; availability INNER joins it. GROUP BY
    uses the original nullable remark, before ISNULL converts it to a space.
    SQL specifies no result ordering here; callers must not claim ordered parity.
    """
    remark_index = index(remarks, 'SKUCode', 'WhCode')
    selected_index = index(selected, 'sc', 'wc')
    pick_index = index(pick, 'SKUCode', 'WhCode')
    result, seen = [], set()
    for item in nms:
        for remark in remark_index.get(sql_key(item['SKUCode'], item['WhCode']), []) or [{}]:
            matches = selected_index.get(sql_key(remark.get('SKUCode'), remark.get('WhCode')), [])
            for chosen in matches or ([] if availability else [{}]):
                for stock in pick_index.get(sql_key(chosen.get('sc'), chosen.get('wc')), []) or [{}]:
                    raw = dict(skucode=item['SKUCode'], whcode=item['WhCode'],
                               slt=stock.get('ParentStockForRationing'), eta=item.get('RLT'),
                               remarks=remark.get('Remark'))
                    group = tuple(sql_key(value) if isinstance(value, str) else value
                                  for value in raw.values())
                    if group in seen:
                        continue
                    seen.add(group)
                    raw['remarks'] = raw['remarks'] if raw['remarks'] is not None else ' '
                    result.append({key: str(value) for key, value in raw.items() if value is not None})
    return result


def parent_rows(rows, importer, standards, masters, *, nms, products, locations, paging, matches=None,
                remarks=None, pick=None, corrected_unpaged=False):
    if nms and (remarks is None or pick is None):
        raise ValueError('parent_expedite_nonempty_transit_consumer_unavailable')
    result = dict(expediteDispatches=[], expediteDispatchestransit=[],
                  createAvailabilityAtParent=[], createAvailabilityAtParenttransit=[])
    # Both unpaged SELECTs have a canonical missing separator. Their GetDataSet
    # failure falls through to the empty-list response; caller owns wire proof.
    if paging is None and not corrected_unpaged:
        return result
    standard = index(standards, 'SKUCode', 'WhCode')
    master = index(masters, 'SKUCode', 'WHCode')
    sku_desc = index(importer['SKUDescriptionTbl'], 'SKUCode')
    loc_desc = index(importer['SiteDescriptionTbl'], 'WHCode')
    sku = index(importer['SkuAttributeData'], 'SKUCode')
    loc = index(importer['LocationAttributeData'], 'WHCode')
    pair = index(importer['SkuLocAttributeData'], 'SKUCode', 'LocCode')
    grouped = {key: [] for key in ('expediteDispatches', 'createAvailabilityAtParent')}
    aliases = dict(sc='SKUCode', wc='WhCode', n='Norm', vn='VirtualNorm', st='Stock',
                   g='GIT', pip='PhysicalInventoryPen', pic='PhysicalInventoryColor',
                   pin='PipelineInventoryPen', plc='PipelineInventoryColor', rq='Req', rtq='RationedQty')
    for a in rows:
        if sql_key(a['PipelineInventoryColor']) not in (sql_key('Black'), sql_key('Red')):
            continue
        quantity = a['RationedQty']
        if quantity is None or quantity < 0:
            continue
        key = sql_key(a['SKUCode'], a['WhCode'])
        sk, wc, parent = sql_key(a['SKUCode']), sql_key(a['WhCode']), sql_key(a['ParentWhCode'])
        weight = permission_multiplicity(products, a['SKUCode']) * permission_multiplicity(locations, a['WhCode'])
        if not weight:
            continue
        target = 'expediteDispatches' if quantity > 0 else 'createAvailabilityAtParent'
        parent_matches = [{}] if quantity > 0 else master.get(sql_key(a['SKUCode'], a['ParentWhCode']), [])
        for slsa, sd, ld, pd, sa, la, pair_row, _master in product(
                standard.get(key, []) or [{}], sku_desc.get(sk, []) or [{}],
                loc_desc.get(wc, []) or [{}], loc_desc.get(parent, []) or [{}],
                sku.get(sk, []) or [{}], loc.get(wc, []) or [{}],
                pair.get(key, []) or [{}], parent_matches):
            if matches is not None and not matches(dict(a, Tags=slsa.get('Tags')), pair_row, sa, la):
                continue
            row = {alias: a[field] for alias, field in aliases.items()}
            row.update(t=slsa.get('Tags'), p=slsa.get('Price'), sd=sd.get('SKUDescription'),
                       wcd=ld.get('WHDescription'), pl=pd.get('WHDescription'))
            row.update({'sl'+str(i): sa.get('SL'+str(i)) for i in (1, 2, 3)})
            row.update({'ll'+str(i): la.get('LL'+str(i)) for i in (1, 2, 3)})
            values = {}
            for field, value in row.items():
                if value is None:
                    continue
                scale = 2 if field in ('pip', 'pin') else 3 if field == 'p' else None
                values[field] = format(Decimal(str(value)), f'.{scale}f') if scale is not None else str(value)
            order = (a.get('BRAge') or 0, sk, wc, parent)
            grouped[target].extend((order, dict(values)) for _ in range(weight))
    page, size = paging if paging is not None else (None, None)
    if nms:
        for target, transit_target, availability in (
                ('expediteDispatches', 'expediteDispatchestransit', False),
                ('createAvailabilityAtParent', 'createAvailabilityAtParenttransit', True)):
            result[transit_target] = parent_transit_rows(
                nms, remarks, pick, [row for _, row in grouped[target]], availability=availability)
    for target, values in grouped.items():
        # Do not invent a tie-break when metadata duplicates disagree.
        seen = {}
        for key, row in values:
            if key in seen and seen[key] != row:
                raise ValueError('parent_expedite_ambiguous_row_number')
            seen[key] = row
        values.sort(key=lambda item: (item[0][0], *[(v is not None, v or ()) for v in item[0][1:]]), reverse=True)
        result[target] = [dict(rn=str(i), **row) for i, (_, row) in enumerate(values, 1)
                          if paging is None or (page-1)*size+1 <= i <= page*size]
    return result
