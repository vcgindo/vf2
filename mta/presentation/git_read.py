"""Explicitly admitted terminal-zero GIT consumers; never a transit fallback.

Authority: pinned PlanningProcessor bf716c4f and ExpediteProcessor e78148cc.
Nonempty logistics are not published by this adapter. Source-invalid queries
remain attributable unavailable responses, not fabricated successful results.
"""
from types import SimpleNamespace

from mta.presentation import hierarchy
from mta.presentation.context import selected_run, permission_catalogue, scope, PublicationUnavailable
from mta.presentation.dbm_filters import STANDARD_GROUPS
from mta.presentation.excess_filters import predicate
from mta.presentation.excess_read import CUSTOM_COLUMNS, pagination
from mta.presentation.planning_read import terminal_git_reports
from mta.presentation.selective import image_rows
from mta.presentation.terminal_supplement import terminal_ancillary


NORMAL_COLUMNS = (
    ('Tags', 't', 1), ('Status', 'st', 2), ('SKU Code', 'sc', 3),
    ('SKU Description', 'skd', 4), ('Location', 'wcd', 5), ('Parent Location', 'prn', 6),
    ('Norm', 'n', 7), ('VirtualNorm', 'vn', 8), ('Stock', 'stk', 9), ('Git', 'g', 11),
    ('On-HandInventory Pen', 'pip', 10), ('Pipeline Inventory Pen', 'plp', 12),
    ('Required Qty', 'rq', 13), ('Price', 'pr', 14), ('ElephantOrderCapping', 'eoc', 15),
    ('Weight', 'wt', 16), ('Volume', 'v', 17), ('Business', 'sl1', 18), ('Category', 'sl2', 19),
    ('Family', 'sl3', 20), ('Zone', 'll1', 23), ('Location Group', 'll2', 24), ('WH Type', 'll3', 25),
)


def terminal_context(payload):
    run = selected_run()
    ancillary = terminal_ancillary(run)
    terminal_git_reports(image_rows(run, 'reports/bpr/vf_RationedReqReport'), ancillary)
    importer = {name: image_rows(run, 'closing/importer/'+name)
                for name in ('SkuAttributeData', 'LocationAttributeData')}
    try:
        manifest = hierarchy.selected_manifest(run)
        if manifest:
            importer = hierarchy.project_attributes(importer, permission_catalogue(), manifest)
    except hierarchy.HierarchyUnavailable as exc:
        raise PublicationUnavailable(str(exc)) from exc
    products, locations = scope(payload, attributes=importer)
    return SimpleNamespace(run=run, attributes=importer, products=products, locations=locations)


def validate_filters(payload, context, *, child_count=False):
    # The selected GIT parent joins expose the same Commons-filter columns as
    # Excess, including its invalid category/coverage/colour-history references.
    # The producer has already proved zero rows; do not evaluate a fabricated row.
    try:
        predicate(payload, context.attributes)
    except PublicationUnavailable as exc:
        raise PublicationUnavailable('LEG-GIT-FILTER-INVALID-SQL:'+str(exc).partition(':')[2]) from exc
    groups = payload.get('filters') or {}
    if not child_count or not any(groups.get(g) is not None for g in STANDARD_GROUPS):
        return
    for item in (groups.get('productFilter') or {}).get('filters', []):
        if item.get('attributeName') not in ('', None) and item['attributeName'].lower() != 'sku':
            raise PublicationUnavailable('LEG-GIT-FILTER-INVALID-SQL:child transporter count missing SKU hierarchy column')
    for item in (groups.get('customAttributeFilter') or {}).get('filters', []):
        name = item.get('attributeName', '').lower()
        if 'skuattr' in name and 'skulocattr' not in name:
            raise PublicationUnavailable('LEG-GIT-FILTER-INVALID-SQL:child transporter count missing sa alias')


def grid(payload, *, count=False):
    context = terminal_context(payload)
    kind = str(payload.get('type', '')).lower()
    if kind not in ('parent', 'child'):
        raise PublicationUnavailable('selected_git_type_not_supported')
    pagination(payload)
    validate_filters(payload, context, child_count=count and kind == 'child')
    if not count and kind == 'child':
        raise PublicationUnavailable('LEG-GIT-CHILD-TRANSPORTER-INVALID-SQL:207/8120; combined child grid unavailable')
    if count:
        return [dict(locationwise=0, **({'transporterwise': 0} if kind == 'child' else {}))]
    return dict(data=[], uiConfig=[dict(header=h, colCode=c, colPosition=p) for h,c,p in NORMAL_COLUMNS])


def custom(payload):
    terminal_context(payload)
    pagination(payload)
    # GetCustomGridData ignores filters and type, including filters: [].
    return dict(data=[], uiConfig=[dict(header=h, colCode=c, colPosition=p) for h,c,p in CUSTOM_COLUMNS])


def graph(payload):
    terminal_context(payload)
    if str(payload.get('type', '')).lower() != 'child':
        raise PublicationUnavailable('selected_git_parent_graph_not_implemented_by_legacy')
    # Four empty typed SQL datasets passed to actual GetGoodsInTransitResponse.
    # The source graph processor never inspects request filters.
    return dict(data={group: {section: dict(data=[], uiconfig=[
        dict(header='LL'+str(i), colCode='ll'+str(i), colPosition=0) for i in range(1,6)])
        for section in ('maxTechBlackRedColumn', 'delayDaysStatisticalBox')}
        for group in ('locationWise', 'transporterWise')})
