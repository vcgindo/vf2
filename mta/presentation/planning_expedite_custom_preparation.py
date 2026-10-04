"""One-time exact custom Expedite LEFT-join occurrences."""
from mta.presentation.selective import image_query
from mta.presentation.rrr_sql import equal,key


def custom_occurrences(run):
    if run.kind!='LEGACY_UI_FIXTURE' or str(run.business_date)!='2026-04-07':
        raise ValueError('Expedite custom requires retained April fixture')
    ctes=['B AS (SELECT * FROM mta.fresh_mta_expediterow WHERE run_id=%s)'];params=[run.pk]
    for alias,path in [('A','closing/consumer_context/NMSAllItems'),('D','reports/bpr/BPR_Table'),('C','closing/importer/SiteDescriptionTbl')]:
        query,values=image_query(run,path);ctes.append(alias+' AS ('+query+')');params.extend(values)
    joins=' FROM B LEFT JOIN A ON '+equal('B."SKUCode"','A."SKUCode"')+' AND '+equal('B."WhCode"','A."WhCode"')
    joins+=' LEFT JOIN D ON '+equal('A."SKUCode"','D."SKUCode"')+' AND '+equal('A."WhCode"','D."WhCode"')
    joins+=' LEFT JOIN C ON '+equal('A."ParentWhCode"','C."WHCode"')
    fields=dict(fact_ordinal='B.ordinal',nms_ordinal='A.vf_ordinal',bpr_ordinal='D.vf_ordinal',
                parent_description_ordinal='C.vf_ordinal',sku_key=key('A."SKUCode"'),location_key=key('A."WhCode"'),
                parent_description='C."WHDescription"')
    return ('WITH '+','.join(ctes)+' SELECT '+','.join(value+' AS '+name for name,value in fields.items())+joins+
            ' WHERE B."RationedQty">0 AND B."IsReceiving" AND '+key('B."PipelineInventoryColor"')+" IN ('black','red')"),params


def recipe_digest():
    import inspect
    from mta.serialization import digest
    return digest(dict(version=1,query=inspect.getsource(custom_occurrences)))
