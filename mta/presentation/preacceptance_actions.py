"""Explicit offline action phase before operations, publication and acceptance."""
from copy import deepcopy
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path

from django.conf import settings
from django.db import connection, transaction

from mta.presentation import actions
from mta.serialization import digest
from mta.temporal.actions import key


SCHEMA = 'fresh-preacceptance-actions-v1'
POLICY = 'own-recommendations-daily-apply-retained-sleep-v1'
FILE_KEYS = ('artifact', 'finalization', 'pick_config', 'shipment')
ACCESS_KEYS = ('product_permissions', 'location_permissions',
               'permissions_sha256', 'hierarchy_sha256')


class PreacceptanceDenied(ValueError):
    pass


def _deny(reason):
    raise PreacceptanceDenied('preacceptance_actions_' + reason)


def _file_bindings(files):
    if not isinstance(files, dict) or set(files) != set(FILE_KEYS):
        _deny('exact_file_roster_required')
    result = {}
    for name in FILE_KEYS:
        item = files[name]
        if not isinstance(item, dict) or set(item) != {'path', 'sha256'}:
            _deny('file_binding_fields_differ')
        path = Path(item['path']) if isinstance(item['path'], str) else None
        if path is None or not path.is_absolute() or not path.is_file():
            _deny('bound_file_unavailable')
        try:
            content = path.read_bytes()
        except OSError as error:
            raise PreacceptanceDenied(
                'preacceptance_actions_bound_file_unavailable') from error
        if (not isinstance(item['sha256'], str)
                or hashlib.sha256(content).hexdigest() != item['sha256']):
            _deny('bound_file_digest_changed')
        result[name] = {'path': str(path.resolve()), 'sha256': item['sha256']}
    return result


def _access(run, access, output):
    if not isinstance(access, dict) or set(access) != set(ACCESS_KEYS):
        _deny('exact_access_binding_required')
    if (access['permissions_sha256'] != settings.VF_MTA_PERMISSIONS_SHA256
            or access['hierarchy_sha256'] != settings.VF_MTA_HIERARCHY_SHA256):
        _deny('access_file_identity_changed')
    from mta.presentation.context import permission_catalogue, scope
    from mta.presentation.hierarchy import selected_manifest
    permission_catalogue()
    if selected_manifest(run) is None:
        _deny('run_bound_hierarchy_required')
    payload = {name: deepcopy(access[name]) for name in
               ('product_permissions', 'location_permissions')}
    products, locations = scope(
        payload, attributes=output['ClosingState'][0]['importer'])
    return deepcopy(access), products, locations


def _namespace(run):
    receipt = run.mdm_input_capture.source.receipt
    from mta.mdm.owned_namespace import verify_binding
    verify_binding(receipt)
    value = receipt.get('owned_namespace') if isinstance(receipt, dict) else None
    if not isinstance(value, dict) or not value:
        _deny('owned_namespace_required')
    return deepcopy(value)


def _sealed(run):
    from mta.runtime.models import (DailyUiPublication, OperationalAcceptance,
        OperationalAttempt)
    return (DailyUiPublication.objects.filter(run=run).exists()
            or OperationalAttempt.objects.filter(run=run).exists()
            or OperationalAcceptance.objects.filter(run=run).exists()
            or run.successors.exists())


def _validated_state(run, files):
    if _sealed(run):
        _deny('run_already_sealed_or_consumed')
    if run.kind != 'DAILY_CHAIN' or run.status != 'SUCCEEDED':
        _deny('successful_daily_run_required')
    from mta.presentation import daily_sources
    daily_sources.receipt(run)
    from mta.runtime.services import read_outputs
    from mta.runtime.validation_storage import read_input
    raw = read_input(run)
    output = read_outputs(run)
    from mta.presentation.operational_admission import verify_input_domain
    profile_digest = verify_input_domain(run, raw, output,
        artifact_path=files['artifact']['path'],
        finalization_path=files['finalization']['path'],
        pick_config_path=files['pick_config']['path'],
        shipment_path=files['shipment']['path'])
    if profile_digest != digest(raw.get('profile')):
        _deny('profile_identity_changed')
    return raw, output, profile_digest


def _case_plan(run, files, output):
    try:
        artifact = json.loads(Path(files['artifact']['path']).read_bytes())
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise PreacceptanceDenied(
            'preacceptance_actions_registered_case_unavailable') from error
    if not isinstance(artifact, dict) or not isinstance(artifact.get('case'), dict):
        _deny('registered_case_unavailable')
    case = artifact['case']
    matches = [index for index, day in enumerate(case.get('days', []))
               if day.get('business_date') == str(run.business_date)]
    if len(matches) != 1 or case.get('commands') != []:
        _deny('registered_case_action_scope_changed')
    from parity.temporal_policy import commands_for_day, policy_for_case
    if policy_for_case(case) != POLICY:
        _deny('unsupported_action_policy')
    suggestions = output['DBMFinal'][0]['Suggestions']
    commands = commands_for_day(case, matches[0], suggestions)
    expected_timestamp = str(run.business_date) + 'T12:00:00+05:30'
    if any(command.get('timestamp') != expected_timestamp
           or command.get('operation') != 'APPLY' for command in commands):
        _deny('command_timestamp_or_operation_changed')
    return commands


def _phase_identity(value):
    return digest(value)


def build_manifest(run, *, actor, access, files):
    """Build the finite future-run manifest; this never writes an action."""
    if actor is None or isinstance(actor, bool) or not str(actor):
        _deny('actor_required')
    actor = str(actor)
    files = _file_bindings(files)
    raw, output, profile_digest = _validated_state(run, files)
    access, products, locations = _access(run, access, output)
    commands = _case_plan(run, files, output)
    if any(sku not in products or location not in locations
           for command in commands for sku, location in command['selected']):
        _deny('planned_pair_outside_authenticated_scope')
    value = {
        'schema': SCHEMA,
        'namespace': _namespace(run),
        'run': {'id': str(run.pk), 'input_digest': run.input_digest,
                'output_digest': run.output_digest,
                'profile_digest': profile_digest,
                'business_date': str(run.business_date)},
        'actor': actor,
        'access': access,
        'files': files,
        'policy': POLICY,
        'commands': commands,
    }
    value['phase_identity'] = _phase_identity(value)
    return value


def _expected_payload(command, actor):
    return {'operation': command['operation'],
            'selected': command['selected'],
            'timestamp': command['timestamp'], 'actor': actor}


def _idempotency_key(phase_identity, ordinal):
    return 'preaccept-' + phase_identity + '-%03d' % ordinal


def _verify_prefix(run, output, manifest):
    commands = manifest['commands']
    existing = list(run.commands.order_by('id'))
    if len(existing) > len(commands):
        _deny('extra_existing_command')
    for ordinal, event in enumerate(existing, 1):
        if (event.idempotency_key != _idempotency_key(
                manifest['phase_identity'], ordinal)
                or event.payload != _expected_payload(
                    commands[ordinal - 1], manifest['actor'])):
            _deny('existing_command_prefix_changed')
    from mta.runtime.temporal import command_state
    current, _ = command_state(run, output['DBMFinal'][0])
    return existing, current


def _verify_next_eligibility(prefix, current, manifest):
    if len(prefix) == len(manifest['commands']):
        return
    command = manifest['commands'][len(prefix)]
    selected = {tuple(pair) for pair in command['selected']}
    available = {key(row) for row in current['Suggestions']}
    if not selected or not selected <= available:
        _deny('current_action_eligibility_changed')


def verify_manifest(run, manifest, *, actor, access):
    """Reconstruct all facts and verify an immutable manifest and prefix."""
    if (not isinstance(manifest, dict) or set(manifest) != {
            'schema', 'namespace', 'run', 'actor', 'access', 'files', 'policy',
            'commands', 'phase_identity'} or manifest.get('schema') != SCHEMA):
        _deny('manifest_fields_differ')
    if manifest.get('phase_identity') != _phase_identity({
            key: value for key, value in manifest.items()
            if key != 'phase_identity'}):
        _deny('manifest_identity_changed')
    if str(actor) != manifest['actor'] or access != manifest['access']:
        _deny('authenticated_actor_or_access_changed')
    expected = build_manifest(run, actor=actor, access=access,
                              files=manifest['files'])
    if expected != manifest:
        _deny('manifest_facts_changed')
    _, output, _ = _validated_state(run, manifest['files'])
    prefix, current = _verify_prefix(run, output, manifest)
    _verify_next_eligibility(prefix, current, manifest)
    return manifest, output, prefix, current


def configured_manifest(run, *, actor, access):
    """Load only the explicitly selected immutable phase manifest."""
    path = getattr(settings, 'VF_MTA_PREACCEPTANCE_FILE', '')
    expected = getattr(settings, 'VF_MTA_PREACCEPTANCE_SHA256', '')
    if not path or not expected:
        _deny('configuration_required')
    path = Path(path)
    if not path.is_absolute() or not path.is_file():
        _deny('configured_manifest_unavailable')
    content = path.read_bytes()
    if hashlib.sha256(content).hexdigest() != expected:
        _deny('configured_manifest_digest_changed')
    try:
        manifest = json.loads(content)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise PreacceptanceDenied(
            'preacceptance_actions_configured_manifest_invalid') from error
    return verify_manifest(run, manifest, actor=actor, access=access)


def _lock_phase_run(run):
    """Serialize this phase with every run/seal writer before reading facts."""
    from mta.runtime.models import CalculationRun
    locked = CalculationRun.objects.select_for_update().get(pk=run.pk)
    lock = int.from_bytes(locked.pk.bytes[:8], 'big', signed=True)
    with connection.cursor() as cursor:
        cursor.execute('SELECT pg_try_advisory_xact_lock(%s)', [lock])
        if not cursor.fetchone()[0]:
            _deny('daily_publication_in_progress')
    return locked


@transaction.atomic
def execute(run, *, actor, access):
    """Apply the missing exact command suffix through the existing writer."""
    run = _lock_phase_run(run)
    manifest, output, prefix, current = configured_manifest(
        run, actor=actor, access=access)
    events = list(prefix)
    for ordinal, command in enumerate(manifest['commands'][len(prefix):],
                                      len(prefix) + 1):
        selected = {tuple(pair) for pair in command['selected']}
        available = {key(row) for row in current['Suggestions']}
        if not selected or not selected <= available:
            _deny('current_action_eligibility_changed')
        payload = {'data': [{'SKUCode': sku, 'WHCode': location}
                            for sku, location in command['selected']],
                   'product_permissions': deepcopy(
                       manifest['access']['product_permissions']),
                   'location_permissions': deepcopy(
                       manifest['access']['location_permissions'])}
        context = actions.PreacceptanceActionContext(run=run, output=output,
            dbm=current, action_timestamp=command['timestamp'],
            idempotency_key=_idempotency_key(manifest['phase_identity'], ordinal))
        event, _ = actions.submit(payload, manifest['actor'],
                                  command['operation'], preacceptance=context)
        events.append(event)
        from mta.runtime.temporal import command_state
        current, _ = command_state(run, output['DBMFinal'][0])
    return events
