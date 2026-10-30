from mta.presentation.native_mode import removed_mode
"""Prepared parent Expedite transit reads; eligibility stays request-scoped."""
from django.db import connection
from mta.presentation.context import PublicationUnavailable
from mta.presentation.planning_expedite_transit_preparation import pick_binding, recipe_digest, production_recipe_digest, RETAINED_PRODUCTION_RECIPE
from mta.runtime.models import PlanningExpediteTransitProjection
from mta.runtime.planning_expedite_transit_schema import verify_guards


def admit(run):
    from mta.presentation.daily_preparation import production_branch
    daily = production_branch(run)
    if daily:
        from mta.presentation.daily_preparation import source_digest
        selected, source = (run, source_digest(run))
    else:
        selected, source = removed_mode('historical_fixture')
        raise PublicationUnavailable('planning_expedite_transit_wrong_fixture')
    receipt = PlanningExpediteTransitProjection.objects.filter(run=run).first()
    recipe = production_recipe_digest() if daily else recipe_digest()
    accepted = (recipe, RETAINED_PRODUCTION_RECIPE) if daily else (recipe,)
    if receipt is None or receipt.source_digest != source or receipt.recipe_digest not in accepted or (receipt.pick_digest != pick_binding(run)):
        raise PublicationUnavailable('planning_expedite_transit_receipt_missing_or_changed')
    try:
        verify_guards(connection)
    except ValueError as exc:
        raise PublicationUnavailable('planning_expedite_transit_guards_changed') from exc


def transit_query(run, branch, eligible_sql, eligible_params,*,read_binding=None):
    """Private caller supplies an ordinal relation for the FULL filtered parent CTE.

    It must precede pagination. Scope multiplicity collapses in the canonical
    GROUP BY. No business-key joins or source reconstruction occur on this read.
    """
    if branch not in ('dispatch','availability'):
        raise ValueError('Unknown parent Expedite transit branch')
    join = 'LEFT JOIN' if branch == 'dispatch' else 'JOIN'
    if read_binding is not None:
        from mta.presentation.scoped_expedite import require_binding
        bound=require_binding(run,read_binding)
        matches,mp=bound.parent.query('match');base,bp=bound.parent.query('base')
        query=('WITH eligible AS ('+eligible_sql+'), matches AS ('
            'SELECT M.base_ordinal,M.parent_stock FROM ('+matches+') M '
            'JOIN eligible E ON E.ordinal=M.grid_ordinal WHERE M.branch=%s), '
            'grouped AS (SELECT DISTINCT ON (B.sku_key,B.location_key,B.rlt,B.remark_key,M.parent_stock) '
            'B.sku_code AS skucode,B.location_code AS whcode,M.parent_stock AS slt,B.rlt AS eta,'
            "COALESCE(B.remark,' ') AS remarks FROM ("+base+') B '+join+' matches M ON M.base_ordinal=B.ordinal '
            'WHERE B.run_id=%s ORDER BY B.sku_key,B.location_key,B.rlt,B.remark_key,M.parent_stock,B.ordinal) SELECT * FROM grouped')
        return query,[*eligible_params,*mp,branch,*bp,run.pk]
    admit(run)
    query = ('WITH eligible AS ('+eligible_sql+'), matches AS ('
        'SELECT M.base_ordinal,M.parent_stock FROM mta.fresh_mta_planningexpeditetransitmatch M '
        'JOIN eligible E ON E.ordinal=M.grid_ordinal WHERE M.run_id=%s AND M.branch=%s), '
        'grouped AS (SELECT DISTINCT ON (B.sku_key,B.location_key,B.rlt,B.remark_key,M.parent_stock) '
        'B.sku_code AS skucode,B.location_code AS whcode,M.parent_stock AS slt,B.rlt AS eta,'
        "COALESCE(B.remark,' ') AS remarks FROM mta.fresh_mta_planningexpeditetransitbase B "
        +join+' matches M ON M.base_ordinal=B.ordinal WHERE B.run_id=%s '
        'ORDER BY B.sku_key,B.location_key,B.rlt,B.remark_key,M.parent_stock,B.ordinal) SELECT * FROM grouped')
    return query,[*eligible_params,run.pk,branch,run.pk]


def transit_rows(run, branch, eligible_sql, eligible_params,*,read_binding=None):
    query, params = transit_query(run,branch,eligible_sql,eligible_params,read_binding=read_binding)
    with connection.cursor() as c:
        c.execute(query,params)
        names = [column[0] for column in c.description]
        return [{name:str(value) for name,value in zip(names,row) if value is not None} for row in c.fetchall()]
