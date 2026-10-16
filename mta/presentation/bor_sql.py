"""BOR requests read sealed occurrences; scopes, filters and remark ties stay live."""
from collections import defaultdict
from django.db import connection
from mta.presentation.bor_sources import admitted_sources
from mta.presentation.bor_prepared_fields import FIELDS,field_name,recipe_digest
from mta.presentation.context import PublicationUnavailable,scope
from mta.presentation.bpr_sql import _projected_attributes,_values_cte
from mta.presentation.rrr_sql import Filters,equal,key
from mta.presentation.selective import image_query
from mta.runtime.bor_prepared_schema import verify_guards
from mta.runtime.models import BorPreparedReceipt,BorPreparedRow,BorInitialRemark,BorLiveRemark,BorSourceRow
from mta.runtime.relational_state import quote


class BorQueryError(ValueError): pass


class _FilterBuildAbort(Exception): pass


def col(owner,name): return 'R.'+quote(field_name(owner,name))


class BorFilters(Filters):
    def column(self,owner,name):
        fields={n.casefold():(n,k) for n,k in FIELDS[owner].items()}
        if name.casefold() not in fields: raise BorQueryError('native BOR filter column missing')
        n,k=fields[name.casefold()]
        return col(owner,n),{'bigint':'int','numeric':'decimal','text':'nvarchar','float':'float'}[k]

    def items(self, group):
        group_name=group
        group=self.groups.get(group)
        if group is None: return
        rows=group.get('filters')
        if rows is None: raise _FilterBuildAbort()
        for item in rows:
            if item is None or (item.get('attributeName') is None and group_name!='colorFilter'):
                raise _FilterBuildAbort()
            if item.get('attributeName')!='': yield item

    @staticmethod
    def value(item, *, nullable=False):
        value=item.get('value')
        if value is None:
            if nullable: return ''
            raise _FilterBuildAbort()
        return str(value)

    def compile(self):
        # Deployed ApplyFiltersForReports catches builder NULL failures and keeps
        # only SQL already appended by Commons. Provider failures remain 500.
        self.unfinished_join=False
        try: self.build()
        except _FilterBuildAbort:
            if self.unfinished_join: raise BorQueryError('native incomplete filter join')
        return ' AND '.join(self.where) or 'TRUE'

    def build(self):
        from mta.presentation.rrr_sql import OPERATORS
        supply=defaultdict(list)
        for i in self.items('supplyChainFilter'):
            name=i['attributeName'].lower()
            if name in ('forlocation','forlocationlocationcode','forchildrenlocationcode','forchildren'):
                supply[name].append(self.value(i))
                if name=='forchildren': self.unfinished_join=True
        for name,owner,field in (('forlocation','D','LocationType'),('forlocationlocationcode','A','WHCode'),
                                 ('forchildrenlocationcode','B','ParentWhCode')):
            self.in_list(owner,field,supply[name])
        self.children=supply['forchildren'];self.unfinished_join=False
        for group,special,code in (('locationFilter','location','WHCode'),('productFilter','sku','SKUCode')):
            # Native local lists are flushed only after the whole group builds.
            items=[{**i,'value':self.value(i)} for i in self.items(group)]
            mapped=[i for i in items if i['attributeName'].lower()!=special]
            if group=='locationFilter': self.in_list('A',code,[i['value'] for i in items if i['attributeName'].lower()==special])
            self.grouped(mapped,lambda name,group=group: ('C',name.replace('p','sl')) if group=='productFilter' else ('D','l'+name))
            if group=='productFilter': self.in_list('A',code,[i['value'] for i in items if i['attributeName'].lower()==special])
        accumulated=defaultdict(list)
        for item in self.items('availabilityFilter'):
            name=item['attributeName'].lower()
            if name in ('category','pic','ohic','pipo,seasonality'):
                accumulated[name].append(self.value(item,nullable=True))
            if name in ('norm','stock','git','availability','virtualnorm'):
                # Commons appends AND before dereferencing value/building the
                # operator. An empty first operator emits no predicate.
                if item.get('value') is None:
                    if self.where: raise BorQueryError('native dangling filter conjunction')
                    raise _FilterBuildAbort()
                if item.get('operator') not in OPERATORS:
                    if self.where: raise BorQueryError('native empty filter operator')
                    continue
                self.where.append(self.compare('B',name,item.get('operator'),self.value(item)))
        if accumulated['category']: raise BorQueryError('native BOR category column missing')
        for name,owner,field in (('pic','B','DispatchColor'),('ohic','B','PhysicalInventoryColor'),('pipo,seasonality','S','Tags')):
            self.in_list(owner,field,accumulated[name])
        for item in self.items('colorFilter'):
            kind=item.get('type')
            if kind=='colorage' and item.get('value') is None and not self.where:
                raise _FilterBuildAbort()
            if self.where or kind in ('colorage','colorcount'):
                raise BorQueryError('native BOR color owner absent or dangling conjunction')
        coverage=list(self.items('coverageFilter'))
        if any(i['attributeName'].lower()=='coverage' for i in coverage):
            raise BorQueryError('native BOR coverage owner absent')
        def custom(name):
            for prefix,owner in (('skulocattr','E'),('skuattr','C'),('locattr','D')):
                if prefix in name.lower(): return owner,name.lower().replace(prefix,'c')
        items=[{**i,'value':self.value(i)} for i in self.items('customAttributeFilter')
               if any(p in i['attributeName'].lower() for p in ('skulocattr','skuattr','locattr'))]
        self.grouped(items,custom)


def projection():
    c=col;dash=lambda owner,name: 'COALESCE('+c(owner,name)+",'-')"
    result=[('DispatchColorSequence',c('B','DispatchColorSequence')),('SKUCode',c('A','SKUCode')),
        ('SKUDesc',dash('F','SKUDescription')),('WHCode',c('A','WHCode')),('WHDescription',dash('G','WHDescription')),
        ('SupplierCode',c('A','SupplierCode')),('SuppDesc',dash('H','WHDescription')),
        ('MOQ','COALESCE('+c('J','MOQ')+',0)::text'),('SOB','COALESCE('+c('I','SOB')+',100)'),
        ('DispatchReq',c('A','DispatchReq')),
        ('TechCol','COALESCE(substring('+c('B','TechColor')+" from 1 for 20),'Pending Order')"),
        ('EcoCol','COALESCE(substring('+c('B','EcoColor')+" from 1 for 20),'Pending Order')"),
        ('Requirement','COALESCE('+c('B','Req')+',0)')]
    result += [(n,c('A',n)) for n in ('ReqTopOfRed','ReqTopOfYellow','ReqTopOfGreen','ReqTopOfBlue',
        'CumulativeTOR','CumulativeTOY','CumulativeTOG','CumulativeTOB','ReqTopOfBlack','CumulativeTOBlack')]
    result += [(n,c('B',n)) for n in ('GIT','Stock','SpikeThreshold','PSOThreshold','StockForReqCalc','DispatchPen',
        'PhysicalInventoryColor','DispatchColor','DirectSpikeOverdue','SpikeOverdueAtParent','PSO')]
    result += [('RelPSO',c('B','RelPSOAndCNR'))]
    result += [(n,c('B',n)) for n in ('ResidualChildrenSnP','SnPToNetOff','SnPNettedOff','ResidualSnP',
        'EcoStockForNormReq','NormReq','BlueReq','Norm','VirtualNorm')]
    result += [(f'sl{i}',c('C',f'SL{i}')) for i in range(1,6)]
    result += [(f'll{i}',c('D',f'LL{i}')) for i in range(1,6)]
    for alias,owner,prefix in (('SKUAttr','C','c'),('LocAttr','D','c'),('SLSAttr','A','SKULocAtt'),('SKULocAttr','E','c')):
        result += [(alias+str(i),dash(owner,prefix+(f'{i:02}' if owner=='A' else str(i)))) for i in range(1,16)]
    return result+[('Remark','RM."Remark"'),('ep',c('B','EcoPen'))]


def remark_query(run):
    fields='"SKUCode","WhCode","SupplierCode","Remark","Username","RemarkDate"'
    from mta.presentation.daily_preparation import production_branch
    if production_branch(run):
        from mta.presentation import ancillary_live
        return ancillary_live.image_query(run,ancillary_live.PATHS[ancillary_live.BOR],
            include_live=ancillary_live.serving_live(run))
    return ('SELECT '+fields+' FROM mta.'+quote(BorInitialRemark._meta.db_table)+' WHERE run_id=%s UNION ALL SELECT '+
        fields+' FROM mta.'+quote(BorLiveRemark._meta.db_table)+' WHERE run_id=%s',[run.pk,run.pk])


def read_bor(payload,*,count=False,export=False,analytics=False):
    run,source=admitted_sources()
    from mta.presentation import native_publication
    native = native_publication.enabled()
    if native:
        native_publication.require_mode()
        from mta.presentation.bor_prepared_fields import production_recipe_digest
    expected_recipe = production_recipe_digest() if native else recipe_digest()
    receipt=BorPreparedReceipt.objects.filter(run=run).first()
    if receipt is None or receipt.source_digest!=source.source_digest or receipt.recipe_digest!=expected_recipe:
        raise PublicationUnavailable('BOR_prepared_receipt_missing_or_changed')
    try: verify_guards(connection)
    except ValueError as exc: raise PublicationUnavailable('BOR_prepared_guards_changed') from exc
    if native:
        from mta.presentation.selective import image_rows
        from mta.presentation.hierarchy import selected_manifest
        importer = {name: image_rows(run, 'closing/importer/' + name)
                    for name in ('SkuAttributeData', 'LocationAttributeData')}
        manifest = selected_manifest(run)
    else:
        importer,manifest=_projected_attributes(run)
    if manifest: raise PublicationUnavailable('BOR_native_hierarchy_required')
    products,locations=scope(payload,attributes=importer)
    ctes=[];params=[]
    for alias,codes in (('P',products),('L',locations)):
        sql,values=_values_cte([{'code':code} for code in sorted(codes) for _ in range(codes.multiplicities[code])],('code',))
        ctes.append(alias+' AS ('+sql+')');params.extend(values)
    if analytics:
        fields=[]
        for band in ('Red','Yellow','Green','Blue'):
            field='A.'+quote('ReqTopOf'+band)
            condition=field+'>0 AND A."DispatchReq">0'
            fields += ['sum('+field+') FILTER (WHERE '+condition+') AS '+quote(band+'_rs'),
                'count(DISTINCT '+key('A."SKUCode"')+"||'-'||"+key('A."WHCode"')+') FILTER (WHERE '+condition+') AS '+quote(band+'_ns'),
                'count(DISTINCT '+key('A."SupplierCode"')+') FILTER (WHERE '+condition+') AS '+quote(band+'_sc')]
        sql=('WITH '+','.join(ctes)+' SELECT '+','.join(fields)+' FROM mta.'+quote(BorSourceRow._meta.db_table)+
            ' A JOIN P ON '+equal('A."SKUCode"','P.code')+' JOIN L ON '+equal('A."WHCode"','L.code')+' WHERE A.run_id=%s')
        params.append(run.pk)
    else:
        filters=BorFilters(payload)
        try: where=filters.compile()
        except PublicationUnavailable as exc: raise BorQueryError(str(exc)) from exc
        rsql,rparams=remark_query(run);ctes.append('remarks AS ('+rsql+')');params+=rparams
        ctes.append('latest AS (SELECT '+key('"SKUCode"')+' sk,'+key('"WhCode"')+' lk,'+key('"SupplierCode"')+
            ' sp,max("RemarkDate") d FROM remarks GROUP BY 1,2,3)')
        ctes.append('RM AS (SELECT M.* FROM remarks M JOIN latest T ON '+key('M."SKUCode"')+'=T.sk AND '+
            key('M."WhCode"')+'=T.lk AND '+key('M."SupplierCode"')+'=T.sp AND M."RemarkDate"=T.d)')
        joins=(' FROM mta.'+quote(BorPreparedRow._meta.db_table)+' R JOIN P ON R.sku_key='+key('P.code')+
            ' JOIN L ON R.location_key='+key('L.code')+' LEFT JOIN RM ON R.sku_key='+key('RM."SKUCode"')+
            ' AND R.location_key='+key('RM."WhCode"')+' AND R.supplier_key='+key('RM."SupplierCode"'))
        if filters.children:
            parent,pvals=image_query(run,'closing/importer/LocationAttributeData')
            ctes.append('parent AS ('+parent+')');params+=pvals
            joins+=(' JOIN parent ON '+equal(col('B','ParentWhCode'),'parent."WHCode"')+' AND ('+
                ' OR '.join(equal('parent."LocationType"','%s') for _ in filters.children)+')')
            params+=filters.children
        sql='WITH '+','.join(ctes)+' SELECT '+('count(*)' if count else ','.join(v+' AS '+quote(n) for n,v in projection()))+joins
        sql+=' WHERE R.run_id=%s AND ('+where+')';params+=[run.pk,*filters.params]
        if not count:
            ordering=('WHCode','SKUCode') if export else ('SKUCode','WHCode')
            sql+=(' ORDER BY '+col('B','DispatchColorSequence')+' NULLS FIRST,'+col('B','DispatchPen')+' DESC NULLS LAST,'+
                ','.join(key(col('A',n))+' NULLS FIRST' for n in ordering))
            paging=payload.get('paginationParameter')
            if paging is not None and not export:
                if not isinstance(paging,dict) or any(type(paging.get(n)) is not int for n in ('pageNumber','recordsPerPage')):
                    raise BorQueryError('native pagination invalid')
                offset=(paging['pageNumber']-1)*paging['recordsPerPage'];size=paging['recordsPerPage']
                if offset<0 or size<=0: raise BorQueryError('native pagination invalid')
                sql+=' LIMIT %s OFFSET %s';params+=[size,offset]
    with connection.cursor() as c:
        c.execute(sql,params)
        if count: return c.fetchone()[0]
        names=[f[0] for f in c.description];rows=[dict(zip(names,row)) for row in c.fetchall()]
    if analytics:
        return [{alias:[{n:rows[0][band+'_'+n] for n in ('rs','ns','sc')}] for band,alias in
                 (('Red','tor'),('Yellow','toy'),('Green','tog'),('Blue','tob'))}]
    for row in rows: row['SOB']=format(row['SOB'],'.6g')
    return rows
