"""Private scoped continuation through the existing Full atomic publisher."""
from copy import deepcopy
from django.db import connection,transaction
from django.utils import timezone
from mta.serialization import digest
from mta.runtime import phase_state,scope_revisions
from mta.runtime.scope_execution import (require_claim,head,receipt_digest,_setting,
    _begin_phase,_seal_day_final,_close_attempt)


def require_pending_final(run,*,receipt_id=None):
    if not connection.in_atomic_block:raise ValueError('Scoped final requires its transaction')
    with connection.cursor() as cursor:
        cursor.execute("SELECT mta.pending_day_final(%s),current_setting('fresh.scope_phase',true)",[run.pk])
        pending,phase_id=cursor.fetchone()
        if not pending or receipt_id is not None and phase_id!=str(receipt_id):
            raise ValueError('Scoped final requires its exact pending owner')


def accepted_prefix(run):
    from mta.runtime.models import RunPhaseAcceptance
    from mta.runtime.mdm_daily_models import MdmDailyInputCapture
    from mta.runtime.prepared_effects import SCHEMA as PREPARED
    from mta.runtime.calculation_effects import SCHEMA as CALCULATION
    capture=MdmDailyInputCapture.objects.select_for_update().get(run=run)
    result=[];parent_image=None;parent_digest=None;recipe=phase_state.recipe_digest()
    for phase in ('PRE_BPR','BPR','DBM'):
        receipt=RunPhaseAcceptance.objects.select_related('snapshot','attempt').get(run=run,phase=phase)
        image=receipt.snapshot;effects=receipt.metadata.get('effects',{})
        if (not receipt.state_sealed or receipt.digest!=receipt_digest(receipt)
                or receipt.source_id!=capture.source_id or receipt.input_digest!=run.input_digest
                or receipt.capture_digest!=capture.revision_digest or image is None
                or image.run_id!=run.pk or image.phase!=phase or image.acceptance_id!=receipt.pk
                or image.parent_id!=parent_image or image.input_digest!=run.input_digest
                or image.recipe_digest!=recipe
                or image.state_digest!=digest(image.manifest)
                or receipt.metadata.get('snapshot_digest')!=image.state_digest
                or receipt.metadata.get('compatibility_digest')!=receipt.attempt.compatibility_digest
                or effects.get('schema')!=(PREPARED if phase=='PRE_BPR' else CALCULATION)
                or receipt.metadata.get('effect_digest')!=digest(effects)
                or phase!='PRE_BPR' and effects.get('parent_acceptance_digest')!=parent_digest):
            raise ValueError('Scoped final accepted business prefix differs')
        result.append(receipt);parent_image=image.pk;parent_digest=receipt.digest
    if head(run.pk)!=('DBM',parent_digest):raise ValueError('Scoped final requires its DBM head')
    return result,capture


def require_final_sources(run,receipt,sources):
    from mta.application.stage_calculation_sources import CalculationSources
    from mta.runtime.models import RunPhaseAcceptance
    require_pending_final(run,receipt_id=receipt.pk)
    receipt=RunPhaseAcceptance.objects.get(pk=receipt.pk,run=run,phase='DAY_FINAL',
                                         state_sealed=False,snapshot__isnull=True)
    scope_revisions.verify_write(run,scope_revisions.next_cut(receipt.revision_before))
    prefix,capture=accepted_prefix(run)
    manifest=prefix[-1].snapshot.manifest
    if type(sources) is not CalculationSources or sources.calculation_digest!=manifest['metadata']['calculation_digest']:
        raise ValueError('Scoped final calculation identity differs')
    def check(expected,actual):
        if expected is None:return actual is None
        if set(expected)=={'image'}:
            image=manifest['images'][expected['image']]
            return isinstance(actual,list) and len(actual)==image['count'] and digest(actual)==image['digest']
        return (isinstance(actual,dict) and set(expected)==set(actual)
                and all(check(value,actual[key]) for key,value in expected.items()))
    actual={key:getattr(sources,key) for key in ('pick_bands','routes','operational','production_reports')}
    if not check(manifest['consumers'],actual):raise ValueError('Scoped final finite consumers differ')
    return scope_revisions.identity(run)


def consume_accepted(run):
    """PRE effects already committed; never re-lock their removed queue rows."""
    require_pending_final(run)
    _prefix,capture=accepted_prefix(run)
    if capture.status!='CAPTURED':raise ValueError('Scoped final capture is already consumed')
    from mta.mdm.daily_input import _consume_capture
    # Ordinary Full retains this marker through its remaining publication and
    # audit receipts. Scoped Full has the same owner; only current-copy writes
    # temporarily leave the PRE effect context in daily_current.publish.
    with connection.cursor() as cursor:
        cursor.execute("SELECT set_config('fresh.mdm_consuming_run',%s,true)",[str(run.pk)])
    _consume_capture(capture,timezone.now())


def frozen_prior(run,raw):
    """Reconstruct native dependencies from their own retained opening only."""
    initial=raw['opening']
    if raw.get('initialization_binding') is None:
        return deepcopy(initial['state'])
    parent=run.predecessor
    if parent is None:
        prior=deepcopy(initial['state'])
    else:
        from mta.runtime.services import read_outputs
        from mta.runtime.temporal import command_states
        if initial is not None or raw['lineage'].get('run_id')!=str(parent.pk):
            raise ValueError('Scoped native predecessor opening differs')
        prior=deepcopy(read_outputs(parent,include_reports=False)['ClosingState'][0])
        prior,commands=command_states(parent,prior,through_date=run.business_date)
        if (raw['lineage'].get('output_digest')!=parent.output_digest
                or raw['lineage'].get('commands')!=commands):
            raise ValueError('Scoped native predecessor action revision differs')
    # This is the existing frozen overlay, never a live queue/source read.
    from mta.runtime.captured_recovery import _restore_working
    _restore_working(raw['mdm_input'],prior,raw['day'],parent)
    return prior


def _finish_accepted_day(attempt_id,worker_token,*,compatibility_digest,master_snapshot=None):
    """BTR may retry; accepted PRE/BPR/DBM calculations/effects never replay."""
    from mta.runtime.input_reader import read_input
    from mta.temporal.chain import produce_btr_from_snapshot
    from mta.runtime.temporal import BOUNDARIES
    from mta.application.native_output_contracts import native_assignments
    from mta.runtime.services import finish_run
    with transaction.atomic():
        _attempt,run=require_claim(attempt_id,worker_token,compatibility_digest=compatibility_digest)
        prefix,_capture=accepted_prefix(run)
        dbm=prefix[-1]
    raw=read_input(run,components=('opening','day','profile','lineage','initialization_binding','mdm_input'))
    profile=raw['profile']
    if type(profile.get('daily_publication')) is not bool:
        raise ValueError('Scoped final publication mode must be captured explicitly')
    if raw.get('initialization_binding') is not None:
        frozen=raw['mdm_input']
        if master_snapshot is not None and digest(master_snapshot)!=digest(frozen):
            raise ValueError('Scoped native frozen master snapshot differs')
        master_snapshot=frozen
    phase,sources=phase_state.read(dbm.snapshot,prior=frozen_prior(run,raw),day=raw['day'],
        profile=profile,master_snapshot=master_snapshot)
    from mta.runtime.scoped_actions import final_phase
    phase=final_phase(run,dbm,phase,expected_revision=_attempt.action_revision)
    with native_assignments(True):
        result=produce_btr_from_snapshot(phase,sources,pick_source_digests=phase.pick_source_digests)
    output=result.output
    if output.pop('_CompletedBoundaries')!=list(BOUNDARIES):
        raise ValueError('Incomplete scoped daily boundary roster')
    lineage=deepcopy(raw['lineage'])
    if _attempt.action_revision:
        from mta.runtime.models import RunCommand
        lineage['scope_actions']=[dict(id=event.pk,digest=event.digest,
            phase_acceptance_id=str(event.phase_acceptance_id),after=event.after_digest)
            for event in RunCommand.objects.filter(run=run,phase_acceptance__isnull=False,
                state_sealed=True).order_by('id')]
    lineage['cohort1']=output.pop('_Cohort1')
    source_digests=output.pop('_PickSourceDigests',None)
    if source_digests is not None:lineage['pick_source_digests']=source_digests
    output['Lineage']=[lineage]
    publication=None
    if profile['daily_publication']:
        publication=dict(supplier=phase.context.prior['supplier'])
        for name in ('shipment_input','transporter_input','production_report_policy',
                     'production_report_opening','production_report_schema'):
            if name in raw['day']:publication[name]=raw['day'][name]
    elif sources.production_reports is not None:
        raise ValueError('Configured scoped reports require publication')
    with transaction.atomic(),_setting('fresh.scope_worker',worker_token), \
            _setting('fresh.mdm_consuming_run',''):
        attempt,run=require_claim(attempt_id,worker_token,compatibility_digest=compatibility_digest)
        if head(run.pk)!=('DBM',dbm.digest):raise ValueError('Scoped DBM head changed during BTR')
        receipt=_begin_phase(attempt,run,'DAY_FINAL')
        finished=finish_run(run,result,expected_digest=run.input_digest,
                            publication_opening=publication,_scoped_unit=receipt)
        _seal_day_final(receipt)
        _close_attempt(attempt,finished,'RELEASED',{})
        return finished
