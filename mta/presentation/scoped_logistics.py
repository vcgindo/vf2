"""Logistics reads from the selected immutable BPR dependency owners.

No preparation, Full publication, live request owner or workflow overlay is
admitted here. The serving dispatcher supplies its already selected ViewBinding.
"""
from mta.presentation.context import PublicationUnavailable
from mta.runtime.relational_state import quote, table_sql, load_image


def require_binding(run, view):
    from mta.presentation.scoped_view import ViewBinding
    from mta.presentation.scoped_expedite import require_binding as require_expedite
    from mta.presentation import logistics_live
    from mta.runtime.models import TransitLiveGeneration
    if not isinstance(view, ViewBinding) or view.run_id != run.pk:
        raise PublicationUnavailable('bpr_logistics_view_owner_differs')
    expedition = require_expedite(run, view.expedite)
    if (view.bpr.sources.source_digest != expedition.sources.source_digest
            or view.bpr.reports.generation.pk != expedition.core.prepared.reports.generation.pk
            or view.bpr.transit is None
            or view.bpr.transit.provenance() != expedition.transit.provenance()):
        raise PublicationUnavailable('bpr_logistics_dependencies_differ')
    # An independently mutable Full overlay cannot certify a phase image.
    if logistics_live.enabled() and TransitLiveGeneration.objects.filter(run_id=run.pk).exists():
        raise PublicationUnavailable('bpr_logistics_live_transit_binding_required')
    return view


def request_query(view):
    from mta.presentation.scoped_requests import FIELDS, DATES
    request = view.expedite.requests
    request.verify_rows()
    sql, params = request.query()
    # RequestBinding returns native wall timestamps. Give native_wire an
    # explicit UTC carrier so the host timezone cannot shift those cells.
    fields = [quote(f) + (" AT TIME ZONE 'UTC' AS " + quote(f) if f in DATES else '') for f in FIELDS]
    return 'SELECT vf_ordinal,' + ','.join(fields) + ' FROM (' + sql + ') captured_requests', params


def history_query(run, view, name):
    from mta.presentation import scoped_sources
    from mta.runtime import phase_state
    require_binding(run, view)
    if name not in ('InTransitWhereAboutsRemarks', 'OpenExpeditRequestRemarksHistory'):
        raise PublicationUnavailable('bpr_logistics_history_source_unavailable')
    sources = view.bpr.sources
    phase = scoped_sources._accepted_phase(sources.acceptance_id, sources.acceptance_digest)
    if phase.snapshot.state_digest != sources.snapshot_digest:
        raise PublicationUnavailable('bpr_logistics_history_owner_differs')
    manifest = phase.snapshot.manifest
    image = scoped_sources._image(manifest, ('state', 'complete', name))
    if image is None:
        raise PublicationUnavailable('bpr_logistics_history_source_unavailable:' + name)
    item = scoped_sources._checked(manifest['images'].get(image))
    table = 'complete/BPR/' + name
    # The sealed BPR manifest deliberately aliases unchanged PRE_BPR bags.
    # Its verified logical entry owns the physical locator; querying the
    # logical BPR key would silently lose those inherited rows.
    physical = item['image']
    if (item['table'] != table
            or image != 'phase/BPR/complete/' + name
            or physical not in ('phase/BPR/complete/' + name, 'phase/PRE_BPR/complete/' + name)):
        raise PublicationUnavailable('bpr_logistics_history_owner_differs')
    # Verify the entire immutable bag, including a genuine zero-row owner.
    load_image(run, item, table_registry=phase_state.REGISTRY)
    registry = phase_state.REGISTRY[table]
    fields = {field: (column, dict(registry)[column]) for field, column, _ in item['fields']}
    if not fields and item['count'] == 0:
        fields = {field: (field, kind) for field, kind in registry}
    if set(fields) != {field for field, _ in registry}:
        raise PublicationUnavailable('bpr_logistics_history_fields_differ')
    selected = []
    for field, (column, kind) in fields.items():
        expression = quote(column)
        if kind == 'datetime':
            expression += " AT TIME ZONE 'UTC'"
        selected.append(expression + ' AS ' + quote(field))
    return ('SELECT vf_ordinal,' + ','.join(selected) + ' FROM ' + table_sql(table)
            + ' WHERE vf_run_id=%s AND vf_image=%s'), [run.pk, physical]
