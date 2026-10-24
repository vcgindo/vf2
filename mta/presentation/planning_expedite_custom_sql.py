"""Scope, validate native RN ties and page prepared custom Expedite occurrences."""
from decimal import Decimal
from django.db import connection
from mta.presentation.context import PublicationUnavailable,scope
from mta.presentation.bpr_sql import _projected_attributes
from mta.presentation.planning_expedite_custom import admitted_expedite_custom
from mta.presentation.planning_custom_sql import NMS_ALIASES
from mta.presentation.selective import image_query
from mta.runtime.relational_state import quote


def custom_grid(run,payload,*,read_binding=None):
    from mta.presentation.excess_read import pagination,CUSTOM_COLUMNS
    from mta.presentation.legacy_ui import BPR_UI_CONFIG
    if any(row.get('Visible') and 'attr' in row['Col_Code'].lower() for row in BPR_UI_CONFIG):
        raise PublicationUnavailable('expedite_custom_visible_dynamic_attributes_unsupported')
    paging=pagination(payload)
    occurrence,params=admitted_expedite_custom(run,read_binding=read_binding)['row'];params=list(params)
    importer,manifest=(_projected_attributes(run) if read_binding is None else (read_binding.attributes(),None))
    if manifest:raise PublicationUnavailable('planning_expedite_custom_native_hierarchy_required')
    products,locations=scope(payload,attributes=importer)
    config=[dict(header=h,colCode=c,colPosition=p) for h,c,p in CUSTOM_COLUMNS]
    if not products or not locations:return dict(data=[],uiConfig=config)
    ctes=['H AS ('+occurrence+')']
    fact='mta.fresh_mta_expediterow'
    if read_binding is not None:
        query,values=read_binding.fact_query('ExpediteDispatches');ctes.append('facts AS ('+query+')');params.extend(values)
        fact='facts'
    for alias,codes in (('P',products),('L',locations)):
        members=sorted(codes)
        ctes.append(alias+'(code,weight) AS (VALUES '+','.join(['(%s::text,%s::bigint)']*len(members))+')')
        params.extend(v for code in members for v in (code,codes.multiplicities[code]))
    for alias,path in [('A','closing/consumer_context/NMSAllItems'),('D','reports/bpr/BPR_Table')]:
        query,values=(image_query(run,path) if read_binding is None else read_binding.image_query(path))
        ctes.append(alias+' AS NOT MATERIALIZED ('+query+')');params.extend(values)
    columns={alias:'A.'+quote(field) for alias,field in NMS_ALIASES.items() if alias!='gcp'}
    columns.update(acp='A."GCP"',n='A."Norm"',pn='H.parent_description',sk='D."Stock"',
        pt='B."PhysicalInventoryColor"',tpp='B."PhysicalInventoryPen"',git='B."GIT"',
        ep='B."PipelineInventoryColor"',epp='B."PipelineInventoryPen"',rq='B."RationedQty"')
    joins=(' FROM H JOIN '+fact+' B ON B.run_id=H.run_id AND B.ordinal=H.fact_ordinal '
        'JOIN P ON P.code=B."SKUCode" JOIN L ON L.code=B."ParentWhCode" '
        'LEFT JOIN A ON A.vf_ordinal=H.nms_ordinal LEFT JOIN D ON D.vf_ordinal=H.bpr_ordinal')
    ctes.append('selected AS (SELECT H.ordinal,H.sku_key,H.location_key,P.weight*L.weight AS weight,'+
        ','.join(value+' AS '+quote(alias) for alias,value in columns.items())+joins+')')
    base='WITH '+','.join(ctes)
    with connection.cursor() as c:
        c.execute(base+' SELECT 1 FROM selected GROUP BY sku_key,location_key HAVING count(DISTINCT ROW('
            +','.join(map(quote,columns))+'))>1 LIMIT 1',params)
        if c.fetchone():raise PublicationUnavailable('expedite_custom_conflicting_row_number_key')
        query=(base+',numbered AS (SELECT row_number() OVER (ORDER BY sku_key NULLS FIRST,location_key NULLS FIRST,ordinal,copies.copy_ordinal) AS "RN",'
            +','.join(map(quote,columns))+' FROM selected CROSS JOIN LATERAL generate_series(1,weight) copies(copy_ordinal)) SELECT * FROM numbered')
        if paging is not None:
            query+=' WHERE "RN" BETWEEN %s AND %s';params.extend(((paging[0]-1)*paging[1]+1,paging[0]*paging[1]))
        c.execute(query+' ORDER BY "RN"',params)
        names=[col[0] for col in c.description]
        rows=[{name:float(value) if isinstance(value,Decimal) else value for name,value in zip(names,row) if value is not None} for row in c.fetchall()]
    return dict(data=rows,uiConfig=config)
