"""Append a canonical BPR batch and publish only its dependent read cut atomically."""
from django.conf import settings
from django.db import transaction
from mta.presentation import ancillary_live, bpr_remarks, scoped_selection, scoped_view
from mta.presentation.context import PublicationUnavailable, scope
from mta.presentation.permissions import _sql_equal
from mta.runtime import scoped_remark_ownership
from mta.runtime.models import CalculationRun, RemarkOwner
from mta.runtime.scope_execution import _source_lock
from mta.presentation.request_scope import remark_validation


class RemarkDenied(ValueError):
    pass


def _permitted(sku, location, products, locations):
    return (any(_sql_equal(sku, code) for code in products)
        and any(_sql_equal(location, code) for code in locations))


@transaction.atomic
def append(payload, actor):
    # Source mutation/execution use this same lock order. Select again after all
    # locks: another successful append may have changed the global remark cut.
    anchor = scoped_selection.read(settings.VF_MTA_PHASE_SELECTION_FILE)
    _source_lock(anchor['run_id'])
    CalculationRun.objects.select_for_update().get(pk=anchor['run_id'])
    owner = RemarkOwner.objects.select_for_update().get(pk=ancillary_live.BPR)
    with remark_validation():
        return _append_locked(payload, actor, anchor, owner)


def _append_locked(payload, actor, anchor, owner):
    view = scoped_selection.selected()
    if str(view.run_id) != anchor['run_id']:
        raise PublicationUnavailable('phase_remark_selection_changed')
    scoped_remark_ownership.verify_guards()
    products, locations = scope(payload, attributes=view.planning.attributes())
    def validate(rows):
        if any(not _permitted(row['SKUCode'], row['WhCode'], products, locations) for row in rows):
            raise RemarkDenied('selected_BPR_remark_scope_denied')
    before = owner.next_ordinal
    with scoped_remark_ownership.publication(view.reference.pk, actor['id']):
        result = bpr_remarks.append(payload, actor, read_binding=view.bpr, validate_rows=validate)
        owner.refresh_from_db(fields=['next_ordinal'])
        if owner.next_ordinal != before:
            fresh = scoped_view.refresh_parent(view.reference.pk, expected_digest=view.reference.digest)
            # The ACK follows a full current-reference validation. No independent
            # source preparation, file copying or business calculation occurs.
            current = scoped_selection.selected()
            if current.read_identity != fresh.read_identity:
                raise PublicationUnavailable('phase_remark_reference_not_current')
    return result


def history(view, payload):
    products, locations = scope(payload, attributes=view.planning.attributes())
    if not _permitted(payload.get('skucode'), payload.get('whcode'), products, locations): return []
    return bpr_remarks.history(payload, read_binding=view.bpr)
