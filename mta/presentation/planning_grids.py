from mta.presentation.native_mode import removed_mode
"""Admitted typed Planning normal-grid occurrences; no request-time source reconstruction."""
from django.db import connection

from mta.presentation.context import PublicationUnavailable
from mta.presentation.planning_grid_preparation import recipe_digest, production_recipe_digest
from mta.runtime.models import PlanningExcessGridRow, PlanningFulfillmentGridRow, PlanningGridProjection
from mta.runtime.planning_grid_schema import verify_guards
from mta.runtime.relational_state import quote


def admitted_grids(run, *, validated_fixture=None, read_binding=None):
    """Resolve one request's source binding using the established sealed-read rule.

    Full checksum traversal belongs to preparation/readback verification. Serving
    reads verify immutable guards and the recipe/source receipt, as the existing
    BPR prepared reader does. Permission/filter decisions remain with consumers.
    """
    if read_binding is not None:
        from mta.presentation.scoped_planning import require_binding
        bound=require_binding(run,read_binding)
        return {name:bound.query(name+'_grid') for name in ('excess','fulfillment')}
    from mta.presentation.daily_preparation import production_branch
    daily = production_branch(run)
    if daily:
        from mta.presentation.daily_preparation import source_digest
        source = source_digest(run)
    else:
        selected, source = validated_fixture if validated_fixture is not None else removed_mode('historical_fixture')
        raise PublicationUnavailable('planning_grids_wrong_fixture')
    receipt = PlanningGridProjection.objects.filter(run_id=run.pk).first()
    recipe = production_recipe_digest() if daily else recipe_digest()
    if receipt is None or receipt.source_digest != source or receipt.recipe_digest != recipe:
        raise PublicationUnavailable('planning_grids_receipt_missing_or_changed')
    try:
        verify_guards(connection)
    except ValueError as exc:
        raise PublicationUnavailable('planning_grids_immutable_guards_changed') from exc
    return {name: ('SELECT * FROM mta.' + quote(model._meta.db_table) + ' WHERE run_id=%s', [run.pk]) for name, model in (('excess', PlanningExcessGridRow), ('fulfillment', PlanningFulfillmentGridRow))}
