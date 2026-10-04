"""Canonical normal Expedite count joins, independent of missing detail facts."""
from itertools import product
from mta.presentation.rrr import index,sql_key
from mta.presentation.permissions import permission_multiplicity
from mta.presentation.excess import checked_integer


def counts(output,rows,kind,*,products,locations,matches=None):
    if kind not in ('parent','child'): raise ValueError('Unsupported Expedite direction')
    closing=output['ClosingState'][0]; imp=closing['importer']
    standard=index(closing['dbm']['SKULocStandardAttributes'],'SKUCode','WhCode')
    sku_desc=index(imp['SKUDescriptionTbl'],'SKUCode'); loc_desc=index(imp['SiteDescriptionTbl'],'WHCode')
    sku=index(imp['SkuAttributeData'],'SKUCode'); loc=index(imp['LocationAttributeData'],'WHCode')
    pair=index(imp['SkuLocAttributeData'],'SKUCode','LocCode')
    result=dict(expediteDispatches=0,createAvailabilityAtParent=0)
    for row in rows:
        if sql_key(row['PipelineInventoryColor']) not in (sql_key('Black'),sql_key('Red')): continue
        quantity=row['RationedQty']
        if quantity is None or quantity<0: continue
        target='expediteDispatches' if quantity>0 else 'createAvailabilityAtParent'
        sk,wc,key=sql_key(row['SKUCode']),sql_key(row['WhCode']),sql_key(row['SKUCode'],row['WhCode'])
        weight=permission_multiplicity(products,row['SKUCode'])*permission_multiplicity(
            locations,row['WhCode'] if kind=='parent' else row['ParentWhCode'])
        if not weight: continue
        for slsa,sd,ld,pd,sa,la,pair_row in product(standard.get(key,[]),sku_desc.get(sk,[]),loc_desc.get(wc,[]),
                loc_desc.get(sql_key(row['ParentWhCode']),[]) or [None],sku.get(sk,[]),loc.get(wc,[]),pair.get(key,[])):
            filter_weight=matches(dict(row,Tags=slsa.get('Tags')),pair_row,sa,la) if matches else 1
            result[target]=checked_integer(result[target]+weight*filter_weight)
    return result
