"""Deployed Planning Fulfilment consumers over checked relational inputs."""
from types import SimpleNamespace

from mta.presentation import hierarchy
from mta.presentation.context import selected_run, permission_catalogue, PublicationUnavailable, scope
from mta.presentation.excess_read import CUSTOM_COLUMNS
from mta.presentation.fulfillment_storage import read_fulfillment
from mta.presentation.permissions import permission_multiplicity
from mta.presentation.rrr import index, sql_key
from mta.presentation.selective import image_rows
from mta.runtime.models import FulfillmentProjection


def fulfillment_context(*, custom=False):
    run = selected_run()
    importer = {name: image_rows(run, 'closing/importer/' + name) for name in (
        'SkuAttributeData', 'LocationAttributeData', 'SkuLocAttributeData',
        'SKUDescriptionTbl', 'SiteDescriptionTbl')}
    native = dict(ClosingState=[dict(importer=importer)])
    if run.kind != 'LEGACY_UI_FIXTURE':
        native['BPRReports'] = [{'vf_RationedReqReport': image_rows(run, 'reports/bpr/vf_RationedReqReport')}]
        native['ClosingState'][0].update(
            dbm={'SKULocStandardAttributes': image_rows(run, 'closing/dbm/SKULocStandardAttributes')},
            orders={'SpikeOrderData': image_rows(run, 'closing/orders/SpikeOrderData')})
    try:
        rows = read_fulfillment(run, output=native)
    except FulfillmentProjection.DoesNotExist as exc:
        raise PublicationUnavailable('selected_run_orderfulfillment_projection_not_published') from exc
    try:
        manifest = hierarchy.selected_manifest(run)
        if manifest:
            importer = hierarchy.project_attributes(importer, permission_catalogue(), manifest)
    except hierarchy.HierarchyUnavailable as exc:
        raise PublicationUnavailable(str(exc)) from exc
    output = {**native, 'ClosingState': [{**native['ClosingState'][0], 'importer': importer}]}
    return SimpleNamespace(run=run, business_date=run.business_date, output=output, storage_output=native,
        rows=rows, nms=image_rows(run, 'closing/consumer_context/NMSAllItems') if custom else None)


def custom_grid(context, payload, paging):
    """Native LEFT joins, NULL omission and permission bags; never fill NMS IDs."""
    config = [dict(header=h,colCode=c,colPosition=p) for h,c,p in CUSTOM_COLUMNS]
    if paging is not None:
        page,size = paging
        if page*size < max(1,(page-1)*size+1):
            return dict(data=[],uiConfig=config)
    importer = context.output['ClosingState'][0]['importer']
    products, locations = scope(payload, attributes=importer)
    nms = index(context.nms, 'SKUCode', 'WhCode')
    parents = index(importer['SiteDescriptionTbl'], 'WHCode')
    values = []
    for b in context.rows['summary']:
        weight = permission_multiplicity(products, b['SKUCode']) * permission_multiplicity(locations, b['WhCode'])
        if not weight:
            continue
        for a in nms.get(sql_key(b['SKUCode'], b['WhCode']), []) or [{}]:
            for c in parents.get(sql_key(a.get('ParentWhCode')), []) or [{}]:
                row = dict(sc=a.get('SKUCode'), sd=a.get('SKUDescription'), pwc=a.get('ParentWhCode'),
                    pn=c.get('WHDescription'), wc=a.get('WhCode'), wd=a.get('WHDescription'),
                    n=b['Norm'], sk=b['Stock'], mn=a.get('MinNorm'), Price=b['Price'], rq=b['RationedQty'])
                row.update({alias:a.get(field) for alias,field in (
                    ('rlt','RLT'),('rcp','RCP'),('gcp','GCP'),('ocp','OCP'),('moc','MinOrderCount'),
                    ('ps','PackSize'),('frf','FGRMFlag'),('da','DBMActive'))})
                row.update({prefix.lower()+str(i):a.get(prefix+str(i)) for prefix in ('SL','LL') for i in range(1,6)})
                values.extend(dict(row) for _ in range(weight))
    if paging is not None and (paging[0]-1)*paging[1]+1 > len(values):
        return dict(data=[],uiConfig=config)
    # ROW_NUMBER orders only by NMS SKU/location, including NULL/NULL when the
    # LEFT join misses. Different rows with the same key cannot acquire an
    # invented deterministic RN or page membership. Exact duplicate rows are safe.
    keyed = {}
    for row in values:
        key = (sql_key(row['sc']), sql_key(row['wc']))
        if key in keyed and keyed[key] != row:
            raise PublicationUnavailable('LEG-FULFILLMENT-CUSTOM-UNORDERED-NMS: distinct rows share the source ROW_NUMBER keys; NOT_PARITY')
        keyed[key] = row
    values.sort(key=lambda row: tuple((value is not None, value or '')
        for value in (sql_key(row['sc']), sql_key(row['wc']))))
    values = [dict(RN=i, **{k:v for k,v in row.items() if v is not None}) for i,row in enumerate(values,1)]
    if paging is not None:
        page,size = paging
        values = [row for row in values if (page-1)*size+1 <= row['RN'] <= page*size]
    return dict(data=values, uiConfig=config)
