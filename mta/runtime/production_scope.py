"""Native UptoBPR entry over the existing capture and phase transaction owners.

Calculation acceptance and Pick files are explicit results, not UI selection or
whole-scope readiness. Full continues through its original terminal owner.
"""
from django.db import connection, transaction
from mta.serialization import digest

SCHEMA='fresh-native-scope-request-v1'


def request(command_key):
    from release.native_identity import require_current
    from mta.runtime.phase_state import recipe_digest
    if type(command_key) is not str or not 1<=len(command_key)<=120:
        raise ValueError('Explicit bounded scope command key required')
    return dict(schema=SCHEMA,scope='UptoBPR',command_key=command_key,
        compatibility_digest=digest(dict(release=require_current(),phase_recipe=recipe_digest())))


def validate_request(value):
    if type(value) is not dict or value!=request(value.get('command_key')):
        raise ValueError('Native scoped request or implementation identity differs')
    return value


def authorize():
    """Read actual registration/roles; runtime and provisioner cannot execute."""
    from mta.mdm.owned_namespace import (_database_identity,_registered_identity,
        _catalogue_evidence,_validate_identity)
    with connection.cursor() as cursor:
        database=_database_identity(cursor)
        registered=_registered_identity(cursor)
        evidence=_catalogue_evidence(cursor,database,registered)
        _validate_identity(database,registered,evidence,installer=True)


def captured_run(run,value):
    """No capture/recalculation on retry, including after later finalization."""
    from mta.runtime.input_reader import read_input
    from mta.runtime.mdm_daily_models import MdmDailyInputCapture
    from mta.runtime.scope_execution import _frozen
    if (run.kind!='DAILY_CHAIN' or run.evidence_mode!='production'
            or read_input(run,components=('scope_request',)).get('scope_request')!=value):
        raise ValueError('Captured native scope identity differs')
    if run.status=='RUNNING':
        _frozen(run)
    elif run.status=='SUCCEEDED':
        from mta.runtime.services import read_outputs
        MdmDailyInputCapture.objects.get(run=run,status='CONSUMED')
        read_outputs(run,include_reports=False)
    else:raise ValueError('Native scoped day has no recoverable captured owner')
    return run


def repeated(raw,expected_sha256,value,arguments):
    """Authenticate a frozen retry before fresh admission can consult live state."""
    from mta.runtime.production_daily import decode
    from mta.runtime.models import CalculationRun
    from mta.runtime.input_reader import read_input
    from mta.runtime.temporal import resolved_pick_root
    day=decode(raw,expected_sha256)['day']['business_date']
    # A date/revision/source identifies at most one native logical capture.
    candidates=list(CalculationRun.objects.filter(kind='DAILY_CHAIN',business_date=day,
        execution_revision=arguments['execution_revision'],
        mdm_input_capture__source__digest=arguments['source_digest'])[:2])
    if not candidates:return None
    if len(candidates)!=1:raise ValueError('Native scoped request has ambiguous captured owners')
    run=candidates[0]
    captured_run(run,value)
    raw=read_input(run,components=('initialization_binding','daily_input_sha256','pick_output_root','lineage'))
    binding=raw['initialization_binding']
    parent=arguments.get('predecessor_id')
    if (binding['id']!=str(arguments['initialization_id'])
            or binding['source_digest']!=arguments['source_digest']
            or binding['configuration_digest']!=arguments['configuration_digest']
            or raw['daily_input_sha256']!=expected_sha256
            or raw['pick_output_root']!=resolved_pick_root(arguments['pick_output_root'])
            or (str(run.predecessor_id) if run.predecessor_id else None)!=(str(parent) if parent is not None else None)
            or raw['lineage'].get('output_digest')!=arguments.get('predecessor_output_digest')):
        raise ValueError('Native scope retry cannot replace frozen arguments')
    return run


def execute(raw,expected_sha256,*,command_key,worker_reference,recovery_of=None,
            inspect_only=False,repair_files=False,**arguments):
    from mta.runtime import production_daily
    from mta.runtime.production_preflight import require
    if not transaction.get_autocommit():raise ValueError('Native scope owns its transaction boundaries')
    value=request(command_key)
    authorize()
    if (arguments.get('retry_capture_id') is not None or arguments.get('report_disposition') is not None
            or arguments.get('feed_attempt') is not None):
        raise ValueError('UptoBPR recovery uses the existing scoped attempt')
    if type(worker_reference) is not str or not 1<=len(worker_reference)<=200:
        raise ValueError('Explicit bounded worker reference required')
    if type(repair_files) is not bool:raise ValueError('Explicit file repair boolean required')
    run=repeated(raw,expected_sha256,value,arguments)
    if run is not None:
        if inspect_only:
            from mta.runtime.scope_execution import head
            latest=run.scope_attempts.filter(command_key=command_key).order_by('-attempt_no').first()
            return dict(scope='UptoBPR',run_id=str(run.pk),captured_request_verified=True,
                accepted_head=list(head(run.pk)),attempt=(None if latest is None else
                    dict(id=str(latest.pk),status=latest.status,
                        worker_token=str(latest.worker_token) if latest.status=='ACTIVE' else None)),
                scope_ready=False,serving_selected=False,application_acceptance=False)
        return advance(run,value,worker_reference=worker_reference,recovery_of=recovery_of,
            repair_files=repair_files)
    if recovery_of is not None:raise ValueError('Scope recovery requires its existing frozen day')
    if inspect_only:
        report,*_=production_daily.inspect_execution(raw,expected_sha256,
            scope_request=value,**arguments)
        require(report,'day')
        return report
    run=production_daily.execute(raw,expected_sha256,scope_request=value,**arguments)
    return advance(run,value,worker_reference=worker_reference,recovery_of=recovery_of,
        repair_files=repair_files)


def fence(attempt_id,*,expected_worker_token,reason):
    """Authorized explicit fencing of this entry's existing native worker only."""
    from mta.runtime.models import RunScopeAttempt
    from mta.runtime.input_reader import read_input
    from mta.runtime.scope_execution import fence as fence_worker
    authorize()
    attempt=RunScopeAttempt.objects.select_related('run').get(pk=attempt_id)
    value=read_input(attempt.run,components=('scope_request',)).get('scope_request')
    validate_request(value)
    captured_run(attempt.run,value)
    if (attempt.scope!='UptoBPR' or attempt.command_key!=value['command_key']
            or attempt.compatibility_digest!=value['compatibility_digest']):
        raise ValueError('Fencing requires this native scope command owner')
    return fence_worker(attempt.pk,expected_worker_token=expected_worker_token,reason=reason)


def _phase(run,name,checksum):
    # This shared validator authenticates the full PRE/BPR parent/effect chain.
    from mta.runtime.scoped_pick_files import _accepted
    receipt=run.phase_acceptances.get(phase=name,state_sealed=True)
    return _accepted(receipt.pk,checksum)


def _produce(attempt,value):
    """Only missing PRE/BPR work; each durable effect has its existing owner."""
    from mta.runtime.scope_execution import head,require_claim
    from mta.runtime.input_reader import read_input
    from mta.runtime import phase_state
    from mta.runtime.scoped_final import frozen_prior
    from mta.runtime.prepared_effects import _accept_prepared
    from mta.runtime.calculation_effects import _accept_calculation
    from mta.temporal.chain import prepare_day,produce_bpr
    from mta.planning.engine import calculate_current_day
    from mta.application.native_output_contracts import native_assignments
    from mta.application.stage_calculation_sources import capture_bpr
    compatibility=value['compatibility_digest']
    with transaction.atomic():
        _,run=require_claim(attempt.pk,attempt.worker_token,compatibility_digest=compatibility)
        phase,checksum=head(run.pk)
    if phase=='BPR':return _phase(run,'BPR',checksum)
    if phase not in ('START','PRE_BPR'):raise ValueError('UptoBPR cannot advance a later phase')
    raw=read_input(run,components=('opening','day','profile','lineage','initialization_binding','mdm_input'))
    prior=frozen_prior(run,raw)
    def calculate(source,**owned):
        return calculate_current_day(source,defer_pick=True,**owned),str(run.pk)
    master=raw['mdm_input'] if raw.get('initialization_binding') is not None else None
    if phase=='START':
        opening_date=(run.predecessor.business_date.isoformat() if run.predecessor_id else raw['opening']['opening_date'])
        with native_assignments(True):
            prepared=prepare_day(prior,opening_date,raw['day'],raw['profile'],str(run.pk),
                calculate,native_daily=True,master_snapshot=master)
        with transaction.atomic():
            parent=_accept_prepared(attempt.pk,attempt.worker_token,prepared,compatibility_digest=compatibility)
    else:
        parent=_phase(run,'PRE_BPR',checksum)
        prepared,_=phase_state.read(parent.snapshot,prior=prior,day=raw['day'],profile=raw['profile'],
            master_snapshot=master,execute_calculation=calculate)
    with native_assignments(True):bpr=produce_bpr(prepared)
    sources=capture_bpr(bpr,{'supplier':prior['supplier']})
    with transaction.atomic():
        return _accept_calculation(attempt.pk,attempt.worker_token,bpr,sources,parent=parent,
            compatibility_digest=compatibility)


def advance(run,value,*,worker_reference,recovery_of=None,repair_files=False):
    from mta.runtime import scope_execution as workers
    from mta.runtime.models import RunScopeAttempt,CalculationRun
    from mta.runtime import scoped_pick_files
    compatibility=value['compatibility_digest']
    run=CalculationRun.objects.get(pk=run.pk)
    # Lock/source revision checks are repeated by claim and every acceptance.
    captured_run(run,value)
    previous=RunScopeAttempt.objects.filter(run=run,command_key=value['command_key']).order_by('-attempt_no').first()
    if previous is not None and (previous.scope!='UptoBPR' or previous.compatibility_digest!=compatibility):
        raise ValueError('Existing scope command compatibility differs')
    if previous is not None and previous.status=='RELEASED':
        if recovery_of is not None:raise ValueError('Released calculation does not require recovery')
        receipt=run.phase_acceptances.get(phase='BPR',state_sealed=True)
        receipt=_phase(run,'BPR',receipt.digest)
        files=scoped_pick_files.prepare(receipt.pk,expected_digest=receipt.digest,repair=repair_files)
    else:
        phase,checksum=workers.head(run.pk)
        if phase not in ('START','PRE_BPR','BPR'):raise ValueError('UptoBPR requires its own accepted prefix')
        attempt=workers.claim(run.pk,scope='UptoBPR',command_key=value['command_key'],
            worker_reference=worker_reference,compatibility_digest=compatibility,
            expected_phase=phase,expected_receipt_digest=checksum,recovery_of=recovery_of)
        try:
            receipt=_produce(attempt,value)
            # File preparation belongs under the worker. A failure preserves
            # the accepted BPR and records this attempt for explicit recovery.
            files=scoped_pick_files.prepare(receipt.pk,expected_digest=receipt.digest,repair=repair_files)
            workers.release(attempt.pk,attempt.worker_token,compatibility_digest=compatibility)
        except Exception as error:
            try:workers.fail(attempt.pk,attempt.worker_token,compatibility_digest=compatibility,error=error)
            except Exception as closing_error:raise error from closing_error
            raise
    return dict(scope='UptoBPR',run_id=str(run.pk),status=run.status,
        business_date=run.business_date.isoformat(),command_key=value['command_key'],
        phase_acceptance_id=str(receipt.pk),phase_acceptance_digest=receipt.digest,
        snapshot_digest=receipt.snapshot.state_digest,pick_files_digest=files.digest,
        calculation_accepted=True,pick_files_ready=True,scope_ready=False,
        serving_selected=False,application_acceptance=False,
        pending=['phase_read_binding','configured_artifact_readiness','end_to_end_acceptance'])
