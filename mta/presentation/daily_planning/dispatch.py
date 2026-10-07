"""Exact approved routes; no fallback from missing extension admission."""
from mta.presentation.context import PublicationUnavailable, scope
from mta.presentation.daily_planning_extension import require
from .sources import _projected_attributes


def read(run, payload, route, *, count=False):
    from .sources import admitted_request
    with admitted_request(run,route):
        return _read(run,payload,route,count=count)


def _read(run, payload, route, *, count=False):
    category=str(payload.get('category','')).casefold()
    kind=str(payload.get('type','')).casefold()
    if route=='overview':
        from .planning_overview_sql import counts
        return counts(run,payload)
    if category=='git':
        if route=='grid':
            from .planning_git_sql import grid
            return grid(run,payload,count=count)
        attributes,_=_projected_attributes(run)
        products,locations=scope(payload,attributes=attributes)
        if route=='graph':
            if kind!='child':
                raise PublicationUnavailable('selected_git_parent_graph_not_implemented_by_legacy')
            from .daily_git_read import graph
            return graph(run,products,locations)
        from .daily_git_custom import custom
        from mta.presentation.excess_read import pagination
        return custom(run,products,locations,pagination(payload))
    if category=='expedite':
        if route=='grid':
            from .planning_expedite_sql import counts,parent_grid,child_grid
            if count:return counts(run,payload)
            if kind=='parent':return parent_grid(run,payload)
            if kind=='child':return child_grid(run,payload)
            raise PublicationUnavailable('selected_expedite_type_not_supported')
        if route=='graph':
            from .planning_expedite_chart_sql import queries
            from mta.presentation.expedite_charts import response
            from mta.presentation.legacy_ui import _no_active_filters
            if not _no_active_filters(payload):
                raise PublicationUnavailable('selected_planning_filters_not_yet_connected')
            return response(queries(run,payload,kind),kind)
        from .planning_expedite_custom_sql import custom_grid
        return custom_grid(run,payload)
    if category not in ('excessinventory','orderfulfillment'):
        raise PublicationUnavailable('selected_planning_branch_not_yet_connected')
    family='excess' if category=='excessinventory' else 'fulfillment'
    if route=='graph':
        from .planning_chart_sql import graph
        return graph(run,payload,family)
    from mta.presentation.excess_read import pagination
    if route=='custom':
        from .planning_custom_sql import custom_grid
        return custom_grid(run,payload,pagination(payload),family=family)
    from .planning_grid_sql import read_grid
    values=read_grid(run,payload,family=family,paging=pagination(payload),count=count)
    if count:return values
    from mta.presentation.excess_grid import excess_grid_config
    from mta.presentation.fulfillment_grid import fulfillment_grid_config
    return dict(data=values,uiConfig=(excess_grid_config() if family=='excess' else fulfillment_grid_config()))
