"""Daily-chain ownership: own persisted predecessor, ordered actions, one run.

No oracle input, copied legacy state or secondary child-run persistence exists
in this service. Parent locking freezes which actions a next day consumes.
"""
from copy import deepcopy
from datetime import date, datetime

from django.db import transaction

from mta.planning.engine import calculate_current_day
from mta.runtime.models import CalculationRun, RunCommand
from mta.runtime.services import read_outputs, finish_run, fail_run
from mta.serialization import storage, digest
from mta.temporal.chain import calculate_day
from mta.temporal.actions import apply_command

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
    return RunCommand.objects.create(run=parent,idempotency_key=idempotency_key,payload=payload,
        digest=digest(payload),before_digest=digest(state),after_digest=digest(result))


def execute_day(*, day, profile, execution_revision, predecessor=None, opening=None, report_exceptions=None):
    if not transaction.get_autocommit():raise ValueError('Daily service owns the durable transaction boundary')
    if not isinstance(execution_revision,str) or not 1<=len(execution_revision)<=80:
        raise ValueError('Explicit execution revision required')
    if (predecessor is None)==(opening is None):raise ValueError('Exactly one initial opening or persisted predecessor required')
    if not profile.get('delivery'):raise ValueError('Complete selected daily delivery profile required')
    day,profile=storage(day),storage(profile)
    today=date.fromisoformat(day['business_date'])
    with transaction.atomic():
        parent=None
        if predecessor is not None:
            parent=CalculationRun.objects.select_for_update().get(pk=predecessor.pk)
            if parent.kind!=KIND or parent.business_date>=today:
                raise ValueError('Invalid daily predecessor')
            previous=read_outputs(parent)
            if parent.input_payload['profile']['delivery']['site_code']!=profile['delivery']['site_code']:
                raise ValueError('Predecessor belongs to another site')
            prior=deepcopy(previous['ClosingState'][0])
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
        raw=dict(schema='fresh-daily-chain-v1',day=day,profile=profile,opening=initial,
                 lineage=lineage,report_exceptions=storage(report_exceptions or {}))
        source_digest=digest(raw)
        existing=CalculationRun.objects.filter(input_digest=source_digest,execution_revision=execution_revision).first()
        if existing is not None:
            if existing.kind!=KIND or existing.predecessor_id!=(parent.pk if parent else None):
                raise ValueError('Daily run identity drift')
            read_outputs(existing)
            return existing
        if parent and parent.successors.filter(status__in=('RUNNING','SUCCEEDED')).exists():
            raise ValueError('Predecessor already consumed; no implicit timeline fork')
        fields=dict(input_digest=source_digest,input_payload=raw,execution_revision=execution_revision,
                    kind=KIND,business_date=today,predecessor=parent)
        if parent is None:
            # A unique root key serializes concurrent initial starts without
            # importing a second timeline/run hierarchy. A new intentional
            # trial uses an explicit new identity or execution revision.
            opening_key=digest(dict(identity=initial['identity'],revision=execution_revision))
            run,created=CalculationRun.objects.get_or_create(opening_key=opening_key,defaults=fields)
            if not created:
                if run.input_digest!=source_digest or run.input_payload!=raw:
                    raise ValueError('Opening already used for different facts; explicit new trial required')
                read_outputs(run)
                return run
        else:
            run=CalculationRun.objects.create(**fields)
    try:
        result=calculate_day(prior,opening_date,raw['day'],raw['profile'],str(run.pk),
            lambda source:(calculate_current_day(source),str(run.pk)),raw['report_exceptions'])
        if [r['boundary'] for r in result['MajorBoundaries']]!=list(BOUNDARIES):
            raise ValueError('Incomplete daily boundary roster')
        result['Lineage']=[lineage]
        return finish_run(run,result,expected_digest=source_digest)
    except Exception as error:
        fail_run(run,error)
        raise
