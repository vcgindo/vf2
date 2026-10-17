"""Fail-closed validation for one successor of an accepted daily execution."""
from copy import deepcopy
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil

from mta.serialization import digest


RUNNER_PATHS = frozenset((
    'mta/runtime/management/commands/run_temporal.py',
    'mta/runtime/temporal_continuation.py',
))

# Exact presentation/activation/validation and MDM configuration-handoff delta between the accepted
# smoke day-one source manifest and the reviewed successor source tree. Any
# further change, including a change under another path, needs a new review.
REVIEWED_NON_EXECUTION_TRANSITION = (
    '9ef812281175fc21b3556bf981ad1416105149bffb19b04c47a1c95dd2d20895'
)


def file_sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def mapping_digest(value):
    payload = json.dumps(value, sort_keys=True, separators=(',', ':')).encode()
    return hashlib.sha256(payload).hexdigest()


def validate_source_transition(previous_source, current_files):
    """Accept only the exact reviewed non-calculation source transition."""
    previous_files = previous_source.get('files')
    if not isinstance(previous_files, dict) or not previous_files:
        raise ValueError('Continuation source manifest is incomplete')
    if previous_files == current_files:
        identity = mapping_digest(previous_files)
        return dict(schema='fresh-modern-successor-source-identity-v1',
            before_digest=identity, after_digest=identity,
            unchanged_semantics_digest=identity,
            reviewed_non_execution_digest=mapping_digest([]), changes=[])
    from mta.runtime.offline_transition import modern_sources
    approved = modern_sources(previous_files, current_files)
    if approved is not None:
        return approved
    changes = [dict(path=path, before=previous_files.get(path), after=current_files.get(path))
               for path in sorted(set(previous_files) | set(current_files))
               if previous_files.get(path) != current_files.get(path)]
    reviewed = [row for row in changes if row['path'] not in RUNNER_PATHS]
    if mapping_digest(reviewed) != REVIEWED_NON_EXECUTION_TRANSITION:
        raise ValueError('Unreviewed engine/application/temporal/action source transition')
    runner = [row for row in changes if row['path'] in RUNNER_PATHS]
    if {row['path'] for row in runner} != RUNNER_PATHS:
        raise ValueError('Successor orchestration source transition is incomplete')
    unchanged = {path: previous_files[path] for path in sorted(set(previous_files) & set(current_files))
                 if previous_files[path] == current_files[path]}
    return dict(schema='fresh-modern-successor-source-transition-v1',
        before_digest=mapping_digest(previous_files), after_digest=mapping_digest(current_files),
        unchanged_semantics_digest=mapping_digest(unchanged),
        reviewed_non_execution_digest=mapping_digest(reviewed), changes=changes)


def successor_index(execution, through, case):
    prefix = execution.get('days')
    if (not isinstance(prefix, list) or not prefix or through != len(prefix)
            or through >= len(case['days'])):
        raise ValueError('Continuation must execute exactly one immediate successor')
    return through


def execution_lineage(previous, execution):
    """Resolve immutable execution ancestors, preserving each original proof link."""
    root = Path(os.environ['VF_EVIDENCE_ROOT']).resolve().parent
    path = (previous / 'execution.json').resolve()
    current = execution
    result = {}
    while True:
        if not path.is_relative_to(root) or path in result:
            raise ValueError('Execution lineage escaped its owner or contains a cycle')
        raw = path.read_bytes()
        if json.loads(raw) != current:
            raise ValueError('Execution lineage content differs')
        result[path] = file_sha(path)
        link = current.get('continuation')
        if not link:
            break
        parent_path = Path(link['path']).resolve()
        if not parent_path.is_relative_to(root) or file_sha(parent_path) != link['sha256']:
            raise ValueError('Execution ancestor identity differs')
        if file_sha(parent_path.parent / 'source.json') != link.get('source_sha256'):
            raise ValueError('Execution ancestor source identity differs')
        parent = json.loads(parent_path.read_bytes())
        prefix = composed_prefix(parent)
        if (not prefix or len(prefix) >= len(current['days'])
                or prefix != composed_prefix(current)[:len(prefix)]
                or any(parent.get(key) != current.get(key) for key in
                       ('artifact_sha256', 'artifact_days', 'action_policy', 'report_exceptions', 'mdm_source'))):
            raise ValueError('Execution ancestor is not the unchanged accepted prefix')
        path, current = parent_path, parent
    return frozenset(result.values())


def _accepted_receipt(summary, previous, execution, *, execution_hashes=None):
    root = Path(os.environ['VF_EVIDENCE_ROOT']).resolve().parent
    receipt_path = (root / summary.get('receipt', '')).resolve()
    if not receipt_path.is_relative_to(root) or not receipt_path.is_file():
        raise ValueError('Accepted parity receipt path differs')
    receipt_bytes = receipt_path.read_bytes()
    if hashlib.sha256(receipt_bytes).hexdigest() != summary.get('sha256'):
        raise ValueError('Accepted parity receipt bytes differ')
    receipt = json.loads(receipt_bytes)
    if execution_hashes is None:
        execution_hashes = execution_lineage(previous, execution)
    if (receipt.get('modern_execution_sha256') not in execution_hashes
            or receipt.get('input_sha256') != execution['artifact_sha256']
            or receipt.get('action_policy') != execution['action_policy']
            or receipt.get('status') not in ('PASS', 'COMPLETE_WITH_LEGACY_FLAWS')):
        raise ValueError('Accepted parity receipt identity differs')
    return receipt


def validate_accepted_prefix(previous, execution, case, *, require_parity=True):
    """Validate every persisted prefix fact before returning its last run."""
    from mta.runtime.management.commands.record_parity import CONTRACTS
    from mta.runtime.models import CalculationRun
    from mta.runtime.services import read_outputs
    from mta.runtime.temporal import BOUNDARIES, KIND, command_state
    from parity.output_archive import OutputArchive
    from parity.replay_temporal import independent_contracts_pass

    days = execution.get('days')
    if (not isinstance(days, list) or not days or execution.get('requested_days') != len(days)
            or execution.get('artifact_days') != len(case['days'])):
        raise ValueError('Continuation requires one complete retained prefix')
    expected = list(CONTRACTS)
    if execution['action_policy'] != 'retained-fixed-actions':
        from parity.temporal_policy import policy_for_case
        if execution['action_policy'] != policy_for_case(case):
            raise ValueError('Continuation action policy differs')
        expected += ['own-action-selection', 'post-action-state']
    prior = None
    execution_hashes = execution_lineage(previous, execution)
    for index, current in enumerate(days):
        expected_revision = current.get('execution_revision', execution.get('revision'))
        if (current.get('day_index') != index
                or current.get('date') != case['days'][index]['business_date']
                or current.get('status') != 'COMPUTED_NOT_YET_PARITY'
                or current.get('input_sha256') != execution['artifact_sha256']
                or not isinstance(expected_revision, str) or not expected_revision):
            raise ValueError('Continuation prefix is not contiguous and complete')
        run = CalculationRun.objects.get(pk=current['run_id'])
        run_predecessor = str(run.predecessor_id) if run.predecessor_id else None
        if (run.status != 'SUCCEEDED' or run.kind != KIND
                or run.business_date.isoformat() != current['date']
                or run_predecessor != current.get('predecessor_id')):
            raise ValueError('Persisted continuation lineage differs')
        if ((str(run.predecessor_id) if run.predecessor_id else None)
                != (str(prior.pk) if prior else None)):
            raise ValueError('Persisted continuation predecessor chain differs')
        if (run.input_digest != current.get('input_digest')
                or run.output_digest != current.get('output_digest')
                or run.execution_revision != expected_revision):
            raise ValueError('Persisted continuation run identity differs')
        mdm = execution.get('mdm_source')
        if mdm is not None:
            capture = getattr(run, 'mdm_input_capture', None)
            if (capture is None or str(capture.source_id) != mdm['id']
                    or capture.status != 'CONSUMED'):
                raise ValueError('Persisted continuation MDM capture differs')
        output = read_outputs(run)
        if (digest(output['ClosingState']) != current.get('closing_digest')
                or current.get('boundaries') != list(BOUNDARIES)
                or current.get('suggestions') != len(output['DBMFinal'][0]['Suggestions'])):
            raise ValueError('Persisted continuation closing state differs')
        manifest = (previous / current['output_archive']).resolve()
        if not manifest.is_relative_to(previous.resolve()):
            raise ValueError('Continuation output archive escaped its evidence owner')
        OutputArchive(manifest).verify(run.output_digest,run.validation_digest)

        state, events = command_state(run, output['DBMFinal'][0])
        action_path = previous / ('actions-%03d.json.gz' % index)
        with gzip.open(action_path, 'rt', encoding='utf-8') as stream:
            action = json.load(stream)
        if (action != {'state': state, 'events': events}
                or digest(state) != current.get('post_action_state_digest')):
            raise ValueError('Continuation action capture differs')
        db_commands = list(run.commands.order_by('id'))
        captured = current.get('commands', [])
        if len(db_commands) != len(captured):
            raise ValueError('Continuation command multiplicity differs')
        for event, row in zip(db_commands, captured):
            command = row.get('command', {})
            try:
                expected_payload = dict(operation=command['operation'],selected=command['selected'],
                    timestamp=command['timestamp'],actor='retained-synthetic-trial')
            except KeyError as error:
                raise ValueError('Continuation command facts are incomplete') from error
            if (event.pk != row.get('id') or event.payload != expected_payload
                    or event.digest != row.get('digest') or event.before_digest != row.get('before')
                    or event.after_digest != row.get('after')):
                raise ValueError('Continuation command identity differs')

        if require_parity:
            summary = run.parity_summary
            if summary.get('offline_rrr_proof'):
                from mta.presentation.offline_rrr import require_proof
                require_proof(run)
            receipt = _accepted_receipt(summary, previous, execution,
                                        execution_hashes=execution_hashes)
            if index >= len(receipt.get('days', [])):
                raise ValueError('Accepted parity receipt lacks prefix day')
            accepted = receipt['days'][index]
            checks = accepted.get('comparisons', [])
            statuses = {row['contract']: row['status'] for row in checks}
            accepted_status = ('PASS_WITH_LEGACY_FLAWS'
                               if any(row['status'] == 'LEGACY_FLAW' for row in checks) else 'PASS')
            if ([row.get('contract') for row in checks] != expected
                    or not independent_contracts_pass(checks)
                    or accepted.get('status') != accepted_status
                    or accepted.get('day_index') != index or accepted.get('date') != current['date']
                    or accepted.get('modern_run') != str(run.pk)
                    or accepted.get('modern_output_digest') != run.output_digest
                    or summary.get('status') != accepted_status or summary.get('day_index') != index
                    or summary.get('artifact_sha256') != execution['artifact_sha256']
                    or summary.get('boundaries') != list(BOUNDARIES)
                    or summary.get('comparisons') != statuses
                    or summary.get('legacy_flaw_is_parity') is not False):
                raise ValueError('Existing parity acceptance differs from full receipt')
        successors = run.successors.filter(status__in=('RUNNING', 'SUCCEEDED'))
        if index + 1 < len(days):
            successors = successors.exclude(pk=days[index + 1]['run_id'])
        if successors.exists():
            raise ValueError('Accepted prefix already has an active successor')
        prior = run
        del output, state, action, db_commands
    return prior


def copy_prefix_evidence(previous, target, execution):
    """Preserve relative archive names and exact action bytes in a sibling receipt."""
    if previous.resolve().parent != target.resolve().parent:
        raise ValueError('Continuation evidence must be a sibling of its retained prefix')
    copied = []
    for current in execution['days']:
        index = current['day_index']
        source_manifest = (previous / current['output_archive']).resolve()
        target_manifest = (target / current['output_archive']).resolve()
        if (not source_manifest.is_relative_to(previous.resolve())
                or not target_manifest.is_relative_to(target.resolve())):
            raise ValueError('Continuation archive path escaped its evidence owner')
        target_manifest.parent.mkdir(parents=True, exist_ok=False)
        shutil.copyfile(source_manifest, target_manifest)
        if file_sha(source_manifest) != file_sha(target_manifest):
            raise ValueError('Continuation archive manifest copy differs')
        action_name = 'actions-%03d.json.gz' % index
        source_action, target_action = previous / action_name, target / action_name
        shutil.copyfile(source_action, target_action)
        if file_sha(source_action) != file_sha(target_action):
            raise ValueError('Continuation action receipt copy differs')
        copied.append(dict(day_index=index, output_archive=current['output_archive'],
                           manifest_sha256=file_sha(target_manifest), action=action_name,
                           action_sha256=file_sha(target_action)))
    return copied


def composed_prefix(execution):
    rows = deepcopy(execution['days'])
    for row in rows:
        row['execution_revision'] = row.get('execution_revision', execution['revision'])
    return rows
