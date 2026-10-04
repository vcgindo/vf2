"""Planning Excess consumers over named, checked terminal relations only.

Authority: deployed PlanningProcessor bf716c4f / ExcessInventoryProcessor
5eb90eb1. Custom ignores request filters and omits NULL JSON properties;
normal grid includes NULLs. NMS hierarchy is native, not supplemented.
"""
from itertools import product
from types import SimpleNamespace

from mta.presentation import hierarchy
from mta.presentation.context import selected_run, permission_catalogue, PublicationUnavailable, scope
from mta.presentation.excess_storage import read_excess
from mta.presentation.permissions import permission_multiplicity
from mta.presentation.rrr import index, sql_key
from mta.presentation.selective import image_rows
from mta.runtime.models import ExcessProjection


def pagination(payload):
    value = payload.get('paginationParameter')
    if value is None:
        return None
    result = tuple(int(value.get(key, 0)) for key in ('pageNumber', 'recordsPerPage'))
    if any(n < -(2**31) or n >= 2**31 for n in result):
        raise ValueError('invalid_pagination')
    return result


def excess_context(*, custom=False):
    run = selected_run()
    importer = {name: image_rows(run, 'closing/importer/' + name) for name in (
        'SkuAttributeData', 'LocationAttributeData', 'SkuLocAttributeData',
        'SKUDescriptionTbl', 'SiteDescriptionTbl')}
    fixture = run.kind == 'LEGACY_UI_FIXTURE'
    standards = image_rows(run, 'closing/dbm/SKULocStandardAttributes') if custom or not fixture else None
    native = dict(ClosingState=[dict(importer=importer, dbm={'SKULocStandardAttributes': standards})])
    if not fixture:
        native['BPRReports'] = [{'vf_RationedReqReport': image_rows(run, 'reports/bpr/vf_RationedReqReport')}]
    try:
        rows = read_excess(run, output=native)
    except ExcessProjection.DoesNotExist as exc:
        raise PublicationUnavailable('selected_run_excessinventory_projection_not_published') from exc
    try:
        manifest = hierarchy.selected_manifest(run)
        if manifest:
            importer = hierarchy.project_attributes(importer, permission_catalogue(), manifest)
    except hierarchy.HierarchyUnavailable as exc:
        raise PublicationUnavailable(str(exc)) from exc
    output = {**native, 'ClosingState': [{**native['ClosingState'][0], 'importer': importer}]}
    return SimpleNamespace(run=run, business_date=run.business_date, output=output, storage_output=native,
        rows=rows, standards=standards,
        nms=image_rows(run, 'closing/consumer_context/NMSAllItems') if custom else None)


# GetCustomGridData emits the same configuration for all four categories,
# including columns absent from this category's SELECT. Do not tailor it.
CUSTOM_COLUMNS = (
    ('SKUCode', 'sc', 1), ('WHCode', 'wc', 2), ('SKUDescription', 'sd', 3), ('WHDescription', 'wd', 4),
    ('DelayDays', 'dd', 5), ('SKUStatus', 'ss', 6), ('Status', 's', 7), ('ParentWhCode', 'pwc', 8),
    ('ParentName', 'pn', 9), ('Norm', 'n', 10), ('MinNorm', 'mn', 11), ('RLT', 'rlt', 12),
    ('RCP', 'rcp', 13), ('GCP', 'gcp', 14), ('OCP', 'ocp', 15), ('MinOrderCount', 'moc', 16),
    ('PackSize', 'ps', 17), ('FGRMFlag', 'frf', 18), ('DBMActive', 'da', 19), ('OrderNo', 'odn', 20),
    ('TruckStatus', 'ts', 21), ('TransporterName', 'tn', 22), ('TransporterCode', 'tc', 23),
    ('FromLocation', 'fl', 24), ('ToLocationQty', 'itq', 25), ('TransporterContact', 'tct', 26),
    ('CreationDate', 'cd', 27), ('SLT', 'slt', 28), ('Ageing', 'ag', 29), ('ETA', 'eta', 30),
    ('CurrentLocation', 'cl', 31), ('Remark', 'rmk', 32), ('LRCode', 'lc', 33), ('Stock', 'sk', 34),
    ('Tech Pen', 'pt', 35), ('Tech Pen Percentage', 'tpp', 36), ('GIT', 'git', 37),
    ('Eco Pen Percentage', 'epp', 38), ('Eco Pen', 'ep', 39), ('RationedQty', 'rq', 40),
    ('Business', 'sl1', 41), ('Category', 'sl2', 42), ('Family', 'sl3', 43),
    ('Zone', 'll1', 46), ('Location Group', 'll2', 47), ('WH Type', 'll3', 48),
)


def custom_grid(context, payload, paging):
    importer = context.output['ClosingState'][0]['importer']
    products, locations = scope(payload, attributes=importer)
    nms = index(context.nms, 'SKUCode', 'WhCode')
    parents = index(importer['SiteDescriptionTbl'], 'WHCode')
    standards = index(context.standards, 'SKUCode', 'WhCode')
    values = []
    for b in context.rows:
        if b['ReportDate'] != str(context.business_date):
            continue
        weight = permission_multiplicity(products, b['SKUCode']) * permission_multiplicity(locations, b['WhCode'])
        pair = sql_key(b['SKUCode'], b['WhCode'])
        for a in nms.get(pair, []):
            for c, e in product(parents.get(sql_key(a['ParentWhCode']), []), standards.get(pair, [])):
                row = dict(sc=a['SKUCode'], sd=a['SKUDescription'], pwc=a['ParentWhCode'], pn=c['WHDescription'],
                    wc=a['WhCode'], wd=a['WHDescription'], n=b['Norm'], sk=b['Stock'], mn=a['MinNorm'],
                    Price=None if e['Price'] is None else float(e['Price']), rlt=a['RLT'], rcp=a['RCP'],
                    gcp=a['GCP'], ocp=a['OCP'], moc=a['MinOrderCount'], ps=a['PackSize'], frf=a['FGRMFlag'],
                    da=a['DBMActive'], pt=b['PhysicalInventoryColor'],
                    tpp=None if b['PhysicalInventoryPen'] is None else float(b['PhysicalInventoryPen']),
                    ep=b['PipelineInventoryColor'],
                    epp=None if b['PipelineInventoryPen'] is None else float(b['PipelineInventoryPen']))
                row.update({prefix.lower()+str(i): a[prefix+str(i)] for prefix in ('SL', 'LL') for i in range(1, 6)})
                values.extend(dict(row) for _ in range(weight))
    # SQL only specifies ROW_NUMBER keys. Preserve occurrences; no tie-break.
    values.sort(key=lambda row: (sql_key(row['sc']), sql_key(row['wc'])))
    values = [dict(RN=i, **{k: v for k, v in row.items() if v is not None}) for i, row in enumerate(values, 1)]
    if paging is not None:
        page, size = paging
        values = [row for row in values if (page-1)*size+1 <= row['RN'] <= page*size]
    return dict(data=values, uiConfig=[dict(header=h, colCode=c, colPosition=p) for h, c, p in CUSTOM_COLUMNS])
