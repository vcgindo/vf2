"""Append a canonical BPR batch and publish only its dependent read cut atomically."""
from django.conf import settings
from copy import deepcopy
from dataclasses import replace
from django.db import connection,transaction
from mta.presentation import ancillary_live, bpr_remarks, scoped_selection, scoped_view
from mta.presentation.context import PublicationUnavailable, scope
from mta.presentation.permissions import _sql_equal
from mta.runtime import scoped_remark_ownership
from mta.runtime.models import CalculationRun, RemarkOwner
from mta.runtime.scope_execution import _source_lock
from mta.presentation.request_scope import remark_validation,validation_reads
from mta.serialization import digest


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
    transaction_identity=_transaction_identity()
    view = scoped_selection.selected()
    if str(view.run_id) != anchor['run_id'] or view.bpr.remarks.highwater!=owner.next_ordinal:
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
            current_identity=_transaction_identity()
            if current_identity[0] is not transaction_identity[0] or current_identity[1]!=transaction_identity[1]:
                raise PublicationUnavailable('phase_remark_transaction_changed')
            fresh = _refresh_after_append(view,before=before,highwater=owner.next_ordinal)
            # The ACK follows a full current-reference validation. No independent
            # source preparation, file copying or business calculation occurs.
            current = scoped_selection.selected()
            if current.read_identity != fresh:
                raise PublicationUnavailable('phase_remark_reference_not_current')
    return result


def _transaction_identity():
    if not connection.in_atomic_block or connection.connection is None or connection.connection.closed:
        raise PublicationUnavailable('phase_remark_transaction_required')
    physical=connection.connection
    with connection.cursor() as cursor:
        cursor.execute('SELECT pg_current_xact_id()::text,current_user,session_user')
        return physical,cursor.fetchone()


def _refresh_after_append(view,*,before,highwater):
    """Private command dataflow; the command selects this graph, never its caller."""
    from mta.presentation import scoped_remarks,scoped_expedite_parent,scoped_expedite
    if not isinstance(view,scoped_view.ViewBinding) or highwater<=before or view.bpr.remarks.highwater!=before:
        raise PublicationUnavailable('phase_remark_previous_cut_differs')
    configuration=deepcopy(view.reference.metadata['runtime_reports'])
    request_digest=view.reference.metadata['scope_request_digest']
    original=scoped_view._metadata(view.bpr,view.planning,view.git,view.expedite,
        view.reference.pick_files,configuration,request_digest)
    if original!=view.reference.metadata or digest(original)!=view.reference.digest:
        raise PublicationUnavailable('phase_remark_previous_graph_differs')
    with validation_reads():
        remarks=scoped_remarks.bind(view.bpr.sources,configuration_digest=view.bpr.reports.generation.configuration_digest)
    old=view.bpr.remarks.provenance();new=remarks.provenance()
    if (remarks.highwater!=highwater or
            {k:v for k,v in old.items() if k!='live_highwater'}!={k:v for k,v in new.items() if k!='live_highwater'}):
        raise PublicationUnavailable('phase_remark_prefix_owner_changed')
    parent=scoped_expedite_parent._prepare(view.expedite.core,remarks,
        expected_core_digest=view.expedite.core.generation.digest,action_revision=view.bpr.sources.action_revision)
    expedition=scoped_expedite.require_binding(view.run,replace(view.expedite,parent=parent))
    row,checksum=scoped_view._save_reference(replace(view.bpr,remarks=remarks),view.planning,view.git,expedition,
        view.reference.pick_files,configuration,request_digest)
    # A composed DBM selection keeps its accepted DBM identity while the BPR
    # remark reference advances. The final independent selection verifies both.
    return dict(view.read_identity,id=str(row.pk),digest=checksum)


def history(view, payload):
    products, locations = scope(payload, attributes=view.planning.attributes())
    if not _permitted(payload.get('skucode'), payload.get('whcode'), products, locations): return []
    return bpr_remarks.history(payload, read_binding=view.bpr)
