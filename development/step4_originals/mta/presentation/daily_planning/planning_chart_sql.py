# Versioned copy of planning_chart_sql; original source SHA256 9b86f64b613ca35beac596c1a86978de0ed0f435d5777898dbfa5daded807eb7.
"""Live scoped aggregates over prepared description/display chart ingredients."""
import re
from django.db import connection
from mta.presentation.context import scope, PublicationUnavailable
from .sources import _projected_attributes
from .sources import admitted_charts
from mta.presentation.planning_chart_preparation import FAMILIES
from mta.runtime.relational_state import quote


def chart_queries(run,payload,category):
    relations=admitted_charts(run)
    importer,manifest=_projected_attributes(run)
    products,locations=scope(payload,attributes=importer)
    if category=='excess':
        specs=[(direction+'_'+measure,'excess',direction,measure=='value')
               for direction in ('location','sku') for measure in ('count','value')]
    elif category=='fulfillment':
        specs=[(direction+'_'+measure,'fulfillment_detail' if measure=='orders' else 'fulfillment_summary',direction,False)
               for measure in ('orders','gap') for direction in ('location','sku')]
    else:raise ValueError('Unknown Planning chart category')
    result={}
    for section,family,direction,amount in specs:
        if not products or not locations:
            result[section]=[]
            continue
        ctes=[];params=[]
        for alias,codes in (('P',products),('L',locations)):
            members=sorted(codes)
            ctes.append(alias+'(code,weight) AS (VALUES '+','.join(['(%s::text,%s::bigint)']*len(members))+')')
            params.extend(v for code in members for v in (code,codes.multiplicities[code]))
        for alias,name in (('M','members'),('D','displays')):
            query,values=relations[name]
            ctes.append(alias+' AS ('+query+' AND family=%s AND direction=%s)')
            params.extend([*values,family,direction])
        fact=FAMILIES[family]
        summed=amount or (family=='fulfillment_detail' and direction=='sku')
        expression=('A."Amount"' if amount else 'A."PendingQty"') if summed else (
            'CASE WHEN A."OrderNo" IS NULL THEN 0 ELSE 1 END' if family=='fulfillment_detail' else '1')
        ctes.append('eligible AS (SELECT M.*,('+expression+')*P.weight*L.weight AS value FROM M JOIN mta.'
                    +quote(fact._meta.db_table)+' A ON A.run_id=M.run_id AND A.ordinal=M.fact_ordinal '
                    'JOIN P ON A."SKUCode"=P.code JOIN L ON A."WhCode"=L.code)')
        # Select the first eligible source occurrence only after live scope.
        # Prepared display membership does not predetermine raw scoped labels.
        ctes.append('totals AS (SELECT group_ordinal,min(ordinal) AS first_ordinal,sum(value)::'
                    +('bigint' if amount else 'integer')+' AS counts FROM eligible GROUP BY group_ordinal)')
        sql=('WITH '+','.join(ctes)+' SELECT E.code,E.description,E.band,T.counts,'
             +','.join('D.h'+str(i) for i in range(1,6))+' FROM totals T '
             'JOIN eligible E ON E.ordinal=T.first_ordinal JOIN D ON D.group_ordinal=T.group_ordinal '
             'ORDER BY T.counts DESC NULLS LAST,T.first_ordinal,D.attribute_ordinal')
        with connection.cursor() as c:
            c.execute(sql,params)
            values=c.fetchall()
        rows=[]
        for code,description,band,counts,*hierarchy in values:
            if description is not None:
                description=(re.sub('-ND-',lambda _:code,description,flags=re.I)
                             if family=='excess' and direction=='sku' else description.replace("'",''))
            row=dict(counts=counts,Details=description)
            row['WHCode' if direction=='location' else 'SKUCode']=code
            if family!='excess':row['Coverage' if family=='fulfillment_summary' else 'OrderStatus']=band
            row.update({('ll' if direction=='location' else 'sl')+str(i):value for i,value in enumerate(hierarchy,1)})
            rows.append(row)
        result[section]=rows
    return result


def graph(run,payload,category):
    queries=chart_queries(run,payload,category)
    if category=='fulfillment':
        from mta.presentation.fulfillment_charts import chart_response
        return chart_response(queries)
    from mta.presentation.excess_charts import excess_chart_response
    result=excess_chart_response(queries)
    for section in result.values():
        for config in section['uiconfig']:config['colPosition']=0
    return {'data':result}
