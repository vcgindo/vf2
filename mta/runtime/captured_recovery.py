"""Explicit interrupted-capture continuation through the normal daily owner.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
from copy import deepcopy
from datetime import date
from pathlib import Path
import uuid

from django.db import connection, transaction
from mta.serialization import digest
from mta.application.stage_observation import operation, stage


def _uncommitted(run):
    from mta.runtime.publication_models import DailyUiPublication
    if (run.kind != 'DAILY_CHAIN' or run.evidence_mode != 'production'
            or run.status not in ('RUNNING','FAILED') or run.output_digest
            or run.output_roster or run.production_digest or run.checkpoints.exists()
            or run.commands.exists() or run.successors.exists()
            or DailyUiPublication.objects.filter(run=run).exists()):
        raise ValueError('Interrupted capture has committed or foreign downstream state')


def _pins(run, attempt, expected):
    actual = dict(run_id=str(run.pk), initialization_id=str(attempt.initialization_id),
        source_digest=attempt.initialization.source.digest,
        input_digest=run.input_digest, input_manifest_digest=run.input_manifest_digest,
        daily_input_sha256=attempt.input_sha256,
        capture_cut=run.production_manifest.get('ingestion_preparation',{}).get('capture_cut'))
    if actual != expected:
        raise ValueError('Interrupted capture independent checkpoint pins differ')


def _restore_working(snapshot, prior, day, parent):
    """Replay the frozen overlay, not intake or calculation, on its own opening.

    The captured day already contains phase requests produced by that overlay.
    Prove those exact rows before feeding the existing single-overlay producer;
    do not append them a second time or weaken its external-feed rejection.
    """
    from mta.mdm.integration_source import replace_working_inputs
    working_day = {**day, 'control_requests':dict(day['control_requests'])}
    if 'phase_controls' in snapshot:
        from mta.mdm.phase_controls_capture import FIELDS, native
        frozen = snapshot['phase_controls']
        for name in FIELDS:
            expected = [native(row,name) for row in frozen[name]]
            if day['control_requests'][name] != expected:
                raise ValueError('Frozen phase request overlay differs')
            working_day['control_requests'][name] = []
    replace_working_inputs(snapshot,prior,working_day,parent)
    if working_day != day:
        raise ValueError('Reconstructed working overlay changed captured day facts')
    from mta.mdm.daily_input import apply_refresh_setting
    apply_refresh_setting(prior['importer_settings'],snapshot)


def resume(*, origin_run_id, execution_revision, expected, archive_path):
    """Called only by execute_day's explicit captured-continuation dispatch.

    Daily/source locks and the original revision cut are checked before marking
    the interruption. One atomic snapshot creates distinct run/attempt/capture
    metadata. Original typed populations and receipts are never rewritten.
    """
    from mta.runtime.models import CalculationRun, ProductionInitialization
    from mta.runtime.daily_feed_models import DailyFeedAttempt
    from mta.runtime.mdm_daily_models import MdmDailyInputCapture
    from mta.runtime.daily_feed import job_lock
    from mta.mdm.supplier_revisions import source_lock
    from mta.runtime.ingestion_admission import preparation_source
    from mta.runtime.opening_scope import release_opening
    from mta.runtime.input_reader import read_input
    from mta.runtime.accepted_daily import epochs
    from mta.runtime.services import fail_run, read_outputs
    if (not transaction.get_autocommit() or not isinstance(execution_revision,str)
            or not 1 <= len(execution_revision) <= 80):
        raise ValueError('Captured continuation owns its transaction and explicit revision')
    old = CalculationRun.objects.get(pk=uuid.UUID(str(origin_run_id)))
    attempt = DailyFeedAttempt.objects.select_related('initialization__source').get(run=old)
    owner = attempt.initialization
    target = Path(archive_path).resolve()
    if target.exists() or target.parent != Path(attempt.archive_path).resolve().parent:
        raise ValueError('Continuation requires a new sibling operation directory')
    with job_lock(owner) as check, operation('continuation:'+str(old.pk)):
        if CalculationRun.objects.filter(execution_revision=execution_revision).exists():
            raise ValueError('This explicit continuation revision was already attempted; no automatic replay')
        ready = preparation_source(owner.source.digest)
        if ready is None:
            raise ValueError('Captured continuation requires compatible certified native admission')
        from mta.mdm.production_families import certified_state_handle
        certified_state_handle(owner,ready)
        with stage('accepted_capture_reconstruction'):
            _uncommitted(old); _pins(old,attempt,expected)
            if old.production_manifest.get('native_report_disposition') is not None:
                raise ValueError('Captured continuation cannot reinterpret an admitted report disposition')
            raw = read_input(old)
        binding = dict(id=str(owner.pk),source_digest=owner.source.digest,
            input_sha256=owner.input_sha256,content_digest=owner.input_digest,
            configuration_digest=owner.configuration_digest)
        if (raw.get('daily_input_sha256') != attempt.input_sha256
                or digest(raw['profile']) != owner.configuration_digest
                or raw.get('initialization_binding') != binding
                or raw['day']['business_date'] != old.business_date.isoformat()):
            raise ValueError('Frozen native request/initialization differs')
        from mta.runtime.input_storage import logical_digest
        if logical_digest(old,raw) != old.input_digest:
            raise ValueError('Complete retained typed input content differs')
        snapshot = raw.get('mdm_input')
        if not isinstance(snapshot,dict):
            raise ValueError('Frozen native MDM snapshot is absent')
        if digest({k:v for k,v in snapshot.items() if k!='revision_digest'}) != snapshot.get('revision_digest'):
            raise ValueError('Frozen native MDM snapshot values differ')
        parent = old.predecessor
        if parent is None:
            initial = raw['opening']
            prior = deepcopy(initial['state'])
            opening_date = initial['opening_date']
        else:
            previous = read_outputs(parent)
            prior = deepcopy(previous['ClosingState'][0]); del previous
            from mta.runtime.temporal import command_states
            prior,_ = command_states(parent,prior,through_date=old.business_date)
            opening_date = parent.business_date.isoformat()
        from datetime import timedelta
        if old.business_date != date.fromisoformat(opening_date)+timedelta(days=1):
            raise ValueError('Frozen native day is not its own immediate successor')
        opening_settings=deepcopy(prior['importer_settings'])
        _restore_working(snapshot,prior,raw['day'],parent)
        with source_lock(owner.source_id), transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ')
            owner = ProductionInitialization.objects.select_for_update().select_related('source').get(pk=owner.pk)
            old = CalculationRun.objects.select_for_update().get(pk=old.pk)
            attempt = DailyFeedAttempt.objects.select_for_update().select_related('initialization__source').get(pk=attempt.pk)
            frozen = MdmDailyInputCapture.objects.select_for_update().get(run=old)
            _uncommitted(old); _pins(old,attempt,expected)
            if (epochs(owner.pk,lock=True) != expected['capture_cut']
                    or attempt.status != 'RUNNING' or attempt.phase != 'VALIDATED'
                    or not attempt.accepted_facts or frozen.origin_id is not None
                    or frozen.status != 'CAPTURED' or frozen.revision_digest != snapshot.get('revision_digest')
                    or old.execution_revision == execution_revision
                    or list(MdmDailyInputCapture.objects.filter(source_id=owner.source_id,
                        status='CAPTURED',retries__isnull=True).values_list('pk',flat=True)) != [old.pk]):
                raise ValueError('Interrupted owner, revisions or unique frozen leaf changed')
            from mta.runtime.mdm_configuration import capture_configuration_for_day
            nms,horizon = capture_configuration_for_day(opening_settings,predecessor=parent,source=owner.source)
            if (snapshot['nms_active'] != nms
                    or snapshot['configuration']['task_status_log_horizon'] != horizon):
                raise ValueError('Frozen NMS/task configuration changed')
            check()
            if old.status != 'RUNNING':
                raise ValueError('External interruption has already been reconciled')
            fail_run(old, RuntimeError('Explicit external-deadline interruption reconciled; immutable input retained'))
            old.refresh_from_db()
            from mta.mdm.integration_source import verify_predecessor, verify_capture, replace_working_inputs
            verify_predecessor(owner.source,parent,retry_capture=frozen)
            verify_capture(owner.source,snapshot)
            attempt.status='FAILED'
            attempt.error=dict(type='ExternalInterruption',message='Original input retained; explicit distinct continuation')
            attempt.save(update_fields=['status','error','updated_at'])
            from mta.runtime.capture_preparation import seed, seal
            from mta.runtime.captured_input import manifest
            from mta.runtime.ingestion_context import RevisionCut
            # Rebind only the new operation's cut after the audited metadata
            # transition; the original cut remains immutable evidence.
            from dataclasses import replace
            ready = replace(ready,revisions=RevisionCut(*epochs(owner.pk)))
            run = CalculationRun.objects.create(kind='DAILY_CHAIN',business_date=old.business_date,
                predecessor=parent,execution_revision=execution_revision,evidence_mode='production',
                input_digest=old.input_digest,input_payload={},
                opening_key=(digest(dict(identity=raw['opening']['identity'],revision=execution_revision))
                             if parent is None else None),
                production_manifest={'ingestion_preparation':seed(ready,reused=False)})
            new_attempt = DailyFeedAttempt.objects.create(initialization=owner,business_date=attempt.business_date,
                batch_id=attempt.batch_id,batch_digest=attempt.batch_digest,binding_digest=attempt.binding_digest,
                request_key=digest(dict(origin=str(attempt.attempt_id),revision=execution_revision)),
                input_sha256=attempt.input_sha256,predecessor=parent,
                predecessor_output_digest=attempt.predecessor_output_digest,run=run,
                status='RUNNING',phase='CALCULATE',archive_path=str(target),
                certification=attempt.certification,master_revision=attempt.master_revision)
            from mta.mdm.daily_input import bind_capture
            daily = bind_capture(run,snapshot,request_digest=frozen.request_digest,origin=frozen)
            run.input_payload=manifest(run,old)
            run.input_manifest_digest=digest(run.input_payload)
            run.save(update_fields=['input_payload','input_manifest_digest'])
            # All existing side-effect owners bind the same frozen input through
            # its new execution owner; no authorization/consumer bypass exists.
            if 'operational_sources' in raw['profile']:
                from mta.runtime.operational_source import authorize_new_run
                authorize_new_run(run)
            from mta.mdm.native_audit import bind
            bind(run,daily,raw['profile'])
            from mta.runtime.temporal import daily_sources_enabled
            if daily_sources_enabled(raw['profile']):
                from mta.presentation.daily_requests import bind as bind_requests
                from mta.presentation.ancillary_live import bind_snapshots
                bind_requests(run,raw['request_inputs']); bind_snapshots(run,raw['remark_inputs'])
            seal(run)
            # A filesystem failure must roll back the metadata transition.
            # A later SQL commit failure may retain this diagnostic receipt;
            # it cannot make its uncommitted run readable or executable.
            target.mkdir()
            from mta.runtime.daily_feed import atomic_json
            atomic_json(target/'captured-origin.json',dict(origin_run_id=str(old.pk),run_id=str(run.pk),
                origin_attempt_id=str(attempt.attempt_id),attempt_id=str(new_attempt.attempt_id),
                input_digest=run.input_digest,input_manifest_digest=run.input_manifest_digest))
        publication_opening=None
        if daily_sources_enabled(raw['profile']):
            publication_opening={'supplier':deepcopy(prior['supplier'])}
            for name in ('shipment_input','transporter_input','production_report_policy',
                         'production_report_opening','production_report_schema'):
                if name in raw['day']:
                    publication_opening[name]=raw['day'][name]
        from mta.application.daily_finalization import configuration
        from mta.runtime.temporal import _finish_captured_day
        release_opening()
        check()
        from mta.runtime.daily_feed import save
        try:
            finished = _finish_captured_day(run,raw,prior,opening_date,raw['lineage'],publication_opening,
                raw['profile'].get('complete_pick') is not None,raw.get('pick_output_root'),
                raw.get('report_exceptions',{}),configuration(raw['profile']),True,capture_snapshot=snapshot)
            new_attempt.refresh_from_db()
            save(new_attempt,'PREPARE','COMMITTED')
            return finished
        except Exception as error:
            new_attempt.refresh_from_db()
            run.refresh_from_db()
            save(new_attempt,new_attempt.phase,'COMMITTED' if run.status=='SUCCEEDED' else 'FAILED',
                dict(type=type(error).__name__,message=str(error)[:2000]))
            raise
