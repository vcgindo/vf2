"""Short-lived, explicitly fenced claims; never infer ownership from elapsed time.

These primitives do not start calculations, accept effects, prepare files or
acknowledge a scope. The native scope entry must first qualify its captured
configuration and implementation, then pass that exact compatibility identity.
"""
from contextlib import contextmanager
import uuid

from django.db import DatabaseError, connection, transaction
from django.utils import timezone
from mta.serialization import digest
from mta.runtime.ingestion_context import sha
from mta.runtime.models import CalculationRun, RunScopeAttempt, RunPhaseAcceptance


def head(run_id):
    with connection.cursor() as cursor:
        cursor.execute('SELECT phase,digest FROM mta.scope_head(%s)', [run_id])
        phase, checksum = cursor.fetchone()
    return phase, checksum


def _source_lock(run_id):
    from mta.runtime.mdm_daily_models import MdmDailyInputCapture
    from mta.mdm.supplier_revisions import lock_transaction
    source_id = MdmDailyInputCapture.objects.filter(run_id=run_id).values_list('source_id', flat=True).first()
    if source_id is None:raise ValueError('Scoped execution requires its captured MDM source')
    lock_transaction(source_id)
    return source_id


def _frozen(run):
    from mta.runtime.input_reader import read_input
    from mta.runtime.mdm_daily_models import MdmDailyInputCapture
    if (run.kind != 'DAILY_CHAIN' or run.status != 'RUNNING' or run.output_digest
            or run.input_payload.get('content_digest') != run.input_digest
            or digest(run.input_payload) != run.input_manifest_digest):
        raise ValueError('Scoped logical input identity differs')
    capture = MdmDailyInputCapture.objects.get(run=run, status='CAPTURED')
    snapshot = read_input(run, components=('mdm_input',)).get('mdm_input')
    if (not snapshot or snapshot['revision_digest'] != capture.revision_digest
            or snapshot['source_id'] != capture.source_id):
        raise ValueError('Scoped capture identity differs')
    return capture


@contextmanager
def _setting(name, value):
    if name not in ('fresh.scope_worker', 'fresh.scope_phase', 'fresh.scope_fence',
                    'fresh.mdm_consuming_run', 'fresh.mdm_current_run'):
        raise ValueError('Unknown scoped transaction setting')
    with connection.cursor() as cursor:
        cursor.execute("SELECT current_setting(%s,true)", [name])
        previous = cursor.fetchone()[0] or ''
        cursor.execute("SELECT set_config(%s,%s,true)", [name, str(value)])
    try:yield
    except DatabaseError:
        # Raw cursor failures do not always mark Django's enclosing atomic
        # block. Its rollback also restores these transaction-local settings.
        transaction.set_rollback(True)
        raise
    finally:
        if not connection.needs_rollback:
            with connection.cursor() as cursor:
                cursor.execute("SELECT set_config(%s,%s,true)", [name, previous])


def claim(run_id, *, scope, command_key, worker_reference, compatibility_digest,
          expected_phase, expected_receipt_digest, recovery_of=None):
    if not transaction.get_autocommit():
        raise ValueError('A scope claim owns its short transaction')
    with transaction.atomic():
        return _claim(run_id, scope=scope, command_key=command_key,
            worker_reference=worker_reference, compatibility_digest=compatibility_digest,
            expected_phase=expected_phase, expected_receipt_digest=expected_receipt_digest,
            recovery_of=recovery_of)


def _claim(run_id, *, scope, command_key, worker_reference, compatibility_digest,
           expected_phase, expected_receipt_digest, recovery_of=None):
    """Transactional primitive, also used by isolated metadata guard fixtures."""
    if not connection.in_atomic_block:raise ValueError('Claim requires its transaction')
    sha(compatibility_digest)
    _source_lock(run_id)
    run = CalculationRun.objects.select_for_update().get(pk=run_id)
    _frozen(run)
    from mta.runtime.input_reader import read_input
    from mta.runtime.production_scope import PUBLICATION_SCHEMA
    captured=read_input(run,components=('scope_request',)).get('scope_request',{})
    if captured.get('schema')==PUBLICATION_SCHEMA and scope!='UptoBPR':
        raise ValueError('PostBPR publication continuation is not released')
    from mta.runtime.runtime_report_request import SCHEMA as PLACEMENT_SCHEMA,validate_request
    if captured.get('schema')==PLACEMENT_SCHEMA:
        validate_request(captured)
        allowed={'UptoBPR':('UptoBPR','PostBPR'),'UptoDBM':('UptoDBM','PostDBM')}.get(captured['scope'],())
        if (scope not in allowed or compatibility_digest!=captured['compatibility_digest']
                or (scope==captured['scope'])!=(command_key==captured['command_key'])):
            raise ValueError('Placement claim differs from captured scope/continuation owner')
    if head(run.pk) != (expected_phase, expected_receipt_digest):
        raise ValueError('Expected accepted phase changed')
    if RunScopeAttempt.objects.filter(run=run, status='ACTIVE').exists():
        raise ValueError('Scoped day already has an active worker; explicit fencing is required')
    previous = None
    if recovery_of is not None:
        previous = RunScopeAttempt.objects.select_for_update().get(pk=recovery_of, run=run)
        if previous.status != 'FAILED' or hasattr(previous, 'recovery'):
            raise ValueError('Recovery requires the failed latest attempt')
        if (previous.scope, previous.command_key, previous.compatibility_digest) != (
                scope, command_key, compatibility_digest):
            raise ValueError('Recovery cannot change its command or compatibility identity')
    elif RunScopeAttempt.objects.filter(run=run, command_key=command_key).exists():
        raise ValueError('Existing command requires its recorded result or explicit recovery')
    from mta.runtime import scope_revisions as revisions
    from mta.runtime.scoped_actions import revision
    before=revisions.require_current(run)
    attempt=RunScopeAttempt.objects.create(run=run, scope=scope, command_key=command_key,
        worker_reference=worker_reference, compatibility_digest=compatibility_digest,
        expected_phase=expected_phase, expected_receipt_digest=expected_receipt_digest,
        input_digest=run.input_digest, input_manifest_digest=run.input_manifest_digest,
        attempt_no=previous.attempt_no+1 if previous else 1, recovery_of=previous,
        action_revision=revision(run),
        revision_before=before,revision_after=revisions.next_cut(before))
    revisions.verify_write(run,attempt.revision_after)
    return attempt


def require_claim(attempt_id, worker_token, *, compatibility_digest):
    """Fence every commit using the current row, never an in-memory lease."""
    attempt,run=_locked_claim(attempt_id,worker_token,compatibility_digest=compatibility_digest)
    from mta.runtime.scope_revisions import require_current
    require_current(run)
    from mta.runtime.scoped_actions import revision
    if attempt.action_revision!=revision(run):
        raise ValueError('Scoped worker action revision changed')
    return attempt,run


def _locked_claim(attempt_id, worker_token, *, compatibility_digest):
    """Identity check also permits recording a failed worker's revision conflict."""
    if not connection.in_atomic_block:raise ValueError('Worker check requires its transaction')
    sha(compatibility_digest)
    identity = RunScopeAttempt.objects.only('run_id').get(pk=attempt_id)
    _source_lock(identity.run_id)
    run = CalculationRun.objects.select_for_update().get(pk=identity.run_id)
    attempt = RunScopeAttempt.objects.select_for_update().get(pk=attempt_id)
    if (attempt.status != 'ACTIVE' or str(attempt.worker_token) != str(worker_token)
            or attempt.compatibility_digest != compatibility_digest
            or attempt.input_digest != run.input_digest
            or attempt.input_manifest_digest != run.input_manifest_digest):
        raise ValueError('Stale or incompatible scoped worker')
    _frozen(run)
    return attempt, run


def fail(attempt_id, worker_token, *, compatibility_digest, error):
    if not transaction.get_autocommit():raise ValueError('Failure record owns its short transaction')
    with transaction.atomic():
        attempt, run = _locked_claim(attempt_id, worker_token, compatibility_digest=compatibility_digest)
        with _setting('fresh.scope_worker', worker_token):
            _close_attempt(attempt,run,'FAILED',dict(type=type(error).__name__,message=str(error)[:4000]))
    return attempt


def fence(attempt_id, *, expected_worker_token, reason):
    """Explicit operator recovery. This asserts no worker-death timeout policy."""
    if not transaction.get_autocommit():raise ValueError('Fencing owns its short transaction')
    if not isinstance(reason, str) or not reason.strip():raise ValueError('Explicit fencing reason required')
    with transaction.atomic():
        identity = RunScopeAttempt.objects.only('run_id').get(pk=attempt_id)
        _source_lock(identity.run_id)
        run=CalculationRun.objects.select_for_update().get(pk=identity.run_id)
        attempt = RunScopeAttempt.objects.select_for_update().get(pk=attempt_id)
        if attempt.status != 'ACTIVE' or str(attempt.worker_token) != str(expected_worker_token):
            raise ValueError('Worker changed before explicit fencing')
        with _setting('fresh.scope_fence', attempt.pk):
            _close_attempt(attempt,run,'FAILED',dict(type='FENCED',message=reason[:4000]))
    return attempt


def release(attempt_id, worker_token, *, compatibility_digest):
    """Release the calculation claim; file/read readiness remains independent."""
    if not transaction.get_autocommit():raise ValueError('Worker release owns its short transaction')
    with transaction.atomic():
        attempt, run = require_claim(attempt_id, worker_token, compatibility_digest=compatibility_digest)
        with _setting('fresh.scope_worker', worker_token):
            _close_attempt(attempt,run,'RELEASED',{})
    return attempt


def _close_attempt(attempt,run,status,failure):
    if status=='RELEASED':
        from mta.runtime.input_reader import read_input
        from mta.runtime.production_scope import PUBLICATION_SCHEMA
        captured=read_input(run,components=('scope_request',)).get('scope_request',{})
        if captured.get('schema')==PUBLICATION_SCHEMA:
            from mta.runtime.runtime_report_publication import read
            if attempt.scope!='UptoBPR':raise ValueError('Unreleased runtime report continuation')
            for placement in ('PostImporter','PostBPR'):
                read(run.pk,placement=placement,verify_bytes=True)
        from mta.runtime.runtime_report_request import SCHEMA as PLACEMENT_SCHEMA
        if captured.get('schema')==PLACEMENT_SCHEMA:
            from mta.runtime.runtime_report_placement_publication import read,PLACEMENTS
            count={'UptoBPR':2,'UptoDBM':3,'PostBPR':5,'PostDBM':5}.get(attempt.scope)
            if count is None:raise ValueError('Unqualified placement scope release')
            for placement in PLACEMENTS[:count]:read(run.pk,placement=placement,verify_bytes=True)
    from mta.runtime import scope_revisions as revisions
    after,observed,diagnostics=revisions.closing(run)
    if diagnostics:
        if status!='FAILED':raise ValueError('Revision conflict cannot release a worker')
        failure={**failure,**diagnostics}
    attempt.status=status;attempt.failure=failure;attempt.finished_at=timezone.now()
    attempt.revision_closed=after
    attempt.save(update_fields=['status','failure','finished_at','revision_closed'])
    observed_after=(observed if diagnostics.get('certification_status')=='INVALIDATED'
                    else revisions.next_cut(observed))
    revisions.verify_write(run,observed_after,retained=status=='FAILED')


def _begin_phase(attempt, run, phase):
    """Open the transaction-local unit; its deferred constraint requires sealing."""
    from mta.runtime.mdm_daily_models import MdmDailyInputCapture
    from mta.runtime.scope_revisions import require_current
    before=require_current(run)
    capture = MdmDailyInputCapture.objects.get(run=run, status='CAPTURED')
    identity = uuid.uuid4()
    with connection.cursor() as cursor:
        cursor.execute("SELECT set_config('fresh.scope_phase',%s,true)", [str(identity)])
    return RunPhaseAcceptance.objects.create(id=identity, run=run, attempt=attempt,
        source_id=capture.source_id, phase=phase, input_digest=run.input_digest,
        capture_digest=capture.revision_digest,revision_before=before)


def _seal_phase(receipt, snapshot, *, effect_digest, partitions, effects=None):
    """The actual phase owner supplies proved effects/typed partition identities."""
    sha(effect_digest)
    receipt.snapshot = snapshot
    receipt.metadata = dict(schema='fresh-phase-acceptance-v1', snapshot_digest=snapshot.state_digest,
        compatibility_digest=receipt.attempt.compatibility_digest,
        effect_digest=effect_digest, partitions=partitions)
    if effects is not None:
        receipt.metadata['effects'] = effects
    if receipt.attempt.action_revision:
        receipt.metadata['action_revision']=receipt.attempt.action_revision
    from mta.runtime import scope_revisions as revisions
    after=revisions.next_cut(revisions.owned_position(receipt.run))
    if after is not None:receipt.metadata['revision_after']=after
    receipt.digest = receipt_digest(receipt)
    receipt.state_sealed = True
    receipt.accepted_at = timezone.now()
    receipt.save(update_fields=['snapshot', 'metadata', 'digest', 'state_sealed', 'accepted_at'])
    revisions.verify_write(receipt.run,after)
    return receipt


def receipt_digest(receipt):
    identity=dict(run_id=str(receipt.run_id), attempt_id=str(receipt.attempt_id),
        source_id=receipt.source_id, phase=receipt.phase, input_digest=receipt.input_digest,
        capture_digest=receipt.capture_digest, snapshot_id=receipt.snapshot_id, metadata=receipt.metadata)
    if receipt.revision_before is not None:identity['revision_before']=receipt.revision_before
    return digest(identity)


def _seal_day_final(receipt):
    """Seal only the actual completed typed root, within its pending unit."""
    from mta.runtime.receipt_integrity import verify_root
    from mta.runtime import scope_revisions as revisions
    run=CalculationRun.objects.get(pk=receipt.run_id)
    if (not connection.in_atomic_block or receipt.phase!='DAY_FINAL'
            or receipt.state_sealed or receipt.snapshot_id is not None):
        raise ValueError('DAY_FINAL requires its unsealed root acceptance')
    with connection.cursor() as cursor:
        cursor.execute('SELECT mta.pending_day_final(%s)',[run.pk])
        if not cursor.fetchone()[0]:raise ValueError('DAY_FINAL worker no longer owns its unit')
    verify_root(run)
    phase,parent_digest=head(run.pk)
    if phase!='DBM':raise ValueError('DAY_FINAL requires its accepted DBM prefix')
    receipt.metadata=dict(schema='fresh-day-final-acceptance-v1',
        parent_acceptance_digest=parent_digest,output_digest=run.output_digest,
        production_digest=run.production_digest,input_manifest_digest=run.input_manifest_digest,
        compatibility_digest=receipt.attempt.compatibility_digest)
    if receipt.attempt.action_revision:
        receipt.metadata['action_revision']=receipt.attempt.action_revision
    after=revisions.next_cut(revisions.owned_position(run))
    if after is not None:receipt.metadata['revision_after']=after
    receipt.digest=receipt_digest(receipt)
    receipt.state_sealed=True;receipt.accepted_at=timezone.now()
    receipt.save(update_fields=['metadata','digest','state_sealed','accepted_at'])
    revisions.verify_write(run,after)
    return receipt
