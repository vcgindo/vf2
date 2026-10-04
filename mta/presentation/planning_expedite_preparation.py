"""One-time Expedite grid occurrences, preserving four directional join grains."""
from mta.presentation.planning_sources import admitted_sources
from mta.presentation.planning_grid_preparation import DIMENSIONS
from mta.presentation.selective import image_query
from mta.presentation.rrr_sql import equal,key
from mta.runtime.models import ExpediteRow
from mta.runtime.relational_state import quote


def grid_occurrences(run,direction,branch):
    if direction not in ('parent','child') or branch not in ('dispatch','availability'):
        raise ValueError('Unknown Expedite grid grain')
    sources=admitted_sources(run)
    ctes=['A AS (SELECT * FROM mta.'+quote(ExpediteRow._meta.db_table)+' WHERE run_id=%s)'];params=[run.pk]
    for alias,table in (*DIMENSIONS,('standard','SKULocStandardAttributes')):
        query,values=image_query(run,('closing/dbm/' if alias=='standard' else 'closing/importer/')+table)
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


def recipe_digest():
    import inspect
    from mta.serialization import digest
    return digest(dict(version=1,query=inspect.getsource(grid_occurrences)))
