"""Prepare stable BOR-OA occurrences; retain each native join multiplicity."""
import hashlib
from mta.presentation.boroa_sources import admitted_sources
from mta.presentation.boroa_contract import SOURCES,PREPARED_FIELDS,field_name,prepared_recipe
from mta.presentation.selective import image_query
from mta.presentation.rrr_sql import equal,key
from mta.runtime.boroa_models import BorOaSourceRow,BorOaRequirement,BorOaPreparedRow
from mta.runtime.relational_state import quote
from mta.serialization import canonical_parts

def query(run, *, read_binding=None):
    if read_binding is None:
        selected,_=admitted_sources(run)
        if selected.pk!=run.pk:raise ValueError('BOROA preparation run differs')
    ctes=[];params=[]
    for alias,model in [('A',BorOaSourceRow),('F',BorOaRequirement)]:
        if read_binding is not None:
            sql,values=read_binding.source_query('BORWithOrderAllocation' if alias=='A' else 'BOROARequirement')
            ctes.append(alias+' AS ('+sql+')');params.extend(values)
            continue
        ctes.append(alias+' AS (SELECT *,ordinal AS vf_ordinal FROM mta.'+quote(model._meta.db_table)+' WHERE run_id=%s)');params.append(run.pk)
    for alias,path in SOURCES.items():
        if read_binding is not None:
            sql,values=read_binding.image_query(path)
            ctes.append(alias+' AS ('+sql+')');params.extend(values)
            continue
        if alias=='E' and run.kind == 'LEGACY_UI_FIXTURE':
            ctes.append('E AS (SELECT *,vf_source_ordinal AS vf_ordinal FROM "stage_demo_bpr_1"."dbo__ColorSequence")');continue
        if alias == 'E':
            from mta.presentation.native_report_colours import query as colour_query
            sql,values=colour_query()
        else:
            sql,values=image_query(run,path)
        ctes.append(alias+' AS ('+sql+')');params.extend(values)
    ctes.append('S3 AS (SELECT * FROM S2)')
    pair=lambda owner,loc:equal('A."SKUCode"',owner+'."SKUCode"')+' AND '+equal('A."WhCode"',owner+'.'+quote(loc))
    joins=' FROM A JOIN E ON '+equal('A."DispatchColor"','E."Color"')
    joins+=' LEFT JOIN B ON '+pair('B','LocCode')+' LEFT JOIN C ON '+equal('A."SKUCode"','C."SKUCode"')
    joins+=' LEFT JOIN D ON '+equal('A."WhCode"','D."WHCode"')+' LEFT JOIN F ON '+pair('F','WhCode')
    joins+=' LEFT JOIN S1 ON '+equal('A."SKUCode"','S1."SKUCode"')+' LEFT JOIN S2 ON '+equal('A."WhCode"','S2."WHCode"')
    joins+=' LEFT JOIN S3 ON '+equal('A."SupplierCode"','S3."WHCode"')
    columns=['ordinal','sku_key','location_key','supplier_key']
    values=['row_number() OVER (ORDER BY '+','.join(a+'.vf_ordinal NULLS FIRST' for a in PREPARED_FIELDS)+')-1',key('A."SKUCode"'),key('A."WhCode"'),key('A."SupplierCode"')]
    for owner,fields in PREPARED_FIELDS.items():
        columns.append(owner.lower()+'_ordinal');values.append(owner+'.vf_ordinal')
        for name in fields:columns.append(field_name(owner,name));values.append(owner+'.'+quote(name))
    return 'WITH '+','.join(ctes)+' SELECT '+','.join(v+' AS '+quote(n) for n,v in zip(columns,values))+joins,params,columns

def row_receipt(run):
    fields=[f.attname for f in BorOaPreparedRow._meta.local_fields if f.name not in ('id','run')]
    h=hashlib.sha256(b'[');count=0
    for row in BorOaPreparedRow.objects.filter(run=run).order_by('ordinal').values(*fields).iterator(chunk_size=1000):
        if count:h.update(b',')
        for part in canonical_parts(row):h.update(part)
        count+=1
    h.update(b']');return count,h.hexdigest()
