"""Exact additive Planning measures, prepared once per admitted generation."""
import hashlib
from uuid import UUID
from pathlib import Path
from django.conf import settings
from django.db import connection, transaction
from django.utils import timezone
from mta.serialization import digest
from mta.presentation.context import PublicationUnavailable, scope
from mta.runtime.planning_summary_models import (METRICS, PlanningSummaryReceipt,
    PlanningSummaryContribution, PlanningSummaryAttempt)

INT32 = frozenset(('expedite_parent', 'expedite_child', 'expedite_custom',
                   'excess_custom', 'fulfillment_custom'))


def recipe_digest():
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def binding(run):
    from mta.presentation import fixture
    validated_fixture = None
    if run.kind == 'LEGACY_UI_FIXTURE':
        selected, source = fixture.binding()
        validated_fixture = (selected, source)
        if selected.pk != run.pk:
            raise PublicationUnavailable('planning_summary_selection_changed')
        from mta.presentation.bpr_sql import _projected_attributes
        attrs, manifest = _projected_attributes(run)
        if manifest:
            raise PublicationUnavailable('planning_overview_native_hierarchy_required')
        if fixture.bpr_ancillary(run)['InTransitData']:
            raise PublicationUnavailable('planning_transporter_nonempty_source_not_prepared')
        generation = dict(btr=getattr(settings, 'VF_BTR_REPORTING_GENERATION', ''), source=source)
    else:
        from mta.presentation.daily_publication import require_ready
        from mta.presentation.daily_planning.sources import _projected_attributes
        from mta.presentation.daily_planning_extension import require
        require(run, 'overview')
        publication = require_ready(run)
        source = publication.source_digest
        attrs, _ = _projected_attributes(run)
        generation = dict(publication=publication.seal_digest)
    # Admission validates immutable sources; it does not execute detail counts.
    from mta.presentation.planning_sources import admitted_sources
    from mta.presentation.planning_git import admitted_git
    from mta.presentation.planning_grids import admitted_grids
    from mta.presentation.planning_expedite_grids import admitted_expedite_grids
    # These direct dependencies share this call's already validated fixture
    # identity. Their receipt/recipe/immutable guards still run independently;
    # no value survives this call and all other readers retain their old path.
    checked = dict(validated_fixture=validated_fixture)
    relations = dict(master=admitted_sources(run, **checked)['git_master'],
        git=admitted_git(run, **checked)['row'], expedite=admitted_expedite_grids(run, **checked)['row'],
        **admitted_grids(run, **checked))
    from mta.runtime import models
    generation['dependencies'] = {name:[{k:str(v) if isinstance(v,UUID) else v for k,v in row.items()}
        for row in getattr(models,name).objects.filter(run=run).values()]
        for name in ('PlanningSourceProjection','PlanningGitProjection',
                     'PlanningGridProjection','PlanningExpediteGridProjection')}
    if run.kind != 'LEGACY_UI_FIXTURE':
        from mta.presentation.selective import image_metadata
        from mta.presentation.daily_transit import PATH, TRANSPORTER_PATH
        generation['transit']={path:image_metadata(run,path) for path in (PATH,TRANSPORTER_PATH)}
    return dict(source_digest=source, generation_digest=digest(generation),
                recipe_digest=recipe_digest(), business_date=run.business_date), attrs, relations


def contribution_queries(run, relations):
    """Unweighted native occurrence bags, retaining raw authorization keys."""
    def grouped(metric, relation, params, product, location, profile='raw'):
        return ("SELECT %s::text AS metric," + product + ' AS product_key,' + location +
            ' AS location_key,%s::text AS equality_profile,count(*)::bigint AS occurrence_count ' +
            relation + ' GROUP BY 2,3'), [metric, profile, *params]
    git, gp = relations['git']; master, mp = relations['master']
    for direction, owner in (('parent', 'WhCode'), ('child', 'ParentWhCode')):
        relation = ('FROM ('+git+') H JOIN ('+master+') A ON '
            'A.rationed_ordinal=H.rationed_ordinal AND A.standard_ordinal=H.standard_ordinal '
            'WHERE H.grid_eligible')
        yield grouped('git_'+direction, relation, [*gp,*mp], 'A."SKUCode"', 'A."'+owner+'"')
    expedite, ep = relations['expedite']
    eligible = "H.direction='child' AND H.branch='dispatch' AND " + ' AND '.join(
        'H.'+name+' IS NOT NULL' for name in ('standard_ordinal','sku_description_ordinal',
        'location_description_ordinal','sku_ordinal','location_ordinal','pair_ordinal'))
    eligible += " AND lower(rtrim(A.\"PipelineInventoryColor\"::text,' ')) IN ('red','black')"
    for direction, owner in (('parent','WhCode'),('child','ParentWhCode')):
        relation = ('FROM ('+expedite+') H JOIN mta.fresh_mta_expediterow A '
            'ON A.run_id=H.run_id AND A.ordinal=H.fact_ordinal WHERE '+eligible)
        yield grouped('expedite_'+direction,relation,ep,'A."SKUCode"','A."'+owner+'"')
    for family, table in (('excess','excessinventoryrow'),('fulfillment','fulfillmentsummaryrow')):
        sql, params = relations[family]
        relation = ('FROM ('+sql+') H JOIN mta.fresh_mta_'+table+
                    ' A ON A.run_id=H.run_id AND A.ordinal=H.fact_ordinal')
        yield grouped(family+'_review',relation,params,'A."SKUCode"','A."WhCode"')
    for family, table, owner, condition in (
        ('expedite','expediterow','ParentWhCode',
         "A.\"RationedQty\">0 AND lower(rtrim(A.\"PipelineInventoryColor\"::text,' ')) IN ('red','black')"),
        ('excess','excessinventoryrow','WhCode','A."ReportDate"=%s'),
        ('fulfillment','fulfillmentsummaryrow','WhCode','TRUE')):
        params=[run.pk]+([run.business_date] if family=='excess' else [])
        yield grouped(family+'_custom','FROM mta.fresh_mta_'+table+
            ' A WHERE A.run_id=%s AND '+condition,params,'A."SKUCode"','A."'+owner+'"')
    if run.kind != 'LEGACY_UI_FIXTURE':
        from mta.presentation.daily_transit import PATH, TRANSPORTER_PATH
        from mta.presentation.selective import image_query
        from mta.presentation.rrr_sql import equal
        a, ap = image_query(run,TRANSPORTER_PATH); t,tp=image_query(run,PATH)
        relation='FROM ('+a+') A JOIN ('+t+') T ON '+equal('A."SKUCode"','T."SKUCode"')+' AND '+equal('A."WhCode"','T."WhCode"')
        yield grouped('git_custom',relation,[*ap,*tp],'A."SKUCode"','A."WhCode"','normalized')


def prepare(run, *, fail_after_rows=False):
    identities, _, relations = binding(run)
    existing=PlanningSummaryReceipt.objects.filter(run=run,**identities).first()
    if existing:
        verify(existing, identities)
        return existing
    attempt=PlanningSummaryAttempt.objects.create(run=run,identity_digest=digest(identities))
    try:
        with transaction.atomic(), connection.cursor() as c:
            c.execute('SELECT pg_advisory_xact_lock(%s)',[int.from_bytes(run.pk.bytes[:8],'big',signed=True)])
            existing=PlanningSummaryReceipt.objects.filter(run=run,**identities).first()
            if existing:
                verify(existing,identities)
                result=existing
            else:
                result=PlanningSummaryReceipt.objects.create(run=run,**identities)
                c.execute("SELECT set_config('fresh.planning_summary_build',%s,true)",[str(result.pk)])
                queries=list(contribution_queries(run,relations))
                sql=' UNION ALL '.join('('+q+')' for q,_ in queries)
                params=[v for _,values in queries for v in values]
                c.execute('INSERT INTO mta.fresh_mta_planningsummarycontribution '
                    '(receipt_id,ordinal,metric,product_key,location_key,equality_profile,occurrence_count) '
                    'SELECT %s,row_number() OVER (ORDER BY metric,product_key NULLS FIRST,location_key NULLS FIRST)-1,'
                    'metric,product_key,location_key,equality_profile,occurrence_count FROM ('+sql+') contributions',
                    [result.pk,*params])
                if fail_after_rows:
                    raise RuntimeError('injected_planning_summary_interruption')
                rows=list(PlanningSummaryContribution.objects.filter(receipt=result).order_by('ordinal').values_list(
                    'metric','product_key','location_key','equality_profile','occurrence_count'))
                result.row_count=len(rows);result.rows_digest=digest(rows)
                result.metrics=list(METRICS);result.status='READY';result.save()
        attempt.status='READY';attempt.completed_at=timezone.now();attempt.save()
        return result
    except Exception as exc:
        attempt.status='FAILED';attempt.error=str(exc)[:2000];attempt.completed_at=timezone.now();attempt.save()
        raise


def verify(receipt, identities):
    if (receipt.status!='READY' or receipt.metrics!=list(METRICS) or
            any(getattr(receipt,k)!=v for k,v in identities.items())):
        raise PublicationUnavailable('planning_summary_generation_unavailable')
    if PlanningSummaryContribution.objects.filter(receipt=receipt).count()!=receipt.row_count:
        raise PublicationUnavailable('planning_summary_row_count_changed')


def admitted(run,payload):
    from mta.presentation.legacy_ui import _no_active_filters
    if not _no_active_filters(payload):
        raise PublicationUnavailable('selected_planning_filters_not_yet_connected')
    identities,attrs,_=binding(run)
    receipt=PlanningSummaryReceipt.objects.filter(run=run,**identities).first()
    if receipt is None:
        raise PublicationUnavailable('planning_summary_generation_unavailable')
    verify(receipt,identities)
    from mta.runtime.planning_summary_schema import verify_guards
    verify_guards(connection)
    return receipt,scope(payload,attributes=attrs)


def identity_value(receipt,payload,actor,resolved):
    return digest(dict(receipt=str(receipt.pk),source=receipt.source_digest,
        generation=receipt.generation_digest,recipe=receipt.recipe_digest,date=str(receipt.business_date),
        actor=actor,scope={n:payload.get(n,[]) for n in ('product_permissions','location_permissions')},
        weights=[sorted(codes.multiplicities.items()) for codes in resolved],
        permissions=getattr(settings,'VF_MTA_PERMISSIONS_SHA256',''),request={'filters':{}}))


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
        raw='P.code=C.product_key AND L.code=C.location_key'
        normalized=equal('P.code','C.product_key')+' AND '+equal('L.code','C.location_key')
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
