"""Bounded native PostBPR entry: continue an accepted day, never recapture it.

This release qualifies only the explicitly approved retained TEST run. The
frozen UptoBPR request and accepted phases remain their original owners.
"""
from copy import deepcopy
from django.db import transaction
from mta.serialization import digest

SCHEMA = 'fresh-owned-post-bpr-test-v1'
PROFILE = '9be6ca606337f997adffa1ce82d1dc4f855df601b0616429774642d06db06eb4'
DISPOSITIONS = dict(schema=SCHEMA, decision='call_018484042fc542ebab4ab493e37e00cb/1',
    site='SUPPLIED-INSTANCE', purpose='owned-scoped-test',
    hooks={name: 'explicit-test-no-op' for name in ('PreDBM', 'PostDBM', 'PostBTR', 'SiteFinal')},
    excluded=['optional-BTR30-file', 'optional-BTR60-file', 'optional-BTR90-file',
              'optional-location-BTR-files', 'post-backups', 'outbound-DBM-email', 'outbound-finish-email'],
    required='all-captured-enabled-calculations-populations-histories-native-completion')


def request(run, *, expected_bpr_digest, expected_action_revision, command_key):
    from release.native_identity import require_current
    from mta.runtime.phase_state import recipe_digest
    from mta.runtime.bpr_history_completion import AUTHORITY
    if (str(run.pk) != AUTHORITY['run'] or run.input_digest != AUTHORITY['input_digest']
            or expected_bpr_digest != AUTHORITY['phase_digest']
            or type(expected_action_revision) is not int or expected_action_revision != 12
            or not isinstance(command_key, str) or not 1 <= len(command_key) <= 120):
        raise ValueError('PostBPR requires the explicitly approved retained run, BPR and action revision')
    value = dict(schema=SCHEMA, scope='PostBPR', run_id=str(run.pk), input_digest=run.input_digest,
        bpr_digest=expected_bpr_digest, action_revision=expected_action_revision, command_key=command_key,
        profile_digest=PROFILE, dispositions=deepcopy(DISPOSITIONS))
    value['compatibility_digest'] = digest(dict(request=value, release=require_current(), phase_recipe=recipe_digest()))
    return value


def _entry(run, value):
    from mta.runtime.input_reader import read_input
    from mta.runtime.production_scope import captured_run, _phase
    from mta.runtime.scope_runtime_reports import validate, require_test_database
    from mta.runtime.scoped_actions import revision
    from mta.runtime.bpr_history_completion import AUTHORITY, _identity
    require_test_database()
    raw = read_input(run, components=('profile', 'scope_request'))
    captured = raw['scope_request']
    if (digest(raw['profile']) != PROFILE or raw['profile']['delivery']['site_code'] != DISPOSITIONS['site']
            or captured['scope'] != 'UptoBPR' or captured['command_key'] == value['command_key']):
        raise ValueError('PostBPR cannot replace the captured configuration or UptoBPR command')
    validate(captured['runtime_reports'])
    captured_run(run, captured)
    phase = _phase(run, 'BPR', value['bpr_digest'])
    _identity(run, phase)
    if str(phase.pk) != AUTHORITY['phase'] or revision(run) != value['action_revision']:
        raise ValueError('PostBPR accepted BPR/action owner changed')
    return phase


def _completed(run, value):
    from mta.runtime.scope_execution import head, receipt_digest
    from mta.runtime.receipt_integrity import verify_root
    from mta.runtime.bpr_history_completion import verified
    final = run.phase_acceptances.select_related('attempt').get(phase='DAY_FINAL', state_sealed=True)
    attempt = final.attempt
    if (run.status != 'SUCCEEDED' or final.digest != receipt_digest(final)
            or head(run.pk) != ('DAY_FINAL', final.digest)
            or attempt.scope != 'PostBPR' or attempt.command_key != value['command_key']
            or attempt.compatibility_digest != value['compatibility_digest'] or attempt.status != 'RELEASED'
            or attempt.action_revision != value['action_revision']
            or final.metadata.get('output_digest') != run.output_digest):
        raise ValueError('PostBPR completed owner differs')
    verify_root(run)
    completion = verified(run)
    return dict(scope='PostBPR', run_id=str(run.pk), business_date=run.business_date.isoformat(),
        status=run.status, command_key=value['command_key'], attempt_id=str(attempt.pk),
        day_final_receipt=str(final.pk), day_final_digest=final.digest,
        output_digest=run.output_digest, bpr_history_completion_digest=completion.digest,
        action_revision=attempt.action_revision, dispositions=value['dispositions'],
        business_complete=True, scope_ready=False, serving_selected=False, application_acceptance=False,
        pending=['terminal-report-file-readiness', 'terminal-serving-selection', 'end-to-end-acceptance'])


def execute(run_id, *, expected_bpr_digest, expected_action_revision, command_key,
            worker_reference, recovery_of=None, inspect_only=False):
    from mta.runtime.production_scope import authorize
    from mta.runtime.models import CalculationRun, RunScopeAttempt
    from mta.runtime import scope_execution as workers, bpr_history_completion as history
    from mta.runtime.scoped_actions import calculate_dbm
    from mta.runtime.scoped_final import _finish_accepted_day
    if not transaction.get_autocommit():
        raise ValueError('Native PostBPR owns its durable phase transactions')
    if not isinstance(worker_reference, str) or not 1 <= len(worker_reference) <= 200:
        raise ValueError('Explicit PostBPR worker reference required')
    authorize()
    run = CalculationRun.objects.select_related('predecessor').get(pk=run_id)
    value = request(run, expected_bpr_digest=expected_bpr_digest,
        expected_action_revision=expected_action_revision, command_key=command_key)
    bpr = _entry(run, value)
    previous = RunScopeAttempt.objects.filter(run=run, command_key=command_key).order_by('-attempt_no').first()
    if previous is not None and (previous.scope != 'PostBPR'
            or previous.compatibility_digest != value['compatibility_digest']):
        raise ValueError('PostBPR retry cannot change its command compatibility')
    if run.status == 'SUCCEEDED':
        if recovery_of is not None: raise ValueError('Completed PostBPR requires no recovery')
        return _completed(run, value)
    phase, checksum = workers.head(run.pk)
    if phase not in ('BPR', 'DBM'):
        raise ValueError('PostBPR requires its retained BPR or unfinished accepted DBM tail')
    if phase == 'DBM':
        dbm = run.phase_acceptances.select_related('attempt').get(phase='DBM', state_sealed=True)
        if (previous is None or dbm.attempt.scope != 'PostBPR'
                or dbm.attempt.command_key != command_key
                or dbm.attempt.compatibility_digest != value['compatibility_digest']):
            raise ValueError('PostBPR cannot take over a different DBM command')
    if previous is not None:
        if previous.status != 'FAILED' or str(previous.pk) != str(recovery_of):
            raise ValueError('PostBPR requires explicit recovery of its failed latest attempt')
    elif recovery_of is not None:
        raise ValueError('PostBPR recovery owner is absent')
    if inspect_only:
        from mta.runtime.models import BprHistoryCompletion
        completion = history.verified(run) if BprHistoryCompletion.objects.filter(run=run).exists() else None
        return dict(request=value, accepted_head=[phase, checksum], bpr_receipt=str(bpr.pk),
            bpr_history_complete=completion is not None, mutation=False,
            business_complete=False, scope_ready=False, serving_selected=False)
    # Explicitly approved late completion occurs before any DBM claim/work.
    # It never edits the original acceptance or recaptures frozen inputs.
    history.complete(run.pk)
    with transaction.atomic():
        attempt = workers._claim(run.pk, scope='PostBPR', command_key=command_key,
            worker_reference=worker_reference, compatibility_digest=value['compatibility_digest'],
            expected_phase=phase, expected_receipt_digest=checksum, recovery_of=recovery_of)
        if attempt.action_revision != expected_action_revision:
            raise ValueError('PostBPR action revision changed before claim')
    try:
        if phase == 'BPR':
            calculate_dbm(attempt.pk, attempt.worker_token, compatibility_digest=value['compatibility_digest'])
        # PostDBM/PostBTR/site hooks are the pinned explicit no-op dispositions.
        # Enabled DBM/BTR producers and finalization remain in the existing engine.
        finished = _finish_accepted_day(attempt.pk, attempt.worker_token,
                                       compatibility_digest=value['compatibility_digest'])
    except Exception as error:
        try:
            workers.fail(attempt.pk, attempt.worker_token, compatibility_digest=value['compatibility_digest'], error=error)
        except Exception as closing_error:
            raise error from closing_error
        raise
    return _completed(finished, value)
