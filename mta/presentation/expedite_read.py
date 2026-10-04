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
    run = selected_run()
    if getattr(run, 'kind', None) == 'LEGACY_UI_FIXTURE':
        from mta.presentation.planning_expedite_sql import parent_grid as prepared_parent_grid
        return prepared_parent_grid(run, payload)
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
    context = expedite_context(include_master=False, custom=True)
    paging = pagination(payload)
    products, locations = scope(payload, attributes=context.importer)
    try:
        from mta.presentation.legacy_ui import BPR_UI_CONFIG
        visible_attributes = [row for row in BPR_UI_CONFIG
                              if row.get('Visible') and 'attr' in row['Col_Code'].lower()]
        rows = custom_rows(context.rows, nms=context.nms, products=products,
                           locations=locations, paging=paging, stable_producer_order=True,
                           bpr_rows=context.bpr_rows,
                           site_descriptions=context.importer['SiteDescriptionTbl'],
                           visible_dynamic_attributes=visible_attributes)
    except ValueError as exc:
        raise PublicationUnavailable(str(exc)) from exc
    # The deployed custom handler deserializes SQL JSON as an object: numeric
    # penetration stays numeric, unlike the parent string-dictionary handler.
    data = [{key: float(value) if isinstance(value, Decimal) else value
             for key, value in row.items()} for row in rows]
    return dict(data=data, uiConfig=[dict(header=h, colCode=c, colPosition=p)
                                    for h, c, p in CUSTOM_COLUMNS])


def child_grid(payload):
    from django.conf import settings
    from mta.presentation.context import scope
    from mta.presentation.excess_read import pagination
    from mta.presentation.excess_filters import predicate
    from mta.presentation.expedite_child import child_rows
    from mta.presentation.legacy_ui import BPR_UI_CONFIG
    if any(row.get('Visible') and 'attr' in row['Col_Code'].lower() for row in BPR_UI_CONFIG):
        raise PublicationUnavailable('child_expedite_dynamic_attributes_not_connected')
    # Commons emits an unqualified norm expression in this joined query.
    # Its child SQL failure envelope has not been qualified; do not silently
    # replace it with a corrected a.Norm predicate.
    availability = (payload.get('filters') or {}).get('availabilityFilter') or {}
    if any(item.get('attributeName', '').lower() == 'norm'
           for item in availability.get('filters', [])):
        raise PublicationUnavailable('child_expedite_norm_filter_contract_unverified')
    context = expedite_context()
    # Direct human approval on 3 October 2026 establishes an initial empty
    # application history ONLY here. It is not a claim about legacy history.
    binding = (str(context.run.pk), str(context.run.business_date), context.run.output_digest)
    if (not settings.VF_MTA_PREVIEW_EMPTY_EXPEDITE_HISTORY or binding != (
            'ac1612c8-0e49-4155-83c3-f59f41422293', '2026-06-17',
            'bd1c522f3df299d2fc3841aed7f66d48e4307e6967450b2d8a5463dc7867d33d')):
        raise PublicationUnavailable('child_expedite_request_history_not_admitted')
    products, locations = scope(payload, attributes=context.importer)
    data = child_rows(context.rows, context.importer, context.standards,
                      products=products, locations=locations, paging=pagination(payload),
                      business_date=context.run.business_date, requests=[],
                      transit=terminal_ancillary(context.run)['InTransitData'],
                      matches=predicate(payload, context.importer))
    positions = {'rq': 12, 'pin': 11}
    return dict(data=data, uiConfig=[dict(header=h, colCode=c, colPosition=positions.get(c, p))
                                    for h, c, p in PARENT_COLUMNS])


def expedite_context(*, include_master=True, custom=False):
    run = selected_run()
    fixture = run.kind == 'LEGACY_UI_FIXTURE'
    names = ['SkuAttributeData', 'LocationAttributeData', 'SkuLocAttributeData',
             'SKUDescriptionTbl', 'SiteDescriptionTbl']
    if include_master or not fixture:
        names.append('MasterData')
    importer = {name: image_rows(run, 'closing/importer/'+name) for name in names}
    standards = image_rows(run, 'closing/dbm/SKULocStandardAttributes')
    native = dict(ClosingState=[dict(importer=importer, dbm={'SKULocStandardAttributes': standards})])
    if include_master or not fixture:
        native['BPRReports'] = [{'vf_RationedReqReport': image_rows(run, 'reports/bpr/vf_RationedReqReport')}]
        native['ClosingState'][0]['btr'] = {'ExpediteDispatches': image_rows(run, 'closing/btr/ExpediteDispatches')}
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
    # Count/custom consume no BPR master or remarks. Their availability must not
    # depend on unrelated parent/child workflow inputs.
    masters = image_rows(run, 'closing/bpr/BPRMaster') if include_master else None
    if include_master:
        if run.kind == 'LEGACY_UI_FIXTURE':
            from mta.presentation.fixture import bpr_ancillary
            ancillary = bpr_ancillary(run)
        else:
            ancillary = terminal_ancillary(run)
    else:
        ancillary = None
    output = {**native, 'ClosingState': [{**native['ClosingState'][0],
                                        'importer': importer, 'bpr': {'BPRMaster': masters}}]}
    return SimpleNamespace(run=run, rows=rows, importer=importer, standards=standards,
                           masters=masters, native_output=native, output=output,
                           bpr_rows=image_rows(run, 'reports/bpr/BPR_Table') if custom else None,
                           nms=image_rows(run, 'closing/consumer_context/NMSAllItems'),
                           remarks=ancillary['BPRReport_RemarkDetails'] if ancillary is not None else None)
