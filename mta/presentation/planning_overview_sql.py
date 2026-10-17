from mta.presentation.native_mode import removed_mode
"""The ten unfiltered SCIH counts over exact prepared grains and typed facts."""
from django.db import connection
from mta.presentation.bpr_sql import _projected_attributes
from mta.presentation.context import PublicationUnavailable,scope
from mta.presentation.planning_git_sql import grid as git_grid
from mta.presentation.planning_grid_sql import read_grid
from mta.presentation.planning_expedite_sql import counts as expedite_counts
from mta.presentation.rrr_sql import key


def counts(run,payload):
    from mta.presentation.legacy_ui import _no_active_filters
    if not _no_active_filters(payload):
        raise PublicationUnavailable('selected_planning_filters_not_yet_connected')
    from mta.presentation.daily_preparation import production_branch
    transit=(__import__('mta.presentation.daily_preparation',fromlist=['ancillary_row']).ancillary_row(run,'InTransitData')
             if production_branch(run) else removed_mode('historical_fixture')['InTransitData'])
    if transit:
        raise PublicationUnavailable('planning_transporter_nonempty_source_not_prepared')
    importer,manifest=_projected_attributes(run)
    if manifest:raise PublicationUnavailable('planning_overview_native_hierarchy_required')
    products,locations=scope(payload,attributes=importer)
    # All ten totals share this request's actor and producer attributes. Reuse
    # that exact permission expansion; each consumer retains its own admission,
    # direction, eligibility and multiplicity. Nothing survives the request.
    resolved_scope=(importer,manifest,products,locations)
    custom=dict(expedite=0,excess=0,fulfillment=0)
    if products and locations:
        ctes,params=[],[]
        for alias,codes in (('P',products),('L',locations)):
            members=sorted(codes)
            ctes.append(alias+'(code,weight) AS (VALUES '+','.join(['(%s::text,%s::bigint)']*len(members))+')')
            params.extend(v for code in members for v in (code,codes.multiplicities[code]))
        selects=[]
        for family,table,location,condition in (
            ('expedite','expediterow','ParentWhCode','A."RationedQty">0 AND '+key('A."PipelineInventoryColor"')+" IN ('red','black')"),
            ('excess','excessinventoryrow','WhCode','A."ReportDate"=%s'),
            ('fulfillment','fulfillmentsummaryrow','WhCode','TRUE')):
            selects.append("SELECT '"+family+"',COALESCE(sum(P.weight*L.weight),0)::integer FROM mta.fresh_mta_"+table+
                ' A JOIN P ON P.code=A."SKUCode" JOIN L ON L.code=A."'+location+'" WHERE A.run_id=%s AND '+condition)
            params.append(run.pk)
            if family=='excess':params.append(run.business_date)
        with connection.cursor() as c:
            c.execute('WITH '+','.join(ctes)+' '+' UNION ALL '.join(selects),params)
            custom.update(c.fetchall())
    git={};expedite={}
    for direction in ('parent','child'):
        selected=dict(payload,type=direction)
        git[direction]=git_grid(run,selected,count=True,overview=True,resolved_scope=resolved_scope)[0]['locationwise']
        expedite[direction]=expedite_counts(run,selected,resolved_scope=resolved_scope)['expediteDispatches']
    excess=read_grid(run,payload,family='excess',paging=None,count=True,resolved_scope=resolved_scope)
    fulfillment=read_grid(run,payload,family='fulfillment',paging=None,count=True,resolved_scope=resolved_scope)
    return [dict(category='git/wip',parentCount=str(git['parent']),childCount=str(git['child']),custom='0'),
        dict(category='expedite',parentCount=str(expedite['parent']),childCount=str(expedite['child']),custom=str(custom['expedite'])),
        dict(category='excessInventory',reviewCount=str(excess),custom=str(custom['excess'])),
        dict(category='orderFulfillment',reviewCount=str(fulfillment),custom=str(custom['fulfillment']))]
