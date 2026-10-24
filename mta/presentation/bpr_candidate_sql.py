"""Shared six-source native candidate join, before target or authorization."""
from mta.presentation.bpr_prepared_fields import SOURCES,FIELDS
from mta.presentation.rrr_sql import equal,key
from mta.runtime.relational_state import quote


def components(bindings):
    if tuple(bindings)!=tuple(SOURCES):raise ValueError('BPR candidate source order differs')
    ctes=[];params=[]
    for owner,(query,values) in bindings.items():
        ctes.append(owner+' AS NOT MATERIALIZED ('+query+')')
        params.extend(values)
    source_order=','.join(owner+'.vf_ordinal' for owner in SOURCES)
    selected=['row_number() OVER (ORDER BY '+source_order+')-1',key('A."SKUCode"'),key('A."WhCode"')]
    selected += [owner+'.vf_ordinal' for owner in SOURCES]
    selected += [owner+'.'+quote(name) for owner,fields in FIELDS.items() for name in fields]
    joins=' FROM A'
    for owner,sku,location in (('V','SKUCode','WhCode'),('S','SKUCode','WhCode'),
            ('C','SKUCode',None),('D',None,'WHCode'),('B','SKUCode','LocCode')):
        conditions=[]
        if sku:conditions.append(equal('A."SKUCode"',owner+'.'+quote(sku)))
        if location:conditions.append(equal('A."WhCode"',owner+'.'+quote(location)))
        joins+=' LEFT JOIN '+owner+' ON '+' AND '.join(conditions)
    return ctes,selected,joins,params
