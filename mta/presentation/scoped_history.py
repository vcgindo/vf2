"""Required BPR lookups/history over declared accepted earlier owners."""
from mta.presentation.context import PublicationUnavailable, scope
from mta.presentation import scoped_dbm


def descriptions(view, payload, kind):
    from mta.presentation.descriptions import description_rows
    from mta.presentation.selective import image_rows
    inherited = view.bpr.sources.inherited_btr
    if inherited is None or inherited.locator['owner_kind'] != 'PREDECESSOR':
        # An initial explicit opening has no implied completed BTR descriptions.
        raise PublicationUnavailable('phase_inherited_description_owner_unavailable')
    owner = inherited.owner
    attributes = {name: image_rows(owner, 'closing/btr/' + name)
                  for name in ('SkuAttributeData', 'LocationAttributeData')}
    products, locations = scope(payload, attributes=attributes)
    table = 'SKUDescriptionTbl' if kind == 'sku' else 'SiteDescriptionTbl'
    return description_rows(image_rows(owner, 'closing/btr/' + table),
        products if kind == 'sku' else locations, kind)


def daily(view, payload):
    from mta.presentation.daily_history import daily_graph
    sku, location = payload.get('SKUCode'), payload.get('WHCode')
    if not isinstance(sku, str) or not isinstance(location, str):
        raise ValueError('SKUCode_and_WHCode_required')
    context = getattr(view,'dbm_context',None)
    if context is None:
        context = scoped_dbm.bind(view.bpr.sources.acceptance_id,
            expected_digest=view.bpr.sources.acceptance_digest,
            action_revision=view.bpr.sources.action_revision)
    products, locations = scope(payload, attributes=context.dbm)
    if sku not in products or location not in locations:
        return []
    state = dict(context.dbm)
    # The current accepted controls/master/action rows are new; the DBM rule
    # histories have not run for N. Preserve their actual earlier row dates.
    for name in ('DailyConsumption', 'SuspendHistory', 'NormChangeLogTbl',
                 'SuggestionsLog', 'SuspendStockType', 'SuspendConsumptionType'):
        state[name] = scoped_dbm._opening_rows(view.bpr.sources, name)
    marker = view.bpr.sources.rows('metadata/bpr/LastBatchRunTbl')
    state['LastBatchRunTbl'] = marker
    return daily_graph(state, sku, location)
