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


def _finite_owner(run, attempt, value, *, terminal=False, retry=False):
    """The inspected stopped terminal6, preserving all seven original records."""
    from mta.runtime.captured_input import finite_prefix, terminal_prefix, retry_prefix
    from mta.runtime.daily_feed_models import DailyFeedAttempt
    fields={'prefix_digest','physical_run_id','physical_manifest_digest','physical_attempt_id',
            'current_revision_cut'}
    if (type(value) is not dict or set(value)!=fields
            or type(value['current_revision_cut']) is not list
            or len(value['current_revision_cut'])!=5
            or any(type(v) is not int or v<0 for v in value['current_revision_cut'])):
        raise ValueError('Finite continuation requires independently inspected prefix and current cut')
    physical,rows,prefix=(retry_prefix if retry else terminal_prefix if terminal else finite_prefix)(run)
    original=DailyFeedAttempt.objects.get(run=physical)
    if (prefix!=value['prefix_digest'] or str(physical.pk)!=value['physical_run_id']
            or physical.input_manifest_digest!=value['physical_manifest_digest']
            or str(original.attempt_id)!=value['physical_attempt_id']
            or not original.accepted_facts or original.initialization_id!=attempt.initialization_id
            or original.input_sha256!=attempt.input_sha256 or original.batch_digest!=attempt.batch_digest
            or physical.input_digest!=run.input_digest):
        raise ValueError('Finite continuation prefix/physical input ownership differs')
    _uncommitted(physical)
    return physical


def _empty_terminal_outputs(run):
    from mta.runtime.relational_state import STORAGE_TABLES,table_sql
    with connection.cursor() as cursor:
        for table in sorted({table_sql(key) for key in STORAGE_TABLES} |
                            {'mta_state.report_export_cell'}):
            cursor.execute('SELECT 1 FROM '+table+' WHERE vf_run_id=%s LIMIT 1',[run.pk])
            if cursor.fetchone() is not None:
                raise ValueError('Interrupted terminal leaf contains typed result rows')
    from mta.runtime.models import (PickProjection,ExcessProjection,FulfillmentProjection,
        ExpediteProjection,PickPostProjection,DailySourceReceipt)
    from mta.runtime.offline_rrr_models import OfflineRrrColourSource
    from mta.runtime.report_generation_models import DailyReportGeneration,DailyReportOrderRouteSource
    if any(model.objects.filter(run=run).exists() for model in (
            PickProjection,ExcessProjection,FulfillmentProjection,ExpediteProjection,
            PickPostProjection,DailySourceReceipt,OfflineRrrColourSource,
            DailyReportGeneration,DailyReportOrderRouteSource)):
        raise ValueError('Interrupted terminal leaf contains output source/report generation rows')


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


def _second_hop_owner(run,attempt,value,*,final_third_hop=False,final_interrupted_fourth_hop=False,
                      final_failed_fifth_hop=False,final_interrupted_sixth_hop=False):
    """Explicit finite continuation of one failed V1 leaf, no failed-row edit."""
    from mta.runtime.captured_input import SCHEMA, SECOND, _origin
    from mta.runtime.daily_feed_models import DailyFeedAttempt
    fields={'physical_run_id','physical_manifest_digest','physical_attempt_id','current_revision_cut'}
    sixth = final_interrupted_sixth_hop
    interrupted = final_interrupted_fourth_hop or sixth
    fifth = final_failed_fifth_hop
    flags=(final_third_hop,final_interrupted_fourth_hop,fifth,sixth)
    if (any(type(flag) is not bool for flag in flags) or sum(flags)>1
            or type(value) is not dict or set(value)!=fields
            or type(value['current_revision_cut']) is not list
            or len(value['current_revision_cut'])!=5
            or any(type(v) is not int or v<0 for v in value['current_revision_cut'])
            or run.input_payload.get('schema')!=(SECOND if any(flags) else SCHEMA)
            or run.status!=('RUNNING' if interrupted else 'FAILED')
            or attempt.status!=('RUNNING' if interrupted else 'FAILED')
            or attempt.phase!='CALCULATE' or attempt.accepted_facts):
        raise ValueError('Second hop requires an exact failed V1 leaf and explicit live cut')
    # Preserve the old two-hop origin for a third continuation. The explicit
    # human-interrupted branch must own exactly the existing third-hop leaf.
    physical=_origin(run,second_allowed=True,third_allowed=interrupted or fifth,
                     fourth_allowed=fifth or sixth,fifth_allowed=sixth)
    if sixth:
        try:
            _origin(run,second_allowed=True,third_allowed=True,fourth_allowed=True)
        except ValueError as error:
            if str(error) != 'Captured reference exceeds the fixed third-hop boundary':
                raise
        else:
            raise ValueError('Final interrupted continuation requires exactly five wrappers')
    if fifth:
        try:
            _origin(run,second_allowed=True,third_allowed=True)
        except ValueError as error:
            if str(error) != 'Captured reference exceeds the fixed third-hop boundary':
                raise
        else:
            raise ValueError('Final failed continuation requires exactly four wrappers')
    if final_interrupted_fourth_hop:
        from mta.runtime.captured_input import _origin as resolve_origin
        try:
            resolve_origin(run,second_allowed=True,third_allowed=False)
        except ValueError as error:
            if str(error) != 'Captured reference exceeds the fixed third-hop boundary':
                raise
        else:
            raise ValueError('Final interrupted continuation requires exactly three wrappers')
    _uncommitted(physical)
    original=DailyFeedAttempt.objects.get(run=physical)
    if (str(physical.pk)!=value['physical_run_id']
            or physical.input_manifest_digest!=value['physical_manifest_digest']
            or str(original.attempt_id)!=value['physical_attempt_id']
            or original.status!='FAILED' or not original.accepted_facts
            or original.initialization_id!=attempt.initialization_id
            or original.input_sha256!=attempt.input_sha256
            or original.batch_digest!=attempt.batch_digest
            or physical.input_digest!=run.input_digest):
        raise ValueError('Second hop physical input/attempt ownership differs')
    return physical


def resume(*, origin_run_id, execution_revision, expected, archive_path, second_hop=None, final_third_hop=False,
           final_interrupted_fourth_hop=False, final_failed_fifth_hop=False, final_interrupted_sixth_hop=False,
           finite_continuation=None, terminal_continuation=None, terminal_retry=None):
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
    flags=(final_third_hop,final_interrupted_fourth_hop,final_failed_fifth_hop,final_interrupted_sixth_hop)
    if (any(type(flag) is not bool for flag in flags) or sum(flags)>1
            or (any(flags) and second_hop is None)
            or (finite_continuation is not None and (second_hop is not None or any(flags)))):
        raise ValueError('Final continuation requires explicit physical pins and current cut')
    retry=terminal_retry is not None
    if retry:
        if terminal_continuation is not None:
            raise ValueError('Terminal retry cannot combine recovery modes')
        terminal_continuation=terminal_retry
    terminal=terminal_continuation is not None
    if terminal:
        if finite_continuation is not None or second_hop is not None or any(flags):
            raise ValueError("Terminal continuation cannot combine another recovery mode")
        finite_continuation=terminal_continuation
    old = CalculationRun.objects.get(pk=uuid.UUID(str(origin_run_id)))
    attempt = DailyFeedAttempt.objects.select_related('initialization__source').get(run=old)
    owner = attempt.initialization
    physical=None if second_hop is None else _second_hop_owner(old,attempt,second_hop,final_third_hop=final_third_hop,
        final_interrupted_fourth_hop=final_interrupted_fourth_hop,
        final_failed_fifth_hop=final_failed_fifth_hop,
        final_interrupted_sixth_hop=final_interrupted_sixth_hop)
    if finite_continuation is not None:
        physical=_finite_owner(old,attempt,finite_continuation,terminal=terminal,retry=retry)
    release=None
    if final_interrupted_sixth_hop or finite_continuation is not None:
        from release.native_identity import require_current
        release=require_current()
        revision_prefix=('native-terminal-retry-' if retry else 'native-terminal-' if terminal else 'native-finite-') if finite_continuation is not None else 'native-interrupted-sixth-'
        if execution_revision != revision_prefix+release['source_commit']:
            raise ValueError('Terminal interrupted execution revision must bind its packaged source')
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
            previous = read_outputs(parent,include_reports=False)
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
            if finite_continuation is not None:
                _empty_terminal_outputs(old)
                physical=_finite_owner(old,attempt,finite_continuation,terminal=terminal,retry=retry)
            if final_interrupted_sixth_hop:
                # This branch admits no partly persisted result or public view.
                # Quoted names come solely from the installed typed catalogue.
                from mta.runtime.relational_state import STORAGE_TABLES,table_sql
                with connection.cursor() as cursor:
                    for table in sorted({table_sql(key) for key in STORAGE_TABLES} |
                                        {'mta_state.report_export_cell'}):
                        cursor.execute('SELECT 1 FROM '+table+' WHERE vf_run_id=%s LIMIT 1',[old.pk])
                        if cursor.fetchone() is not None:
                            raise ValueError('Interrupted terminal leaf contains typed result rows')
                from mta.runtime.models import (PickProjection,ExcessProjection,FulfillmentProjection,
                    ExpediteProjection,PickPostProjection,DailySourceReceipt)
                from mta.runtime.offline_rrr_models import OfflineRrrColourSource
                if any(model.objects.filter(run=old).exists() for model in (
                        PickProjection,ExcessProjection,FulfillmentProjection,ExpediteProjection,
                        PickPostProjection,DailySourceReceipt,OfflineRrrColourSource)):
                    raise ValueError('Interrupted terminal leaf contains output source receipts')
            if second_hop is not None:
                physical=_second_hop_owner(old,attempt,second_hop,final_third_hop=final_third_hop,
                    final_interrupted_fourth_hop=final_interrupted_fourth_hop,
                    final_failed_fifth_hop=final_failed_fifth_hop,
                    final_interrupted_sixth_hop=final_interrupted_sixth_hop)
            expected_cut=(finite_continuation['current_revision_cut'] if finite_continuation is not None
                else expected['capture_cut'] if physical is None else second_hop['current_revision_cut'])
            original_ok=(attempt.status=='RUNNING' and attempt.phase=='VALIDATED'
                and bool(attempt.accepted_facts) and frozen.origin_id is None)
            second_ok=(physical is not None and frozen.origin_id==(
                uuid.UUID(old.input_payload['origin_run_id'])
                if any(flags) or finite_continuation is not None else physical.pk))
            if (epochs(owner.pk,lock=True) != expected_cut
                    or not (original_ok if physical is None else second_ok)
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
            if physical is None or final_interrupted_fourth_hop or final_interrupted_sixth_hop:
                if old.status != 'RUNNING':
                    raise ValueError('External interruption has already been reconciled')
                message = ('Explicit human-stop interruption reconciled; immutable input retained'
                    if final_interrupted_fourth_hop or final_interrupted_sixth_hop else
                    'Explicit external-deadline interruption reconciled; immutable input retained')
                fail_run(old, RuntimeError(message))
                old.refresh_from_db()
            from mta.mdm.integration_source import verify_predecessor, verify_capture, replace_working_inputs
            verify_predecessor(owner.source,parent,retry_capture=frozen,
                **({} if finite_continuation is None else
                   {'finite_prefix_digest':finite_continuation['prefix_digest']}))
            verify_capture(owner.source,snapshot)
            if physical is None or final_interrupted_fourth_hop or final_interrupted_sixth_hop:
                attempt.status='FAILED'
                attempt.error=dict(type='HumanInterruption' if final_interrupted_fourth_hop or final_interrupted_sixth_hop else 'ExternalInterruption',
                    message='Original input retained; explicit distinct continuation')
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
            finite_attempt={} if finite_continuation is None else {'recovery_origin':attempt}
            attempt_arguments=dict(initialization=owner,business_date=attempt.business_date,
                batch_id=attempt.batch_id,batch_digest=attempt.batch_digest,binding_digest=attempt.binding_digest,
                request_key=digest(dict(origin=str(attempt.attempt_id),revision=execution_revision)),
                input_sha256=attempt.input_sha256,predecessor=parent,
                predecessor_output_digest=attempt.predecessor_output_digest,run=run,
                status='RUNNING',phase='CALCULATE',archive_path=str(target),
                certification=attempt.certification,master_revision=attempt.master_revision,**finite_attempt)
            if finite_continuation is None:
                new_attempt=DailyFeedAttempt.objects.create(**attempt_arguments)
            from mta.mdm.daily_input import bind_capture
            daily = bind_capture(run,snapshot,request_digest=frozen.request_digest,origin=frozen)
            if finite_continuation is not None:
                from mta.runtime.captured_input import finite_manifest, terminal_manifest
                run.input_payload=(terminal_manifest if terminal else finite_manifest)(run,old,
                    expected_prefix_digest=finite_continuation['prefix_digest'],
                    packaged_source=release['source_commit'],**({'retry':True} if retry else {}))
            else:
                run.input_payload=manifest(run,old,final_interrupted_fourth_hop=final_interrupted_fourth_hop,
                    final_failed_fifth_hop=final_failed_fifth_hop,
                    final_interrupted_sixth_hop=final_interrupted_sixth_hop)
            run.input_manifest_digest=digest(run.input_payload)
            run.save(update_fields=['input_payload','input_manifest_digest'])
            if finite_continuation is not None:
                # SQL admission sees the completed canonical capture/reference.
                new_attempt=DailyFeedAttempt.objects.create(**attempt_arguments)
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
            continuation=dict(origin_run_id=str(old.pk),run_id=str(run.pk),
                origin_attempt_id=str(attempt.attempt_id),attempt_id=str(new_attempt.attempt_id),
                input_digest=run.input_digest,input_manifest_digest=run.input_manifest_digest)
            if final_interrupted_sixth_hop or finite_continuation is not None:
                continuation.update(kind=('failed-terminal-retry-v1' if retry else 'stopped-finite-terminal-v1' if terminal else 'stopped-terminal-sixth-finite-v1' if finite_continuation is not None
                    else 'human-interrupted-fifth-to-terminal-sixth-v1'),
                    origin_execution_revision=old.execution_revision,
                    execution_revision=execution_revision,native_release=release)
            atomic_json(target/'captured-origin.json',continuation)
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
        lineage=raw['lineage']
        if final_interrupted_sixth_hop or finite_continuation is not None:
            lineage=deepcopy(lineage)
            lineage['captured_continuation']=continuation
        try:
            finished = _finish_captured_day(run,raw,prior,opening_date,lineage,publication_opening,
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
