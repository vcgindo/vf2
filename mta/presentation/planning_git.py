"""Admitted typed Planning normal-grid occurrences; no request-time source reconstruction."""
from django.db import connection

from mta.presentation import fixture
from mta.presentation.context import PublicationUnavailable
from mta.presentation.planning_git_preparation import recipe_digest,production_recipe_digest
from mta.runtime.models import PlanningGitOccurrence, PlanningGitProjection
from mta.runtime.planning_git_schema import verify_guards
from mta.runtime.relational_state import quote


def admitted_git(run, *, validated_fixture=None):
    """Resolve one request's source binding using the established sealed-read rule.

    Full checksum traversal belongs to preparation/readback verification. Serving
    reads verify immutable guards and the recipe/source receipt, as the existing
    BPR prepared reader does. Permission/filter decisions remain with consumers.
    """
    from mta.presentation.daily_preparation import production_branch
    daily = production_branch(run)
    if daily:
        from mta.presentation.daily_preparation import source_digest
        selected,source=run,source_digest(run)
    else:
        selected, source = validated_fixture if validated_fixture is not None else fixture.binding()
        if (getattr(run, 'kind', None) != 'LEGACY_UI_FIXTURE' or selected.pk != run.pk
                or str(run.business_date) != '2026-04-07'):
            raise PublicationUnavailable('planning_git_wrong_fixture')
    receipt = PlanningGitProjection.objects.filter(run_id=run.pk).first()
    recipe=production_recipe_digest() if daily else recipe_digest()
    if receipt is None or receipt.source_digest != source or receipt.recipe_digest != recipe:
        raise PublicationUnavailable('planning_git_receipt_missing_or_changed')
    try:
        verify_guards(connection)
    except ValueError as exc:
        raise PublicationUnavailable('planning_git_immutable_guards_changed') from exc
    return {
        name: ('SELECT * FROM mta.' + quote(model._meta.db_table) + ' WHERE run_id=%s', [run.pk])
        for name, model in (('row', PlanningGitOccurrence),)
    }
