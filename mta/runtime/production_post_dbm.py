"""Bounded native PostDBM: continue the accepted TEST day through BTR/final.

The native entry owns admission/recovery only. Existing accepted phases and
scoped_final own calculations and atomic publication. No earlier phase replay.
"""
from copy import deepcopy
from django.db import transaction
from mta.serialization import digest

SCHEMA = 'fresh-owned-post-dbm-test-v1'
AUTHORITY = dict(
    decision='call_fd913222abc84ca78e37638c9be9a00d',
    run='a2661554-4450-4ac2-a2fc-c2055e685663',
    input_digest='353f4693eb31126f368079f9e478f3ef3f3fb9143360ddf4214a7f9d081074a6',
    input_manifest_digest='28605ca9aa21d2d0c294d71f18a2a77913a0d667f4e1cd198db91885fbb880aa',
    profile_digest='9be6ca606337f997adffa1ce82d1dc4f855df601b0616429774642d06db06eb4',
    scope_request_digest='d2f72fc573cd6f920c1644ba465ba443dd9a5fe1f59c6742b0901f09de35fe70',
    dbm='a3542565-f3ae-4ad8-8365-12539c69a42c',
    dbm_digest='a824dc63a9f8041504dd9c1fc3b1bfa2f2136e4bdc756b050fd061fca14a77ff',
    dbm_attempt='8f9bd9a0-3072-4cd1-ac68-71b579e2b0a6',
    action_revision=177)
DISPOSITIONS = dict(schema=SCHEMA, purpose='owned-scoped-test', site='SUPPLIED-INSTANCE',
    decision='call_da428cf59cff45978a7199f4872087ce',
    hooks={name: 'explicit-test-no-op' for name in ('PostBTR', 'SiteFinal')},
    excluded=['optional-BTR30-file', 'optional-BTR60-file', 'optional-BTR90-file',
              'optional-location-BTR-files', 'post-backups', 'outbound-finish-email'],
    required='all-captured-enabled-calculations-populations-histories-native-completion')


def request(run, *, expected_dbm_digest, expected_action_revision, command_key):
    from release.native_identity import require_current
    from mta.runtime.phase_state import recipe_digest
    if (str(run.pk) != AUTHORITY['run'] or run.input_digest != AUTHORITY['input_digest']
            or run.input_manifest_digest != AUTHORITY['input_manifest_digest']
            or expected_dbm_digest != AUTHORITY['dbm_digest']
            or type(expected_action_revision) is not int
            or expected_action_revision != AUTHORITY['action_revision']
            or type(command_key) is not str or not 1 <= len(command_key) <= 120):
        raise ValueError('PostDBM requires its approved retained run, DBM and action revision')
    value = dict(schema=SCHEMA, scope='PostDBM', run_id=str(run.pk),
        input_digest=run.input_digest, input_manifest_digest=run.input_manifest_digest,
        dbm_digest=expected_dbm_digest, action_revision=expected_action_revision,
        command_key=command_key, authority=deepcopy(AUTHORITY), dispositions=deepcopy(DISPOSITIONS))
    value['compatibility_digest'] = digest(dict(request=value,
        release=require_current(), phase_recipe=recipe_digest()))
    return value


def _entry(run, value):
    from mta.runtime.input_reader import read_input
    from mta.runtime.production_scope import captured_run, _phase
    from mta.runtime.scope_runtime_reports import validate, require_test_database
    from mta.runtime.scoped_actions import revision
    require_test_database()
    raw = read_input(run, components=('profile', 'scope_request'))
    captured = raw['scope_request']
    if (digest(raw['profile']) != AUTHORITY['profile_digest']
            or digest(captured) != AUTHORITY['scope_request_digest']
            or captured['scope'] != 'UptoDBM' or captured['command_key'] == value['command_key']):
        raise ValueError('PostDBM cannot replace its captured UptoDBM configuration or command')
    validate(captured['runtime_reports'])
    captured_run(run, captured)
    phase = _phase(run, 'DBM', value['dbm_digest'])
    owner = phase.attempt
    if (str(phase.pk) != AUTHORITY['dbm'] or str(owner.pk) != AUTHORITY['dbm_attempt']
            or owner.status != 'RELEASED' or owner.scope != 'UptoDBM'
            or owner.command_key != captured['command_key']
            or owner.compatibility_digest != captured['compatibility_digest']
            or revision(run) != value['action_revision']):
        raise ValueError('PostDBM accepted DBM/action owner changed')
    return phase


def _completed(run, value):
    from mta.runtime.scope_execution import head, receipt_digest
    from mta.runtime.receipt_integrity import verify_root
    final = run.phase_acceptances.select_related('attempt').get(phase='DAY_FINAL', state_sealed=True)
    attempt = final.attempt
    if (run.status != 'SUCCEEDED' or final.digest != receipt_digest(final)
            or head(run.pk) != ('DAY_FINAL', final.digest)
            or attempt.scope != 'PostDBM' or attempt.command_key != value['command_key']
            or attempt.compatibility_digest != value['compatibility_digest'] or attempt.status != 'RELEASED'
            or attempt.action_revision != value['action_revision']
            or attempt.expected_phase != 'DBM' or attempt.expected_receipt_digest != value['dbm_digest']
            or final.metadata.get('output_digest') != run.output_digest):
        raise ValueError('PostDBM completed owner differs')
    verify_root(run)
    return dict(scope='PostDBM', run_id=str(run.pk), business_date=run.business_date.isoformat(),
        status=run.status, command_key=value['command_key'], attempt_id=str(attempt.pk),
        day_final_receipt=str(final.pk), day_final_digest=final.digest,
        output_digest=run.output_digest, action_revision=attempt.action_revision,
        dispositions=value['dispositions'], business_complete=True,
        scope_ready=False, serving_selected=False, application_acceptance=False,
        pending=['terminal-report-file-readiness', 'terminal-serving-selection', 'end-to-end-acceptance'])


def _recovery_owner(run, value, recovery_of):
    """A new key cannot abandon a failed or active continuation command."""
    latest = run.scope_attempts.order_by('-created_at', '-id').first()
    if latest is not None and str(latest.pk) == AUTHORITY['dbm_attempt']:
        if latest.status != 'RELEASED' or recovery_of is not None:
            raise ValueError('PostDBM recovery owner is absent')
        return
    if (latest is None or latest.scope != 'PostDBM'
            or latest.command_key != value['command_key']
            or latest.compatibility_digest != value['compatibility_digest']):
        raise ValueError('PostDBM cannot replace its latest continuation command owner')
    if latest.status != 'FAILED' or str(latest.pk) != str(recovery_of):
        raise ValueError('PostDBM requires explicit recovery of its failed latest attempt')


def execute(run_id, *, expected_dbm_digest, expected_action_revision, command_key,
            worker_reference, recovery_of=None, inspect_only=False):
    from mta.runtime.production_scope import authorize
    from mta.runtime.models import CalculationRun
    from mta.runtime import scope_execution as workers
    from mta.runtime.scoped_final import _finish_accepted_day
    if not transaction.get_autocommit():
        raise ValueError('Native PostDBM owns its durable phase transactions')
    if (type(worker_reference) is not str or not 1 <= len(worker_reference) <= 200
            or type(inspect_only) is not bool):
        raise ValueError('Explicit PostDBM worker and inspection flag required')
    authorize()
    run = CalculationRun.objects.select_related('predecessor').get(pk=run_id)
    value = request(run, expected_dbm_digest=expected_dbm_digest,
        expected_action_revision=expected_action_revision, command_key=command_key)
    dbm = _entry(run, value)
    if run.status == 'SUCCEEDED':
        if recovery_of is not None: raise ValueError('Completed PostDBM requires no recovery')
        return _completed(run, value)
    if workers.head(run.pk) != ('DBM', value['dbm_digest']):
        raise ValueError('PostDBM requires its accepted pre-BTR DBM head')
    _recovery_owner(run, value, recovery_of)
    if inspect_only:
        return dict(request=value, accepted_head=['DBM', dbm.digest],
            dbm_receipt=str(dbm.pk), mutation=False,
            business_complete=False, scope_ready=False, serving_selected=False)
    with transaction.atomic():
        workers._source_lock(run.pk)
        locked = CalculationRun.objects.select_for_update().get(pk=run.pk)
        _recovery_owner(locked, value, recovery_of)
        attempt = workers._claim(run.pk, scope='PostDBM', command_key=command_key,
            worker_reference=worker_reference, compatibility_digest=value['compatibility_digest'],
            expected_phase='DBM', expected_receipt_digest=dbm.digest, recovery_of=recovery_of)
        if attempt.action_revision != expected_action_revision:
            raise ValueError('PostDBM action revision changed before claim')
    try:
        finished = _finish_accepted_day(attempt.pk, attempt.worker_token,
                                       compatibility_digest=value['compatibility_digest'])
    except Exception as error:
        try:
            workers.fail(attempt.pk, attempt.worker_token, compatibility_digest=value['compatibility_digest'], error=error)
        except Exception as closing_error:
            raise error from closing_error
        raise
    return _completed(finished, value)


def fence(attempt_id, *, expected_worker_token, reason):
    """Explicitly fence only this entry's inspected worker; no timeout inference."""
    from mta.runtime.production_scope import authorize
    from mta.runtime.models import RunScopeAttempt
    from mta.runtime.scope_execution import fence as fence_worker
    authorize()
    attempt = RunScopeAttempt.objects.select_related('run').get(pk=attempt_id)
    value = request(attempt.run, expected_dbm_digest=attempt.expected_receipt_digest,
        expected_action_revision=attempt.action_revision, command_key=attempt.command_key)
    _entry(attempt.run, value)
    if (attempt.scope != 'PostDBM' or attempt.expected_phase != 'DBM'
            or attempt.compatibility_digest != value['compatibility_digest']):
        raise ValueError('PostDBM fencing requires its exact native command owner')
    return fence_worker(attempt.pk, expected_worker_token=expected_worker_token, reason=reason)
