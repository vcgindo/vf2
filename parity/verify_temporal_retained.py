"""Qualify retained canonical receipts against a fresh persisted temporal run.

This is regression evidence, not fresh SQL execution or ledger-governed acceptance.
No source databases are opened and no comparison fields are dropped.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path

from parity.temporal import BOUNDARIES, differences, fingerprint, legacy_states, command_membership
from mta.serialization import digest
from mta.temporal.actions import apply_command, key

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_gz(path):
    with gzip.open(path, 'rt', encoding='utf-8') as stream:
        return json.load(stream)


def qualify_scripts(result):
    records = []
    baseline = json.loads((ROOT/'baseline/manifest.json').read_text())
    pinned = {row['path'].replace('\\', '/').lower(): row['sha256'] for row in baseline['engine_sources']}
    for row in result['scripts']:
        source = row['path'].replace('\\', '/')
        while '//' in source:
            source = source.replace('//', '/')
        relative = source[len('Scripts/'):] if source.startswith('Scripts/') else source.split('/Scripts/', 1)[1]
        local = Path('F:/VFlow_Local/local-runtime/mta-engine/Scripts')/relative
        preserved = Path('F:/VFlow_Source_Backup/deployed-demo/MTA/V6/Scripts')/relative
        expected = row['sha256']
        if pinned.get(local.as_posix().lower()) != expected or sha(local) != expected or sha(preserved) != expected:
            raise ValueError('Retained script provenance differs: '+relative)
        records.append(dict(path=relative, sha256=expected))
    if not records:
        raise ValueError('Missing canonical script provenance')
    return records


def verify(artifact, ledger, execution, target):
    target.mkdir(parents=True, exist_ok=False)
    retained = json.loads(ledger.read_text())
    fresh = json.loads((execution/'execution.json').read_text())
    expected_hash = sha(artifact)
    register = json.loads((ROOT/'baseline/temporal-regression.json').read_text())
    if register['input']['sha256'] != expected_hash or register['ledger']['sha256'] != sha(ledger):
        raise ValueError('Retained temporal receipt/input does not match the frozen register')
    case = json.loads(artifact.read_text())['case']
    baseline = json.loads((ROOT/'baseline/manifest.json').read_text())
    registered = [r for rows in baseline.values() if isinstance(rows, list) for r in rows
                  if isinstance(r, dict) and r.get('sha256') == expected_hash]
    if not registered or retained['input_sha256'] != expected_hash or fresh['artifact_sha256'] != expected_hash:
        raise ValueError('Retained/fresh input identity differs from registered artifact')
    if retained['status'] != 'PASS' or len(retained['days']) != len(case['days']):
        raise ValueError('Retained receipt is not a complete passing timeline')
    report = dict(status='RUNNING', classification='RETAINED_CANONICAL_REGRESSION',
                  artifact_sha256=expected_hash, retained_ledger_sha256=sha(ledger),
                  execution_sha256=sha(execution/'execution.json'), days=[])
    for ordinal, entry in enumerate(fresh['days']):
        index = entry['day_index']; old = retained['days'][index]
        if index != ordinal or old['day_index'] != index or old['date'] != entry['date'] or old['status'] != 'PASS':
            raise ValueError('Retained date/ordinal differs')
        if entry['status'] != 'COMPUTED_NOT_YET_PARITY' or entry['boundaries'] != list(BOUNDARIES):
            raise ValueError('Modern run incomplete')
        expected_commands = [c for c in case['commands'] if c['after_day'] == index]
        if [c['command'] for c in entry['commands']] != expected_commands:
            raise ValueError('Fresh action schedule differs')
        incoming_commands = [c for c in case['commands'] if c['after_day']==index-1] if index else []
        retained_commands = old['legacy_commands'] if 'legacy_commands' in old else [r['command'] for r in old['actions']]
        if retained_commands != incoming_commands:
            raise ValueError('Retained legacy action schedule differs')
        modern_path = execution/f'day-{index:03d}.json.gz'
        modern = load_gz(modern_path)
        if digest(modern) != entry['output_digest'] or digest(modern['ClosingState']) != entry['closing_digest']:
            raise ValueError('Export differs from persisted output receipt')
        if index:
            parent = fresh['days'][index-1]
            lineage = modern['Lineage'][0]
            if entry['predecessor_id'] != parent['run_id'] or lineage['run_id'] != parent['run_id'] or lineage['output_digest'] != parent['output_digest']:
                raise ValueError('Own-state predecessor lineage differs')
            if lineage['commands'] != [{k:c[k] for k in ('id','digest','before','after')} for c in parent['commands']]:
                raise ValueError('Own-state action lineage differs')
        states = {r['boundary']:r['state'] for r in modern['MajorBoundaries']}
        full_path = ledger.parent/old['legacy_full_output'] if old.get('legacy_full_output') else None
        day = dict(day_index=index, date=entry['date'], modern_sha256=sha(modern_path), comparisons=[])
        legacy = None
        if full_path:
            result = load_gz(full_path)
            if result['status'] != 'PASS':
                raise ValueError('Legacy full receipt failed')
            if [r['command'] for r in result['command_inputs']] != incoming_commands:
                raise ValueError('Retained canonical command inputs differ')
            if incoming_commands:
                action_state = load_gz(execution/f'day-{index-1:03d}.json.gz')['DBMFinal'][0]
                day['action_comparisons'] = []
                for position, action in enumerate(result['command_inputs']):
                    for api in baseline['canonical_api']:
                        if action['api_sha256'] != api['sha256'] or sha(api['path']) != api['sha256']:
                            raise ValueError('Retained command API provenance differs')
                    command = action['command']; selected = set(map(tuple, command['selected']))
                    matched = command_membership(action_state, selected)
                    event = fresh['days'][index-1]['commands'][position]
                    if differences(action['matched_before'], matched) or digest(action_state) != event['before']:
                        raise ValueError('Command input/membership differs')
                    action_state = apply_command(action_state, command['operation'], selected, command['timestamp'])
                    table = 'NormAcceptanceTbl' if command['operation']=='APPLY' else 'NormsInSleepModeTbl'
                    affected = [r for r in action_state[table] if key(r) in selected]
                    if differences(action['affected_after'], affected) or digest(action_state) != event['after']:
                        raise ValueError('Command output differs')
                    day['action_comparisons'].append(dict(command=command, status='PASS'))
            day.update(legacy_sha256=sha(full_path), scripts=qualify_scripts(result))
            legacy = legacy_states(result)
        for name in BOUNDARIES:
            actual = fingerprint(states[name], '/'+name)
            expected = old['legacy_fingerprints'][name]
            if legacy is not None and fingerprint(legacy[name], '/'+name) != expected:
                raise ValueError('Retained full output does not match its ledger')
            comparison = dict(boundary=name, expected=expected, actual=actual,
                              status='PASS' if expected == actual else 'FAIL')
            if expected != actual and legacy is not None:
                comparison['differences'] = differences(legacy[name], states[name], '/'+name)
            day['comparisons'].append(comparison)
            if comparison['status'] == 'FAIL':
                break
        day['status'] = 'PASS' if all(r['status']=='PASS' for r in day['comparisons']) else 'FAIL'
        report['days'].append(day)
        if day['status'] == 'FAIL':
            break
    report['status'] = ('FAIL' if any(d['status']=='FAIL' for d in report['days']) else
                        'PASS' if len(report['days'])==len(case['days']) else 'PARTIAL_PASS')
    (target/'comparison.json').write_text(json.dumps(report,indent=2), encoding='utf-8')
    print(json.dumps(dict(status=report['status'], days=len(report['days']),
        passed_boundaries=sum(c['status']=='PASS' for d in report['days'] for c in d['comparisons']))))
    return report


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    for name in ('artifact','ledger','execution','target'):
        parser.add_argument('--'+name,type=Path,required=True)
    options=parser.parse_args()
    if options.target.exists():
        parser.error('New evidence directory required')
    try:
        result=verify(**vars(options))
    except Exception as error:
        options.target.mkdir(parents=True,exist_ok=True)
        (options.target/'failure.json').write_text(json.dumps(dict(status='HARNESS_FAILURE',
            error_type=type(error).__name__,error=str(error)),indent=2),encoding='utf-8')
        raise
    raise SystemExit(1 if result['status']=='FAIL' else 0)
