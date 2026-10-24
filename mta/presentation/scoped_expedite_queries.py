"""Scoped Expedite occurrence SQL; original Full recipes stay unchanged.

Preparation-only relations, not readiness, persistence or UI selection.
Pick, request and parent-transit dependencies are deliberately not inferred.
"""
import inspect
from mta.presentation.context import PublicationUnavailable
from mta.presentation.planning_sources import admitted_sources
from mta.presentation.planning_grid_preparation import DIMENSIONS
from mta.presentation.rrr_sql import equal,key
from mta.runtime.relational_state import quote
from mta.serialization import digest


def _sources(run,bound):
    if bound is None:raise PublicationUnavailable('expedite_scoped_binding_required')
    return admitted_sources(run,read_binding=bound)


def grid_occurrences(run,direction,branch,*,read_binding):
    if direction not in ('parent','child') or branch not in ('dispatch','availability'):
        raise ValueError('Unknown Expedite grid grain')
    sources=_sources(run,read_binding)
    query,params=read_binding.fact_query('ExpediteDispatches')
    ctes=['A AS ('+query+')'];params=list(params)
    for alias,table in (*DIMENSIONS,('standard','SKULocStandardAttributes')):
        query,values=read_binding.image_query(('closing/dbm/' if alias=='standard' else 'closing/importer/')+table)
        ctes.append(alias+' AS ('+query+')');params.extend(values)
    if direction=='parent' and branch=='availability':
        query,values=sources['bpr_master'];ctes.append('master AS ('+query+')');params.extend(values)
    join='JOIN' if direction=='child' and branch=='availability' else 'LEFT JOIN'
    joins=' FROM A '+join+' standard ON '+equal('A."SKUCode"','standard."SKUCode"')+' AND '+equal('A."WhCode"','standard."WhCode"')
    for alias,field in [('sd','SKUCode'),('ld','WHCode'),('sa','SKUCode'),('la','WHCode')]:
        joins+=' '+join+' '+alias+' ON '+equal('A.'+quote('SKUCode' if field=='SKUCode' else 'WhCode'),alias+'.'+quote(field))
    joins+=' LEFT JOIN ld pd ON '+equal('A."ParentWhCode"','pd."WHCode"')
    joins+=' '+join+' pair ON '+equal('A."SKUCode"','pair."SKUCode"')+' AND '+equal('A."WhCode"','pair."LocCode"')
    fields=[('fact_ordinal','A.ordinal'),('standard_ordinal','standard.vf_ordinal'),('sku_description_ordinal','sd.vf_ordinal'),
            ('location_description_ordinal','ld.vf_ordinal'),('parent_description_ordinal','pd.vf_ordinal'),
            ('sku_ordinal','sa.vf_ordinal'),('location_ordinal','la.vf_ordinal'),('pair_ordinal','pair.vf_ordinal'),
            ('sku_description','sd."SKUDescription"'),('location_description','ld."WHDescription"'),('parent_description','pd."WHDescription"')]
    if direction=='parent' and branch=='availability':
        joins+=' JOIN master ON '+equal('A."SKUCode"','master."SKUCode"')+' AND '+equal('A."ParentWhCode"','master."WHCode"')
        fields.append(('master_ordinal','master.source_ordinal'))
    else:fields.append(('master_ordinal','NULL::bigint'))
    fields += [(p.lower()+str(i),alias+'.'+quote(p+str(i))) for alias,p in [('sa','SL'),('la','LL')] for i in range(1,6)]
    where='A."RationedQty"'+('>0' if branch=='dispatch' else '=0')
    if direction=='parent' or branch=='dispatch':where+=' AND '+key('A."PipelineInventoryColor"')+" IN ('black','red')"
    return 'WITH '+','.join(ctes)+' SELECT '+','.join(value+' AS '+quote(name) for name,value in fields)+joins+' WHERE '+where,params


def custom_occurrences(run,*,read_binding):
    _sources(run,read_binding)
    query,params=read_binding.fact_query('ExpediteDispatches')
    ctes=['B AS ('+query+')'];params=list(params)
    for alias,path in [('A','closing/consumer_context/NMSAllItems'),('D','reports/bpr/BPR_Table'),('C','closing/importer/SiteDescriptionTbl')]:
        query,values=read_binding.image_query(path);ctes.append(alias+' AS ('+query+')');params.extend(values)
    joins=' FROM B LEFT JOIN A ON '+equal('B."SKUCode"','A."SKUCode"')+' AND '+equal('B."WhCode"','A."WhCode"')
    joins+=' LEFT JOIN D ON '+equal('A."SKUCode"','D."SKUCode"')+' AND '+equal('A."WhCode"','D."WhCode"')
    joins+=' LEFT JOIN C ON '+equal('A."ParentWhCode"','C."WHCode"')
    fields=dict(fact_ordinal='B.ordinal',nms_ordinal='A.vf_ordinal',bpr_ordinal='D.vf_ordinal',
                parent_description_ordinal='C.vf_ordinal',sku_key=key('A."SKUCode"'),location_key=key('A."WhCode"'),
                parent_description='C."WHDescription"')
    return ('WITH '+','.join(ctes)+' SELECT '+','.join(value+' AS '+name for name,value in fields.items())+joins+
            ' WHERE B."RationedQty">0 AND B."IsReceiving" AND '+key('B."PipelineInventoryColor"')+" IN ('black','red')"),params


def members(run,direction,family,*,read_binding):
    if direction not in ('parent','child') or family not in ('critical','receiving','nil_stock','chronic'):
        raise ValueError('Unknown Expedite chart grain')
    if direction=='child' and family in ('nil_stock','chronic'):
        raise ValueError('Parent-only Expedite chart')
    sources=_sources(run,read_binding)
    query,params=read_binding.fact_query('ExpediteDispatches')
    ctes=['E AS ('+query+')'];params=list(params)
    for alias,table in [('D','SiteDescriptionTbl'),('L','LocationAttributeData')]:
        query,values=read_binding.image_query('closing/importer/'+table)
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
        query,values=sources['bpr_master'];ctes.append('M AS ('+query+')');params.extend(values)
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


def recipe_digest():
    return digest(dict(schema='fresh-bpr-expedite-occurrence-queries-v1',
        source=inspect.getsource(inspect.getmodule(recipe_digest)),dimensions=DIMENSIONS))
