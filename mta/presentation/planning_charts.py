"""Admitted typed Planning chart ingredients; no request-time source reconstruction."""
from django.db import connection

from mta.presentation import fixture
from mta.presentation.context import PublicationUnavailable
from mta.presentation.planning_chart_preparation import recipe_digest, production_recipe_digest
from mta.runtime.models import PlanningChartMember, PlanningChartDisplay, PlanningChartProjection
from mta.runtime.planning_chart_schema import verify_guards
from mta.runtime.relational_state import quote


def admitted_charts(run):
    """Resolve one request's source binding using the established sealed-read rule.

    Full checksum traversal belongs to preparation/readback verification. Serving
    reads verify immutable guards and the recipe/source receipt, as the existing
    BPR prepared reader does. Permission/filter decisions remain with consumers.
    """
    from mta.presentation.daily_preparation import production_branch
    daily = production_branch(run)
    if daily:
        from mta.presentation.daily_preparation import source_digest
        source = source_digest(run)
    else:
        selected, source = fixture.binding()
        if (getattr(run, 'kind', None) != 'LEGACY_UI_FIXTURE' or selected.pk != run.pk
                or str(run.business_date) != '2026-04-07'):
            raise PublicationUnavailable('planning_charts_wrong_fixture')
    receipt = PlanningChartProjection.objects.filter(run_id=run.pk).first()
    recipe = production_recipe_digest() if daily else recipe_digest()
    if receipt is None or receipt.source_digest != source or receipt.recipe_digest != recipe:
        raise PublicationUnavailable('planning_charts_receipt_missing_or_changed')
    try:
        verify_guards(connection)
    except ValueError as exc:
        raise PublicationUnavailable('planning_charts_immutable_guards_changed') from exc
    return {
        name: ('SELECT * FROM mta.' + quote(model._meta.db_table) + ' WHERE run_id=%s', [run.pk])
        for name, model in (('members', PlanningChartMember), ('displays', PlanningChartDisplay))
    }
