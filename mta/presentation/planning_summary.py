"""One current scoped read of the retained, sealed Planning contributions."""
import json
from types import SimpleNamespace
from uuid import UUID
from django.conf import settings
from django.db import connection
from mta.serialization import digest
from mta.presentation.context import PublicationUnavailable, scope

# Exact producer recipe of the accepted immutable contribution generation.
# This pins production provenance, independently of this response reader.
PREPARED_RECIPE = '189dd5148e1c9b4e13eb33a285ae666823925d4bead69e583d670745bf01ba9d'
METRICS = ('git_parent','git_child','git_custom','expedite_parent','expedite_child',
           'expedite_custom','excess_review','excess_custom','fulfillment_review','fulfillment_custom')
INT32 = frozenset(('expedite_parent','expedite_child','expedite_custom','excess_custom','fulfillment_custom'))


def read(run, payload):
    from mta.presentation import fixture
    from mta.presentation.legacy_ui import _no_active_filters
    from mta.presentation.bpr_sql import _projected_attributes
    if not _no_active_filters(payload):
        raise PublicationUnavailable('selected_planning_filters_not_yet_connected')
    if run.kind != 'LEGACY_UI_FIXTURE':
        from mta.presentation.planning_summary_daily import require_ready
        from mta.presentation.daily_planning.sources import _projected_attributes as daily_attributes
        from mta.presentation.daily_planning_extension import require
        require(run, 'overview')
        receipt = require_ready(run)
        attrs, _ = daily_attributes(run)
        return counts(receipt, scope(payload, attributes=attrs)), run.business_date.isoformat()
    selected, source = fixture.binding()
    if selected.pk != run.pk:
        raise PublicationUnavailable('planning_summary_selection_changed')
    checked = dict(validated_fixture=(selected,source))
    attrs, manifest = _projected_attributes(run)
    if manifest:
        raise PublicationUnavailable('planning_overview_native_hierarchy_required')
    if fixture.bpr_ancillary(run, **checked)['InTransitData']:
        raise PublicationUnavailable('planning_transporter_nonempty_source_not_prepared')
    from mta.presentation.planning_sources import admitted_sources
    from mta.presentation.planning_git import admitted_git
    from mta.presentation.planning_grids import admitted_grids
    from mta.presentation.planning_expedite_grids import admitted_expedite_grids
    for validate in (admitted_sources,admitted_git,admitted_grids,admitted_expedite_grids):
        validate(run, **checked)
    from mta.runtime import models
    dependencies = {name:[{k:str(v) if isinstance(v,UUID) else v for k,v in row.items()}
        for row in getattr(models,name).objects.filter(run=run).values()]
        for name in ('PlanningSourceProjection','PlanningGitProjection',
                     'PlanningGridProjection','PlanningExpediteGridProjection')}
    generation = digest(dict(btr=getattr(settings,'VF_BTR_REPORTING_GENERATION',''),
                             source=source,dependencies=dependencies))
    from mta.runtime.planning_summary_schema import verify_guards
    verify_guards(connection)
    with connection.cursor() as cursor:
        cursor.execute("""SELECT id,metrics,row_count FROM mta.fresh_mta_planningsummaryreceipt
            WHERE run_id=%s AND source_digest=%s AND generation_digest=%s
            AND recipe_digest=%s AND business_date=%s AND status='READY'""",
            [run.pk,source,generation,PREPARED_RECIPE,run.business_date])
        rows=cursor.fetchall()
        metrics = rows[0][1] if len(rows) == 1 else None
        if isinstance(metrics, str):
            metrics = json.loads(metrics)
        if len(rows)!=1 or metrics!=list(METRICS):
            raise PublicationUnavailable('planning_summary_generation_unavailable')
        owner,_,expected_count=rows[0]
        cursor.execute('SELECT count(*) FROM mta.fresh_mta_planningsummarycontribution WHERE receipt_id=%s',[owner])
        if cursor.fetchone()[0]!=expected_count:
            raise PublicationUnavailable('planning_summary_row_count_changed')
    return counts(SimpleNamespace(pk=owner),scope(payload,attributes=attrs)),run.business_date.isoformat()


def counts(receipt, resolved):
    products,locations=resolved
    totals={name:0 for name in METRICS}
    if products and locations:
        from mta.presentation.bpr_sql import _values_cte
        from mta.presentation.rrr_sql import equal
        ctes=[];params=[]
        for alias,codes in (('P',products),('L',locations)):
            sql,values=_values_cte([dict(code=code,weight=codes.multiplicities[code]) for code in sorted(codes)],('code','weight'),{'weight':'::bigint'})
            ctes.append(alias+' AS ('+sql+')');params.extend(values)
        branches=[]
        for profile,product,location in (
            ('raw','P.code=C.product_key','L.code=C.location_key'),
            ('normalized',equal('P.code','C.product_key'),equal('L.code','C.location_key'))):
            branches.append('SELECT C.metric,C.occurrence_count::numeric*(P.weight*L.weight) AS amount '
                'FROM mta.fresh_mta_planningsummarycontribution C JOIN P ON '+product+
                ' JOIN L ON '+location+" WHERE C.equality_profile='"+profile+"' AND C.receipt_id=%s")
        query='WITH '+','.join(ctes)+' SELECT metric,sum(amount) FROM ('+' UNION ALL '.join(branches)+') weighted GROUP BY metric'
        with connection.cursor() as c:
            c.execute(query,[*params,receipt.pk,receipt.pk]);totals.update((k,int(v)) for k,v in c.fetchall())
    for metric in INT32:
        if totals[metric]>2147483647:
            from django.db import DataError
            raise DataError('integer out of range')
    return [dict(category='git/wip',parentCount=str(totals['git_parent']),childCount=str(totals['git_child']),custom=str(totals['git_custom'])),
        dict(category='expedite',parentCount=str(totals['expedite_parent']),childCount=str(totals['expedite_child']),custom=str(totals['expedite_custom'])),
        dict(category='excessInventory',reviewCount=str(totals['excess_review']),custom=str(totals['excess_custom'])),
        dict(category='orderFulfillment',reviewCount=str(totals['fulfillment_review']),custom=str(totals['fulfillment_custom']))]
