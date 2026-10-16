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
    """Read native report sources after the existing base publication is sealed."""
    from mta.presentation.daily_publication import require_ready
    if run.kind != 'DAILY_CHAIN' or run.status != 'SUCCEEDED':
        raise PublicationUnavailable('planning_summary_accepted_daily_required')
    publication = require_ready(run)
    from mta.presentation.planning_sources import admitted_sources
    from mta.presentation.planning_git import admitted_git
    from mta.presentation.planning_grids import admitted_grids
    from mta.presentation.planning_expedite_grids import admitted_expedite_grids
    relations = dict(master=admitted_sources(run)['git_master'],
        git=admitted_git(run)['row'], expedite=admitted_expedite_grids(run)['row'],
        **admitted_grids(run))
    from mta.runtime import models
    from mta.presentation.selective import image_metadata
    from mta.presentation.daily_transit import PATH, TRANSPORTER_PATH
    generation=dict(publication=publication.seal_digest,
        dependencies={name:[{k:str(v) if isinstance(v,UUID) else v for k,v in row.items()}
            for row in getattr(models,name).objects.filter(run=run).values()]
            for name in ('PlanningSourceProjection','PlanningGitProjection',
                         'PlanningGridProjection','PlanningExpediteGridProjection')},
        transit={path:image_metadata(run,path) for path in (PATH,TRANSPORTER_PATH)})
    return dict(source_digest=publication.source_digest,generation_digest=digest(generation),
                recipe_digest=recipe_digest(),business_date=run.business_date),None,relations


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


def _prepare(run, *, fail_after_rows=False):
    with transaction.atomic(), connection.cursor() as cursor:
        cursor.execute("SELECT set_config('fresh.daily_publication_build',%s,true)",[str(run.pk)])
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


def prepare(run, *, fail_after_rows=False):
    if str(run.pk) == str(settings.VF_MTA_PUBLISHED_RUN):
        raise PublicationUnavailable('selected_run_cannot_be_prepared')
    return _prepare(run,fail_after_rows=fail_after_rows)


def require_ready(run, *, verify_rows=False):
    identities,_,_=binding(run)
    receipt=PlanningSummaryReceipt.objects.filter(run=run,**identities).first()
    if receipt is None:
        raise PublicationUnavailable('planning_summary_generation_unavailable')
    verify(receipt,identities)
    if verify_rows:
        verify_contribution_rows(receipt)
    from mta.runtime.planning_summary_schema import verify_guards
    verify_guards(connection)
    return receipt


def verify_contribution_rows(receipt):
    """Startup/selection checksum over complete ordered typed summary rows."""
    from mta.serialization import rows_digest
    count = 0
    def rows():
        nonlocal count
        values = PlanningSummaryContribution.objects.filter(receipt=receipt).order_by('ordinal').values_list(
            'ordinal', 'metric', 'product_key', 'location_key', 'equality_profile', 'occurrence_count')
        for ordinal, *row in values.iterator(chunk_size=1000):
            if ordinal != count:
                raise PublicationUnavailable('planning_summary_ordinals_changed')
            count += 1
            yield row
    checksum = rows_digest(rows())
    if count != receipt.row_count or checksum != receipt.rows_digest:
        raise PublicationUnavailable('planning_summary_rows_changed')
