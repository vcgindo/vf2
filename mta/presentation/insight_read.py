"""Named native dependencies for the existing Guided Insights projections."""
from types import SimpleNamespace

from mta.presentation import hierarchy
from mta.presentation.context import selected_run, permission_catalogue, PublicationUnavailable
from mta.presentation.selective import image_rows


KINDS = frozenset(('loc', 'sku', 'pie', 'ageing', 'chronic-loc', 'chronic-sku',
                   'chronic-grid', 'availability-trend', 'availability-ageing', 'excess-sku', 'excess-value'))


def insight_context(kind):
    if kind not in KINDS:
        raise ValueError('unknown_guided_insight')
    run = selected_run()
    names = ['SkuAttributeData', 'LocationAttributeData', 'SkuLocAttributeData']
    if kind.startswith('availability-'):
        names.append('BPR')
        if kind == 'availability-ageing':
            names.append('BTRSnapshotForUI')
    elif not kind.startswith('excess-'):
        names.append('ChronicUnavalabilityData' if kind.startswith('chronic-')
                     else 'DBMNormSuggestionsData')
        if kind.endswith('loc'):
            names.append('SiteDescriptionTbl')
        elif kind.endswith('sku'):
            names.append('SKUDescriptionTbl')
    owner = 'closing/importer/' if kind.startswith('excess-') else 'closing/btr/'
    state = {name: image_rows(run, owner + name) for name in names}
    try:
        manifest = hierarchy.selected_manifest(run)
        if manifest:
            state = hierarchy.project_attributes(state, permission_catalogue(), manifest)
    except hierarchy.HierarchyUnavailable as exc:
        raise PublicationUnavailable(str(exc)) from exc
    dbm = ({'DBMMaster': image_rows(run, 'closing/dbm/DBMMaster')}
           if kind in ('loc', 'sku', 'pie', 'ageing') else {})
    nms = (image_rows(run, 'closing/consumer_context/NMSAllItems')
           if kind == 'chronic-grid' else None)
    history = None
    if kind.startswith('excess-'):
        from mta.presentation.excess_history import selected_manifest, read_history
        history = read_history(run, selected_manifest(run))
    return SimpleNamespace(run=run, business_date=run.business_date,
                           state=state, dbm=dbm, nms=nms, history=history)
