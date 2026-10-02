"""Deployed parent Expedite grid projection over admitted terminal facts.

No calculation, publication or route selection occurs here. Nonempty transit
requires its separate consumer port; it must not silently become empty.
"""
from decimal import Decimal
from itertools import product

from mta.presentation.permissions import permission_multiplicity
from mta.presentation.rrr import index, sql_key


def parent_rows(rows, importer, standards, masters, *, nms, products, locations, paging):
    if nms:
        raise ValueError('parent_expedite_nonempty_transit_consumer_unavailable')
    result = dict(expediteDispatches=[], expediteDispatchestransit=[],
                  createAvailabilityAtParent=[], createAvailabilityAtParenttransit=[])
    # Both unpaged SELECTs have a canonical missing separator. Their GetDataSet
    # failure falls through to the empty-list response; caller owns wire proof.
    if paging is None:
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
        for slsa, sd, ld, pd, sa, la, _, _master in product(
                standard.get(key, []) or [{}], sku_desc.get(sk, []) or [{}],
                loc_desc.get(wc, []) or [{}], loc_desc.get(parent, []) or [{}],
                sku.get(sk, []) or [{}], loc.get(wc, []) or [{}],
                pair.get(key, []) or [{}], parent_matches):
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
    page, size = paging
    for target, values in grouped.items():
        # Do not invent a tie-break when metadata duplicates disagree.
        seen = {}
        for key, row in values:
            if key in seen and seen[key] != row:
                raise ValueError('parent_expedite_ambiguous_row_number')
            seen[key] = row
        values.sort(key=lambda item: (item[0][0], *[(v is not None, v or ()) for v in item[0][1:]]), reverse=True)
        result[target] = [dict(rn=str(i), **row) for i, (_, row) in enumerate(values, 1)
                          if (page-1)*size+1 <= i <= page*size]
    return result
