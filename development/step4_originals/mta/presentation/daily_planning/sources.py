"""Occurrence-preserving read-time hierarchy over admitted native relations."""
from contextvars import ContextVar
from contextlib import contextmanager
from django.db import connection
from mta.presentation import selective, hierarchy
from mta.presentation.context import permission_catalogue
from mta.presentation.daily_planning_extension import require
from mta.presentation.bpr_sql import _values_cte
from mta.runtime.relational_state import quote

image_rows = selective.image_rows
_request = ContextVar('daily_planning_request', default=None)


@contextmanager
def admitted_request(run, route):
    require(run,route)
    token=_request.set({'run':str(run.pk)})
    try:
        yield
    finally:
        _request.reset(token)


def _projected_attributes(run):
    request=_request.get()
    if request is None or request['run'] != str(run.pk):
        require(run, 'grid')
        request={}
    if 'attributes' in request:
        return request['attributes']
    original = {name: image_rows(run, 'closing/importer/' + name)
                for name in ('SkuAttributeData', 'LocationAttributeData')}
    manifest = hierarchy.selected_manifest(run)
    result=hierarchy.project_attributes(original, permission_catalogue(), manifest), manifest
    request['attributes']=result
    return result


def dimensions(run):
    attrs, _ = _projected_attributes(run)
    return {prefix: _values_cte([
        dict(ordinal=i, **{'h'+str(n): row[prefix+str(n)] for n in (1,2,3)})
        for i,row in enumerate(attrs[table])], ('ordinal','h1','h2','h3'),
        {'ordinal':'::bigint'})
        for prefix,table in (('SL','SkuAttributeData'),('LL','LocationAttributeData'))}


def image_query(run, path):
    query, params = selective.image_query(run, path)
    if path not in ('closing/importer/SkuAttributeData', 'closing/importer/LocationAttributeData'):
        return query, params
    prefix = 'SL' if path.endswith('/SkuAttributeData') else 'LL'
    projection, values = dimensions(run)[prefix]
    fields = [field[0] for field in selective.image_metadata(run,path)['fields']]
    selected = ['N.vf_ordinal'] + [
        ('H.h'+field[-1] if field in (prefix+'1',prefix+'2',prefix+'3') else 'N.'+quote(field))
        +' AS '+quote(field) for field in fields]
    return ('WITH native AS ('+query+'), hierarchy AS ('+projection+') SELECT '+','.join(selected)+
            ' FROM native N JOIN hierarchy H ON H.ordinal=N.vf_ordinal'), [*params,*values]


def occurrence(run, relation, model, *, chart_display=False):
    query, params = relation
    dimensions_sql = dimensions(run)
    ctes=['native AS ('+query+')']; params=list(params)
    for prefix in ('SL','LL'):
        sql, values=dimensions_sql[prefix]
        ctes.append(prefix+' AS ('+sql+')'); params.extend(values)
    names=[field.column for field in model._meta.local_fields]
    selected=[]
    for name in names:
        value='N.'+quote(name)
        if name in ('sl1','sl2','sl3'): value='SL.h'+name[-1]
        if name in ('ll1','ll2','ll3'): value='LL.h'+name[-1]
        if chart_display and name in ('h1','h2','h3'):
            value="CASE WHEN N.direction='sku' THEN SL."+name+' ELSE LL.'+name+' END'
        selected.append(value+' AS '+quote(name))
    joins=' FROM native N'
    for prefix,ordinal in (('SL','sku_ordinal'),('LL','location_ordinal')):
        if chart_display:
            joins+=' LEFT JOIN '+prefix+" ON N.direction='"+('sku' if prefix=='SL' else 'location')+"' AND "+prefix+'.ordinal=N.attribute_ordinal'
        elif ordinal in names:
            joins+=' LEFT JOIN '+prefix+' ON '+prefix+'.ordinal=N.'+ordinal
        else:
            joins+=' LEFT JOIN '+prefix+' ON FALSE'
    return ('SELECT * FROM (WITH '+','.join(ctes)+' SELECT '+','.join(selected)+joins+
            ') projected WHERE TRUE'), params


def admitted_git(run):
    from mta.presentation.planning_git import admitted_git as native
    from mta.runtime.models import PlanningGitOccurrence
    return {'row':occurrence(run,native(run)['row'],PlanningGitOccurrence)}


def admitted_grids(run):
    from mta.presentation.planning_grids import admitted_grids as native
    from mta.runtime.models import PlanningExcessGridRow, PlanningFulfillmentGridRow
    relations=native(run)
    return {name:occurrence(run,relations[name],model) for name,model in
            (('excess',PlanningExcessGridRow),('fulfillment',PlanningFulfillmentGridRow))}


def admitted_expedite_grids(run):
    from mta.presentation.planning_expedite_grids import admitted_expedite_grids as native
    from mta.runtime.models import PlanningExpediteGridOccurrence
    return {'row':occurrence(run,native(run)['row'],PlanningExpediteGridOccurrence)}


def admitted_charts(run):
    from mta.presentation.planning_charts import admitted_charts as native
    from mta.runtime.models import PlanningChartDisplay
    relations=native(run)
    return {**relations,'displays':occurrence(run,relations['displays'],PlanningChartDisplay,chart_display=True)}


def expedite_chart_relation(run):
    from mta.runtime.models import PlanningExpediteChartMember
    model=PlanningExpediteChartMember
    return occurrence(run,('SELECT * FROM mta.'+quote(model._meta.db_table)+' WHERE run_id=%s',[run.pk]),model)


def git_sources(run, *, chart):
    from mta.presentation.daily_git_preparation import sources, LOCATION_PATH
    relations, bindings, config=sources(run,chart=chart)
    if chart: relations={**relations,LOCATION_PATH:image_query(run,LOCATION_PATH)}
    return relations,bindings,config


def git_custom_count(run, products, locations):
    from mta.presentation.daily_transit import PATH, TRANSPORTER_PATH
    from mta.presentation.rrr_sql import equal
    if not products or not locations:return 0
    ctes=[]; params=[]
    for alias,path in (('A',TRANSPORTER_PATH),('T',PATH)):
        sql,values=selective.image_query(run,path); ctes.append(alias+' AS ('+sql+')'); params.extend(values)
    for alias,codes in (('P',products),('L',locations)):
        sql,values=_values_cte([dict(code=code,weight=codes.multiplicities[code]) for code in sorted(codes)],
            ('code','weight'), {'weight':'::bigint'})
        ctes.append(alias+' AS ('+sql+')'); params.extend(values)
    query=('WITH '+','.join(ctes)+' SELECT COALESCE(sum(P.weight*L.weight),0) FROM A JOIN T ON '+
           equal('A."SKUCode"','T."SKUCode"')+' AND '+equal('A."WhCode"','T."WhCode"')+
           ' JOIN P ON '+equal('A."SKUCode"','P.code')+' JOIN L ON '+equal('A."WhCode"','L.code'))
    with connection.cursor() as cursor:
        cursor.execute(query,params)
        return int(cursor.fetchone()[0])
