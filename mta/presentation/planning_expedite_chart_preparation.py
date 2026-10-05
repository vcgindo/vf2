"""Exact one-time Expedite chart membership; scope and aggregation remain live."""
from mta.presentation.selective import image_query
from mta.presentation.planning_sources import admitted_sources
from mta.presentation.rrr_sql import equal,key


def members(run,direction,family):
    if direction not in ('parent','child') or family not in ('critical','receiving','nil_stock','chronic'):
        raise ValueError('Unknown Expedite chart grain')
    if direction=='child' and family in ('nil_stock','chronic'):
        raise ValueError('Parent-only Expedite chart')
    ctes=['E AS (SELECT * FROM mta.fresh_mta_expediterow WHERE run_id=%s)'];params=[run.pk]
    for alias,table in [('D','SiteDescriptionTbl'),('L','LocationAttributeData')]:
        query,values=image_query(run,'closing/importer/'+table)
        ctes.append(alias+' AS ('+query+')');params.extend(values)
    joins=' FROM E S';fact='S';master='NULL::bigint';attr=True
    where='TRUE'
    if family=='critical':
        where='S."RationedQty">0 AND '+key('S."PipelineInventoryColor"')+" IN ('black','red')"
        code='S."ParentWhCode"'
        if direction=='child':
            where+=' AND S."IsParent"'
            joins+=' JOIN E A ON '+equal('S."SKUCode"','A."SKUCode"')+' AND '+equal('S."ParentWhCode"','A."WhCode"')
            fact='A';code='A."WhCode"'
    elif family=='receiving':
        code='S."WhCode"'
        if direction=='child':where='S."IsReceiving"'
    else:
        query,values=admitted_sources(run)['bpr_master'];ctes.append('M AS ('+query+')');params.extend(values)
        joins+=' JOIN M ON '+equal('S."SKUCode"','M."SKUCode"')+' AND '+equal('S."ParentWhCode"','M."WHCode"')
        code='M."ParentWhCode"';master='M.source_ordinal';attr=False
        where='S."RationedQty"=0' if family=='nil_stock' else 'S."BRAge">0'
    joins+=' JOIN D ON '+equal(code,'D."WHCode"')
    if attr:joins+=' JOIN L ON '+equal(code,'L."WHCode"')
    columns=dict(scope_ordinal='S.ordinal',fact_ordinal=fact+'.ordinal',master_ordinal=master,
                 description_ordinal='D.vf_ordinal',location_ordinal='L.vf_ordinal' if attr else 'NULL::bigint',
                 code=code,code_key=key(code),description='D."WHDescription"',description_key=key('D."WHDescription"'))
    for field in ('LogisticsLocation','LL1','LL2','LL3','LL4','LL5'):
        columns[field.lower()]='L."'+field+'"' if attr else 'NULL::text'
    return 'WITH '+','.join(ctes)+' SELECT '+','.join(value+' AS '+name for name,value in columns.items())+joins+' WHERE '+where,params


def prepost_members(run):
    """Compact exact parent child-location multiplicity, before live permissions.

    Parent's CTE groups SKU/location after joining children on location only.
    The outer report joins that grouped pair back to every matching Pick row.
    Retain source and target ordinals separately; no SKU condition on children.
    """
    from mta.presentation.planning_expedite_transit_preparation import pick_source,PICK_TABLE
    pick_source(verify_values=True)
    return ('WITH P AS (SELECT * FROM '+PICK_TABLE+'), children AS ('
        'SELECT '+key('"ParentWhCode"')+' AS location_key,count(*)::bigint AS multiplicity FROM P '
        'WHERE "ParentWhCode" IS NOT NULL GROUP BY '+key('"ParentWhCode"')+') '
        'SELECT S.vf_source_ordinal AS scope_ordinal,T.vf_source_ordinal AS fact_ordinal,C.multiplicity '
        'FROM P S JOIN children C ON '+key('S."WhCode"')+'=C.location_key '
        'JOIN P T ON '+equal('S."SKUCode"','T."SKUCode"')+' AND '+equal('S."WhCode"','T."WhCode"')+
        ' WHERE T."WhCode" IS NOT NULL AND T."ParentWhCode" IS NOT NULL AND NOT '+equal('T."WhCode"','T."ParentWhCode"')),[]


def recipe_digest():
    import inspect
    from mta.serialization import digest
    return digest(dict(version=1,members=inspect.getsource(members),prepost=inspect.getsource(prepost_members)))
