"""Scope and page prepared custom occurrences before display expansion."""
from contextlib import nullcontext
from django.db import connection, transaction
from mta.presentation.planning_custom import admitted_custom
from mta.presentation.bpr_sql import _projected_attributes
from mta.presentation.context import scope,PublicationUnavailable
from mta.presentation.selective import image_query
from mta.presentation.excess_read import CUSTOM_COLUMNS
from mta.runtime.models import ExcessInventoryRow,FulfillmentSummaryRow
from mta.runtime.relational_state import quote, table_sql
from mta.serialization import storage

NMS_ALIASES=dict(sc='SKUCode',sd='SKUDescription',pwc='ParentWhCode',wc='WhCode',wd='WHDescription',
                 mn='MinNorm',rlt='RLT',rcp='RCP',gcp='GCP',ocp='OCP',moc='MinOrderCount',ps='PackSize',
                 frf='FGRMFlag',da='DBMActive',
                 **{p.lower()+str(i):p+str(i) for p in ('SL','LL') for i in range(1,6)})

NMS_PATH = 'closing/consumer_context/NMSAllItems'
PHYSICAL_NMS = 'SELECT * FROM ' + table_sql('Importer/NMSAllItems') + ' WHERE vf_run_id=%s AND vf_image=%s'


def custom_grid(run,payload,paging,*,family,read_binding=None):
    config=[dict(header=h,colCode=c,colPosition=p) for h,c,p in CUSTOM_COLUMNS]
    if family=='fulfillment' and paging is not None:
        page,size=paging
        if page*size<max(1,(page-1)*size+1):return dict(data=[],uiConfig=config)
    relation,values=admitted_custom(run,read_binding=read_binding)[family]
    importer,manifest=(_projected_attributes(run) if read_binding is None else (read_binding.attributes(),None))
    if manifest:raise PublicationUnavailable('planning_custom_native_hierarchy_required')
    products,locations=scope(payload,attributes=importer)
    if not products or not locations:return dict(data=[],uiConfig=config)
    model=ExcessInventoryRow if family=='excess' else FulfillmentSummaryRow
    ctes=['H AS ('+relation+')'];params=list(values)
    for alias,codes in (('P',products),('L',locations)):
        members=sorted(codes)
        ctes.append(alias+'(code,weight) AS (VALUES '+','.join(['(%s::text,%s::bigint)']*len(members))+')')
        params.extend(v for code in members for v in (code,codes.multiplicities[code]))
    fact_relation='mta.'+quote(model._meta.db_table)
    if read_binding is not None:
        query,fact_params=read_binding.fact_query('ExcessInventoryDetails' if family=='excess' else 'OrderFulfillmentSummary')
        ctes.append('F AS ('+query+')');params.extend(fact_params);fact_relation='F'
    ctes.append('eligible AS (SELECT H.*,P.weight*L.weight AS weight FROM H JOIN '+fact_relation
                +' B ON B.run_id=H.run_id AND B.ordinal=H.fact_ordinal JOIN P ON B."SKUCode"=P.code JOIN L ON B."WhCode"=L.code)')
    base='WITH '+','.join(ctes)
    if family=='fulfillment' and paging is not None:
        with connection.cursor() as c:
            c.execute(base+' SELECT COALESCE(sum(weight),0) FROM eligible',params)
            if (paging[0]-1)*paging[1]+1>c.fetchone()[0]:return dict(data=[],uiConfig=config)
    nms,nms_params=(image_query(run,NMS_PATH) if read_binding is None else read_binding.image_query(NMS_PATH))
    ctes.append('A AS NOT MATERIALIZED ('+nms+')');params.extend(nms_params)
    if family=='excess':
        standard,standard_params=(image_query(run,'closing/dbm/SKULocStandardAttributes') if read_binding is None else read_binding.image_query('closing/dbm/SKULocStandardAttributes'))
        ctes.append('S AS NOT MATERIALIZED ('+standard+')');params.extend(standard_params)
    columns={alias:'A.'+quote(field) for alias,field in NMS_ALIASES.items()}
    columns.update(pn='X.parent_description',n='B."Norm"',sk='B."Stock"')
    if family=='excess':
        columns.update(Price='S."Price"',pt='B."PhysicalInventoryColor"',tpp='B."PhysicalInventoryPen"',
                       ep='B."PipelineInventoryColor"',epp='B."PipelineInventoryPen"')
    else:columns.update(Price='B."Price"',rq='B."RationedQty"')
    joins=(' FROM chosen X JOIN '+fact_relation+' B ON B.run_id=X.run_id AND B.ordinal=X.fact_ordinal '
           'LEFT JOIN A ON A.vf_ordinal=X.nms_ordinal')
    if family=='excess':joins+=' JOIN S ON S.vf_ordinal=X.standard_ordinal'
    if family=='fulfillment':
        # Different scoped outputs sharing source ROW_NUMBER keys stay denied.
        # This whole-set validation is required even for a small requested page.
        chosen = 'chosen AS (SELECT * FROM eligible)'
        # The terminal fact and physical NMS keys make both joins at most
        # one-to-one. Only repeated eligible keys can then disagree.
        if read_binding is None and nms == PHYSICAL_NMS and nms_params == [run.pk, NMS_PATH]:
            chosen = ('chosen AS MATERIALIZED (SELECT * FROM ('
                      'SELECT E.*,count(*) OVER (PARTITION BY sku_key,location_key) AS tie_count '
                      'FROM eligible E) tied WHERE tie_count>1)')
        ambiguity='WITH '+','.join(ctes)+','+chosen+' SELECT 1'+joins
        ambiguity+=' GROUP BY X.sku_key,X.location_key HAVING count(DISTINCT ROW('+','.join(columns.values())+'))>1 LIMIT 1'
        with connection.cursor() as c:
            c.execute(ambiguity,params)
            if c.fetchone():
                raise PublicationUnavailable('LEG-FULFILLMENT-CUSTOM-UNORDERED-NMS: distinct rows share the source ROW_NUMBER keys; NOT_PARITY')
    ctes.append('numbered AS (SELECT E.*,row_number() OVER (ORDER BY E.sku_key NULLS FIRST,E.location_key NULLS FIRST,'
                'E.ordinal,copies.n) AS rn FROM eligible E CROSS JOIN LATERAL generate_series(1,E.weight) copies(n))')
    if paging is None:ctes.append('chosen AS (SELECT * FROM numbered)')
    else:
        ctes.append('chosen AS (SELECT * FROM numbered WHERE rn BETWEEN %s AND %s)')
        params.extend(((paging[0]-1)*paging[1]+1,paging[0]*paging[1]))
    sql='WITH '+','.join(ctes)+' SELECT X.rn,'+','.join(value+' AS '+quote(alias) for alias,value in columns.items())+joins+' ORDER BY X.rn'
    bounded_excess_page = family == 'excess' and read_binding is None and paging is not None
    with (transaction.atomic() if bounded_excess_page else nullcontext()), connection.cursor() as c:
        # Compilation dominates this bounded page on mature data.
        if bounded_excess_page:
            c.execute("SELECT current_setting('jit')")
            previous_jit = c.fetchone()[0]
            c.execute('SET LOCAL jit=off')
        c.execute(sql,params)
        names=['RN',*columns]
        rows=storage([dict(zip(names,values)) for values in c.fetchall()])
        if bounded_excess_page:
            c.execute("SELECT set_config('jit',%s,true)", [previous_jit])
    if family=='excess':
        for row in rows:
            for field in ('Price','tpp','epp'):
                if row[field] is not None:row[field]=float(row[field])
    return dict(data=[{k:v for k,v in row.items() if v is not None} for row in rows],uiConfig=config)
