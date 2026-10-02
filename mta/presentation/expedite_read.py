"""Selective, checksum-verified persisted inputs for Expedite consumers."""
from types import SimpleNamespace

from mta.presentation import hierarchy
from mta.presentation.context import selected_run, permission_catalogue, PublicationUnavailable
from mta.presentation.expedite_storage import read_expedite
from mta.presentation.selective import image_rows
from mta.presentation.terminal_supplement import terminal_ancillary
from mta.runtime.models import ExpediteProjection

PARENT_COLUMNS = (
    ('Tags', 't', 1), ('SKU code', 'sc', 2), ('SKU Description', 'sd', 3),
    ('Location', 'wcd', 4), ('Parent location', 'pl', 5), ('Norm', 'n', 6),
    ('Virtual Norm', 'vn', 7), ('Stock', 'st', 8), ('On-hand Inventory Pen', 'pip', 9),
    ('GIT', 'g', 10), ('Required Quantity', 'rq', 13), ('Pipeline Inventory Pen', 'pin', 12),
    ('RationedQty', 'rtq', 15), ('Price', 'am', 16), ('Business', 'sl1', 17),
    ('Category', 'sl2', 18), ('Family', 'sl3', 19), ('Zone', 'll1', 22),
    ('Location Group', 'll2', 23), ('WH Type', 'll3', 24),
)


def parent_grid(payload):
    from mta.presentation.context import scope
    from mta.presentation.excess_read import pagination
    from mta.presentation.expedite_parent import parent_filter, parent_rows
    context = expedite_context()
    paging = pagination(payload)
    if paging is None:
        # Canonical SQL156 is swallowed into empty success. Do not present this
        # required export path as working or silently authorize that defect.
        raise PublicationUnavailable('LEG-EXPEDITE-PARENT-UNPAGED-SQL156: legacy empty-success; NOT_PARITY')
    selected = parent_filter(payload, context.importer)
    products, locations = scope(payload, attributes=context.importer)
    data = parent_rows(context.rows, context.importer, context.standards, context.masters,
                       nms=context.nms, products=products, locations=locations,
                       paging=paging, matches=selected)
    return dict(data=data, uiConfig=[dict(header=h, colCode=c, colPosition=p) for h,c,p in PARENT_COLUMNS])


def custom_grid(payload):
    from decimal import Decimal
    from mta.presentation.context import scope
    from mta.presentation.excess_read import CUSTOM_COLUMNS, pagination
    from mta.presentation.expedite_custom import custom_rows
    context = expedite_context()
    paging = pagination(payload)
    products, locations = scope(payload, attributes=context.importer)
    try:
        rows = custom_rows(context.rows, nms=context.nms, products=products,
                           locations=locations, paging=paging, stable_producer_order=True)
    except ValueError as exc:
        raise PublicationUnavailable(str(exc)) from exc
    # The deployed custom handler deserializes SQL JSON as an object: numeric
    # penetration stays numeric, unlike the parent string-dictionary handler.
    data = [{key: float(value) if isinstance(value, Decimal) else value
             for key, value in row.items()} for row in rows]
    return dict(data=data, uiConfig=[dict(header=h, colCode=c, colPosition=p)
                                    for h, c, p in CUSTOM_COLUMNS])


def expedite_context():
    run = selected_run()
    importer = {name: image_rows(run, 'closing/importer/'+name) for name in (
        'MasterData', 'SkuAttributeData', 'LocationAttributeData', 'SkuLocAttributeData',
        'SKUDescriptionTbl', 'SiteDescriptionTbl')}
    standards = image_rows(run, 'closing/dbm/SKULocStandardAttributes')
    native = dict(BPRReports=[{'vf_RationedReqReport': image_rows(run, 'reports/bpr/vf_RationedReqReport')}],
                  ClosingState=[dict(importer=importer, dbm={'SKULocStandardAttributes': standards},
                                     btr={'ExpediteDispatches': image_rows(run, 'closing/btr/ExpediteDispatches')})])
    try:
        rows = read_expedite(run, output=native)
    except ExpediteProjection.DoesNotExist as exc:
        raise PublicationUnavailable('selected_run_expedite_projection_not_published') from exc
    try:
        manifest = hierarchy.selected_manifest(run)
        if manifest:
            importer = hierarchy.project_attributes(importer, permission_catalogue(), manifest)
    except hierarchy.HierarchyUnavailable as exc:
        raise PublicationUnavailable(str(exc)) from exc
    ancillary = terminal_ancillary(run)
    masters = image_rows(run, 'closing/bpr/BPRMaster')
    output = {**native, 'ClosingState': [{**native['ClosingState'][0],
                                        'importer': importer, 'bpr': {'BPRMaster': masters}}]}
    return SimpleNamespace(run=run, rows=rows, importer=importer, standards=standards,
                           masters=masters, native_output=native, output=output,
                           nms=image_rows(run, 'closing/consumer_context/NMSAllItems'),
                           remarks=ancillary['BPRReport_RemarkDetails'])
