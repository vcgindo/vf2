"""Deployed ExpediteFromChild read contract, with explicit preview history input."""
from datetime import datetime, time, timedelta
from decimal import Decimal
from itertools import product

from mta.presentation.permissions import permission_multiplicity
from mta.presentation.rrr import index, sql_key


def child_rows(rows, importer, standards, *, products, locations, paging,
               business_date, requests, transit, matches=None):
    # This bounded reader has only been authorized for declared empty histories.
    # Never turn unavailable or future populated inputs into empty arrays.
    if requests != [] or transit != []:
        raise ValueError('child_expedite_requires_approved_empty_request_and_transit_inputs')
    standard = index(standards, 'SKUCode', 'WhCode')
    sku_desc = index(importer['SKUDescriptionTbl'], 'SKUCode')
    loc_desc = index(importer['SiteDescriptionTbl'], 'WHCode')
    sku = index(importer['SkuAttributeData'], 'SKUCode')
    loc = index(importer['LocationAttributeData'], 'WHCode')
    pair = index(importer['SkuLocAttributeData'], 'SKUCode', 'LocCode')
    grouped = dict(expediteDispatches=[], createAvailabilityAtParent=[])
    aliases = dict(sc='SKUCode', wc='WhCode', n='Norm', vn='VirtualNorm', st='Stock',
                   g='GIT', pip='PhysicalInventoryPen', pic='PhysicalInventoryColor',
                   pin='PipelineInventoryPen', plc='PipelineInventoryColor', rq='Req',
                   rtq='RationedQty', sap='RationedQty', ec='ParentPipelineInventoryColor')
    for a in rows:
        quantity = a['RationedQty']
        if quantity == 0:
            target = 'createAvailabilityAtParent'
        elif quantity is not None and quantity > 0 and sql_key(a['PipelineInventoryColor']) in (sql_key('Black'), sql_key('Red')):
            target = 'expediteDispatches'
        else:
            continue
        weight = permission_multiplicity(products, a['SKUCode']) * permission_multiplicity(locations, a['ParentWhCode'])
        if not weight:
            continue
        sk, wc, parent = sql_key(a['SKUCode']), sql_key(a['WhCode']), sql_key(a['ParentWhCode'])
        key = sql_key(a['SKUCode'], a['WhCode'])
        fallback = [{}] if target == 'expediteDispatches' else []
        for slsa, sd, ld, pd, sa, la, pair_row in product(
                standard.get(key, []) or fallback, sku_desc.get(sk, []) or fallback,
                loc_desc.get(wc, []) or fallback, loc_desc.get(parent, []) or [{}],
                sku.get(sk, []) or fallback, loc.get(wc, []) or fallback,
                pair.get(key, []) or fallback):
            filter_weight = matches(dict(a, Tags=slsa.get('Tags')), pair_row, sa, la) if matches else 1
            if not filter_weight:
                continue
            row = {alias: a[field] for alias, field in aliases.items()}
            row.update(t=slsa.get('Tags'), p=slsa.get('Price'), sd=sd.get('SKUDescription'),
                       wcd=ld.get('WHDescription'), pl=pd.get('WHDescription'), remark=None,
                       eta=None if a['RLT'] is None else
                           (datetime.combine(business_date, time()) + timedelta(days=int(a['RLT']))).isoformat(),
                       intransit='[]')
            row.update({'sl'+str(i): sa.get('SL'+str(i)) for i in range(1, 6)})
            row.update({'ll'+str(i): la.get('LL'+str(i)) for i in range(1, 6)})
            for field in ('pip', 'pin', 'p'):
                if row[field] is not None:
                    row[field] = float(Decimal(str(row[field])))
            order = (a['BRAge'], sk, wc, parent)
            grouped[target].extend((order, dict(row)) for _ in range(weight * filter_weight))
    result = {}
    for target, values in grouped.items():
        seen = {}
        for key, row in values:
            if key in seen and seen[key] != row:
                raise ValueError('child_expedite_ambiguous_row_number')
            seen[key] = row
        values.sort(key=lambda item: tuple((v is not None, v if v is not None else 0) for v in item[0]), reverse=True)
        result[target] = [dict(rn=i, **row) for i, (_, row) in enumerate(values, 1)
                          if paging is None or (paging[0]-1)*paging[1]+1 <= i <= paging[0]*paging[1]]
    return result
