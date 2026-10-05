"""Admission for source-bound prepared Expedite chart membership."""
from django.db import connection
from mta.presentation import fixture
from mta.presentation.context import PublicationUnavailable
from mta.presentation.planning_expedite_transit_preparation import pick_source
from mta.presentation.planning_expedite_chart_preparation import recipe_digest
from mta.runtime.models import PlanningExpediteChartProjection
from mta.runtime.planning_expedite_chart_schema import verify_guards


def admit(run):
    selected, source = fixture.binding()
    if (selected.pk != run.pk or getattr(run,'kind',None) != 'LEGACY_UI_FIXTURE'
            or str(run.business_date) != '2026-04-07'):
        raise PublicationUnavailable('planning_expedite_chart_wrong_fixture')
    receipt = PlanningExpediteChartProjection.objects.filter(run=run).first()
    if (receipt is None or receipt.source_digest != source or receipt.recipe_digest != recipe_digest()
            or receipt.pick_digest != pick_source()):
        raise PublicationUnavailable('planning_expedite_chart_receipt_missing_or_changed')
    try:
        verify_guards(connection)
    except ValueError as exc:
        raise PublicationUnavailable('planning_expedite_chart_guards_changed') from exc
