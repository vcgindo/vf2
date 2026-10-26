"""Versioned owned-test entry for the released eight-report placement contract.

Capture and Full execution remain production_daily/execute_day. Existing scope
claims, phase acceptance and scoped_final own split execution and recovery.
This entry chooses neither a serving generation nor a production default.
"""
from django.db import transaction
from mta.runtime import runtime_report_request as contract


def execute(raw,expected_sha256,*,scope,command_key,runtime_reports,worker_reference=None,
            recovery_of=None,inspect_only=False,repair_files=False,**arguments):
    from mta.runtime import production_scope as original,production_daily
    from mta.runtime.scope_runtime_reports import require_publication_writer,require_test_database
    from mta.runtime.production_preflight import require
    if not transaction.get_autocommit():raise ValueError('Native placement entry owns its transaction boundaries')
    if type(inspect_only) is not bool or type(repair_files) is not bool:
        raise ValueError('Explicit placement inspection/repair flags required')
    require_publication_writer();original.authorize();require_test_database()
    value=contract.request(scope,command_key,runtime_reports=runtime_reports)
    if any(arguments.get(name) is not None for name in ('feed_attempt','report_disposition')):
        raise ValueError('Placement request cannot replace its captured input/dispositions')
    if scope!='Full' and arguments.get('retry_capture_id') is not None:
        raise ValueError('Scoped placement recovery retains its existing capture')
    if scope=='Full' and (worker_reference is not None or recovery_of is not None):
        raise ValueError('Full uses its existing native capture/completion owner')
    if scope!='Full' and (type(worker_reference) is not str or not 1<=len(worker_reference)<=200):
        raise ValueError('Explicit bounded scoped worker reference required')
    # Existing Full native retry uses a new failed-capture successor/revision;
    # it never adopts an already-running calculation or resets a failed run.
    run=original.repeated(raw,expected_sha256,value,arguments)
    if run is None:
        if recovery_of is not None:raise ValueError('Scoped recovery requires its existing run')
        if inspect_only:
            report,*_=production_daily.inspect_execution(raw,expected_sha256,scope_request=value,**arguments)
            require(report,'day')
            return report
        run=production_daily.execute(raw,expected_sha256,scope_request=value,**arguments)
    if scope=='Full':
        if run.status!='SUCCEEDED':raise ValueError('Full placement has not completed')
        from mta.runtime.receipt_integrity import verify_root
        from mta.runtime.runtime_report_placement_publication import read
        verify_root(run)
        final=read(run.pk,placement='Final',verify_bytes=True)
        return dict(scope=scope,run_id=str(run.pk),status=run.status,output_digest=run.output_digest,
            runtime_report_publication=str(final.pk),runtime_report_digest=final.digest,
            business_complete=True,serving_selected=False,application_acceptance=False)
    if inspect_only:
        from mta.runtime.scope_execution import head
        return dict(scope=scope,run_id=str(run.pk),accepted_head=list(head(run.pk)),mutation=False)
    if scope=='UptoDBM':
        from mta.runtime.production_upto_dbm import advance
        result=advance(run,value,worker_reference=worker_reference,recovery_of=recovery_of,repair_files=repair_files)
        placement='PostDBM'
    else:
        result=original.advance(run,value,worker_reference=worker_reference,recovery_of=recovery_of,repair_files=repair_files)
        from mta.runtime.production_upto_dbm import _bpr_files
        bpr=run.phase_acceptances.get(phase='BPR',state_sealed=True)
        _files,artifact=_bpr_files(run,bpr,value,repair=repair_files)
        result['input_archive_receipt']=artifact['receipt_sha256'];placement='PostBPR'
    from mta.runtime.runtime_report_placement_publication import read
    published=read(run.pk,placement=placement,verify_bytes=True)
    result['runtime_reports']=dict(ready=True,publication_id=str(published.pk),publication_digest=published.digest,
                                  configuration_digest=published.configuration_digest)
    return result


def _continued(run,captured,*,scope,command_key,expected_revision):
    from mta.runtime.scope_execution import head,receipt_digest
    from mta.runtime.receipt_integrity import verify_root
    from mta.runtime.runtime_report_placement_publication import read
    final=run.phase_acceptances.select_related('attempt').get(phase='DAY_FINAL',state_sealed=True)
    attempt=final.attempt
    if (head(run.pk)!=('DAY_FINAL',final.digest) or final.digest!=receipt_digest(final)
            or attempt.scope!=scope or attempt.command_key!=command_key or attempt.status!='RELEASED'
            or attempt.compatibility_digest!=captured['compatibility_digest']
            or attempt.action_revision!=expected_revision or final.metadata.get('output_digest')!=run.output_digest):
        raise ValueError('Completed placement continuation owner differs')
    verify_root(run);published=read(run.pk,placement='Final',verify_bytes=True)
    return dict(scope=scope,run_id=str(run.pk),status=run.status,output_digest=run.output_digest,
        attempt_id=str(attempt.pk),day_final_receipt=str(final.pk),day_final_digest=final.digest,
        runtime_report_publication=str(published.pk),runtime_report_digest=published.digest,
        action_revision=expected_revision,business_complete=True,serving_selected=False,application_acceptance=False)


def continue_run(run_id,*,scope,expected_phase_digest,expected_action_revision,command_key,
                 worker_reference,recovery_of=None,inspect_only=False):
    from mta.runtime import production_scope as original,scope_execution as workers
    from mta.runtime.models import CalculationRun
    from mta.runtime.input_reader import read_input
    from mta.runtime.scoped_actions import revision,calculate_dbm
    from mta.runtime.scoped_final import _finish_accepted_day
    from mta.runtime.scope_runtime_reports import require_publication_writer
    from mta.runtime.runtime_report_execution import publish_phase
    if (not transaction.get_autocommit() or scope not in ('PostBPR','PostDBM')
            or type(command_key) is not str or not 1<=len(command_key)<=120 or not command_key.strip()
            or type(worker_reference) is not str or not 1<=len(worker_reference)<=200
            or type(expected_action_revision) is not int or expected_action_revision<0 or type(inspect_only) is not bool):
        raise ValueError('Exact bounded placement continuation command required')
    require_publication_writer();original.authorize()
    run=CalculationRun.objects.select_related('predecessor').get(pk=run_id)
    captured=contract.validate_request(read_input(run,components=('scope_request',))['scope_request'])
    original.captured_run(run,captured)
    source_scope,source_phase={'PostBPR':('UptoBPR','BPR'),'PostDBM':('UptoDBM','DBM')}[scope]
    if captured['scope']!=source_scope or captured['command_key']==command_key:
        raise ValueError('Continuation cannot replace captured source scope/command')
    accepted=original._phase(run,source_phase,expected_phase_digest)
    source_attempt=accepted.attempt
    if (source_attempt.scope!=source_scope or source_attempt.status!='RELEASED'
            or source_attempt.command_key!=captured['command_key']
            or source_attempt.compatibility_digest!=captured['compatibility_digest']
            or revision(run)!=expected_action_revision):
        raise ValueError('Accepted continuation source or action cut differs')
    if run.status=='SUCCEEDED':
        if recovery_of is not None:raise ValueError('Completed continuation requires no recovery')
        return _continued(run,captured,scope=scope,command_key=command_key,expected_revision=expected_action_revision)
    def latest_owner(locked):
        latest=locked.scope_attempts.order_by('-created_at','-id').first()
        if latest is not None and latest.pk==source_attempt.pk:
            if recovery_of is not None or latest.status!='RELEASED':raise ValueError('Continuation recovery is absent')
        elif (latest is None or latest.scope!=scope or latest.command_key!=command_key
                or latest.compatibility_digest!=captured['compatibility_digest'] or latest.status!='FAILED'
                or str(latest.pk)!=str(recovery_of)):
            raise ValueError('Continuation requires its exact failed latest worker for recovery')
    latest_owner(run)
    phase,checksum=workers.head(run.pk)
    if phase not in (('BPR','DBM') if scope=='PostBPR' else ('DBM',)):
        raise ValueError('Continuation has no applicable accepted phase head')
    if phase==source_phase and checksum!=expected_phase_digest:raise ValueError('Accepted source phase changed')
    if inspect_only:return dict(scope=scope,run_id=str(run.pk),accepted_head=[phase,checksum],mutation=False)
    with transaction.atomic():
        workers._source_lock(run.pk)
        locked=CalculationRun.objects.select_for_update().get(pk=run.pk)
        latest_owner(locked)
        attempt=workers._claim(run.pk,scope=scope,command_key=command_key,worker_reference=worker_reference,
            compatibility_digest=captured['compatibility_digest'],expected_phase=phase,expected_receipt_digest=checksum,
            recovery_of=recovery_of)
        if attempt.action_revision!=expected_action_revision:raise ValueError('Continuation action revision changed')
    try:
        if phase=='BPR':
            contract.hook_for(captured['runtime_reports'],'PreDBM')
            dbm=calculate_dbm(attempt.pk,attempt.worker_token,compatibility_digest=captured['compatibility_digest'])
        else:dbm=original._phase(run,'DBM',checksum)
        publish_phase(attempt,dbm,captured)
        finished=_finish_accepted_day(attempt.pk,attempt.worker_token,compatibility_digest=captured['compatibility_digest'])
    except Exception as error:
        try:workers.fail(attempt.pk,attempt.worker_token,compatibility_digest=captured['compatibility_digest'],error=error)
        except Exception as closing_error:raise error from closing_error
        raise
    return _continued(finished,captured,scope=scope,command_key=command_key,expected_revision=expected_action_revision)


def fence(attempt_id,*,expected_worker_token,reason):
    from mta.runtime.production_scope import authorize
    from mta.runtime.models import RunScopeAttempt
    from mta.runtime.input_reader import read_input
    from mta.runtime.scope_execution import fence as fence_worker
    authorize()
    attempt=RunScopeAttempt.objects.select_related('run').get(pk=attempt_id)
    request=contract.validate_request(read_input(attempt.run,components=('scope_request',))['scope_request'])
    scopes=(request['scope'],{'UptoBPR':'PostBPR','UptoDBM':'PostDBM'}.get(request['scope']))
    if attempt.scope not in scopes or attempt.compatibility_digest!=request['compatibility_digest']:
        raise ValueError('Placement fencing requires its captured scoped worker')
    return fence_worker(attempt.pk,expected_worker_token=expected_worker_token,reason=reason)
