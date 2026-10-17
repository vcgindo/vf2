from mta.presentation.native_mode import removed_mode
"""Admitted typed Planning normal-grid occurrences; no request-time source reconstruction."""
from django.db import connection

from mta.presentation.context import PublicationUnavailable
from mta.presentation.planning_expedite_preparation import recipe_digest
from mta.runtime.models import PlanningExpediteGridOccurrence, PlanningExpediteGridProjection
from mta.runtime.planning_expedite_grid_schema import verify_guards
from mta.runtime.relational_state import quote


def admitted_expedite_grids(run, *, validated_fixture=None):
    """Resolve one request's source binding using the established sealed-read rule.

    Full checksum traversal belongs to preparation/readback verification. Serving
    reads verify immutable guards and the recipe/source receipt, as the existing
    BPR prepared reader does. Permission/filter decisions remain with consumers.
    """
    from mta.presentation.daily_preparation import production_branch
    if production_branch(run):
        from mta.presentation.daily_preparation import source_digest
        source = source_digest(run)
    else:
        selected, source = validated_fixture if validated_fixture is not None else removed_mode('historical_fixture')
        raise PublicationUnavailable('planning_expedite_grid_wrong_fixture')
    receipt = PlanningExpediteGridProjection.objects.filter(run_id=run.pk).first()
    if receipt is None or receipt.source_digest != source or receipt.recipe_digest != recipe_digest():
        raise PublicationUnavailable('planning_expedite_grid_receipt_missing_or_changed')
    try:
        verify_guards(connection)
    except ValueError as exc:
        raise PublicationUnavailable('planning_expedite_grid_immutable_guards_changed') from exc
    return {name: ('SELECT * FROM mta.' + quote(model._meta.db_table) + ' WHERE run_id=%s', [run.pk]) for name, model in (('row', PlanningExpediteGridOccurrence),)}
