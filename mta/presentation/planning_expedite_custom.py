"""Admitted typed Planning normal-grid occurrences; no request-time source reconstruction."""
from django.db import connection

from mta.presentation import fixture
from mta.presentation.context import PublicationUnavailable
from mta.presentation.planning_expedite_custom_preparation import recipe_digest
from mta.runtime.models import PlanningExpediteCustomOccurrence, PlanningExpediteCustomProjection
from mta.runtime.planning_expedite_custom_schema import verify_guards
from mta.runtime.relational_state import quote


def admitted_expedite_custom(run):
    """Resolve one request's source binding using the established sealed-read rule.

    Full checksum traversal belongs to preparation/readback verification. Serving
    reads verify immutable guards and the recipe/source receipt, as the existing
    BPR prepared reader does. Permission/filter decisions remain with consumers.
    """
    selected, source = fixture.binding()
    if (getattr(run, 'kind', None) != 'LEGACY_UI_FIXTURE' or selected.pk != run.pk
            or str(run.business_date) != '2026-04-07'):
        raise PublicationUnavailable('planning_expedite_custom_wrong_fixture')
    receipt = PlanningExpediteCustomProjection.objects.filter(run_id=run.pk).first()
    if receipt is None or receipt.source_digest != source or receipt.recipe_digest != recipe_digest():
        raise PublicationUnavailable('planning_expedite_custom_receipt_missing_or_changed')
    try:
        verify_guards(connection)
    except ValueError as exc:
        raise PublicationUnavailable('planning_expedite_custom_immutable_guards_changed') from exc
    return {
        name: ('SELECT * FROM mta.' + quote(model._meta.db_table) + ' WHERE run_id=%s', [run.pk])
        for name, model in (('row', PlanningExpediteCustomOccurrence),)
    }
