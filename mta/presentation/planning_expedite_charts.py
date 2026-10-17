from mta.presentation.native_mode import removed_mode
"""Admission for source-bound prepared Expedite chart membership."""
from django.db import connection
from mta.presentation.context import PublicationUnavailable
from mta.presentation.planning_expedite_transit_preparation import pick_binding
from mta.presentation.planning_expedite_chart_preparation import recipe_digest,production_recipe_digest
from mta.runtime.models import PlanningExpediteChartProjection
from mta.runtime.planning_expedite_chart_schema import verify_guards


def admit(run):
    from mta.presentation.daily_preparation import production_branch
    daily = production_branch(run)
    if daily:
        from mta.presentation.daily_preparation import source_digest
        selected, source = (run, source_digest(run))
    else:
        selected, source = removed_mode('historical_fixture')
        raise PublicationUnavailable('planning_expedite_chart_wrong_fixture')
    receipt = PlanningExpediteChartProjection.objects.filter(run=run).first()
    recipe = production_recipe_digest() if daily else recipe_digest()
    if receipt is None or receipt.source_digest != source or receipt.recipe_digest != recipe or (receipt.pick_digest != pick_binding(run)):
        raise PublicationUnavailable('planning_expedite_chart_receipt_missing_or_changed')
    try:
        verify_guards(connection)
    except ValueError as exc:
        raise PublicationUnavailable('planning_expedite_chart_guards_changed') from exc
