"""Canonical commands on immutable paused phases, consumed once downstream."""
from copy import deepcopy
from dataclasses import replace
from datetime import datetime
from django.db import connection,transaction
from mta.serialization import digest,storage

TABLES=('DBMMaster','Suggestions','NormAcceptanceTbl','NormsInSleepModeTbl')


def revision(run):
    with connection.cursor() as cursor:
        cursor.execute('SELECT mta.scope_action_revision(%s)',[run.pk])
        return cursor.fetchone()[0]


def restore(run,receipt):
    from mta.runtime.input_reader import read_input
    from mta.runtime.scoped_final import frozen_prior
    from mta.runtime import phase_state
    if receipt.run_id!=run.pk or not receipt.state_sealed or receipt.phase not in ('BPR','DBM'):
        raise ValueError('Scoped action requires its accepted BPR/DBM base')
    raw=read_input(run,components=('opening','day','profile','lineage','initialization_binding','mdm_input','execution_settings'))
    return phase_state.read(receipt.snapshot,prior=frozen_prior(run,raw),
        day=raw['day'],profile=raw['profile'],
        master_snapshot=raw['mdm_input'] if raw.get('initialization_binding') is not None else None)


def state_for(phase):
    from mta.temporal.day_phases import BprDay,DbmDay
    from mta.temporal.chain import dbm_action_state
    if type(phase) is BprDay:return storage(dbm_action_state(phase))
    if type(phase) is DbmDay:return storage({name:deepcopy(phase.final_dbm[name]) for name in TABLES})
    raise ValueError('Actions require the actual paused calculation phase')


def state_after(run,receipt,phase,*,expected_revision):
    """Validate exact canonical effects against every retained typed action image."""
    return _state_after(run,receipt,state_for(phase),phase.context.action_revision,
                        expected_revision=expected_revision)


def _dbm_action_base(run,receipt):
    """Read the four immutable action inputs under record's source/run locks.

    The accepted prefix and fresh input identity certify their frozen owner.
    Calculation continuation still restores and validates the complete phase.
    """
    from mta.runtime import phase_state,relational_state as typed
    from mta.runtime.input_reader import read_input
    from mta.runtime.scoped_final import accepted_prefix
    from mta.runtime.ingestion_context import sha
    if not connection.in_atomic_block:
        raise ValueError('Scoped DBM action read requires its owning transaction')
    read_input(run,components=())
    prefix,_capture=accepted_prefix(run,lock_capture=False)
    accepted=prefix[-1]
    if accepted.pk!=receipt.pk or accepted.digest!=receipt.digest:
        raise ValueError('Scoped DBM action accepted owner differs')
    manifest=accepted.snapshot.manifest
    refs=prefix[0].snapshot.manifest['references']
    if any(p.snapshot.manifest.get('schema')!=phase_state.SCHEMA
           or p.snapshot.manifest.get('phase')!=p.phase
           or p.snapshot.manifest.get('references')!=refs for p in prefix):
        raise ValueError('Scoped DBM action snapshot dependencies differ')
    initial=manifest['metadata'].get('action_revision',0)
    if type(initial) is not int or initial<0:
        raise ValueError('Scoped DBM action base revision differs')
    state={}
    for name in TABLES:
        logical='phase/DBM/dbm/'+name
        if manifest['state']['final_dbm'].get(name)!={'image':logical}:
            raise ValueError('Scoped DBM action table binding differs')
        item=manifest['images'].get(logical)
        if (type(item) is not dict or item.get('image')!=logical
                or item.get('table')!='DBM/'+name or type(item.get('count')) is not int
                or item['count']<0 or type(item.get('fields')) is not list
                or item['count'] and not item['fields']):
            raise ValueError('Scoped DBM action image descriptor differs')
        sha(item.get('digest'))
        columns=dict(phase_state.REGISTRY[item['table']]);seen=set()
        for field in item['fields']:
            if (not isinstance(field,(list,tuple)) or len(field)!=3
                    or field[0]!=field[1] or field[0] not in columns or field[0] in seen
                    or field[2] not in ('str','int','float','bool')):
                raise ValueError('Scoped DBM action image fields differ')
            seen.add(field[0])
        state[name]=typed.load_image(run,deepcopy(item),table_registry=phase_state.REGISTRY)
    return storage(state),initial


def _action_reader(run,receipt):
    # require_current has verified the native accepted-state guards for this
    # certified cut. Older/component owners retain the complete restore.
    if (receipt.phase=='DBM'
            and 'bpr_consumer_cut' in run.production_manifest.get('ingestion_preparation',{})):
        base,initial=_dbm_action_base(run,receipt)
        return lambda expected: _state_after(run,receipt,deepcopy(base),initial,
                                             expected_revision=expected)
    phase,_sources=restore(run,receipt)
    return lambda expected: state_after(run,receipt,phase,expected_revision=expected)


def _state_after(run,receipt,state,initial_revision,*,expected_revision):
    from mta.runtime.models import RunCommand
    from mta.runtime.relational_state import load_image
    from mta.temporal.actions import apply_command
    current=initial_revision
    for event in RunCommand.objects.filter(run=run,phase_acceptance=receipt).order_by('id'):
        if (not event.state_sealed or digest(event.payload)!=event.digest
                or event.scope_parent_revision!=current or digest(state)!=event.before_digest
                or not event.state_manifest or set(event.state_manifest)-set(TABLES[1:])):
            raise ValueError('Scoped action chain or typed owner differs')
        command=event.payload
        expected=storage(apply_command(state,command['operation'],
            [tuple(key) for key in command['selected']],command['timestamp']))
        for name,image in event.state_manifest.items():
            if image['image']!='action/'+str(event.pk)+'/'+name or image['table']!='DBM/'+name:
                raise ValueError('Scoped action image identity differs')
            state[name]=load_image(run,image)
        if state!=expected or digest(state)!=event.after_digest:
            raise ValueError('Scoped action canonical typed result differs')
        current=event.pk
    if type(expected_revision) is not int or current!=expected_revision or revision(run)!=expected_revision:
        raise ValueError('Scoped action consumer revision changed')
    return state


@transaction.atomic
def record(run_id,*,phase_id,phase_digest,expected_revision,operation,selected,
           timestamp,actor,idempotency_key):
    from mta.runtime.models import CalculationRun,RunCommand,RunPhaseAcceptance
    from mta.runtime.scope_execution import _source_lock,head,receipt_digest
    from mta.runtime import scope_revisions
    from mta.temporal.actions import apply_command
    from mta.runtime.relational_state import save_image
    if (operation not in ('APPLY','SLEEP') or not isinstance(actor,str) or not actor
            or not isinstance(idempotency_key,str) or not 1<=len(idempotency_key)<=120
            or not isinstance(selected,list) or not selected
            or any(not isinstance(pair,(list,tuple)) or len(pair)!=2
                or any(not isinstance(value,str) or not value for value in pair) for pair in selected)
            or type(expected_revision) is not int or expected_revision<0):
        raise ValueError('Explicit scoped action identity/selection required')
    payload=storage(dict(operation=operation,selected=selected,timestamp=timestamp,actor=actor))
    _source_lock(run_id)
    run=CalculationRun.objects.select_for_update().get(pk=run_id)
    existing=RunCommand.objects.filter(run=run,idempotency_key=idempotency_key).first()
    if existing is not None:
        if (str(existing.phase_acceptance_id)!=str(phase_id) or existing.payload!=payload
                or existing.scope_parent_revision!=expected_revision or not existing.state_sealed
                or existing.phase_acceptance.digest!=phase_digest):
            raise ValueError('Idempotency key has different scoped action facts')
        return existing
    receipt=RunPhaseAcceptance.objects.select_related('snapshot').get(pk=phase_id,run=run)
    with connection.cursor() as cursor:
        cursor.execute('SELECT mta.actionable_scope_phase(%s,%s)',[run.pk,receipt.pk])
        actionable=cursor.fetchone()[0]
    if (not actionable or receipt.digest!=phase_digest or receipt_digest(receipt)!=receipt.digest
            or head(run.pk)!=(receipt.phase,receipt.digest) or revision(run)!=expected_revision):
        raise ValueError('Scoped action requires its exact released stage/action head')
    event_date=datetime.fromisoformat(timestamp).date()
    last=RunCommand.objects.filter(run=run,phase_acceptance__isnull=False).order_by('-id').first()
    if event_date<(datetime.fromisoformat(last.payload['timestamp']).date() if last else run.business_date):
        raise ValueError('Command date precedes its parent or prior command')
    before=scope_revisions.require_current(run)
    current_state=_action_reader(run,receipt)
    state=current_state(expected_revision)
    result=storage(apply_command(state,operation,[tuple(key) for key in selected],timestamp))
    event=RunCommand.objects.create(run=run,phase_acceptance=receipt,idempotency_key=idempotency_key,
        payload=payload,digest=digest(payload),before_digest=digest(state),after_digest=digest(result),
        state_sealed=False,scope_parent_revision=expected_revision,scope_revision_before=before)
    changed={name for name in TABLES[1:] if state[name]!=result[name]}
    if not changed:changed={'NormAcceptanceTbl'}
    event.state_manifest={name:save_image(run,'action/'+str(event.pk)+'/'+name,
        'closing/dbm/'+name,result[name]) for name in sorted(changed)}
    event.scope_revision_after=scope_revisions.next_cut(scope_revisions.owned_position(run))
    event.save(update_fields=['state_manifest','scope_revision_after'])
    scope_revisions.verify_write(run,event.scope_revision_after)
    event.refresh_from_db()
    # A writer/type conversion failure rolls the command and every image back.
    current_state(event.pk)
    return event


def calculate_dbm(attempt_id,worker_token,*,compatibility_digest):
    """Restore BPR, bind its actions, run only DBM and accept its actual effects."""
    from mta.runtime.scope_execution import require_claim,head
    from mta.runtime.models import RunPhaseAcceptance
    from mta.runtime.calculation_effects import _accept_calculation
    from mta.temporal.chain import produce_dbm
    from mta.application.native_output_contracts import native_assignments
    with transaction.atomic():
        attempt,run=require_claim(attempt_id,worker_token,compatibility_digest=compatibility_digest)
        parent=RunPhaseAcceptance.objects.select_related('snapshot').get(run=run,phase='BPR',state_sealed=True)
        if head(run.pk)!=('BPR',parent.digest):raise ValueError('DBM requires its exact accepted BPR head')
        expected=attempt.action_revision
    phase,sources=restore(run,parent)
    from mta.runtime.occurrence_text_policy import verify_phase
    verify_phase(run,phase)
    state=state_after(run,parent,phase,expected_revision=expected)
    with native_assignments(True):
        dbm=produce_dbm(phase,_action_state=state if expected else None,_action_revision=expected)
    with transaction.atomic():
        return _accept_calculation(attempt_id,worker_token,dbm,sources,parent=parent,
                                   compatibility_digest=compatibility_digest)


def final_phase(run,receipt,phase,*,expected_revision):
    state=state_after(run,receipt,phase,expected_revision=expected_revision)
    if expected_revision==phase.context.action_revision:return phase
    from mta.temporal.chain import carry_dbm_controls
    final=dict(phase.final_dbm,**{name:state[name] for name in TABLES[1:]})
    return replace(phase,final_dbm=final,control_final=carry_dbm_controls(phase.control_final,final),
                   context=replace(phase.context,action_revision=expected_revision))
