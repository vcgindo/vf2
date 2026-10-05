"""Live scoped aggregates over prepared Expedite chart membership."""
from django.db import connection
from mta.presentation.planning_expedite_charts import admit
from mta.presentation.bpr_sql import _projected_attributes
from mta.presentation.context import scope,PublicationUnavailable
from mta.presentation.rrr_sql import key,equal
from mta.presentation.planning_expedite_transit_preparation import PICK_TABLE


def fetch(query,params):
    with connection.cursor() as c:
        c.execute(query,params);names=[col[0] for col in c.description]
        return [dict(zip(names,row)) for row in c.fetchall()]


def queries(run,payload,kind):
    if kind not in ('parent','child'):raise ValueError('Unsupported Expedite chart direction')
    admit(run)
    importer,manifest=_projected_attributes(run)
    if manifest:raise PublicationUnavailable('planning_expedite_chart_native_hierarchy_required')
    products,locations=scope(payload,attributes=importer)
    permission_ctes=[];permission_params=[]
    for alias,codes in (('P',products),('L',locations)):
        members=sorted(codes)
        if members:
            permission_ctes.append(alias+'(code,weight) AS (VALUES '+','.join(['(%s::text,%s::bigint)']*len(members))+')')
            permission_params.extend(v for code in members for v in (code,codes.multiplicities[code]))
        else:permission_ctes.append(alias+'(code,weight) AS (SELECT NULL::text,0::bigint WHERE FALSE)')
    tables={}
    for family in (('critical','receiving','nil_stock','chronic') if kind=='parent' else ('critical','receiving')):
        loc='ParentWhCode' if kind=='child' and family=='critical' else 'WhCode'
        selected=('SELECT H.*,P.weight*L.weight AS weight,A."BRAgeRedCount" AS red,A."BRAgeBlackCount" AS black,'
            'A."PipelineInventoryPen" AS pen,S."WhCode" AS wh,S."ParentWhCode" AS parent,'
            +key('S."WhCode"')+' AS whkey,'+key('S."ParentWhCode"')+' AS parentkey,'
            'CASE WHEN S."RationedQty">0 AND '+key('S."PipelineInventoryColor"')+" IN ('black','red') THEN 1 ELSE 0 END AS critical "
            'FROM mta.fresh_mta_planningexpeditechartmember H '
            'JOIN mta.fresh_mta_expediterow S ON S.run_id=H.run_id AND S.ordinal=H.scope_ordinal '
            'JOIN mta.fresh_mta_expediterow A ON A.run_id=H.run_id AND A.ordinal=H.fact_ordinal '
            'JOIN P ON P.code=S."SKUCode" JOIN L ON L.code=S."'+loc+'" '
            'WHERE H.run_id=%s AND H.direction=%s AND H.family=%s')
        params=[*permission_params,run.pk,kind,family]
        ctes=[*permission_ctes,'selected AS ('+selected+')']
        display='code,replace(description,\'\'\'\',\'\') AS "Details",logisticslocation AS "LogisticsLocation",ll1,ll2,ll3,ll4,ll5'
        if family=='receiving':
            ctes.append('windowed AS (SELECT *,sum(critical*weight) OVER (PARTITION BY whkey,parentkey)::integer AS paircount,'
                'sum(critical*weight) OVER (PARTITION BY whkey)::integer AS whcount FROM selected)')
            group=['whkey','parentkey','paircount','whcount',key("replace(description,'''','')"),key('logisticslocation'),*[key('ll'+str(i)) for i in range(1,6)]]
            ctes.append('distinct_rows AS (SELECT DISTINCT ON ('+','.join(group)+') * FROM windowed ORDER BY '+','.join(group)+',ordinal)')
            tables[family]=fetch('WITH '+','.join(ctes)+' SELECT wh AS "WhCode",parent AS "ParentWhCode",paircount AS "ParentwiseCount",whcount AS "MaxPipelineInv",'
                +display.partition(',')[2]+' FROM distinct_rows ORDER BY paircount DESC,whcount DESC,ordinal',params)
            continue
        grouped=['code_key','description_key']
        if family=='critical':grouped += [key('logisticslocation'),*[key('ll'+str(i)) for i in range(1,6)]]
        partition=','.join(grouped)
        ctes.append('aggregated AS (SELECT *,row_number() OVER (PARTITION BY '+partition+' ORDER BY ordinal) AS first_member,'
            'sum(weight) OVER (PARTITION BY '+partition+')::integer AS counts,'
            'sum(red*weight) OVER (PARTITION BY '+partition+')::integer AS redsum,'
            'sum(black*weight) OVER (PARTITION BY '+partition+')::integer AS blacksum,'
            'sum(CASE WHEN pen<>100 THEN weight ELSE 0 END) OVER (PARTITION BY '+partition+')::integer AS redcount,'
            'sum(CASE WHEN pen=100 THEN weight ELSE 0 END) OVER (PARTITION BY '+partition+')::integer AS blackcount FROM selected)')
        code_alias='ParentWhCode' if kind=='parent' else 'WhCode'
        output='counts,code AS "'+code_alias+'",'+display.partition(',')[2]
        if kind=='parent' and family in ('critical','nil_stock'):
            output+=',redsum AS "BRAgeRedCount1",blacksum AS "BrAgeBlackCount1",redcount AS "BRAgeRedCount",blackcount AS "BrAgeBlackCount"'
        else:output+=',redsum AS "BRAgeRedCount",blacksum AS "BrAgeBlackCount"'
        rows=fetch('WITH '+','.join(ctes)+' SELECT '+output+' FROM aggregated WHERE first_member=1 ORDER BY '+('counts DESC,' if family in ('nil_stock','chronic') else '')+'ordinal',params)
        if family!='critical':
            for row in rows:
                for field in ('LogisticsLocation','ll1','ll2','ll3','ll4','ll5'):row.pop(field)
        tables[family]=rows
    bands=('Black','Red','Yellow','Green','White','Blue')
    tables['pre_post']=[]
    for state,field in [('Pre','DispatchColor'),('Post','PostPipelineInventoryColor')]:
        if kind=='parent':
            joins=(' FROM mta.fresh_mta_planningexpediteprepostmember H JOIN '+PICK_TABLE+' S ON S.vf_source_ordinal=H.scope_ordinal '
                'JOIN '+PICK_TABLE+' T ON T.vf_source_ordinal=H.fact_ordinal JOIN P ON P.code=S."SKUCode" JOIN L ON L.code=S."WhCode" WHERE H.run_id=%s')
            weight='P.weight*L.weight*H.multiplicity';params=[*permission_params,run.pk]
        else:
            joins=(' FROM '+PICK_TABLE+' T JOIN P ON P.code=T."SKUCode" JOIN L ON L.code=T."WhCode" WHERE NOT '+equal('T."WhCode"','T."ParentWhCode"'))
            weight='P.weight*L.weight';params=list(permission_params)
        columns=','.join('COALESCE(sum(CASE WHEN '+key('T."'+field+'"')+"='"+band.lower()+"' THEN "+weight+' ELSE 0 END),0)::integer AS "'+band+'Count"' for band in bands)
        row=fetch('WITH '+','.join(permission_ctes)+' SELECT '+columns+joins,params)[0]
        tables['pre_post'].append(dict(state=state,**row,TotalCount=0))
    return tables
