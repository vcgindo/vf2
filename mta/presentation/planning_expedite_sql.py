"""SQL parent Expedite grid over prepared occurrences and nested-transit matches."""
from copy import deepcopy
from decimal import Decimal
from django.db import connection, transaction
from mta.presentation.bpr_sql import _projected_attributes
from mta.presentation.context import PublicationUnavailable, scope
from mta.presentation.expedite_parent import parent_filter
from mta.presentation.planning_grid_sql import GridFilters
from mta.presentation.planning_expedite_grids import admitted_expedite_grids
from mta.presentation.planning_expedite_transit import transit_rows
from mta.presentation.rrr_sql import key, equal
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


def selected_parent(run,payload,*,child=False,count_direction=None,resolved_scope=None):
    """One complete scope/filter relation shared by paging and nested transit."""
    importer, manifest = _projected_attributes(run) if resolved_scope is None else resolved_scope[:2]
    if manifest:
        raise PublicationUnavailable('planning_expedite_native_hierarchy_required')
    if child:
        from mta.presentation.excess_filters import predicate
        predicate(payload,importer)
    else:
        parent_filter(payload,importer)
    filtered = deepcopy(payload)
    supply = (filtered.get('filters') or {}).get('supplyChainFilter')
    if supply and not child:
        supply['filters'] = [item for item in supply['filters'] if item.get('attributeName','').lower() != 'forchildren']
    filters = ExpediteFilters(filtered,'expedite-parent',ExpediteRow)
    where = filters.compile()
    products, locations = scope(payload,attributes=importer) if resolved_scope is None else resolved_scope[2:]
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
             'JOIN P ON P.code=A."SKUCode" JOIN L ON L.code=A.'+quote('ParentWhCode' if child and count_direction!='parent' else 'WhCode')+' '
             'LEFT JOIN S ON S.vf_ordinal=H.standard_ordinal')
    for alias,table,ordinal in [('B','SkuLocAttributeData','pair_ordinal'),('C','SkuAttributeData','sku_ordinal'),('D','LocationAttributeData','location_ordinal')]:
        if alias not in filters.owners and not (child and alias=='D' and filters.children): continue
        query, values = image_query(run,'closing/importer/'+table)
        ctes.append(alias+' AS NOT MATERIALIZED ('+query+')');params.extend(values)
        if alias in filters.owners:
            joins += ' LEFT JOIN '+alias+' ON '+alias+'.vf_ordinal=H.'+ordinal
    if child and filters.children:
        joins += ' JOIN D parent ON '+equal('A."ParentWhCode"','parent."WHCode"')+' AND ('+' OR '.join(equal('parent."LocationType"','%s') for _ in filters.children)+')'
        params.extend(filters.children)
    params.extend(filters.params)
    columns = {alias:'A.'+quote(field) for alias,field in ALIASES.items()}
    columns.update(DISPLAY)
    if count_direction is not None:
        if not child or count_direction not in ('parent','child'):
            raise ValueError('Invalid Expedite count grain')
        # Child dispatch LEFT matches become the canonical count INNER grain;
        # child availability already has that grain, with no parent-master join.
        where += ' AND '+ ' AND '.join('H.'+field+' IS NOT NULL' for field in
            ('standard_ordinal','sku_description_ordinal','location_description_ordinal','sku_ordinal','location_ordinal','pair_ordinal'))
        where += ' AND '+key('A."PipelineInventoryColor"')+" IN ('red','black')"
    if child:
        columns.update(sap='A."RationedQty"',ec='A."ParentPipelineInventoryColor"',rlt='A."RLT"')
        columns.update({p+str(i):'H.'+p+str(i) for p in ('sl','ll') for i in (4,5)})
    age = 'A."BRAge"' if child else 'COALESCE(A."BRAge",0)'
    selected = ('SELECT H.ordinal,H.branch,P.weight*L.weight AS weight,'+age+' AS age,'
                +','.join(key('A.'+quote(field))+' AS '+name for field,name in [('SKUCode','sk'),('WhCode','lk'),('ParentWhCode','pk')])+','
                +','.join(value+' AS '+quote(alias) for alias,value in columns.items())+joins+
                " WHERE H.direction='"+('child' if child else 'parent')+"' AND "+where)
    return 'WITH '+','.join(ctes)+' '+selected,params


def counts(run,payload,*,resolved_scope=None):
    direction=str(payload.get('type','')).casefold()
    if direction not in ('parent','child'):
        raise ValueError('Unsupported Expedite direction')
    availability=(payload.get('filters') or {}).get('availabilityFilter') or {}
    if any(item.get('attributeName','').lower()=='norm' for item in availability.get('filters',[])):
        raise PublicationUnavailable('expedite_count_norm_filter_contract_unverified')
    selected,params=selected_parent(run,payload,child=True,count_direction=direction,resolved_scope=resolved_scope)
    result=dict(expediteDispatches=0,createAvailabilityAtParent=0)
    with connection.cursor() as c:
        c.execute('WITH selected AS ('+selected+') SELECT branch,sum(weight)::integer FROM selected GROUP BY branch',params)
        for branch,total in c.fetchall():
            result['expediteDispatches' if branch=='dispatch' else 'createAvailabilityAtParent']=total
    return result


def parent_grid(run,payload):
    from mta.presentation.expedite_read import PARENT_COLUMNS
    from mta.presentation.excess_read import pagination
    paging = pagination(payload)
    if paging is None:
        raise PublicationUnavailable('LEG-EXPEDITE-PARENT-UNPAGED-SQL156: legacy empty-success; NOT_PARITY')
    selected, params = selected_parent(run,payload)
    with transaction.atomic(), connection.cursor() as c:
        # Compilation dominates this bounded prepared-row query. Preserve the
        # caller's setting, including callers that already own a transaction.
        c.execute("SELECT current_setting('jit')")
        previous_jit = c.fetchone()[0]
        c.execute('SET LOCAL jit=off')
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
        c.execute("SELECT set_config('jit',%s,true)",[previous_jit])
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


def child_grid(run,payload):
    from datetime import datetime,time,timedelta
    from mta.presentation.expedite_read import PARENT_COLUMNS
    from mta.presentation.excess_read import pagination
    from mta.presentation.planning_expedite_requests import empty_requests
    from mta.presentation.fixture import bpr_ancillary
    if empty_requests(run) or bpr_ancillary(run)['InTransitData']:
        raise PublicationUnavailable('child_expedite_requires_approved_empty_request_and_transit_inputs')
    selected,params=selected_parent(run,payload,child=True)
    fields=[*FIELDS,'sap','ec','rlt','sl4','sl5','ll4','ll5']
    with connection.cursor() as c:
        c.execute('WITH selected AS ('+selected+') SELECT 1 FROM selected GROUP BY branch,age,sk,lk,pk '
                  'HAVING count(DISTINCT ROW('+','.join(map(quote,fields))+'))>1 LIMIT 1',params)
        if c.fetchone():raise PublicationUnavailable('child_expedite_ambiguous_row_number')
        query=('WITH selected AS ('+selected+'), numbered AS (SELECT branch,'
            'row_number() OVER (PARTITION BY branch ORDER BY age DESC NULLS LAST,sk DESC NULLS LAST,lk DESC NULLS LAST,pk DESC NULLS LAST,ordinal,copies.copy_ordinal) AS rn,'
            +','.join(map(quote,fields))+' FROM selected CROSS JOIN LATERAL generate_series(1,weight) copies(copy_ordinal)) SELECT * FROM numbered')
        paging=pagination(payload)
        if paging is not None:
            query+=' WHERE rn BETWEEN %s AND %s';params=[*params,(paging[0]-1)*paging[1]+1,paging[0]*paging[1]]
        c.execute(query+' ORDER BY branch,rn',params)
        names=[col[0] for col in c.description]
        rows=[dict(zip(names,row)) for row in c.fetchall()]
    result=dict(expediteDispatches=[],createAvailabilityAtParent=[])
    for row in rows:
        target='expediteDispatches' if row.pop('branch')=='dispatch' else 'createAvailabilityAtParent'
        rlt=row.pop('rlt')
        row.update(remark=None,intransit='[]',eta=None if rlt is None else
                   (datetime.combine(run.business_date,time())+timedelta(days=rlt)).isoformat())
        for field in ('pip','pin','p'):
            if row[field] is not None:row[field]=float(row[field])
        result[target].append(row)
    positions={'rq':12,'pin':11}
    return dict(data=result,uiConfig=[dict(header=h,colCode=c,colPosition=positions.get(c,p)) for h,c,p in PARENT_COLUMNS])
