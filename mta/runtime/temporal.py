"""Daily-chain ownership: own persisted predecessor, ordered actions, one run.

No oracle input, copied legacy state or secondary child-run persistence exists
in this service. Parent locking freezes which actions a next day consumes.
"""
from copy import deepcopy
from datetime import date, datetime, timedelta
import uuid
import logging
from time import perf_counter

from django.db import connection, transaction
from django.conf import settings

from mta.planning.engine import calculate_current_day
from mta.runtime.models import CalculationRun, RunCommand
from mta.runtime.services import read_outputs, finish_run, fail_run
from mta.serialization import storage, digest
from mta.temporal.chain import calculate_day
from mta.temporal.actions import apply_command
from mta.runtime.input_reader import read_input
from mta.runtime.opening_scope import opening_operation, release_opening, sealed_identity
from mta.application.stage_observation import operation, stage

KIND='DAILY_CHAIN'
BOUNDARIES=('controls','final-bpr-bluezone','dbm-imported','final-suspensions',
            'final-suggestions','post-rule-reports','btr-insights','closing-state')
logger = logging.getLogger(__name__)


def resolved_pick_root(value):
    from pathlib import Path
    return str(Path(value).resolve(strict=True))


def prepare_native_opening(owner, frame, profile, opening, predecessor):
    """Do complete immutable root copying/comparison before the writer snapshot.

    The caller must compare this exact seal with the locked initialization and
    still perform its live source/admission checks inside the transaction.
    """
    identity = (sealed_identity(owner), owner.source.digest)
    if storage(frame['profile']) != profile:
        raise ValueError('Native daily configuration differs from its initialization')
    if predecessor is not None:
        return identity, None
    initial = storage(opening)
    # The ordinary native entry already passes this very immutable opening.
    # Other callers retain the complete normalized value comparison.
    if opening is not frame['opening'] and initial != storage(frame['opening']):
        raise ValueError('Native initial opening differs from its typed initialization')
    if not isinstance(initial.get('identity'), str) or not initial['identity']:
        raise ValueError('Explicit initial timeline identity required')
    return identity, (initial, deepcopy(initial['state']), initial['opening_date'],
        dict(opening_identity=initial['identity'], opening_digest=digest(initial)))


def request_input(*, day, profile, initial, lineage, report_exceptions=None,
                  finalization_binding=None, initialization_binding=None,
                  daily_input_sha256=None, complete_pick=False, pick_output_root=None,
                  pick_config_sha256=None, shipment_sha256=None, scope_request=None):
    """Exact pre-capture identity shared by execution and read-only inspection."""
    raw=dict(schema='fresh-daily-chain-v1',day=day,profile=profile,opening=initial,
             lineage=lineage,report_exceptions=storage(report_exceptions or {}))
    if finalization_binding is not None: raw['finalization_binding']=finalization_binding
    if initialization_binding is not None:
        raw['initialization_binding']=initialization_binding
        raw['daily_input_sha256']=daily_input_sha256
    if complete_pick: raw['pick_output_root']=pick_output_root
    if pick_config_sha256 is not None: raw['pick_config_sha256']=pick_config_sha256
    if shipment_sha256 is not None: raw['shipment_sha256']=shipment_sha256
    if scope_request is not None: raw['scope_request']=storage(scope_request)
    return raw


def daily_sources_enabled(profile):
    """Explicit captured input overrides a serving default, including false."""
    if 'daily_publication' in profile:
        if type(profile['daily_publication']) is not bool:
            raise ValueError('daily_publication must be an explicit boolean')
        return profile['daily_publication']
    return bool(getattr(settings, 'VF_MTA_DAILY_PUBLICATION', False))


def replay_completed(existing, *, complete_pick=False, pick_output_root=None, report_disposition=None):
    """Verify a completed run before restoring derived files; never calculate."""
    from mta.application.native_report_disposition import verify_replay
    verify_replay(existing, existing.production_manifest.get('lineage'), report_disposition)
    output = read_outputs(existing,include_reports=False)
    if complete_pick:
        from mta.application.complete_daily_batch_files import write_run_pick_files
        write_run_pick_files(existing.pk, output['ClosingState'][0]['complete'], pick_output_root)
    return existing


def command_state(run, state, *, through_date=None, domain='dbm'):
    """Verify every action's before/after chain; never mutate completed output."""
    state=deepcopy(state)
    receipts=[]
    last_date=run.business_date
    for event in run.commands.filter(phase_acceptance__isnull=True).order_by('id'):
        if digest(event.payload)!=event.digest:
            raise ValueError('Command input/ordering drift')
        command=event.payload
        event_date=datetime.fromisoformat(command['timestamp']).date()
        if event_date<last_date or (through_date is not None and event_date>through_date):
            raise ValueError('Command date outside its temporal execution boundary')
        last_date=event_date
        from mta.domain.elephant_orders import ACTION
        event_domain = 'orders' if command.get('operation') == ACTION else 'dbm'
        if event_domain != domain:
            continue
        if digest(state)!=event.before_digest:
            raise ValueError('Command input/ordering drift')
        if event.state_manifest:
            from mta.runtime.relational_state import load_image
            if domain == 'orders' and (set(event.state_manifest) != {'ElephantOrders'}
                    or event.state_manifest['ElephantOrders']['table'] != 'BPR/ElephantOrders'):
                raise ValueError('Elephant command typed owner differs')
            for name,metadata in event.state_manifest.items():
                state[name]=load_image(run,metadata)
        else:
            if domain == 'orders':
                raise ValueError('Elephant command requires its typed action image')
            state=storage(apply_command(state,command['operation'],
                        [tuple(k) for k in command['selected']],command['timestamp']))
        if digest(state)!=event.after_digest:
            raise ValueError('Command output drift')
        receipts.append(dict(id=event.pk,digest=event.digest,before=event.before_digest,after=event.after_digest))
    return state,receipts


def command_states(run, closing, *, through_date=None):
    """Reconstruct each action owner and retain the single global event order."""
    result = deepcopy(closing)
    result['dbm'], receipts = command_state(run, result['dbm'], through_date=through_date)
    if 'orders' in result:
        result['orders'], order_receipts = command_state(run, result['orders'],
            through_date=through_date, domain='orders')
        receipts += order_receipts
    return result, sorted(receipts, key=lambda row: row['id'])


@transaction.atomic
def record_command(run, *, operation, selected, timestamp, actor, idempotency_key):
    if not isinstance(idempotency_key,str) or not 1<=len(idempotency_key)<=120:
        raise ValueError('Explicit bounded idempotency key required')
    if not isinstance(actor,str) or not actor:
        raise ValueError('Command actor required')
    payload=storage(dict(operation=operation,selected=selected,timestamp=timestamp,actor=actor))
    parent=CalculationRun.objects.select_for_update().get(pk=run.pk)
    if parent.kind!=KIND:raise ValueError('Commands require a daily-chain run')
    output=read_outputs(parent,include_reports=False)
    from mta.domain.elephant_orders import ACTION, apply_due_dates
    closing,_=command_states(parent,output['ClosingState'][0])
    domain = 'orders' if operation == ACTION else 'dbm'
    state=closing[domain]
    existing=parent.commands.filter(idempotency_key=idempotency_key).first()
    if existing:
        if existing.payload!=payload:raise ValueError('Idempotency key has different command facts')
        return existing
    event_date=datetime.fromisoformat(payload['timestamp']).date()
    previous_event=parent.commands.order_by('-id').first()
    last_date=(datetime.fromisoformat(previous_event.payload['timestamp']).date()
               if previous_event else parent.business_date)
    if event_date<last_date:
        raise ValueError('Command date precedes its parent or prior command')
    if parent.successors.filter(status__in=('RUNNING','SUCCEEDED')).exists():
        raise ValueError('Daily output has already been consumed; act on the current run')
    result=storage(apply_due_dates(state,selected) if domain == 'orders' else
                   apply_command(state,operation,[tuple(k) for k in selected],timestamp))
    event=RunCommand.objects.create(run=parent,idempotency_key=idempotency_key,payload=payload,
        digest=digest(payload),before_digest=digest(state),after_digest=digest(result),state_sealed=False)
    from mta.runtime.relational_state import save_image
    changed={name for name in state if state[name]!=result[name]}
    allowed = {'ElephantOrders'} if domain == 'orders' else {'NormAcceptanceTbl','NormsInSleepModeTbl','Suggestions'}
    if changed-allowed:
        raise ValueError('Unexpected action state writer')
    event.state_manifest={name:save_image(parent,'action/'+str(event.pk)+'/'+name,
        'closing/'+domain+'/'+name,result[name]) for name in changed}
    # A no-change accepted command is still distinguishable from legacy events.
    if not event.state_manifest:
        name = 'ElephantOrders' if domain == 'orders' else 'NormAcceptanceTbl'
        event.state_manifest={name:save_image(parent,'action/'+str(event.pk)+'/'+name,
            'closing/'+domain+'/'+name,result[name])}
    event.state_sealed=True
    # The final BEFORE trigger seals the row after the existing consumer guard
    # has checked its manifest-only update. Callers cannot set the seal directly.
    event.save(update_fields=['state_manifest'])
    return event


@opening_operation
def execute_day(*, day, profile, execution_revision, predecessor=None, opening=None,
                report_exceptions=None, mdm_source=None, mdm_retry=None,
                pick_output_root=None, pick_config_sha256=None, finalization_config=None,
                shipment_sha256=None, production_initialization=None, daily_input_sha256=None,
                consumer_opening=None, report_disposition=None, feed_attempt=None,
                prepared_arguments=None, prepared_state=None, _captured_retry=None,
                scope_request=None):
    if _captured_retry is not None:
        # The finite-reference kind uses this same production owner. Its
        # independently pinned stopped prefix is authenticated by resume;
        # frozen business arguments cannot be supplied alongside it.
        if any(value is not None for value in (day,profile,predecessor,opening,mdm_source,mdm_retry,
                feed_attempt,prepared_arguments,prepared_state,production_initialization,
                report_exceptions,pick_output_root,pick_config_sha256,finalization_config,
                shipment_sha256,daily_input_sha256,consumer_opening,report_disposition,scope_request)):
            raise ValueError('Captured continuation cannot replace its frozen native arguments')
        from mta.runtime.captured_recovery import resume
        return resume(execution_revision=execution_revision, **_captured_retry)
    started = perf_counter()
    if not transaction.get_autocommit():raise ValueError('Daily service owns the durable transaction boundary')
    if not isinstance(execution_revision,str) or not 1<=len(execution_revision)<=80:
        raise ValueError('Explicit execution revision required')
    if (predecessor is None)==(opening is None):raise ValueError('Exactly one initial opening or persisted predecessor required')
    if mdm_source is not None and mdm_retry is not None:
        raise ValueError('Choose a fresh MDM capture or one frozen retry capture')
    if not profile.get('delivery'):raise ValueError('Complete selected daily delivery profile required')
    day,profile=storage(day),storage(profile)
    if shipment_sha256 is not None and (
            not isinstance(shipment_sha256,str) or len(shipment_sha256)!=64
            or any(c not in '0123456789abcdef' for c in shipment_sha256)
            or 'shipment_input' not in day):
        raise ValueError('Shipment identity requires an explicit SHA256 and supplied day source')
    if 'operational_sources' in profile:
        from mta.application.operational_capture import CAPTURE_POLICY
        if profile['operational_sources'] != CAPTURE_POLICY:
            raise ValueError('Unsupported explicit operational source capture policy')
    from mta.application.daily_finalization import configuration
    finalization = configuration(profile)
    finalization_binding = None
    native = production_initialization is not None
    if scope_request is not None:
        from mta.runtime.production_scope import validate_request
        validate_request(scope_request)
        from mta.runtime.runtime_report_request import SCHEMA as PLACEMENT_SCHEMA
        placement_full=scope_request.get('schema')==PLACEMENT_SCHEMA and scope_request.get('scope')=='Full'
        if (not native or (mdm_retry is not None and not placement_full) or feed_attempt is not None
                or report_disposition is not None or type(profile.get('daily_publication')) is not bool):
            raise ValueError('UptoBPR requires an original native capture and explicit publication mode')
    from mta.application.native_report_disposition import RETRIES
    if report_disposition is not None or execution_revision in RETRIES.values():
        if (report_disposition not in RETRIES or not native or mdm_retry is None or report_exceptions
                or execution_revision != RETRIES[report_disposition]):
            raise ValueError('Exact native report disposition requires a frozen native retry')
    if 'native_upload_audit' in profile and not native:
        raise ValueError('Native upload audit requires production initialization')
    prepared_root = None
    master_reuse = None
    master_change = None
    if native:
        from mta.mdm.initialization_contract import sha
        sha(daily_input_sha256, 'native daily input')
        if finalization_config is not None or report_exceptions:
            raise ValueError('Native daily execution requires unchanged calculations')
        if finalization is None:
            raise ValueError('Native daily execution requires initialized finalization configuration')
    elif finalization is not None:
        from mta.application.daily_finalization import validate_supplement
        finalization_binding = validate_supplement(finalization_config, profile, opening)
    elif finalization_config is not None:
        raise ValueError('Finalization supplement requires its explicit policy')
    if finalization is not None and mdm_source is None and mdm_retry is None:
        raise ValueError('Generic finalization requires an explicit owned task/MDM capture source')
    complete_pick = profile.get('complete_pick') is not None
    if finalization is not None and not complete_pick:
        raise ValueError('Generic finalization requires the complete Pick producer')
    if complete_pick != (pick_output_root is not None):
        raise ValueError('Complete Pick policy and explicit owned output root must be supplied together')
    if pick_config_sha256 is not None and not complete_pick:
        raise ValueError('Complete Pick configuration identity requires complete Pick')
    if complete_pick:
        pick_output_root = resolved_pick_root(pick_output_root)
        if profile['complete_pick'] != {'policy': 'canonical-tied-order-v1'}:
            raise ValueError('Unsupported complete Pick policy')
    publication_enabled = daily_sources_enabled(profile)
    today=date.fromisoformat(day['business_date'])
    from mta.mdm.supplier_revisions import source_lock
    supplier_lock_source = mdm_source.pk if mdm_source is not None else None
    if mdm_retry is not None:
        from mta.runtime.mdm_daily_models import MdmDailyInputCapture
        supplier_lock_source = MdmDailyInputCapture.objects.get(
            run_id=getattr(mdm_retry, 'pk', mdm_retry)).source_id
    if native:
        # Sealed opening decoding/hashing is not write-transaction work. The
        # locked initialization/source identities and all live owners are still
        # checked inside the capture snapshot below.
        from mta.mdm.production_families import prepare_opening, frame_for_daily
        from mta.mdm.initialization import read_initialized_input
        prepared_owner = prepare_opening(production_initialization.source)
        prepared_frame = frame_for_daily(prepared_owner, predecessor)
        prepared_seal, prepared_root = prepare_native_opening(
            prepared_owner, prepared_frame, profile, opening, predecessor)
        del prepared_frame, prepared_owner
    # Acquire before REPEATABLE READ establishes its first snapshot, including
    # before any source FK/header locks. Release after freezing, not calculation.
    with source_lock(supplier_lock_source), transaction.atomic():
        if mdm_source is not None or mdm_retry is not None:
            # Must be the transaction's first statement. Queue rows, histories,
            # task headers and subtasks then share one PostgreSQL snapshot.
            with connection.cursor() as cursor:
                cursor.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ')
        if native and scope_request is not None:
            from mta.runtime.scope_consumers import lock_history_owners
            lock_history_owners()
        initialization_binding = None
        if native:
            from mta.runtime.models import ProductionInitialization
            from mta.mdm.initialization import read_initialized_input
            from mta.mdm.production_families import require_initialization
            initialized = ProductionInitialization.objects.select_for_update().select_related('source').get(
                pk=production_initialization.pk)
            if prepared_state is not None:
                from mta.runtime.accepted_daily import epochs
                if (prepared_state.initialization_id!=str(initialized.pk)
                        or prepared_state.source_digest!=initialized.source.digest
                        or tuple(epochs(initialized.pk,lock=True))!=prepared_state.revisions.as_tuple()):
                    raise ValueError('Native preparation changed before capture')
            if prepared_arguments is not None:
                from mta.runtime.daily_feed_models import DailyFeedAttempt
                from mta.runtime.accepted_daily import check
                prepared_attempt = DailyFeedAttempt.objects.select_for_update(of=('self',)).select_related(
                    'initialization__source','certification','master_revision').get(pk=feed_attempt)
                check(prepared_attempt, prepared_arguments, locked=True)
            if (sealed_identity(initialized), initialized.source.digest) != prepared_seal:
                raise ValueError('Native initialization changed after immutable opening preparation')
            require_initialization(initialized.source)
            if mdm_source is not None and mdm_source.pk != initialized.source_id:
                raise ValueError('Native daily source differs from its initialization')
            if mdm_retry is not None and supplier_lock_source != initialized.source_id:
                raise ValueError('Native retry source differs from its initialization')
            if mdm_source is None and mdm_retry is None:
                raise ValueError('Native daily execution requires its owned MDM source/capture')
            initialization_binding = dict(id=str(initialized.pk), source_digest=initialized.source.digest,
                input_sha256=initialized.input_sha256, content_digest=initialized.input_digest,
                configuration_digest=initialized.configuration_digest)
            if predecessor is None:
                if consumer_opening is None:
                    raise ValueError('Native root requires explicitly declared consumer opening')
                from mta.runtime.production_daily import initialize_consumers
                initialize_consumers(initialized, consumer_opening, daily_input_sha256)
            elif consumer_opening is not None:
                raise ValueError('Native successor cannot replace consumer ownership')
        elif mdm_source is not None and mdm_source.receipt.get('schema') == 'fresh-production-mdm-source-v1':
            raise ValueError('Native source requires its initialization boundary')
        parent=None
        if predecessor is not None:
            parent=CalculationRun.objects.select_for_update().get(pk=predecessor.pk)
            if parent.kind!=KIND or parent.business_date>=today:
                raise ValueError('Invalid daily predecessor')
            parent_profile = read_input(parent, components=('profile',))['profile']
            if (configuration(parent_profile) is not None or finalization is not None):
                if configuration(parent_profile) != finalization:
                    raise ValueError('Generic finalization predecessor configuration differs')
                if digest(parent_profile) != digest(profile):
                    raise ValueError('Generic finalization requires its own unchanged configuration')
                parent_capture = getattr(parent, 'mdm_input_capture', None)
                selected_source_id = mdm_source.pk if mdm_source is not None else None
                if mdm_retry is not None:
                    from mta.runtime.mdm_daily_models import MdmDailyInputCapture
                    retry_capture = MdmDailyInputCapture.objects.select_related('run').get(
                        run_id=getattr(mdm_retry, 'pk', mdm_retry))
                    if (retry_capture.run.status != 'FAILED'
                            or retry_capture.run.predecessor_id != parent.pk
                            or retry_capture.run.business_date != today):
                        raise ValueError('Cohort1 retry predecessor or date differs')
                    selected_source_id = retry_capture.source_id
                if (parent_capture is None or parent_capture.status != 'CONSUMED'
                        or parent_capture.source_id != selected_source_id):
                    raise ValueError('Generic finalization requires its own consumed task source')
                from mta.application.daily_finalization import ACTIVE_POLICY
                if finalization['policy'] == ACTIVE_POLICY and not native:
                    from mta.presentation.operational_admission import verify
                    verify(parent, selected=False)
            previous=read_outputs(parent,include_reports=False)
            if finalization is not None:
                from mta.application.daily_finalization import verify_successor
                verify_successor(previous, parent_profile, parent.business_date.isoformat())
            if parent.input_payload['profile']['delivery']['site_code']!=profile['delivery']['site_code']:
                raise ValueError('Predecessor belongs to another site')
            prior=deepcopy(previous['ClosingState'][0])
            del previous  # The predecessor trace is verified, not the next day's working state.
            prior,commands=command_states(parent,prior,through_date=today)
            opening_date=parent.business_date.isoformat()
            lineage=dict(run_id=str(parent.pk),output_digest=parent.output_digest,commands=commands)
            initial=None
        elif prepared_root is not None:
            initial, prior, opening_date, lineage = prepared_root
            if date.fromisoformat(opening_date)>=today:raise ValueError('Opening must precede current facts')
        else:
            initial=storage(opening)
            if not isinstance(initial.get('identity'),str) or not initial['identity']:
                raise ValueError('Explicit initial timeline identity required')
            prior=deepcopy(initial['state'])
            opening_date=initial['opening_date']
            if date.fromisoformat(opening_date)>=today:raise ValueError('Opening must precede current facts')
            lineage=dict(opening_identity=initial['identity'],opening_digest=digest(initial))
        if native:
            if today != date.fromisoformat(opening_date) + timedelta(days=1):
                raise ValueError('Native daily execution requires the immediately preceding day')
            if parent is not None:
                parent_binding = read_input(parent, components=('initialization_binding',)).get('initialization_binding')
                if parent_binding != initialization_binding:
                    raise ValueError('Native predecessor belongs to another initialization')
            lineage['initialization_id'] = str(initialized.pk)
        publication_opening = ({'supplier': deepcopy(prior['supplier'])}
            if publication_enabled else None)
        raw=request_input(day=day,profile=profile,initial=initial,lineage=lineage,
            report_exceptions=report_exceptions,finalization_binding=finalization_binding,
            initialization_binding=initialization_binding,daily_input_sha256=daily_input_sha256,
            complete_pick=complete_pick,pick_output_root=pick_output_root,
            pick_config_sha256=pick_config_sha256,shipment_sha256=shipment_sha256,
            scope_request=scope_request)
        capture_snapshot=None; origin_capture=None; request_digest=None
        if mdm_source is not None or mdm_retry is not None:
            from mta.mdm.daily_input import (apply_refresh_setting,
                capture_pending_conflicts, capture_prune_candidates, compose, compose_pair_exclusions,
                select_capture)
            request_digest=digest(raw)
            configuration_source=mdm_source
            if mdm_retry is not None:
                from mta.runtime.mdm_daily_models import MdmDailyInputCapture
                origin_capture=MdmDailyInputCapture.objects.select_for_update().select_related('run').get(
                    run_id=getattr(mdm_retry,'pk',mdm_retry))
                from mta.runtime.mdm_models import MdmSource
                configuration_source=MdmSource.objects.select_for_update().get(pk=origin_capture.source_id)
            if not native and configuration_source.receipt.get('schema') == 'fresh-production-mdm-source-v1':
                raise ValueError('Native source/capture requires its initialization boundary')
            from mta.runtime.mdm_configuration import capture_configuration_for_day
            nms_active, task_horizon = capture_configuration_for_day(
                prior['importer_settings'], predecessor=parent, source=configuration_source)
            if mdm_retry is not None:
                repeated=MdmDailyInputCapture.objects.select_related('run').filter(
                    source_id=origin_capture.source_id,request_digest=request_digest,
                    run__execution_revision=execution_revision).first()
                if repeated is not None:
                    if repeated.origin_id!=origin_capture.pk:
                        raise ValueError('Daily run identity drift')
                    if repeated.run.evidence_mode!='production':raise ValueError('Daily evidence policy identity drift')
                    return replay_completed(repeated.run, complete_pick=complete_pick,
                                            pick_output_root=pick_output_root, report_disposition=report_disposition)
                active_leaf_ids=list(MdmDailyInputCapture.objects.filter(
                    source_id=origin_capture.source_id,status='CAPTURED',retries__isnull=True)
                    .values_list('run_id',flat=True))
                if (origin_capture.run.status!='FAILED' or origin_capture.status!='CAPTURED'
                        or active_leaf_ids!=[origin_capture.run_id]
                        or origin_capture.request_digest!=request_digest
                        or origin_capture.run.predecessor_id != (parent.pk if parent else None)
                        or origin_capture.run.business_date != today
                        or origin_capture.run.execution_revision == execution_revision):
                    raise ValueError('MDM retry does not match this failed daily request')
                origin_raw=read_input(origin_capture.run, components=('mdm_input','request_inputs','remark_inputs'))
                capture_snapshot=deepcopy(origin_raw.get('mdm_input'))
                if not capture_snapshot or capture_snapshot['revision_digest']!=origin_capture.revision_digest:
                    raise ValueError('Failed MDM capture input drift')
                if capture_snapshot['nms_active']!=nms_active:
                    raise ValueError('NMSActive changed for frozen MDM retry')
                if capture_snapshot['configuration']['task_status_log_horizon']!=task_horizon:
                    raise ValueError('TaskStatusLogHorizon changed for frozen MDM retry')
            else:
                from mta.runtime.mdm_daily_models import MdmDailyInputCapture
                from mta.runtime.mdm_models import MdmSource
                mdm_source=MdmSource.objects.select_for_update().get(pk=mdm_source.pk)
                repeated=MdmDailyInputCapture.objects.select_related('run').filter(
                    source=mdm_source,request_digest=request_digest,
                    run__execution_revision=execution_revision).first()
                if repeated is not None:
                    if repeated.run.predecessor_id!=(parent.pk if parent else None):
                        raise ValueError('Daily run identity drift')
                    if repeated.run.evidence_mode!='production':raise ValueError('Daily evidence policy identity drift')
                    if scope_request is not None:
                        from mta.runtime.production_scope import captured_run
                        return captured_run(repeated.run,scope_request)
                    return replay_completed(repeated.run, complete_pick=complete_pick,
                                            pick_output_root=pick_output_root, report_disposition=report_disposition)
                capture_snapshot=select_capture(mdm_source,nms_active=nms_active,
                    task_status_log_horizon=task_horizon)
            from mta.mdm.integration_source import verify_predecessor
            if native:
                verify_predecessor(configuration_source, parent, retry_capture=origin_capture)
            else:
                verify_predecessor(configuration_source, parent)
            base_master=raw['day']['raw_master']
            from mta.application.daily_finalization import ACTIVE_POLICY
            if profile.get('complete_daily', {}).get('policy') == ACTIVE_POLICY:
                from mta.mdm.daily_input import nms_master_raw
                if capture_snapshot['nms_active'] is not True:
                    raise ValueError('Active finalization requires active NMS intake')
                if native and prepared_state is not None and parent is not None and origin_capture is None:
                    from mta.application.persistent_master import select
                    master_reuse=select(prior,profile,raw['day'],capture_snapshot,
                        parent.production_manifest.get('master_preparation'),prepared_state.revisions.as_tuple())
                if master_reuse is None:
                    base_master=nms_master_raw(prior)
                else:
                    from mta.application.persistent_master import NmsMasterRows
                    reference=dict(contract='native-nms-master-compatibility-v1',run_id=str(parent.pk),
                        output_digest=parent.output_digest,initialization_id=str(initialized.pk),
                        source_digest=initialized.source.digest,master_revision_id=prepared_state.master_revision_id)
                    base_master=NmsMasterRows(prior['consumer_context']['NMSAllItems'],reference=reference,plan=master_reuse.plan)
            if (native and prepared_state is not None and parent is not None
                    and origin_capture is None and master_reuse is None):
                from mta.application.persistent_master import changed
                master_change=changed(parent,profile,capture_snapshot,prepared_state.master_revision_id)
            if origin_capture is None:
                capture_snapshot=compose_pair_exclusions(capture_snapshot,base_master)
            # Native SetRunDate precedes NMSImportData. Preserve the sealed
            # legacy adapter's opening-date behavior outside native execution.
            composed=(base_master if master_reuse is not None else compose(capture_snapshot,base_master,
                last_run_date=today.isoformat() if native else opening_date))
            if profile.get('complete_daily', {}).get('policy') == ACTIVE_POLICY and not native:
                from django.conf import settings
                from mta.mdm.approval_hierarchy import project
                composed = project(composed,
                    path=getattr(settings, 'VF_MDM_APPROVAL_HIERARCHY_FILE', ''),
                    artifact_sha256=configuration_source.receipt['artifact_sha256'])
            if origin_capture is None:
                capture_snapshot=capture_pending_conflicts(capture_snapshot,mdm_source,composed)
                capture_snapshot=capture_prune_candidates(capture_snapshot,mdm_source,today)
            raw['day']['raw_master']=storage(composed)
            if profile.get('complete_daily', {}).get('policy') == ACTIVE_POLICY:
                from mta.mdm.supplier_capture import complete_feeds
                raw['day']['supplier_feeds'] = complete_feeds(capture_snapshot, prior)
            elif capture_snapshot['nms_active'] and 'supplier' in capture_snapshot:
                from mta.mdm.supplier_capture import feeds as supplier_feeds, require_format
                require_format(capture_snapshot, prior['importer_settings'])
                raw['day']['supplier_feeds'] = supplier_feeds(capture_snapshot)
            raw['day']['exclusions']=deepcopy(capture_snapshot['pair_exclusions'])
            from mta.mdm.integration_source import verify_capture, replace_working_inputs
            verify_capture(configuration_source, capture_snapshot)
            replace_working_inputs(capture_snapshot, prior, raw['day'], parent)
            apply_refresh_setting(prior['importer_settings'], capture_snapshot)
            raw['mdm_input']=capture_snapshot
        if publication_enabled:
            from mta.presentation.daily_requests import snapshot as request_snapshot
            from mta.presentation.ancillary_live import snapshot_all
            raw['request_inputs'] = (deepcopy(origin_raw.get('request_inputs'))
                if origin_capture is not None else request_snapshot())
            raw['remark_inputs'] = (deepcopy(origin_raw.get('remark_inputs', {}))
                if origin_capture is not None else snapshot_all(
                    business_date=today,
                    bpr_remark_horizon=profile.get('daily_publication_config', {}).get('bpr_remark_horizon')))
            # Optional explicit external shipment facts stay in the immutable
            # day input; absence remains unavailable, never an empty population.
            publication_opening['shipment_input'] = raw['day'].get('shipment_input')
            publication_opening['transporter_input'] = raw['day'].get('transporter_input')
            if 'production_report_policy' in raw['day']:
                publication_opening['production_report_policy'] = raw['day']['production_report_policy']
                publication_opening['production_report_opening'] = raw['day']['production_report_opening']
                publication_opening['production_report_schema'] = raw['day']['production_report_schema']
        batch_references, owner_references, content_identity = {}, {}, None
        staged_attempt = None
        if feed_attempt is not None:
            from mta.runtime.daily_feed_models import DailyFeedAttempt
            staged_attempt=DailyFeedAttempt.objects.select_for_update().get(pk=feed_attempt)
            if (not native or staged_attempt.initialization_id!=initialized.pk
                    or staged_attempt.business_date!=today or staged_attempt.input_sha256!=daily_input_sha256
                    or staged_attempt.status!='RUNNING' or staged_attempt.run_id is not None):
                raise ValueError('CSV attempt does not own this native day')
            if staged_attempt.accepted_facts:
                from mta.runtime.accepted_daily import references
                batch_references=references(staged_attempt)
        if prepared_state is not None:
            from mta.runtime.run_input_references import owners, identity
            from mta.runtime.input_storage import content_root
            owner_references=owners(initialized,raw,prepared_state.master_revision_id,
                unchanged=master_reuse is not None,parent=parent)
            content_identity=identity(initialized)
            source_digest=content_root(raw,content_identity,owner_references=owner_references,
                batch_references=batch_references)
        else:
            source_digest=digest(raw)
        disposition_binding = None
        effective_report_exceptions = raw['report_exceptions']
        if report_disposition is not None:
            from mta.application.native_report_disposition import admit
            disposition_binding = admit(requested=report_disposition, native=native,
                origin=origin_capture, parent=parent, initialization=initialized, raw=raw,
                request_digest=request_digest, execution_revision=execution_revision)
            effective_report_exceptions = {'native_report_disposition': disposition_binding}
        existing=CalculationRun.objects.filter(input_digest=source_digest,execution_revision=execution_revision).first()
        if existing is not None:
            if existing.kind!=KIND or existing.predecessor_id!=(parent.pk if parent else None):
                raise ValueError('Daily run identity drift')
            if existing.evidence_mode!='production':raise ValueError('Daily evidence policy identity drift')
            if scope_request is not None:
                from mta.runtime.production_scope import captured_run
                return captured_run(existing,scope_request)
            return replay_completed(existing, complete_pick=complete_pick,
                                    pick_output_root=pick_output_root, report_disposition=report_disposition)
        if parent and parent.successors.filter(status__in=('RUNNING','SUCCEEDED')).exists():
            raise ValueError('Predecessor already consumed; no implicit timeline fork')
        new_id=uuid.uuid4()
        fields=dict(id=new_id,input_digest=source_digest,input_payload={},execution_revision=execution_revision,
                    evidence_mode='production',
                    kind=KIND,business_date=today,predecessor=parent)
        if prepared_state is not None:
            from mta.runtime.capture_preparation import seed
            fields['production_manifest']={'ingestion_preparation':seed(prepared_state,reused=master_reuse is not None)}
        if disposition_binding is not None:
            fields['production_manifest'] = {'native_report_disposition': disposition_binding}
        if parent is None:
            # A unique root key serializes concurrent initial starts without
            # importing a second timeline/run hierarchy. A new intentional
            # trial uses an explicit new identity or execution revision.
            opening_key=digest(dict(identity=initial['identity'],revision=execution_revision))
            run,created=CalculationRun.objects.get_or_create(opening_key=opening_key,defaults=fields)
            if not created:
                if run.input_digest!=source_digest or read_input(run)!=raw:
                    raise ValueError('Opening already used for different facts; explicit new trial required')
                if run.evidence_mode!='production':raise ValueError('Daily evidence policy identity drift')
                if scope_request is not None:
                    from mta.runtime.production_scope import captured_run
                    return captured_run(run,scope_request)
                return replay_completed(run, complete_pick=complete_pick,
                                        pick_output_root=pick_output_root)
        else:
            run=CalculationRun.objects.create(**fields)
        if staged_attempt is not None:
            staged_attempt.run = run
            staged_attempt.save(update_fields=['run', 'updated_at'])
        if capture_snapshot is not None:
            from mta.mdm.daily_input import bind_capture
            daily_capture = bind_capture(run,capture_snapshot,request_digest=request_digest,origin=origin_capture)
        from mta.runtime.input_storage import save_input
        if native:
            from mta.runtime.production_daily import input_table
            options = (dict(version=3,batch_references=batch_references,owner_references=owner_references,
                            content_identity=content_identity) if prepared_state is not None else {})
            run.input_payload=save_input(run,raw,table_selector=input_table,**options)
        else:
            run.input_payload=save_input(run,raw)
        run.input_manifest_digest=digest(run.input_payload)
        run.save(update_fields=['input_payload','input_manifest_digest'])
        if 'operational_sources' in profile:
            from mta.runtime.operational_source import authorize_new_run
            authorize_new_run(run)
        if capture_snapshot is not None:
            from mta.mdm.native_audit import bind as bind_native_audit
            bind_native_audit(run, daily_capture, profile)
        if publication_enabled:
            from mta.presentation.daily_requests import bind as bind_requests
            from mta.presentation.ancillary_live import bind_snapshots
            bind_requests(run, raw['request_inputs'])
            bind_snapshots(run, raw['remark_inputs'])
        if prepared_state is not None:
            from mta.runtime.capture_preparation import seal
            consumer_snapshot=(raw.get('remark_inputs',{}).get('BPRReport_RemarkDetails')
                if scope_request is not None else None)
            seal(run,consumer_snapshot=consumer_snapshot)
    release_opening()
    logger.warning('daily_phase run=%s phase=input_capture seconds=%.6f', run.pk, perf_counter()-started)
    if scope_request is not None and not placement_full:
        from mta.runtime.production_scope import captured_run
        return captured_run(run,scope_request)
    return _finish_captured_day(run,raw,prior,opening_date,lineage,publication_opening,
        complete_pick,pick_output_root,effective_report_exceptions,finalization,native,
        master_reuse,master_change,capture_snapshot,disposition_binding)


def _finish_captured_day(run,raw,prior,opening_date,lineage,publication_opening,
        complete_pick,pick_output_root,effective_report_exceptions,finalization,native,
        master_reuse=None,master_change=None,capture_snapshot=None,disposition_binding=None):
    """The same calculation and sole atomic finish owner for fresh/reused input."""
    profile=raw['profile'];today=date.fromisoformat(raw['day']['business_date'])
    source_digest=run.input_digest
    try:
        calculated_at = perf_counter()
        def calculation(source,**owned):
            return (calculate_current_day(source,defer_pick=True,**owned) if complete_pick else
                    calculate_current_day(source,**owned)),str(run.pk)
        from mta.runtime.runtime_report_request import SCHEMA as PLACEMENT_SCHEMA
        report_work=None
        if raw.get('scope_request',{}).get('schema')==PLACEMENT_SCHEMA:
            from mta.runtime.runtime_report_execution import calculate_full
            result,report_work=calculate_full(run,prior,opening_date,raw['day'],raw['profile'],calculation,
                opening=publication_opening,report_exceptions=effective_report_exceptions,
                master_snapshot=capture_snapshot,prepared_master=master_reuse or master_change)
        else:
            result=calculate_day(prior,opening_date,raw['day'],raw['profile'],str(run.pk),calculation,
                effective_report_exceptions,native_daily=native,
                **({'master_snapshot':capture_snapshot} if native else {}),
                **({'prepared_master':master_reuse or master_change} if master_reuse is not None or master_change is not None else {}))
        logger.warning('daily_phase run=%s phase=calculation seconds=%.6f', run.pk, perf_counter()-calculated_at)
        completed=result.pop('_CompletedBoundaries')
        if completed!=list(BOUNDARIES):
            raise ValueError('Incomplete daily boundary roster')
        lineage = deepcopy(lineage)
        if disposition_binding is not None:
            lineage['native_report_disposition'] = disposition_binding
        result['Lineage']=[lineage]
        if finalization is not None:
            from mta.application.daily_finalization import verify_successor, verify_finalization_identity, ACTIVE_POLICY
            lineage['cohort1'] = result.pop('_Cohort1')
            # Active MDM archive/clear/task writers execute transactionally
            # in finish_run. Their markers cannot be complete before then.
            if finalization['policy'] != ACTIVE_POLICY:
                verify_successor(result, profile, today.isoformat())
            else:
                verify_finalization_identity(result,profile,today.isoformat())
        if complete_pick:
            source_digests = result.pop('_PickSourceDigests', None)
            if source_digests is not None:
                lineage['pick_source_digests'] = source_digests
            from mta.application.complete_daily_batch_files import write_run_pick_files
            with operation(str(run.pk)), stage('Pick_files'):
                write_run_pick_files(run.pk, result['ClosingState'][0]['complete'], pick_output_root)
        commit_at = perf_counter()
        with operation(str(run.pk)), stage('atomic_persistence'):
            finished = finish_run(run,result,expected_digest=source_digest,
                                  publication_opening=publication_opening,_report_work=report_work)
        logger.warning('daily_phase run=%s phase=commit seconds=%.6f', run.pk, perf_counter()-commit_at)
        return finished
    except Exception as error:
        fail_run(run,error)
        raise
