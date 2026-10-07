"""Independent offline legacy capture and retained-output comparison.

The orchestration owner must bind and provision its owned legacy namespace
before calling :func:`capture_legacy_day`.  This module deliberately imports no
legacy adapter at module import time.
"""
from copy import deepcopy
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from mta.serialization import digest

CAPTURE_SCHEMA = 'fresh-offline-legacy-capture-v1'


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _write_json_exclusive(path, value):
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')


def _authority():
    # Importing replay_temporal imports legacy namespace ownership.  Keep this
    # lazy so a runner can bind the namespace before any adapter is imported.
    from parity import replay_temporal
    return replay_temporal


def _registered_artifact(artifact, expected_sha):
    artifact = Path(artifact).resolve()
    if _sha(artifact) != expected_sha:
        raise ValueError('Frozen artifact bytes changed')
    manifest = json.loads((ROOT / 'baseline/manifest.json').read_text(encoding='utf-8'))
    registered = [row for row in manifest['retained_resources']
                  if row.get('sha256') == expected_sha]
    if not registered:
        raise ValueError('Use a registered frozen temporal artifact')
    registered_paths = {Path(row['path']).resolve() for row in registered}
    if artifact not in registered_paths:
        raise ValueError('Artifact path differs from its registered identity')


def _bound_namespace(expected):
    if not expected:
        raise ValueError('Explicit legacy namespace binding is required')
    from parity import legacy_isolation
    actual = dict(legacy_isolation.MAPPING)
    if actual != expected:
        raise ValueError('Bound legacy namespace differs from requested ownership')
    if len(set(actual.values())) != len(actual) or any(
            not value.startswith('VFTEST_Fresh_') for value in actual.values()):
        raise ValueError('Legacy namespace is not an owned Fresh mapping')
    return actual


def _execute_legacy_day(*args, **kwargs):
    from parity.adapters.legacy.temporal_day import execute_day
    return execute_day(*args, **kwargs)


def _source_receipt(destination, authority):
    files = authority.source_files()
    value = {'schema': 'fresh-offline-temporal-source-v1', 'files': files,
             'files_digest': digest(files)}
    path = destination / 'source.json'
    _write_json_exclusive(path, value)
    return files, path


def _read_capture(receipt_path, expected_sha=None):
    receipt_path = Path(receipt_path).resolve()
    if expected_sha is None:
        raise ValueError('Capture receipt digest is required')
    if _sha(receipt_path) != expected_sha:
        raise ValueError('Legacy capture receipt digest differs')
    receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
    if receipt.get('schema') != CAPTURE_SCHEMA:
        raise ValueError('Unknown legacy capture receipt')
    return receipt_path, receipt


def _capture_file(receipt_path, receipt, field, sha_field):
    path = Path(receipt[field])
    if not path.is_absolute():
        path = receipt_path.parent / path
    path = path.resolve()
    if not path.is_relative_to(receipt_path.parent) or _sha(path) != receipt[sha_field]:
        raise ValueError('Legacy capture file identity differs')
    return path


def _verify_source(receipt_path, receipt, current=None):
    source = Path(receipt['source_receipt'])
    if not source.is_absolute():
        source = receipt_path.parent / source
    source = source.resolve()
    if (not source.is_relative_to(receipt_path.parent)
            or _sha(source) != receipt['source_receipt_sha256']):
        raise ValueError('Legacy source receipt digest differs')
    value = json.loads(source.read_text(encoding='utf-8'))
    if (value.get('files_digest') != receipt['source_files_digest']
            or digest(value.get('files')) != value.get('files_digest')):
        raise ValueError('Legacy source dependency receipt differs')
    if current is not None and value['files'] != current:
        raise ValueError('Legacy capture dependencies changed')
    return value['files']


def _predecessor(case, index, receipt_path, receipt_sha, input_sha, policy, sources_digest):
    if index == 0:
        if receipt_path is not None or receipt_sha is not None:
            raise ValueError('Initial capture cannot adopt a predecessor receipt')
        return deepcopy(case['opening']), case['opening_date'], None
    if receipt_path is None or receipt_sha is None:
        raise ValueError('Next-day capture requires its own predecessor receipt and digest')
    path, prior = _read_capture(receipt_path, receipt_sha)
    if (prior.get('status') != 'CAPTURED' or prior.get('day_index') != index - 1
            or prior.get('date') != case['days'][index - 1]['business_date']
            or prior.get('input_sha256') != input_sha
            or prior.get('action_policy') != policy
            or prior.get('source_files_digest') != sources_digest):
        raise ValueError('Legacy predecessor is not the contiguous same-contract capture')
    _verify_source(path, prior)
    closing_path = _capture_file(path, prior, 'closing_path', 'closing_sha256')
    authority = _authority()
    closing = authority.load_gzip(closing_path)
    if digest(closing) != prior['closing_digest']:
        raise ValueError('Legacy predecessor closing digest differs')
    return closing, prior['date'], {
        'receipt': str(path), 'sha256': receipt_sha,
        'day_index': prior['day_index'], 'closing_digest': prior['closing_digest'],
    }


def capture_legacy_day(*, artifact, expected_sha, destination, day_index,
                       namespace, predecessor_receipt=None,
                       predecessor_receipt_sha256=None):
    """Capture exactly one next canonical legacy day from its own predecessor."""
    artifact, destination = Path(artifact), Path(destination).resolve()
    if destination.exists():
        raise ValueError('Preserve prior attempt; choose a new capture destination')
    destination.mkdir(parents=True, exist_ok=False)
    receipt = {'schema': CAPTURE_SCHEMA, 'status': 'FAILED',
               'day_index': day_index, 'input_sha256': expected_sha,
               'namespace': dict(namespace), 'started_at_monotonic': time.monotonic()}
    started = time.monotonic()
    try:
        _registered_artifact(artifact, expected_sha)
        case = json.loads(artifact.read_text(encoding='utf-8'))['case']
        if not 0 <= day_index < len(case['days']):
            raise ValueError('Requested legacy day is outside the frozen artifact')
        mapping = _bound_namespace(dict(namespace))
        authority = _authority()
        from parity.temporal_policy import policy_for_case, commands_for_day
        policy = policy_for_case(case)
        sources, source_path = _source_receipt(destination, authority)
        prior, opening_date, predecessor = _predecessor(
            case, day_index, predecessor_receipt, predecessor_receipt_sha256,
            expected_sha, policy, digest(sources))
        day = {**deepcopy(case['days'][day_index]), **deepcopy(case['static_day'])}
        commands = commands_for_day(case, day_index - 1, prior['dbm']['Suggestions']) if day_index else []
        # Namespace equality has been checked before importing the adapter.
        result = _execute_legacy_day(
            prior, opening_date, day, case['profile'], None, commands=commands,
            initial=day_index == 0,
            post_policy=lambda suggestions: commands_for_day(case, day_index, suggestions),
        )
        capture_path = destination / ('legacy-%03d.json.gz' % day_index)
        closing_path = destination / ('legacy-closing-%03d.json.gz' % day_index)
        authority.dump_gzip(capture_path, result)
        authority.dump_gzip(closing_path, result['closing'])
        receipt.update(
            status='CAPTURED', date=day['business_date'], artifact_days=len(case['days']),
            action_policy=policy, namespace=mapping, predecessor=predecessor,
            source_receipt=str(source_path), source_receipt_sha256=_sha(source_path),
            source_files_digest=digest(sources), commands=commands,
            capture_path=str(capture_path), capture_sha256=_sha(capture_path),
            capture_digest=digest(result), closing_path=str(closing_path),
            closing_sha256=_sha(closing_path), closing_digest=digest(result['closing']),
            post_commands=result['post_commands'],
            post_action_state_digest=digest(result['post_command_state']),
            scripts=result['scripts'], command_receipts=result['command_inputs'],
            post_command_receipts=result['post_command_receipts'],
        )
    except Exception as error:
        receipt.update(error_type=type(error).__name__, error=str(error),
                       traceback=traceback.format_exc())
        failure = error
    else:
        failure = None
    receipt['seconds'] = round(time.monotonic() - started, 3)
    receipt.pop('started_at_monotonic', None)
    _write_json_exclusive(destination / 'receipt.json', receipt)
    if failure is not None:
        raise failure
    return receipt


def capture_one(artifact, expected_sha, destination, day_index, previous=None):
    """Runner-facing one-day API after the subprocess binds its namespace."""
    from parity import legacy_isolation
    previous = Path(previous).resolve() if previous is not None else None
    return capture_legacy_day(
        artifact=artifact, expected_sha=expected_sha, destination=destination,
        day_index=day_index, namespace=dict(legacy_isolation.MAPPING),
        predecessor_receipt=previous,
        predecessor_receipt_sha256=_sha(previous) if previous is not None else None,
    )


def _capture_lineage(receipt_path, receipt_sha):
    lineage = []
    path, receipt = _read_capture(receipt_path, receipt_sha)
    while True:
        lineage.append((path, receipt))
        predecessor = receipt.get('predecessor')
        if predecessor is None:
            break
        path, receipt = _read_capture(predecessor['receipt'], predecessor['sha256'])
    lineage.reverse()
    for index, (_, item) in enumerate(lineage):
        if item.get('status') != 'CAPTURED' or item.get('day_index') != index:
            raise ValueError('Legacy capture lineage is not a contiguous accepted prefix')
    return lineage


def _compare_retained(*, artifact, expected_sha, modern_execution,
                      legacy_receipt, legacy_receipt_sha256, destination):
    """Compare an immutable legacy capture lineage to retained modern outputs."""
    artifact = Path(artifact)
    modern_execution = Path(modern_execution).resolve()
    destination = Path(destination).resolve()
    if destination.exists():
        raise ValueError('Preserve prior comparison; choose a new destination')
    destination.mkdir(parents=True, exist_ok=False)
    _registered_artifact(artifact, expected_sha)
    case = json.loads(artifact.read_text(encoding='utf-8'))['case']
    authority = _authority()
    from parity.temporal_policy import policy_for_case
    from parity.temporal import differences, fingerprint, legacy_states
    policy = policy_for_case(case)
    current_sources = authority.source_files()
    lineage = _capture_lineage(legacy_receipt, legacy_receipt_sha256)
    if len(lineage) > len(case['days']):
        raise ValueError('Legacy capture exceeds the frozen horizon')
    for path, capture in lineage:
        if (capture['input_sha256'] != expected_sha or capture['action_policy'] != policy
                or capture['date'] != case['days'][capture['day_index']]['business_date']):
            raise ValueError('Legacy capture input/action/date lineage differs')
        _verify_source(path, capture, current_sources)
    modern_path = modern_execution / 'execution.json'
    modern = json.loads(modern_path.read_text(encoding='utf-8'))
    if (modern.get('artifact_sha256') != expected_sha
            or modern.get('action_policy') != policy
            or len(modern.get('days', [])) < len(lineage)):
        raise ValueError('Modern retained execution input/action/span differs')
    limitation = modern.get('report_exceptions', {})
    if limitation:
        from parity.report_flaws import validate_scope
        validate_scope(limitation, expected_sha, verify_sources=True)
    record = {
        'status': 'RUNNING', 'input_sha256': expected_sha,
        'modern_execution_sha256': _sha(modern_path),
        'requested_days': len(lineage), 'artifact_days': len(case['days']),
        'databases': lineage[-1][1]['namespace'], 'days': [],
        'action_policy': policy, 'report_limitation_digest': digest(limitation),
        'legacy_capture_receipt': {'path': str(Path(legacy_receipt).resolve()),
                                   'sha256': legacy_receipt_sha256},
    }
    for index, (receipt_path, capture) in enumerate(lineage):
        entry = {'day_index': index, 'date': capture['date'], 'status': 'RUNNING',
                 'opening_digest': (digest(case['opening']) if index == 0
                                    else lineage[index - 1][1]['closing_digest']),
                 'commands': capture['commands']}
        try:
            current = modern['days'][index]
            if (current.get('day_index') != index or current.get('date') != entry['date']
                    or current.get('status') != 'COMPUTED_NOT_YET_PARITY'):
                raise ValueError('Modern date/status differs')
            legacy_path = _capture_file(receipt_path, capture, 'capture_path', 'capture_sha256')
            legacy = authority.load_gzip(legacy_path)
            if digest(legacy) != capture['capture_digest']:
                raise ValueError('Legacy capture logical digest differs')
            if current.get('output_archive'):
                actual = authority.OutputArchive(modern_execution / current['output_archive'])
                actual.verify(current['output_digest'])
            else:
                modern_day = modern_execution / ('day-%03d.json.gz' % index)
                actual = authority.load_gzip(modern_day)
                if digest(actual) != current['output_digest']:
                    raise ValueError('Modern export/readback digest differs')
            checks = authority.compare_day(legacy, actual, limitation, entry['date'])
            if authority.independent_contracts_pass(checks):
                action_path = modern_execution / ('actions-%03d.json.gz' % index)
                post = authority.load_gzip(action_path)['state']
                if digest(post) != current['post_action_state_digest']:
                    raise ValueError('Modern persisted action state digest differs')
                for name, left, right in (
                    ('own-action-selection', legacy['post_commands'],
                     [row['command'] for row in current['commands']]),
                    ('post-action-state', legacy['post_command_state'], post),
                ):
                    delta = differences(left, right, '/' + name)
                    checks.append({'contract': name, 'status': 'FAIL' if delta else 'PASS',
                                   'differences': delta})
            passed = len(checks) == 31 and authority.independent_contracts_pass(checks)
            status = ('DIVERGENCE' if not passed else 'PASS_WITH_LEGACY_FLAWS'
                      if any(row['status'] == 'LEGACY_FLAW' for row in checks) else 'PASS')
            entry.update(
                status=status, closing_digest=capture['closing_digest'], comparisons=checks,
                scripts=capture['scripts'], command_receipts=capture['command_receipts'],
                legacy_capture_path=str(legacy_path),
                legacy_closing_path=capture['closing_path'],
                legacy_capture_sha256=capture['capture_sha256'],
                legacy_boundaries={key: fingerprint(value, '/' + key)
                                   for key, value in legacy_states(legacy).items()},
                modern_run=current['run_id'], modern_output_digest=current['output_digest'],
                post_commands=legacy['post_commands'],
                post_command_receipts=capture['post_command_receipts'],
                post_action_state_digest=digest(legacy['post_command_state']),
                capture_receipt={'path': str(receipt_path), 'sha256': _sha(receipt_path)},
            )
        except Exception:
            entry.update(status='HARNESS_FAILURE', error=traceback.format_exc())
        record['days'].append(entry)
        success = entry['status'] in ('PASS', 'PASS_WITH_LEGACY_FLAWS')
        record['status'] = (
            ('COMPLETE_WITH_LEGACY_FLAWS'
             if any(day['status'] == 'PASS_WITH_LEGACY_FLAWS' for day in record['days']) else 'PASS')
            if index == len(lineage) - 1 and success else 'RUNNING' if success else entry['status']
        )
        if not success:
            break
    _write_json_exclusive(destination / 'replay.json', record)
    _write_json_exclusive(destination / 'source.json', {
        'schema': 'fresh-offline-retained-comparison-source-v1',
        'files': current_sources, 'files_digest': digest(current_sources),
    })
    return record


def compare_retained(artifact, expected_sha, modern_execution,
                     legacy_capture, destination):
    """Runner-facing comparison API using the terminal capture receipt path."""
    legacy_capture = Path(legacy_capture).resolve()
    return _compare_retained(
        artifact=artifact, expected_sha=expected_sha,
        modern_execution=modern_execution, legacy_receipt=legacy_capture,
        legacy_receipt_sha256=_sha(legacy_capture), destination=destination,
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    capture = commands.add_parser('capture-legacy', aliases=['legacy-only'])
    compare = commands.add_parser('compare-retained')
    for command in (capture, compare):
        command.add_argument('--artifact', type=Path, required=True)
        command.add_argument('--expected-sha', required=True)
        command.add_argument('--destination', type=Path, required=True)
    capture.add_argument('--day-index', type=int, required=True)
    capture.add_argument('--namespace-json', type=Path, required=True)
    capture.add_argument('--predecessor-receipt', type=Path)
    capture.add_argument('--predecessor-receipt-sha256')
    compare.add_argument('--modern-execution', type=Path, required=True)
    compare.add_argument('--legacy-receipt', type=Path, required=True)
    compare.add_argument('--legacy-receipt-sha256', required=True)
    options = vars(parser.parse_args(argv))
    command = options.pop('command')
    if command in ('capture-legacy', 'legacy-only'):
        namespace_path = options.pop('namespace_json')
        options['namespace'] = json.loads(namespace_path.read_text(encoding='utf-8'))
        capture_legacy_day(**options)
    else:
        legacy_capture = options.pop('legacy_receipt')
        supplied_sha = options.pop('legacy_receipt_sha256')
        if _sha(legacy_capture) != supplied_sha:
            raise ValueError('Legacy capture receipt digest differs')
        record = compare_retained(legacy_capture=legacy_capture, **options)
        return 0 if record['status'] in ('PASS', 'COMPLETE_WITH_LEGACY_FLAWS') else 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
