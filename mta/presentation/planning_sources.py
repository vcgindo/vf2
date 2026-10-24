from mta.presentation.native_mode import removed_mode
"""Admitted typed Planning masters; no request-time source reconstruction."""
from django.db import connection

from mta.presentation.context import PublicationUnavailable
from mta.presentation.planning_source_sql import recipe_digest
from mta.runtime.models import PlanningBprMasterRow, PlanningGitMasterRow, PlanningSourceProjection
from mta.runtime.planning_source_schema import verify_guards
from mta.runtime.relational_state import quote


def admitted_sources(run, *, validated_fixture=None, read_binding=None):
    """Resolve one request's source binding using the established sealed-read rule.

    Full checksum traversal belongs to preparation/readback verification. Serving
    reads verify immutable guards and the recipe/source receipt, as the existing
    BPR prepared reader does. Permission/filter decisions remain with consumers.
    """
    if read_binding is not None:
        from mta.presentation.scoped_prepared import PreparedBinding
        if not isinstance(read_binding,PreparedBinding) or read_binding.run_id!=run.pk:
            raise PublicationUnavailable('planning_sources_phase_owner_differs')
        return {name:read_binding.query(name) for name in ('bpr_master','git_master')}
    from mta.presentation.daily_preparation import production_branch
    if production_branch(run):
        from mta.presentation.daily_preparation import source_digest
        source = source_digest(run)
    else:
        selected, source = validated_fixture if validated_fixture is not None else removed_mode('historical_fixture')
        raise PublicationUnavailable('planning_sources_wrong_fixture')
    receipt = PlanningSourceProjection.objects.filter(run_id=run.pk).first()
    if receipt is None or receipt.source_digest != source or receipt.recipe_digest != recipe_digest():
        raise PublicationUnavailable('planning_sources_receipt_missing_or_changed')
    try:
        verify_guards(connection)
    except ValueError as exc:
        raise PublicationUnavailable('planning_sources_immutable_guards_changed') from exc
    return {name: ('SELECT * FROM mta.' + quote(model._meta.db_table) + ' WHERE run_id=%s', [run.pk]) for name, model in (('bpr_master', PlanningBprMasterRow), ('git_master', PlanningGitMasterRow))}
