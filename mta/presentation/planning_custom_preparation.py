"""One-time exact custom-grid references; no normal-grid membership reuse."""
from mta.presentation.rrr_sql import equal,key
from mta.presentation.selective import image_query
from mta.runtime.models import ExcessInventoryRow,FulfillmentSummaryRow
from mta.runtime.relational_state import quote


def custom_occurrences(run,family):
    if run.kind!='LEGACY_UI_FIXTURE' or str(run.business_date)!='2026-04-07':
        raise ValueError('Planning custom preparation requires retained April fixture')
    if family not in ('excess','fulfillment'):raise ValueError('Unknown custom family')
    model=ExcessInventoryRow if family=='excess' else FulfillmentSummaryRow
    fact='SELECT * FROM mta.'+quote(model._meta.db_table)+' WHERE run_id=%s'
    params=[run.pk]
    if family=='excess':
        fact+=' AND "ReportDate"=%s';params.append(run.business_date)
    ctes=['B AS ('+fact+')']
    for alias,path in [('A','closing/consumer_context/NMSAllItems'),('C','closing/importer/SiteDescriptionTbl'),
                       ('E','closing/dbm/SKULocStandardAttributes')]:
        if alias=='E' and family=='fulfillment':continue
        query,values=image_query(run,path);ctes.append(alias+' AS ('+query+')');params.extend(values)
    join='JOIN' if family=='excess' else 'LEFT JOIN'
    joins=' FROM B '+join+' A ON '+equal('B."SKUCode"','A."SKUCode"')+' AND '+equal('B."WhCode"','A."WhCode"')
    joins+=' '+join+' C ON '+equal('A."ParentWhCode"','C."WHCode"')
    fields=[('fact_ordinal','B.ordinal'),('nms_ordinal','A.vf_ordinal'),('parent_description_ordinal','C.vf_ordinal'),
            ('sku_key',key('A."SKUCode"')),('location_key',key('A."WhCode"')),
            ('parent_description','C."WHDescription"')]
    if family=='excess':
        joins+=' JOIN E ON '+equal('B."SKUCode"','E."SKUCode"')+' AND '+equal('B."WhCode"','E."WhCode"')
        fields.append(('standard_ordinal','E.vf_ordinal'))
    return 'WITH '+','.join(ctes)+' SELECT '+','.join(value+' AS '+quote(name) for name,value in fields)+joins,params


def recipe_digest():
    import inspect
    from mta.serialization import digest
    return digest(dict(version=1,query=inspect.getsource(custom_occurrences)))
