"""BOR-OA scoped/filterable SQL over sealed occurrences, with live remark ties."""
from django.db import connection
from mta.presentation.boroa_sources import admitted_sources
from mta.presentation.boroa_contract import PREPARED_FIELDS,field_name,prepared_recipe
from mta.presentation.boroa_filters import BorOaFilters,BorOaQueryError
from mta.presentation.boroa_configuration import configuration
from mta.presentation.context import PublicationUnavailable,scope
from mta.presentation.bpr_sql import _projected_attributes,_values_cte
from mta.presentation.rrr_sql import equal,key
from mta.presentation.selective import image_query
from mta.runtime.relational_state import quote
from mta.runtime.boroa_models import BorOaPreparedRow,BorOaPreparedReceipt,BorOaInitialRemark,BorOaLiveRemark

def col(owner,name):return 'R.'+quote(field_name(owner,name))

def projection():
    result=[('SKUCode',col('A','SKUCode')),('SKUDescription',col('S1','SKUDescription')),
        ('WhCode',col('A','WhCode')),('WHDescription',col('S2','WHDescription')),
        ('SupplierCode',col('A','SupplierCode')),('SupplierDesc',col('S3','WHDescription'))]
    result += [(name,col('A',name)) for name in ('Norm','VirtualNorm','Stock','GIT','ParentLeftoverStock','Requirement',
        'Req_TOB','Req_TOR','Req_TOY','Req_TOG','Req_TOBlue','DispatchQty','Dispatch_TOB','Dispatch_TOR',
        'Dispatch_TOY','Dispatch_TOG','Dispatch_ToBlue','DispatchColor')]
    result.append(('AdvAllocDone',col('F','AdvAllocDone')))
    result += [(f'sl{i}',col('C',f'SL{i}')) for i in range(1,6)]
    result += [(f'll{i}',col('D',f'LL{i}')) for i in range(1,6)]
    for alias,owner,prefix in [('SKULocAttr','B','c'),('SLSAttr','A','SKULocAtt'),('SKUAttr','C','c'),('LocAttr','D','c')]:
        result += [(alias+str(i),'COALESCE('+col(owner,prefix+(f'{i:02}' if owner=='A' else str(i)))+",'-')") for i in range(1,16)]
    return result+[('Remark','RM."Remark"')]

def remark_query(run):
    fields='"SKUCode","WhCode","SupplierCode","Remark","Username","RemarkDate"'
    from mta.presentation.daily_preparation import production_branch
    if production_branch(run):
        from mta.presentation import ancillary_live
        return ancillary_live.image_query(run,ancillary_live.PATHS[ancillary_live.BOROA],
            include_live=ancillary_live.serving_live(run))
    return ('SELECT '+fields+' FROM mta.'+quote(BorOaInitialRemark._meta.db_table)+' WHERE run_id=%s UNION ALL SELECT '+fields+
        ' FROM mta.'+quote(BorOaLiveRemark._meta.db_table)+' WHERE run_id=%s',[run.pk,run.pk])

def read_boroa(payload,*,count=False,export=False):
    from mta.runtime.boroa_prepared_schema import verify_guards
    run,source=admitted_sources();receipt=BorOaPreparedReceipt.objects.filter(run=run).first()
    if receipt is None or receipt.source_digest!=source.source_digest or receipt.recipe_digest!=prepared_recipe():
        raise PublicationUnavailable('BOROA_prepared_receipt_missing_or_changed')
    try:verify_guards(connection)
    except ValueError as exc:raise PublicationUnavailable('BOROA_prepared_guards_changed') from exc
    attrs,supplement=_projected_attributes(run)
    if supplement:raise PublicationUnavailable('BOROA_native_hierarchy_required')
    products,locations=scope(payload,attributes=attrs);ctes=[];params=[];join_params=[]
    for alias,codes in [('P',products),('L',locations)]:
        sql,values=_values_cte([{'code':code} for code in sorted(codes) for _ in range(codes.multiplicities[code])],('code',))
        ctes.append(alias+' AS ('+sql+')');params.extend(values)
    ctes.append('prepared AS (SELECT * FROM mta.'+quote(BorOaPreparedRow._meta.db_table)+' WHERE run_id=%s)');params.append(run.pk)
    if count:
        # Native count omits description and remark joins. Project stable join
        # occurrence IDs before scopes so their multiplicities remain live.
        columns=['sku_key','location_key','supplier_key']
        for owner in ('A','B','C','D','E','F'):
            columns.append(owner.lower()+'_ordinal');columns += [field_name(owner,n) for n in PREPARED_FIELDS[owner]]
        ctes.append('R AS (SELECT DISTINCT '+','.join(map(quote,columns))+' FROM prepared)')
    else:ctes.append('R AS (SELECT * FROM prepared)')
    joins=' FROM R JOIN P ON R.sku_key='+key('P.code')+' JOIN L ON R.location_key='+key('L.code')
    filters=BorOaFilters(payload,count=count)
    try:where=filters.compile()
    except PublicationUnavailable as exc:raise BorOaQueryError(str(exc)) from exc
    if filters.children:
        parent,values=image_query(run,'closing/importer/LocationAttributeData');ctes.append('parent AS ('+parent+')');params+=values
        joins+=' JOIN parent ON '+equal(col('F','ParentWhCode'),'parent."WHCode"')+' AND ('+' OR '.join(equal('parent."LocationType"','%s') for _ in filters.children)+')'
        join_params+=filters.children
    if not count:
        remarks,values=remark_query(run);ctes.append('remarks AS ('+remarks+')');params+=values
        ctes.append('latest AS (SELECT '+key('"SKUCode"')+' sk,'+key('"WhCode"')+' lk,'+key('"SupplierCode"')+' sp,max("RemarkDate") d FROM remarks GROUP BY 1,2,3)')
        ctes.append('RM AS (SELECT M.* FROM remarks M JOIN latest T ON '+key('M."SKUCode"')+'=T.sk AND '+key('M."WhCode"')+'=T.lk AND '+key('M."SupplierCode"')+'=T.sp AND M."RemarkDate"=T.d)')
        joins+=' LEFT JOIN RM ON R.sku_key='+key('RM."SKUCode"')+' AND R.location_key='+key('RM."WhCode"')+' AND R.supplier_key='+key('RM."SupplierCode"')
    config=configuration();condition=[v for v in config['environment'] if v['ConfigKey']=='BOROA_DISPATCH_CONDITION' and v['Category']=='ClientSpecific']
    if len(condition)!=1:raise PublicationUnavailable('BOROA_dispatch_configuration_missing')
    if int(condition[0]['ConfigValue']):where='('+col('A','DispatchQty')+'>0) AND ('+where+')'
    order=col('E','SequenceNo')+' ASC NULLS FIRST,'+','.join(col('A',n)+' DESC NULLS LAST' for n in (
        'OrderBlackUnsatisfiedPercentage','OrderRedUnsatisfiedPercentage','OrderYellowUnsatisfiedPercentage','OrderGreenUnsatisfiedPercentage','DispatchPen'))
    select='count(*)' if count else 'row_number() OVER (ORDER BY '+order+')::integer AS "RN",'+','.join(v+' AS '+quote(n) for n,v in projection())
    sql='WITH '+','.join(ctes)+' SELECT '+select+joins+' WHERE '+where;params += [*join_params,*filters.params]
    if not count:
        sql='SELECT * FROM ('+sql+') ranked'
        paging=payload.get('paginationParameter')
        if paging is not None and not export:
            if not isinstance(paging,dict) or any(type(paging.get(n))is not int for n in ('pageNumber','recordsPerPage')):raise BorOaQueryError('native BOROA pagination invalid')
            # Native BETWEEN allows zero/negative bounds; do not invent validation.
            lower=(paging['pageNumber']-1)*paging['recordsPerPage']+1;upper=paging['pageNumber']*paging['recordsPerPage']
            sql+=' WHERE "RN" BETWEEN %s AND %s';params += [lower,upper]
        sql+=' ORDER BY "RN"'
    with connection.cursor() as c:
        c.execute(sql,params)
        if count:return c.fetchone()[0]
        names=[d[0] for d in c.description];return [dict(zip(names,row)) for row in c.fetchall()]
