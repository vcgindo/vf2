"""Existing predecessor availability history, with the current request cutoff."""
from dataclasses import dataclass
from django.db import connection
from mta.presentation.request_scope import in_read_request, once_per_request

from mta.presentation import scoped_btr, hierarchy, guided_history_prepared
from mta.presentation.context import PublicationUnavailable


KINDS = frozenset(('availability-trend', 'availability-ageing'))


@dataclass(frozen=True)
class AvailabilityBinding:
    view: object
    btr: scoped_btr.BtrBinding
    receipt: object
    aggregate: dict | None = None

    @property
    def run(self): return self.view.run

    def attributes(self):
        return {name:self.btr.rows('closing/btr/'+name)
                for name in ('SkuAttributeData','LocationAttributeData')}

    def read(self, cutoff, predicate, products, locations, kind, *, minimum_age, payload):
        if kind not in KINDS:
            raise PublicationUnavailable('scoped_availability_kind_required')
        # The existing reader checks the actual predecessor source, immutable
        # prepared receipt and guards. Its optional rollup retains live scope
        # checks. The current date supplies cutoff; it never changes ownership.
        rows = guided_history_prepared.read_prepared(self.btr.predecessor, cutoff,
            predicate, products, locations, kind, minimum_age=minimum_age, payload=payload, read_binding=self)
        if rows is None:
            raise PublicationUnavailable('scoped_availability_predecessor_not_prepared')
        return rows


def bind(view):
    from mta.presentation.registered_report_view import applicable_reference
    if not applicable_reference(view.reference):
        raise PublicationUnavailable('selected_availability_registered_view_required')
    btr = scoped_btr.bind(view)
    if btr.run.pk != view.run_id:
        raise PublicationUnavailable('availability_scoped_run_differs')
    try:
        if hierarchy.selected_manifest(view.run) or hierarchy.selected_manifest(btr.predecessor):
            raise PublicationUnavailable('scoped_availability_hierarchy_not_bound')
    except hierarchy.HierarchyUnavailable as error:
        raise PublicationUnavailable(str(error)) from error
    receipt=require_owner(btr.predecessor)
    # The optional rollup is a separate owner. Validate it before response
    # cache hits too; absent rollups keep the original occurrence-reader path.
    from mta.presentation.guided_aggregates import source_binding, compatible_recipe
    from mta.runtime.models import ReportAggregateReceipt
    from mta.runtime.report_aggregate_schema import verify_guards
    row=ReportAggregateReceipt.objects.filter(run=btr.predecessor).first()
    aggregate=None
    if row is not None:
        if row.source_digest!=source_binding(btr.predecessor) or not compatible_recipe(row.recipe_digest):
            raise PublicationUnavailable('Guided_aggregate_receipt_changed')
        verify_guards(connection)
        aggregate=dict(source=row.source_digest,recipe=row.recipe_digest,
            rows=row.rows_digest,members=row.members_digest)
    return AvailabilityBinding(view,btr,receipt,aggregate)


def _require_owner(run):
    # Missing history must not be reported as an empty permitted population.
    # Authenticate this inherited family even when the caller has zero grants.
    from mta.presentation.daily_preparation import source_digest, production_branch
    from mta.presentation.guided_history_fields import schema_digest
    from mta.runtime.guided_history_schema import verify_guards
    from mta.runtime.models import GuidedHistoryPreparedProjection
    if not production_branch(run):
        raise PublicationUnavailable('scoped_availability_predecessor_not_prepared')
    receipt = GuidedHistoryPreparedProjection.objects.filter(run=run,family='availability').first()
    if (receipt is None or receipt.source_digest != source_digest(run)
            or receipt.schema_digest != schema_digest()):
        raise PublicationUnavailable('scoped_availability_history_receipt_differs')
    try: verify_guards(connection)
    except ValueError as error:
        raise PublicationUnavailable('scoped_availability_history_guards_differ') from error
    return receipt


@once_per_request
def _request_owner(run, physical, stamp):
    return _require_owner(run)


def require_owner(run):
    """Reuse only within an active request and identical live DB/role cut."""
    from mta.presentation.identity_reuse import stamp
    if not in_read_request(): return _require_owner(run)
    before=stamp()
    physical=connection.connection
    if before is None or physical is None: return _require_owner(run)
    receipt=_request_owner(run,physical,before)
    if connection.connection is physical and stamp()==before: return receipt
    return _require_owner(run)
