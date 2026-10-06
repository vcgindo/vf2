"""Admitted typed Planning masters; no request-time source reconstruction."""
from django.db import connection

from mta.presentation import fixture
from mta.presentation.context import PublicationUnavailable
from mta.presentation.planning_source_sql import recipe_digest
from mta.runtime.models import PlanningBprMasterRow, PlanningGitMasterRow, PlanningSourceProjection
from mta.runtime.planning_source_schema import verify_guards
from mta.runtime.relational_state import quote


def admitted_sources(run):
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
        selected, source = fixture.binding()
        if (getattr(run, 'kind', None) != 'LEGACY_UI_FIXTURE' or selected.pk != run.pk
                or str(run.business_date) != '2026-04-07'):
            raise PublicationUnavailable('planning_sources_wrong_fixture')
    receipt = PlanningSourceProjection.objects.filter(run_id=run.pk).first()
    if receipt is None or receipt.source_digest != source or receipt.recipe_digest != recipe_digest():
        raise PublicationUnavailable('planning_sources_receipt_missing_or_changed')
    try:
        verify_guards(connection)
    except ValueError as exc:
        raise PublicationUnavailable('planning_sources_immutable_guards_changed') from exc
    return {
        name: ('SELECT * FROM mta.' + quote(model._meta.db_table) + ' WHERE run_id=%s', [run.pk])
        for name, model in (('bpr_master', PlanningBprMasterRow), ('git_master', PlanningGitMasterRow))
    }
