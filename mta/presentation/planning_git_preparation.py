from mta.presentation.native_mode import removed_mode
"""One-time GIT location membership; count LEFT pair versus grid INNER pair."""
from mta.presentation.planning_sources import admitted_sources
from mta.presentation.planning_grid_preparation import DIMENSIONS
from mta.presentation.rrr_sql import equal,key
from mta.presentation.selective import image_query
from mta.runtime.relational_state import quote


def git_occurrences(run):
    query,params=admitted_sources(run)['git_master']
    if removed_mode('historical_fixture')['InTransitData']:
        raise ValueError('GIT preparation requires qualified empty shipment source')
    ctes=['a AS ('+query+')'];params=list(params)
    for alias,table in DIMENSIONS:
        query,values=image_query(run,'closing/importer/'+table)
        ctes.append(alias+' AS ('+query+')');params.extend(values)
    fields=[('rationed_ordinal','a.rationed_ordinal'),('standard_ordinal','a.standard_ordinal'),
            ('sku_description_ordinal','sd.vf_ordinal'),('location_description_ordinal','ld.vf_ordinal'),
            ('parent_description_ordinal','pd.vf_ordinal'),('sku_ordinal','sa.vf_ordinal'),
            ('location_ordinal','la.vf_ordinal'),('pair_ordinal','pair.vf_ordinal'),
            ('sku_description','sd."SKUDescription"'),('location_description','ld."WHDescription"'),
            ('parent_description','pd."WHDescription"'),('grid_eligible','pair.vf_ordinal IS NOT NULL')]
    fields += [(prefix.lower()+str(i),alias+'.'+quote(prefix+str(i))) for alias,prefix in (('sa','SL'),('la','LL')) for i in range(1,6)]
    joins=(' FROM a JOIN sd ON '+equal('a."SKUCode"','sd."SKUCode"')+
           ' JOIN ld ON '+equal('a."WhCode"','ld."WHCode"')+
           ' LEFT JOIN ld pd ON '+equal('a."ParentWhCode"','pd."WHCode"')+
           ' JOIN sa ON '+equal('a."SKUCode"','sa."SKUCode"')+
           ' JOIN la ON '+equal('a."WhCode"','la."WHCode"')+
           ' LEFT JOIN pair ON '+equal('a."SKUCode"','pair."SKUCode"')+' AND '+equal('a."WhCode"','pair."LocCode"'))
    # Empty admitted InTransitData proves canonical transporter LEFT join has
    # one NULL match, empty nested transit and NULL AgeingOrder. No engine run.
    where=' WHERE a."Git">0 AND '+key('a."PhysicalInventoryColor"')+" IN ('black','red')"
    return 'WITH '+','.join(ctes)+' SELECT '+','.join(value+' AS '+quote(name) for name,value in fields)+joins+where,params


def production_git_occurrences(run,*,read_binding=None):
    relations=admitted_sources(run) if read_binding is None else admitted_sources(run,read_binding=read_binding)
    query,params=relations['git_master']
    ctes=['a AS ('+query+')'];params=list(params)
    # PlanningProcessor.GetMonitorGITParent LEFT JOINs the transporter source on
    # SKU/location without selecting any transporter fields.  Its sole effect on
    # this prepared location grain is occurrence multiplication: one row per
    # matching transporter occurrence, or one NULL-side row when none match.
    from mta.presentation.daily_transit import TRANSPORTER_PATH
    query,values=image_query(run,TRANSPORTER_PATH) if read_binding is None else read_binding.image_query(TRANSPORTER_PATH)
    ctes.append('tm AS ('+query+')');params.extend(values)
    for alias,table in DIMENSIONS:
        path='closing/importer/'+table
        query,values=image_query(run,path) if read_binding is None else read_binding.image_query(path)
        ctes.append(alias+' AS ('+query+')');params.extend(values)
    fields=[('rationed_ordinal','a.rationed_ordinal'),('standard_ordinal','a.standard_ordinal'),
            ('sku_description_ordinal','sd.vf_ordinal'),('location_description_ordinal','ld.vf_ordinal'),
            ('parent_description_ordinal','pd.vf_ordinal'),('sku_ordinal','sa.vf_ordinal'),
            ('location_ordinal','la.vf_ordinal'),('pair_ordinal','pair.vf_ordinal'),
            ('sku_description','sd."SKUDescription"'),('location_description','ld."WHDescription"'),
            ('parent_description','pd."WHDescription"'),('grid_eligible','pair.vf_ordinal IS NOT NULL')]
    if read_binding is not None:fields.append(('transporter_ordinal','tm.vf_ordinal'))
    fields += [(prefix.lower()+str(i),alias+'.'+quote(prefix+str(i))) for alias,prefix in (('sa','SL'),('la','LL')) for i in range(1,6)]
    joins=(' FROM a LEFT JOIN tm ON '+equal('a."SKUCode"','tm."SKUCode"')+
           ' AND '+equal('a."WhCode"','tm."WhCode"')+
           ' JOIN sd ON '+equal('a."SKUCode"','sd."SKUCode"')+
           ' JOIN ld ON '+equal('a."WhCode"','ld."WHCode"')+
           ' LEFT JOIN ld pd ON '+equal('a."ParentWhCode"','pd."WHCode"')+
           ' JOIN sa ON '+equal('a."SKUCode"','sa."SKUCode"')+
           ' JOIN la ON '+equal('a."WhCode"','la."WHCode"')+
           ' LEFT JOIN pair ON '+equal('a."SKUCode"','pair."SKUCode"')+' AND '+equal('a."WhCode"','pair."LocCode"'))
    where=' WHERE a."Git">0 AND '+key('a."PhysicalInventoryColor"')+" IN ('black','red')"
    return 'WITH '+','.join(ctes)+' SELECT '+','.join(value+' AS '+quote(name) for name,value in fields)+joins+where,params


def recipe_digest():
    import inspect
    from mta.serialization import digest
    return digest(dict(version=1,query=inspect.getsource(git_occurrences)))


def production_recipe_digest():
    import inspect
    from mta.serialization import digest
    return digest(dict(version=2,query=inspect.getsource(production_git_occurrences)))
