"""Canonical child-transporter count; supplied scopes remain enforced.

PlanningProcessor GetPlanningGridCount, SHA bf716c4f84e43920b5f2ab302e3d3c78ec685f5d714471c53047d377537d3486.
The two description joins both use destination WhCode, as deployed. This does
not repair the separate invalid child transporter grid or missing filter aliases.
"""
from django.db import connection
from mta.presentation.context import PublicationUnavailable
from mta.presentation.daily_transit import TRANSPORTER_PATH
from mta.presentation.rrr_sql import equal, key
from mta.presentation.selective import image_query
from mta.presentation.planning_grid_sql import GridFilters
from mta.runtime.relational_state import CATALOG, quote


class CountFilters(GridFilters):
    def __init__(self,payload):
        super().__init__(payload,'git',None)

    def column(self,owner,name):
        if owner=='C':
            raise PublicationUnavailable('LEG-GIT-FILTER-INVALID-SQL:child transporter count missing sa alias')
        table={'A':'BPR/GoodsInTransitTransporterMaster',
               'B':'Importer/SkuLocAttributeData','D':'Importer/LocationAttributeData'}[owner]
        alias={'A':'a','B':'sla','D':'la'}[owner]
        # GetPlanningGridCount leaves these Commons columns unqualified. In
        # its actual joins the only owner is vf (numeric stock fields) or slsa
        # (Tags); unlike the grid, they are not columns of transporter a.
        if owner=='A' and name.lower() in ('norm','stock','git','virtualnorm'):
            table='BPR/vf_RationedReqReport';alias='vf'
        elif owner=='A' and name.lower()=='tags':
            table='Importer/SKULocStandardAttributes';alias='slsa'
        fields={field.lower():(field,kind) for field,kind in CATALOG['tables'][table]}
        if name.lower() not in fields:
            raise PublicationUnavailable('LEG-GIT-FILTER-INVALID-SQL:child transporter count missing column '+name)
        actual,kind=fields[name.lower()]
        return alias+'.'+quote(actual),kind


def count(run, payload, products, locations,*,read_binding=None):
    # Reuse the qualified Commons predicate semantics, but resolve every column
    # against this query's actual grain and aliases. Missing native fields fail.
    filters=CountFilters(payload); where=filters.compile()
    if read_binding is not None:
        from mta.presentation.planning_sources import admitted_sources
        admitted_sources(run,read_binding=read_binding)
        if read_binding.transit is None:
            raise PublicationUnavailable('bpr_transit_read_source_unavailable')
    if not products or not locations:
        return 0
    paths = dict(a=TRANSPORTER_PATH, slsa='closing/dbm/SKULocStandardAttributes',
                 vf='reports/bpr/vf_RationedReqReport', ld='closing/importer/SiteDescriptionTbl',
                 la='closing/importer/LocationAttributeData', sla='closing/importer/SkuLocAttributeData')
    ctes=[]; params=[]
    for alias, path in paths.items():
        sql, values = image_query(run, path) if read_binding is None else read_binding.image_query(path)
        ctes.append(alias+' AS ('+sql+')'); params.extend(values)
    for alias, codes in (('P', products), ('L', locations)):
        ctes.append(alias+'(code) AS (VALUES '+','.join('(%s::text)' for _ in codes)+')')
        params.extend(sorted(codes))
    joins = (' FROM a LEFT JOIN slsa ON '+equal('a."SKUCode"','slsa."SKUCode"')+
             ' AND '+equal('a."WhCode"','slsa."WhCode"')+
             ' JOIN vf ON '+equal('a."SKUCode"','vf."SKUCode"')+
             ' AND '+equal('a."WhCode"','vf."WhCode"')+
             ' JOIN ld wd ON '+equal('a."WhCode"','wd."WHCode"')+
             ' JOIN ld pd ON '+equal('a."WhCode"','pd."WHCode"')+
             ' JOIN la ON '+equal('a."WhCode"','la."WHCode"')+
             ' LEFT JOIN sla ON '+equal('a."SKUCode"','sla."SKUCode"')+
             ' AND '+equal('a."WhCode"','sla."LocCode"')+
             ' JOIN P ON '+equal('a."SKUCode"','P.code')+
             ' JOIN L ON '+equal('a."ParentWhCode"','L.code'))
    if filters.children:
        joins+=' JOIN la parent ON '+equal('a."ParentWhCode"','parent."WHCode"')+' AND ('+' OR '.join(
            equal('parent."LocationType"','%s') for _ in filters.children)+')'
        params.extend(filters.children)
    params.extend(filters.params)
    grouping = ','.join(key('a."'+name+'"') for name in ('TransporterCode','OrderNo','ParentWhCode','WhCode'))
    sql = ('WITH '+','.join(ctes)+' SELECT count(*) FROM (SELECT '+grouping+joins+
           ' WHERE '+key('a."PhysicalInventoryColor"')+" IN ('black','red') AND "+where+' GROUP BY '+grouping+') grouped')
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        return int(cursor.fetchone()[0])
