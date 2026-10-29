"""Private acceptance of the actual BPR/DBM producers, before DAY_FINAL."""
from django.db import connection, transaction
from mta.serialization import digest
from mta.runtime import phase_state
from mta.runtime.scope_execution import (require_claim, head, receipt_digest,
    _setting, _begin_phase, _seal_phase)

SCHEMA='fresh-calculation-phase-effects-v1'


def _parent(run, parent, phase):
    from mta.runtime.models import RunPhaseAcceptance
    from mta.runtime.prepared_effects import SCHEMA as PREPARED
    expected='PRE_BPR' if phase=='BPR' else 'BPR'
    parent=RunPhaseAcceptance.objects.select_related('snapshot','attempt').get(pk=parent.pk)
    image=parent.snapshot
    if (parent.run_id!=run.pk or parent.phase!=expected or not parent.state_sealed
            or parent.input_digest!=run.input_digest
            or parent.digest!=receipt_digest(parent) or image is None
            or image.acceptance_id!=parent.pk or image.run_id!=run.pk
            or image.phase!=expected or image.input_digest!=run.input_digest
            or image.state_digest!=digest(image.manifest)
            or image.recipe_digest!=phase_state.recipe_digest()
            or parent.metadata.get('snapshot_digest')!=image.state_digest
            or parent.metadata.get('compatibility_digest')!=parent.attempt.compatibility_digest
            or parent.metadata.get('effects',{}).get('schema')!=(PREPARED if phase=='BPR' else SCHEMA)
            or parent.metadata.get('effect_digest')!=digest(parent.metadata.get('effects'))
            or head(run.pk)!=(expected,parent.digest)):
        raise ValueError('Calculation phase requires its exact accepted business parent')
    return parent


def _accept_calculation(attempt_id, worker_token, phase, sources, *, parent,
                        compatibility_digest):
    from mta.application.accepted_inputs import consume
    with consume(phase.context):
        return _accept_calculation_phase(attempt_id, worker_token, phase, sources,
            parent=parent, compatibility_digest=compatibility_digest)


def _accept_calculation_phase(attempt_id, worker_token, phase, sources, *, parent,
                              compatibility_digest):
    from mta.temporal.day_phases import BprDay,DbmDay
    from mta.application.stage_calculation_sources import CalculationSources
    from mta.application.daily_finalization import configuration,ACTIVE_POLICY,POLICY
    from mta.runtime.input_reader import read_execution_input as read_input
    from mta.runtime.mdm_daily_models import MdmDailyInputCapture
    from mta.mdm.initialization_contract import SOURCE_SCHEMA
    from mta.mdm.daily_source import SCHEMA as DAILY_SOURCE,APPROVAL_DAY_ARTIFACT_SHA
    from mta.mdm.daily_current import _write_partition,_partition_identity
    from mta.mdm.master_owners import phase_copy_batches
    from mta.runtime.ingestion_context import sha
    if not connection.in_atomic_block:
        raise ValueError('Calculation acceptance requires its transaction')
    attempt,run=require_claim(attempt_id,worker_token,compatibility_digest=compatibility_digest)
    kind='BPR' if type(phase) is BprDay else 'DBM' if type(phase) is DbmDay else None
    profile=read_input(run,components=('profile',))['profile']
    if (kind is None or type(sources) is not CalculationSources
            or not phase.context.native_daily or phase.context.identity!=str(run.pk)
            or phase.context.today!=run.business_date.isoformat()
            or phase.context.action_revision!=(attempt.action_revision if kind=='DBM' else 0)
            or digest(phase.context.profile)!=digest(profile)
            or phase.context.finalization!=configuration(profile)):
        raise ValueError('Calculation acceptance requires its exact native producer')
    sha(sources.calculation_digest)
    parent=_parent(run,parent,kind)
    capture=MdmDailyInputCapture.objects.select_related('source').get(run=run,status='CAPTURED')
    if parent.source_id!=capture.source_id or parent.capture_digest!=capture.revision_digest:
        raise ValueError('Calculation parent capture differs')
    policy=phase.context.finalization['policy']
    native=capture.source.receipt.get('schema')==SOURCE_SCHEMA
    if (policy not in (ACTIVE_POLICY,POLICY) or capture.nms_active!=(policy==ACTIVE_POLICY)
            or not native and (policy!=ACTIVE_POLICY
                or capture.source.receipt.get('schema')!=DAILY_SOURCE
                or capture.source.receipt.get('artifact_sha256')!=APPROVAL_DAY_ARTIFACT_SHA)):
        raise ValueError('Calculation copies require their mode-bound source')
    if native:
        from mta.mdm.production_families import require_binding
        from mta.mdm.location_transition import run_identity,admit
        require_binding(capture.source)
        run_identity(run,capture.source)
        admit(capture.source,run.business_date,run.predecessor)
    batches=phase_copy_batches(kind,phase.importer if kind=='BPR' else phase.final_dbm)
    with transaction.atomic(),_setting('fresh.scope_worker',worker_token):
        receipt=_begin_phase(attempt,run,kind)
        with _setting('fresh.mdm_current_run',run.pk):
            from contextlib import nullcontext
            from mta.runtime.accepted_current_write import _accepted_current_write
            from mta.application.accepted_inputs import accepted
            with (_accepted_current_write(run, capture.source) if native and accepted() else nullcontext()):
                for _family,model,partition,rows,path in batches:
                    _write_partition(capture.source,model,partition,rows,path)
        image=phase_state.save(run,phase,sources,parent=parent.snapshot,acceptance=receipt)
        effects=dict(schema=SCHEMA,phase=kind,parent_acceptance_digest=parent.digest,
                     calculation_digest=sources.calculation_digest)
        receipt=_seal_phase(receipt,image,effect_digest=digest(effects),
                            partitions=_partition_identity(batches),effects=effects)
        from mta.runtime.master_revisions import accept_phase
        accept_phase(receipt)
        return receipt
