"""SQL parent Expedite grid over prepared occurrences and nested-transit matches."""
from copy import deepcopy
from decimal import Decimal
from django.db import connection
from mta.presentation.bpr_sql import _projected_attributes
from mta.presentation.context import PublicationUnavailable, scope
from mta.presentation.expedite_parent import parent_filter
from mta.presentation.planning_grid_sql import GridFilters
from mta.presentation.planning_expedite_grids import admitted_expedite_grids
from mta.presentation.planning_expedite_transit import transit_rows
from mta.presentation.rrr_sql import key
from mta.presentation.selective import image_query
from mta.runtime.models import ExpediteRow
from mta.runtime.relational_state import quote


class ExpediteFilters(GridFilters):
    def column(self, owner, name):
        if owner == 'A' and name.lower() == 'tags':
            return 'S."Tags"','text'
        return super().column(owner,name)


ALIASES = dict(sc='SKUCode',wc='WhCode',n='Norm',vn='VirtualNorm',st='Stock',g='GIT',
               pip='PhysicalInventoryPen',pic='PhysicalInventoryColor',pin='PipelineInventoryPen',
               plc='PipelineInventoryColor',rq='Req',rtq='RationedQty')
DISPLAY = dict(t='S."Tags"',p='S."Price"',sd='H.sku_description',wcd='H.location_description',pl='H.parent_description')
DISPLAY.update({p+str(i):'H.'+p+str(i) for p in ('sl','ll') for i in (1,2,3)})
FIELDS = [*ALIASES,*DISPLAY]


def selected_parent(run,payload):
    """One complete scope/filter relation shared by paging and nested transit."""
    importer, manifest = _projected_attributes(run)
    if manifest:
        raise PublicationUnavailable('planning_expedite_native_hierarchy_required')
    parent_filter(payload,importer)
    filtered = deepcopy(payload)
    supply = (filtered.get('filters') or {}).get('supplyChainFilter')
    if supply:
        supply['filters'] = [item for item in supply['filters'] if item.get('attributeName','').lower() != 'forchildren']
    filters = ExpediteFilters(filtered,'expedite-parent',ExpediteRow)
    where = filters.compile()
    products, locations = scope(payload,attributes=importer)
    relation, params = admitted_expedite_grids(run)['row']; params = list(params)
    standard, values = image_query(run,'closing/dbm/SKULocStandardAttributes')
    ctes = ['H AS ('+relation+')','S AS NOT MATERIALIZED ('+standard+')'];params.extend(values)
    for alias,codes in (('P',products),('L',locations)):
        members = sorted(codes)
        if members:
            ctes.append(alias+'(code,weight) AS (VALUES '+','.join(['(%s::text,%s::bigint)']*len(members))+')')
            params.extend(v for code in members for v in (code,codes.multiplicities[code]))
        else:
            ctes.append(alias+'(code,weight) AS (SELECT NULL::text,0::bigint WHERE FALSE)')
    joins = (' FROM H JOIN mta.fresh_mta_expediterow A ON A.run_id=H.run_id AND A.ordinal=H.fact_ordinal '
             'JOIN P ON P.code=A."SKUCode" JOIN L ON L.code=A."WhCode" '
             'LEFT JOIN S ON S.vf_ordinal=H.standard_ordinal')
    for alias,table,ordinal in [('B','SkuLocAttributeData','pair_ordinal'),('C','SkuAttributeData','sku_ordinal'),('D','LocationAttributeData','location_ordinal')]:
        if alias not in filters.owners: continue
        query, values = image_query(run,'closing/importer/'+table)
        ctes.append(alias+' AS NOT MATERIALIZED ('+query+')');params.extend(values)
        joins += ' LEFT JOIN '+alias+' ON '+alias+'.vf_ordinal=H.'+ordinal
    params.extend(filters.params)
    columns = {alias:'A.'+quote(field) for alias,field in ALIASES.items()}
    columns.update(DISPLAY)
    selected = ('SELECT H.ordinal,H.branch,P.weight*L.weight AS weight,COALESCE(A."BRAge",0) AS age,'
                +','.join(key('A.'+quote(field))+' AS '+name for field,name in [('SKUCode','sk'),('WhCode','lk'),('ParentWhCode','pk')])+','
                +','.join(value+' AS '+quote(alias) for alias,value in columns.items())+joins+
                " WHERE H.direction='parent' AND "+where)
    return 'WITH '+','.join(ctes)+' '+selected,params


def parent_grid(run,payload):
    from mta.presentation.expedite_read import PARENT_COLUMNS
    from mta.presentation.excess_read import pagination
    paging = pagination(payload)
    if paging is None:
        raise PublicationUnavailable('LEG-EXPEDITE-PARENT-UNPAGED-SQL156: legacy empty-success; NOT_PARITY')
    selected, params = selected_parent(run,payload)
    with connection.cursor() as c:
        c.execute('WITH selected AS ('+selected+') SELECT 1 FROM selected GROUP BY branch,age,sk,lk,pk '
                  'HAVING count(DISTINCT ROW('+','.join(map(quote,FIELDS))+'))>1 LIMIT 1',params)
        if c.fetchone():
            raise PublicationUnavailable('parent_expedite_ambiguous_row_number')
        query = ('WITH selected AS ('+selected+'), numbered AS (SELECT branch,'
            'row_number() OVER (PARTITION BY branch ORDER BY age DESC,sk DESC NULLS LAST,lk DESC NULLS LAST,pk DESC NULLS LAST,ordinal,copies.copy_ordinal) AS rn,'
            +','.join(map(quote,FIELDS))+' FROM selected CROSS JOIN LATERAL generate_series(1,weight) copies(copy_ordinal)) '
            'SELECT * FROM numbered WHERE rn BETWEEN %s AND %s ORDER BY branch,rn')
        c.execute(query,[*params,(paging[0]-1)*paging[1]+1,paging[0]*paging[1]])
        names = [column[0] for column in c.description]
        rows = [dict(zip(names,row)) for row in c.fetchall()]
    result = dict(expediteDispatches=[],createAvailabilityAtParent=[])
    for row in rows:
        target = 'expediteDispatches' if row.pop('branch') == 'dispatch' else 'createAvailabilityAtParent'
        values = {}
        for field,value in row.items():
            if value is None: continue
            scale = 2 if field in ('pip','pin') else 3 if field == 'p' else None
            values[field] = format(Decimal(str(value)),f'.{scale}f') if scale is not None else str(value)
        result[target].append(values)
    for branch,target in [('dispatch','expediteDispatchestransit'),('availability','createAvailabilityAtParenttransit')]:
        result[target] = transit_rows(run,branch,'WITH selected AS ('+selected+') SELECT ordinal FROM selected WHERE branch=%s',[*params,branch])
    return dict(data=result,uiConfig=[dict(header=h,colCode=c,colPosition=p) for h,c,p in PARENT_COLUMNS])
