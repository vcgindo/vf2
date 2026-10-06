"""Prepared GIT location reads with native directional permission ownership."""
from types import SimpleNamespace
from django.db import connection
from mta.presentation.planning_git import admitted_git
from mta.presentation.planning_grid_sql import GridFilters
from mta.presentation.planning_sources import admitted_sources
from mta.presentation.bpr_sql import _projected_attributes
from mta.presentation.context import scope,PublicationUnavailable
from mta.presentation.fixture import bpr_ancillary
from mta.presentation.selective import image_query
from mta.presentation.rrr_sql import equal
from mta.runtime.models import PlanningGitMasterRow
from mta.runtime.relational_state import quote


def grid(run,payload,*,count=False,overview=False,resolved_scope=None):
    from mta.presentation.git_read import validate_filters,NORMAL_COLUMNS
    from mta.presentation.excess_read import pagination
    kind=str(payload.get('type','')).lower()
    if kind not in ('parent','child'):raise PublicationUnavailable('selected_git_type_not_supported')
    paging=pagination(payload)
    occurrence,params=admitted_git(run)['row'];params=list(params)
    master,values=admitted_sources(run)['git_master']
    from mta.presentation.daily_preparation import production_branch
    transit=(__import__('mta.presentation.daily_preparation',fromlist=['ancillary_row']).ancillary_row(run,'InTransitData')
             if production_branch(run) else bpr_ancillary(run)['InTransitData'])
    if transit:raise PublicationUnavailable('planning_transporter_nonempty_source_not_prepared')
    importer,manifest=_projected_attributes(run) if resolved_scope is None else resolved_scope[:2]
    if manifest:raise PublicationUnavailable('planning_git_native_hierarchy_required')
    validate_filters(payload,SimpleNamespace(attributes=importer),child_count=count and kind=='child')
    filters=GridFilters(payload,'git',PlanningGitMasterRow)
    where=filters.compile()
    if overview:
        if not count:raise ValueError('Overview requires GIT count')
        where+=' AND H.grid_eligible'
    products,locations=scope(payload,attributes=importer) if resolved_scope is None else resolved_scope[2:]
    config=[dict(header=h,colCode=c,colPosition=p) for h,c,p in NORMAL_COLUMNS]
    if not products or not locations:
        return [dict(locationwise=0,**({'transporterwise':0} if kind=='child' else {}))] if count else combined_grid(kind,[],config)
    ctes=['H AS ('+occurrence+')','A AS ('+master+')'];params.extend(values)
    for alias,codes in (('P',products),('L',locations)):
        members=sorted(codes)
        ctes.append(alias+'(code,weight) AS (VALUES '+','.join(['(%s::text,%s::bigint)']*len(members))+')')
        params.extend(v for code in members for v in (code,codes.multiplicities[code]))
    owners=set(filters.owners)
    if not count:owners.add('C')
    joins=(' FROM H JOIN A ON A.rationed_ordinal=H.rationed_ordinal AND A.standard_ordinal=H.standard_ordinal '
           'JOIN P ON A."SKUCode"=P.code JOIN L ON A.'+quote('WhCode' if kind=='parent' else 'ParentWhCode')+'=L.code')
    for alias,table,ordinal in [('B','SkuLocAttributeData','pair_ordinal'),('C','SkuAttributeData','sku_ordinal'),('D','LocationAttributeData','location_ordinal')]:
        if alias not in owners and not(alias=='D' and filters.children):continue
        query,values=image_query(run,'closing/importer/'+table);ctes.append(alias+' AS NOT MATERIALIZED ('+query+')');params.extend(values)
        if alias in owners:joins+=' LEFT JOIN '+alias+' ON '+alias+'.vf_ordinal=H.'+ordinal
    if filters.children:
        joins+=' JOIN D parent ON '+equal('A."ParentWhCode"','parent."WHCode"')+' AND ('+' OR '.join(equal('parent."LocationType"','%s') for _ in filters.children)+')'
        params.extend(filters.children)
    params.extend(filters.params)
    if count:
        with connection.cursor() as c:
            c.execute('WITH '+','.join(ctes)+' SELECT COALESCE(sum(P.weight*L.weight),0)'+joins+' WHERE '+where,params)
            total=int(c.fetchone()[0])
        return [dict(locationwise=total,**({'transporterwise':0} if kind=='child' else {}))]
    aliases=dict(st='Status',sc='SKUCode',wc='WhCode',t='Tags',pwc='ParentWhCode',n='Norm',vn='VirtualNorm',stk='Stock',g='Git',pip='PhysicalInventoryPen',pic='PhysicalInventoryColor',plp='PipelineInventoryPen',plc='PipelineInventoryColor',rq='Req',pr='Price')
    columns={alias:'A.'+quote(field) for alias,field in aliases.items()}
    columns.update(skd='H.sku_description',wcd='H.location_description',prn='H.parent_description',
                   eoc='C."ElephantOrderCapping"',v='C."Volume"',wt='C."Weight"')
    columns.update({p+str(i):'H.'+p+str(i) for p in ('sl','ll') for i in range(1,6)})
    ctes.append('selected AS (SELECT row_number() OVER (ORDER BY trunc(A."PhysicalInventoryPen")::integer DESC NULLS LAST,H.ordinal,copies.n) AS rn,'
                +','.join(value+' AS '+quote(alias) for alias,value in columns.items())+joins+
                ' CROSS JOIN LATERAL generate_series(1,P.weight*L.weight) copies(n) WHERE H.grid_eligible AND '+where+')')
    sql='WITH '+','.join(ctes)+' SELECT * FROM selected'
    if paging is not None:
        sql+=' WHERE rn BETWEEN %s AND %s';params.extend(((paging[0]-1)*paging[1]+1,paging[0]*paging[1]))
    sql+=' ORDER BY rn'
    with connection.cursor() as c:
        c.execute(sql,params);names=[d[0] for d in c.description]
        rows=[dict(zip(names,row)) for row in c.fetchall()]
    from decimal import Decimal
    for row in rows:
        for field,value in row.items():
            if isinstance(value,Decimal):row[field]=float(value)
        row.update(AgeingOrder=None,transit=[])
    return combined_grid(kind,rows,config)


def combined_grid(kind,rows,config):
    """Keep the independently admitted empty shipment grain separate.

    The caller rejects nonempty InTransitData before this assembly. No aggregate
    GIT row supplies TransporterCode/OrderNo/InTransitQty or a shipment SKU.
    The existing child frontend consumes two independent data/uiConfig objects.
    """
    location = dict(data=rows,uiConfig=config)
    if kind == 'parent':
        return location
    return dict(locationWise=location,transporterWise=dict(data=[],uiConfig=[]))
