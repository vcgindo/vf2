"""Daily-chain ownership: own persisted predecessor, ordered actions, one run.

No oracle input, copied legacy state or secondary child-run persistence exists
in this service. Parent locking freezes which actions a next day consumes.
"""
from copy import deepcopy
from datetime import date, datetime
import uuid

from django.db import connection, transaction
from django.conf import settings

from mta.planning.engine import calculate_current_day
from mta.runtime.models import CalculationRun, RunCommand
from mta.runtime.services import read_outputs, finish_run, fail_run
from mta.serialization import storage, digest
from mta.temporal.chain import calculate_day
from mta.temporal.actions import apply_command
from mta.runtime.validation_storage import read_input, store_input

KIND='DAILY_CHAIN'
BOUNDARIES=('controls','final-bpr-bluezone','dbm-imported','final-suspensions',
            'final-suggestions','post-rule-reports','btr-insights','closing-state')


def command_state(run, state, *, through_date=None):
    """Verify every action's before/after chain; never mutate completed output."""
    state=deepcopy(state)
    receipts=[]
    last_date=run.business_date
    for event in run.commands.order_by('id'):
        if digest(event.payload)!=event.digest or digest(state)!=event.before_digest:
            raise ValueError('Command input/ordering drift')
        command=event.payload
        event_date=datetime.fromisoformat(command['timestamp']).date()
        if event_date<last_date or (through_date is not None and event_date>through_date):
            raise ValueError('Command date outside its temporal execution boundary')
        last_date=event_date
        if event.state_manifest:
            from mta.runtime.relational_state import load_image
            for name,metadata in event.state_manifest.items():
                state[name]=load_image(run,metadata)
        else:
            state=storage(apply_command(state,command['operation'],
                        [tuple(k) for k in command['selected']],command['timestamp']))
        if digest(state)!=event.after_digest:
            raise ValueError('Command output drift')
        receipts.append(dict(id=event.pk,digest=event.digest,before=event.before_digest,after=event.after_digest))
    return state,receipts


@transaction.atomic
def record_command(run, *, operation, selected, timestamp, actor, idempotency_key):
    if not isinstance(idempotency_key,str) or not 1<=len(idempotency_key)<=120:
        raise ValueError('Explicit bounded idempotency key required')
    if not isinstance(actor,str) or not actor:
        raise ValueError('Command actor required')
    payload=storage(dict(operation=operation,selected=selected,timestamp=timestamp,actor=actor))
    parent=CalculationRun.objects.select_for_update().get(pk=run.pk)
    if parent.kind!=KIND:raise ValueError('Commands require a daily-chain run')
    output=read_outputs(parent)
    state,_=command_state(parent,output['DBMFinal'][0])
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
    result=storage(apply_command(state,operation,[tuple(k) for k in selected],timestamp))
    event=RunCommand.objects.create(run=parent,idempotency_key=idempotency_key,payload=payload,
        digest=digest(payload),before_digest=digest(state),after_digest=digest(result))
    from mta.runtime.relational_state import save_image
    changed={name for name in state if state[name]!=result[name]}
    if changed-{'NormAcceptanceTbl','NormsInSleepModeTbl','Suggestions'}:
        raise ValueError('Unexpected action state writer')
    event.state_manifest={name:save_image(parent,'action/'+str(event.pk)+'/'+name,
        'closing/dbm/'+name,result[name]) for name in changed}
    # A no-change accepted command is still distinguishable from legacy events.
    if not event.state_manifest:
        event.state_manifest={'NormAcceptanceTbl':save_image(parent,'action/'+str(event.pk)+'/NormAcceptanceTbl',
            'closing/dbm/NormAcceptanceTbl',result['NormAcceptanceTbl'])}
    event.save(update_fields=['state_manifest'])
    return event


def execute_day(*, day, profile, execution_revision, predecessor=None, opening=None,
                report_exceptions=None, mdm_source=None, mdm_retry=None):
    if not transaction.get_autocommit():raise ValueError('Daily service owns the durable transaction boundary')
    if not isinstance(execution_revision,str) or not 1<=len(execution_revision)<=80:
        raise ValueError('Explicit execution revision required')
    if (predecessor is None)==(opening is None):raise ValueError('Exactly one initial opening or persisted predecessor required')
    if mdm_source is not None and mdm_retry is not None:
        raise ValueError('Choose a fresh MDM capture or one frozen retry capture')
    if not profile.get('delivery'):raise ValueError('Complete selected daily delivery profile required')
    day,profile=storage(day),storage(profile)
    publication_enabled = bool(profile.get('daily_publication') or
                               getattr(settings, 'VF_MTA_DAILY_PUBLICATION', False))
    today=date.fromisoformat(day['business_date'])
    with transaction.atomic():
        if mdm_source is not None or mdm_retry is not None:
            # Must be the transaction's first statement. Queue rows, histories,
            # task headers and subtasks then share one PostgreSQL snapshot.
            with connection.cursor() as cursor:
                cursor.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ')
        parent=None
        if predecessor is not None:
            parent=CalculationRun.objects.select_for_update().get(pk=predecessor.pk)
            if parent.kind!=KIND or parent.business_date>=today:
                raise ValueError('Invalid daily predecessor')
            previous=read_outputs(parent)
            if parent.input_payload['profile']['delivery']['site_code']!=profile['delivery']['site_code']:
                raise ValueError('Predecessor belongs to another site')
            prior=deepcopy(previous['ClosingState'][0])
            del previous  # The predecessor trace is verified, not the next day's working state.
            prior['dbm'],commands=command_state(parent,prior['dbm'],through_date=today)
            opening_date=parent.business_date.isoformat()
            lineage=dict(run_id=str(parent.pk),output_digest=parent.output_digest,commands=commands)
            initial=None
        else:
            initial=storage(opening)
            if not isinstance(initial.get('identity'),str) or not initial['identity']:
                raise ValueError('Explicit initial timeline identity required')
            prior=deepcopy(initial['state'])
            opening_date=initial['opening_date']
            if date.fromisoformat(opening_date)>=today:raise ValueError('Opening must precede current facts')
            lineage=dict(opening_identity=initial['identity'],opening_digest=digest(initial))
        publication_opening = ({'supplier': deepcopy(prior['supplier'])}
            if publication_enabled else None)
        raw=dict(schema='fresh-daily-chain-v1',day=day,profile=profile,opening=initial,
                 lineage=lineage,report_exceptions=storage(report_exceptions or {}))
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
                    read_outputs(repeated.run)
                    return repeated.run
                active_leaf_ids=list(MdmDailyInputCapture.objects.filter(
                    source_id=origin_capture.source_id,status='CAPTURED',retries__isnull=True)
                    .values_list('run_id',flat=True))
                if (origin_capture.run.status!='FAILED' or origin_capture.status!='CAPTURED'
                        or active_leaf_ids!=[origin_capture.run_id]
                        or origin_capture.request_digest!=request_digest):
                    raise ValueError('MDM retry does not match this failed daily request')
                origin_raw=read_input(origin_capture.run)
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
                    read_outputs(repeated.run)
                    return repeated.run
                capture_snapshot=select_capture(mdm_source,nms_active=nms_active,
                    task_status_log_horizon=task_horizon)
            # The caller's current full raw feed is the new run's base.  The
            # predecessor remains immutable and supplies closing state only.
            base_master=raw['day']['raw_master']
            if origin_capture is None:
                capture_snapshot=compose_pair_exclusions(capture_snapshot,base_master)
            composed=compose(capture_snapshot,base_master,last_run_date=opening_date)
            if origin_capture is None:
                capture_snapshot=capture_pending_conflicts(capture_snapshot,mdm_source,composed)
                capture_snapshot=capture_prune_candidates(capture_snapshot,mdm_source,today)
            raw['day']['raw_master']=storage(composed)
            raw['day']['exclusions']=deepcopy(capture_snapshot['pair_exclusions'])
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
        source_digest=digest(raw)
        existing=CalculationRun.objects.filter(input_digest=source_digest,execution_revision=execution_revision).first()
        if existing is not None:
            if existing.kind!=KIND or existing.predecessor_id!=(parent.pk if parent else None):
                raise ValueError('Daily run identity drift')
            read_outputs(existing)
            return existing
        if parent and parent.successors.filter(status__in=('RUNNING','SUCCEEDED')).exists():
            raise ValueError('Predecessor already consumed; no implicit timeline fork')
        new_id=uuid.uuid4()
        fields=dict(id=new_id,input_digest=source_digest,input_payload=store_input(new_id,raw),execution_revision=execution_revision,
                    kind=KIND,business_date=today,predecessor=parent)
        if parent is None:
            # A unique root key serializes concurrent initial starts without
            # importing a second timeline/run hierarchy. A new intentional
            # trial uses an explicit new identity or execution revision.
            opening_key=digest(dict(identity=initial['identity'],revision=execution_revision))
            run,created=CalculationRun.objects.get_or_create(opening_key=opening_key,defaults=fields)
            if not created:
                if run.input_digest!=source_digest or read_input(run)!=raw:
                    raise ValueError('Opening already used for different facts; explicit new trial required')
                read_outputs(run)
                return run
        else:
            run=CalculationRun.objects.create(**fields)
        if capture_snapshot is not None:
            from mta.mdm.daily_input import bind_capture
            bind_capture(run,capture_snapshot,request_digest=request_digest,origin=origin_capture)
        if publication_enabled:
            from mta.presentation.daily_requests import bind as bind_requests
            from mta.presentation.ancillary_live import bind_snapshots
            bind_requests(run, raw['request_inputs'])
            bind_snapshots(run, raw['remark_inputs'])
    try:
        result=calculate_day(prior,opening_date,raw['day'],raw['profile'],str(run.pk),
            lambda source:(calculate_current_day(source),str(run.pk)),raw['report_exceptions'])
        if [r['boundary'] for r in result['MajorBoundaries']]!=list(BOUNDARIES):
            raise ValueError('Incomplete daily boundary roster')
        result['Lineage']=[lineage]
        return finish_run(run,result,expected_digest=source_digest,
                          publication_opening=publication_opening)
    except Exception as error:
        fail_run(run,error)
        raise
