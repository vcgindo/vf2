"""Build stable BOR source/dimension occurrences once, without live overlays."""
import hashlib
from django.db import connection
from mta.presentation.bor_sources import admitted_sources,MODELS
from mta.presentation.bor_prepared_fields import SOURCES,FIELDS,OWNERS,field_name,recipe_digest
from mta.presentation.selective import image_query
from mta.presentation.rrr_sql import equal,key
from mta.runtime.relational_state import quote
from mta.runtime.models import BorPreparedRow
from mta.serialization import canonical_parts


def query(run):
    selected,_=admitted_sources(run)
    if selected.pk!=run.pk: raise ValueError('BOR preparation run differs')
    ctes=[];params=[]
    for alias,table in (('A','SupplierDispatchReq'),('I','SOBData'),('J','MOQData')):
        ctes.append(alias+' AS (SELECT *,ordinal AS vf_ordinal FROM mta.'+
            quote(MODELS[table]._meta.db_table)+' WHERE run_id=%s)')
        params.append(run.pk)
    for alias,path in SOURCES.items():
        sql,values=image_query(run,path)
        ctes.append(alias+' AS ('+sql+')');params.extend(values)
    ctes.append('H AS (SELECT * FROM G)')
    pair=lambda owner,loc: equal('A."SKUCode"',owner+'."SKUCode"')+' AND '+equal('A."WHCode"',owner+'.'+quote(loc))
    joins=' FROM A LEFT JOIN B ON '+pair('B','WhCode')+' LEFT JOIN S ON '+pair('S','WhCode')
    joins+=' LEFT JOIN C ON '+equal('A."SKUCode"','C."SKUCode"')
    joins+=' LEFT JOIN D ON '+equal('A."WHCode"','D."WHCode"')
    joins+=' LEFT JOIN E ON '+pair('E','LocCode')
    joins+=' LEFT JOIN F ON '+equal('A."SKUCode"','F."SKUCode"')
    joins+=' LEFT JOIN G ON '+equal('A."WHCode"','G."WHCode"')
    joins+=' LEFT JOIN H ON '+equal('A."SupplierCode"','H."WHCode"')
    for owner in ('I','J'):
        joins+=' LEFT JOIN '+owner+' ON '+pair(owner,'WHCode')+' AND '+equal('A."SupplierCode"',owner+'."SupplierCode"')
    ordinals=','.join(owner+'.vf_ordinal NULLS FIRST' for owner in OWNERS)
    columns=['ordinal','sku_key','location_key','supplier_key']
    selected=['row_number() OVER (ORDER BY '+ordinals+')-1',key('A."SKUCode"'),key('A."WHCode"'),key('A."SupplierCode"')]
    for owner,fields in FIELDS.items():
        columns.append(owner.lower()+'_ordinal');selected.append(owner+'.vf_ordinal')
        for name in fields:
            columns.append(field_name(owner,name));selected.append(owner+'.'+quote(name))
    sql='WITH '+','.join(ctes)+' SELECT '+','.join(v+' AS '+quote(n) for n,v in zip(columns,selected))+joins+' WHERE A."DispatchReq">0'
    return sql,params,columns


def row_receipt(run):
    fields=[f.attname for f in BorPreparedRow._meta.local_fields if f.name not in ('id','run')]
    checksum=hashlib.sha256(b'[');count=0
    for row in BorPreparedRow.objects.filter(run=run).order_by('ordinal').values(*fields).iterator(chunk_size=1000):
        if count: checksum.update(b',')
        for part in canonical_parts(row): checksum.update(part)
        count+=1
    checksum.update(b']')
    return count,checksum.hexdigest()
