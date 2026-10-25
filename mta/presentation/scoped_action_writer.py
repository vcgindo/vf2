"""Canonical paused-phase action and its BPR read dependencies commit together."""
from collections import Counter
from uuid import uuid4

from django.conf import settings
from django.db import transaction

from mta.presentation import actions, scoped_selection, scoped_dbm, scoped_view, scoped_dbm_view
from mta.presentation.context import PublicationUnavailable, scope
from mta.runtime import scoped_actions, scoped_action_ownership
from mta.runtime.models import CalculationRun, OperationalAcceptance, RemarkOwner
from mta.runtime.scope_execution import _source_lock
from mta.temporal.actions import key
from mta.presentation.request_scope import remark_validation, validation_reads


@transaction.atomic
def submit(payload, actor, operation):
    if not settings.VF_MTA_ACTIONS_ENABLED:
        raise actions.ActionDenied('demo_read_only')
    if operation not in ('APPLY','SLEEP'):
        raise ValueError('Unknown scoped action')
    selected = actions.selected_pairs(payload)
    anchor = scoped_selection.read(settings.VF_MTA_PHASE_SELECTION_FILE)
    _source_lock(anchor['run_id'])
    CalculationRun.objects.select_for_update().get(pk=anchor['run_id'])
    RemarkOwner.objects.select_for_update().get(pk='BPRReport_RemarkDetails')
    # Reuse the existing locked-writer validation lifetime. The marker creates
    # no cache across writes; each validated_read opens its own SELECT-only
    # traversal. The final selected() below is a fresh independent traversal.
    with remark_validation():
        return _submit_locked(payload,actor,operation,selected,anchor)


def _submit_locked(payload,actor,operation,selected,anchor):
    with validation_reads():
        view = scoped_selection.selected()
        if str(view.run_id)!=anchor['run_id']:
            raise PublicationUnavailable('phase_action_selection_changed')
        context = view.dbm_context if isinstance(view,scoped_dbm_view.DbmViewBinding) else scoped_dbm.bind(view.bpr.sources.acceptance_id,
            expected_digest=view.bpr.sources.acceptance_digest, action_revision=view.bpr.sources.action_revision)
        if OperationalAcceptance.objects.filter(run_id=context.run.pk).exists():
            raise actions.ActionDenied('operational_acceptance_sealed')
        products, locations = scope(payload, attributes=context.dbm)
        if any(sku not in products or location not in locations for sku,location in selected):
            raise actions.ActionDenied('selected_pair_outside_authenticated_scope')
    # Preserve the existing HTTP response's canonical affected-row arithmetic.
    chosen = set(selected)
    suggestions = [row for row in context.dbm['Suggestions'] if key(row) in chosen]
    if operation=='APPLY':
        keys = {key(row) for row in suggestions}
        masters = Counter(key(row) for row in context.dbm['DBMMaster'])
        affected = sum(key(row) in keys for row in context.dbm['NormAcceptanceTbl'])
        affected += sum(masters[key(row)] for row in suggestions)
    else:
        affected = 2*len(suggestions)
    scoped_action_ownership.verify_guards()
    action_phase = view.dbm_phase if isinstance(view,scoped_dbm_view.DbmViewBinding) else None
    with scoped_action_ownership.publication(view.reference.pk, actor):
        event = scoped_actions.record(context.run.pk,
            phase_id=action_phase.pk if action_phase else view.bpr.sources.acceptance_id,
            phase_digest=action_phase.digest if action_phase else view.bpr.sources.acceptance_digest,
            expected_revision=view.bpr.sources.action_revision, operation=operation,
            selected=[list(pair) for pair in selected], timestamp=actions.timestamp(),
            actor=str(actor), idempotency_key='http-'+str(uuid4()))
        fresh = scoped_view.prepare(view.bpr.sources.acceptance_id,
            expected_digest=view.bpr.sources.acceptance_digest, action_revision=event.pk)
        if isinstance(view,scoped_dbm_view.DbmViewBinding):
            fresh = scoped_dbm_view.compose(fresh,view.dbm_phase.pk,expected_digest=view.dbm_phase.digest)
        # A stale/missing/ambiguous view aborts the command and every dependent
        # generation. The old accepted reference remains available on rollback.
        current = scoped_selection.selected()
        if current.read_identity!=fresh.read_identity:
            raise PublicationUnavailable('phase_action_reference_not_current')
    return event, dict(data='' if operation=='APPLY' else None,
        message='Saved Succesfully' if affected else None)
