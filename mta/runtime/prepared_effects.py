"""Atomic PRE_BPR effects using the existing captured-input business writers.

This private phase owner is not a public scope entry or publication selector.
It requires the already qualified producer/claim; normal Full stays unchanged.
"""
from django.db import connection, transaction
from mta.serialization import digest
from mta.runtime import phase_state
from mta.runtime.scope_execution import (require_claim, _setting, _begin_phase,
    _seal_phase, receipt_digest, head)

SCHEMA = 'fresh-prepared-mdm-effects-v1'
RAW = ('SOBDataRaw', 'MOQDataRaw1', 'MOQDataRaw2')
FAMILIES = dict(force=('importer/ForceNormChange','controls/upload_log'),
    season=('aux/season_requests','controls/seasonality'), stop_pipo=('aux/phase_stops',),
    phase_controls=('aux/phase_requests','aux/phase_in_requests'),
    supplier=tuple('supplier_raw/'+name for name in RAW))


def writer_output(prepared):
    """Only actual finalizer arguments; never claim an unproduced DBM closing."""
    return dict(ClosingState=[dict(importer=prepared.importer, controls=prepared.control_final,
        control_aux=prepared.control_aux,
        dbm=dict(Seasonality=prepared.control_final['seasonality']),
        complete={name: prepared.supplier_final[name] for name in RAW})])


def _families(image, captured):
    images=image.manifest['images']
    return {name: {path: {key: images['phase/PRE_BPR/'+path][key] for key in ('count','digest')}
                   for path in paths} for name, paths in FAMILIES.items() if name in captured}


def _project(run, capture, prepared):
    from mta.application.daily_finalization import ACTIVE_POLICY, POLICY
    from mta.mdm.daily_source import SCHEMA as DAILY_SOURCE, APPROVAL_DAY_ARTIFACT_SHA
    from mta.mdm.initialization_contract import SOURCE_SCHEMA
    from mta.mdm.master_owners import importer_batches
    from mta.mdm.daily_current import _write_partition, _partition_identity
    policy=prepared.context.finalization['policy']
    native=capture.source.receipt.get('schema') == SOURCE_SCHEMA
    if (policy not in (ACTIVE_POLICY,POLICY) or capture.nms_active != (policy == ACTIVE_POLICY)
            or not native and (policy != ACTIVE_POLICY
                or capture.source.receipt.get('schema') != DAILY_SOURCE
                or capture.source.receipt.get('artifact_sha256') != APPROVAL_DAY_ARTIFACT_SHA)):
        raise ValueError('Prepared current publication requires its mode-bound source')
    if native:
        from mta.mdm.production_families import require_binding
        require_binding(capture.source)
    batches=importer_batches(prepared.importer,prepared.nms['NMSAllItems'])
    with _setting('fresh.mdm_current_run',run.pk):
        for _family, model, partition, rows, path in batches:
            _write_partition(capture.source,model,partition,rows,path)
    return _partition_identity(batches)


def _accept_prepared(attempt_id, worker_token, prepared, *, compatibility_digest):
    """Caller owns one acceptance transaction; failure rolls back every effect."""
    from mta.temporal.day_phases import PreparedDay
    from mta.runtime.input_reader import read_input
    from mta.mdm.daily_input import _lock_consumption, _apply_consumption_effects
    from mta.application.daily_finalization import mark, configuration
    if not connection.in_atomic_block:raise ValueError('Prepared effects require their transaction')
    attempt,run=require_claim(attempt_id,worker_token,compatibility_digest=compatibility_digest)
    # Certified capture cuts include every guarded write. Claim/phase headers
    # and early effects advance those epochs themselves. The native scope
    # entry must qualify a phase-owned revision cut before admitting this path;
    # never discard the Full capture-cut check or silently adopt live epochs.
    if run.production_manifest.get('ingestion_preparation') is not None:
        raise ValueError('Certified scoped capture requires its qualified phase revision cut')
    profile=read_input(run,components=('profile',))['profile']
    if (type(prepared) is not PreparedDay or not prepared.context.native_daily
            or prepared.context.identity != str(run.pk)
            or prepared.context.today != run.business_date.isoformat()
            or digest(prepared.context.profile) != digest(profile)
            or prepared.context.finalization != configuration(profile)
            or prepared.complete is None or prepared.nms is None
            or head(run.pk) != ('START','')):
        raise ValueError('Prepared effects require their exact unaccepted producer')
    work=_lock_consumption(run)
    if work is None:raise ValueError('Prepared effects require their unconsumed capture')
    # A nested savepoint makes catching a later Python failure safe even when
    # the caller keeps its surrounding transaction open.
    with transaction.atomic(), _setting('fresh.scope_worker',worker_token), \
            _setting('fresh.mdm_consuming_run',run.pk):
        receipt=_begin_phase(attempt,run,'PRE_BPR')
        now=_apply_consumption_effects(run,work,output=writer_output(prepared))
        mark(prepared.complete,'NMSTaskStatusUpdate.sql')
        if work.capture.nms_active:
            mark(prepared.complete,'NMSImportData.sql','NMSArchiveInputData.sql','NMSClearInputTables.sql')
        partitions=_project(run,work.capture,prepared)
        image=phase_state.save(run,prepared,None,acceptance=receipt)
        effects=dict(schema=SCHEMA, source_id=work.capture.source_id,
            capture_digest=work.capture.revision_digest, effects_at=now.isoformat(),
            families=_families(image,work.snapshot),
            pair_exclusion_digest=digest(work.final_exclusions))
        return _seal_phase(receipt,image,effect_digest=digest(effects),
                           partitions=partitions,effects=effects)


def prepared_family_owner(source, owner, family):
    """Verify a RUNNING family owner against its explicit accepted typed phase.

    No public selected-run reader or next-day predecessor gains eligibility.
    Accepted evidence survives failure/release of its worker, as required by D5.
    """
    from mta.runtime.models import RunPhaseAcceptance
    from mta.runtime.mdm_daily_models import MdmDailyInputCapture
    from mta.runtime.input_reader import read_input
    run=owner.last_run
    if run is None or run.status != 'RUNNING' or owner.source_id != source.pk:
        raise ValueError('Prepared family requires its RUNNING logical owner')
    receipt=RunPhaseAcceptance.objects.select_related('snapshot','attempt').filter(
        run=run,source=source,phase='PRE_BPR',state_sealed=True).first()
    capture=MdmDailyInputCapture.objects.filter(run=run,source=source,status='CAPTURED').first()
    if receipt is None or receipt.snapshot_id is None or capture is None or family not in FAMILIES:
        raise ValueError('Prepared family has no accepted typed owner')
    image=receipt.snapshot
    captured=read_input(run,components=('mdm_input',))['mdm_input']
    effects=receipt.metadata.get('effects',{})
    if (receipt.digest != receipt_digest(receipt) or receipt.input_digest != run.input_digest
            or receipt.capture_digest != capture.revision_digest
            or captured['revision_digest'] != capture.revision_digest
            or image.acceptance_id != receipt.pk or image.run_id != run.pk or image.phase != 'PRE_BPR'
            or image.input_digest != run.input_digest or image.state_digest != digest(image.manifest)
            or image.recipe_digest != phase_state.recipe_digest()
            or receipt.metadata.get('snapshot_digest') != image.state_digest
            or receipt.metadata.get('compatibility_digest') != receipt.attempt.compatibility_digest
            or effects.get('schema') != SCHEMA or effects.get('source_id') != source.pk
            or effects.get('capture_digest') != capture.revision_digest
            or receipt.metadata.get('effect_digest') != digest(effects)
            or effects.get('families') != _families(image,captured) or family not in effects['families']):
        raise ValueError('Prepared family acceptance identity differs')
    frozen=captured[family]
    if (owner.receipt_digest != frozen['source_digest']
            or owner.generation < frozen['anchor']['generation']
            or 'root_state_digest' in frozen['anchor'] and
               owner.root_state_digest != frozen['anchor']['root_state_digest']
            or effects.get('pair_exclusion_digest') != digest(captured['pair_exclusions'])):
        raise ValueError('Prepared family installation/capture anchor differs')
    images=image.manifest['images']
    values={path: phase_state.typed.load_image(run,images['phase/PRE_BPR/'+path],
                                              table_registry=phase_state.REGISTRY)
            for path in FAMILIES[family]}
    if family == 'force':
        valid=(owner.closing_digest == digest(values['importer/ForceNormChange'])
            and owner.closing_log_digest == digest(values['controls/upload_log']))
    elif family == 'season':
        valid=(owner.closing_queue_digest == digest(values['aux/season_requests'])
            and owner.closing_current_digest == digest(values['controls/seasonality']))
    elif family == 'stop_pipo':valid=owner.closing_queue_digest == digest(values['aux/phase_stops'])
    elif family == 'phase_controls':
        valid=owner.closing_queue_digest == digest({name:values['aux/'+name]
                                                   for name in ('phase_requests','phase_in_requests')})
    else:raise ValueError('No last-run owner for this prepared family')
    if not valid:raise ValueError('Prepared family current anchor differs from its typed phase')
    return receipt
