"""Prove the completed browser trial and its own next day, with no new actions."""
from copy import deepcopy
import gzip
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
import django
django.setup()
from django.core.management import call_command
from mta.runtime.management.commands.prove_action_http import INPUT_SHA, REPLAY_SHA, frozen_existing, sha
from mta.runtime.models import CalculationRun
from mta.runtime.services import read_outputs
from development.temporal import execute_day
from mta.runtime.temporal import command_state
from development.validation_storage import export_run, read_input
from mta.serialization import digest
from parity.output_archive import OutputArchive
from parity.replay_temporal import compare_day, independent_contracts_pass
from parity.temporal import differences
from parity.temporal_policy import POLICY, commands_for_day

TRIAL = '20261d94-b78a-4141-8770-2fe2d5b3354b'


def main():
    target = Path(sys.argv[1])
    assert target.parent == Path('/evidence') and not target.exists()
    target.mkdir()
    result = dict(status='FAILED', commands_submitted=False, legacy_replays=0,
                  parent=TRIAL, serving_changes=False)
    before = frozen_existing()
    (target / 'existing-before.json').write_text(json.dumps(before, indent=2))
    try:
        prepared = Path('/evidence/f3-stage2-dbm-prepare-001')
        identity = json.loads((prepared / 'readback.json').read_text())
        prior_receipt = json.loads((prepared / 'pre-action-comparison-0.json').read_text())
        assert prior_receipt['status'] == 'PASS'
        parent = CalculationRun.objects.get(pk=TRIAL)
        assert str(parent.pk) == identity['run_id'] and parent.output_digest == identity['output_digest']
        assert not parent.successors.exists(), 'Never silently repeat an accepted next day'
        artifact = Path('/inputs/representative-bridge-input.json')
        replay = Path('/evidence/f2-auto-sql-012/replay.json')
        assert sha(artifact) == INPUT_SHA and sha(replay) == REPLAY_SHA
        case = json.loads(artifact.read_text())['case']
        retained = json.loads(replay.read_text())
        assert retained['status'] == 'PASS' and retained['action_policy'] == POLICY

        def legacy_day(index):
            entry = retained['days'][index]
            assert len(entry['comparisons']) == 31 and independent_contracts_pass(entry['comparisons'])
            registered = entry['legacy_capture_path'].replace('\\', '/')
            assert registered.startswith('D:/freshvcf-build/evidence/')
            path = Path('/evidence') / registered[len('D:/freshvcf-build/evidence/'):]
            assert sha(path) == entry['legacy_capture_sha256']
            with gzip.open(path, 'rt', encoding='utf-8') as stream:
                value = json.load(stream)
            assert digest(value['closing']) == entry['closing_digest']
            return value, entry

        output = read_outputs(parent)
        commands = commands_for_day(case, 0, output['DBMFinal'][0]['Suggestions'])
        actual = list(parent.commands.order_by('id').values_list('payload', flat=True))
        expected = [{k: command[k] for k in ('operation', 'selected', 'timestamp')} | {'actor': '1'}
                    for command in commands]
        assert actual == expected and len(actual) == 3, 'Actual browser actions differ from retained policy'
        state, lineage = command_state(parent, output['DBMFinal'][0])
        legacy, entry0 = legacy_day(0)
        delta_actions = differences(legacy['post_commands'], commands, '/own-action-selection')
        delta_state = differences(legacy['post_command_state'], state, '/post-action-state')
        assert not delta_actions and not delta_state, (delta_actions, delta_state)
        checks0 = deepcopy(prior_receipt['days'][0]['comparisons'])
        assert len(checks0) == 29 and independent_contracts_pass(checks0)
        post = dict(actual_browser_commands=actual, command_lineage=lineage,
                    raw_suggestions=len(state['Suggestions']), post_action_digest=digest(state),
                    legacy_capture_sha256=entry0['legacy_capture_sha256'], comparisons=checks0 + [
                        dict(contract='own-action-selection', status='PASS', differences=[]),
                        dict(contract='post-action-state', status='PASS', differences=[])])
        (target / 'post-action-readback.json').write_text(json.dumps(post, indent=2))
        print(json.dumps({'status': 'BROWSER_COMMANDS_AND_FULL_POST_STATE_PASS', 'commands': 3}), flush=True)
        del output, state, legacy

        day = {**deepcopy(case['days'][1]), **deepcopy(case['static_day'])}
        following = execute_day(day=day, profile=case['profile'],
                                execution_revision=parent.execution_revision, predecessor=parent)
        result['next_run'] = str(following.pk)
        archive = OutputArchive(export_run(following, target / 'day-001'))
        legacy, entry1 = legacy_day(1)
        checks1 = compare_day(legacy, archive)
        assert len(checks1) == 29 and independent_contracts_pass(checks1), checks1
        assert following.predecessor_id == parent.pk and following.commands.count() == 0
        own_input = read_input(following)
        assert own_input['lineage'] == dict(run_id=TRIAL, output_digest=parent.output_digest, commands=lineage)
        native = read_outputs(following)
        assert not differences(archive['ClosingState'], native['ClosingState'], '/next-day-native-readback')
        days = [dict(day_index=i, run_id=str(r.pk), input_digest=r.input_digest, output_digest=r.output_digest)
                for i, r in enumerate((parent, following))]
        modern = dict(artifact_sha256=INPUT_SHA, action_policy='retained-fixed-actions',
                      revision=parent.execution_revision, days=days)
        modern_path = target / 'execution.json'
        modern_path.write_text(json.dumps(modern, indent=2))
        comparison = dict(status='PASS', input_sha256=INPUT_SHA, action_policy='retained-fixed-actions',
            modern_execution_sha256=sha(modern_path), requested_days=2, days=[
                dict(day_index=i, date=str(r.business_date), modern_run=str(r.pk),
                     modern_output_digest=r.output_digest, status='PASS', comparisons=checks)
                for i, (r, checks) in enumerate(((parent, checks0), (following, checks1)))])
        comparison_path = target / 'comparison.json'
        comparison_path.write_text(json.dumps(comparison, indent=2))
        call_command('record_parity', replay=comparison_path, modern_execution=modern_path)
        after = frozen_existing()
        assert all(after['runs'][key] == value for key, value in before['runs'].items() if key != TRIAL)
        assert after['commands'] == before['commands']
        assert set(after['runs']) - set(before['runs']) == {str(following.pk)}
        (target / 'existing-after.json').write_text(json.dumps(after, indent=2))
        result.update(status='PASS_BROWSER_ACTIONS_AND_OWN_NEXT_DAY', comparisons=60,
            reused_preaction_comparisons=29, new_postaction_comparisons=2, new_nextday_comparisons=29,
            next_date=str(following.business_date), next_output_digest=following.output_digest,
            next_input_lineage=own_input['lineage'], next_current_suggestions=len(native['DBMFinal'][0]['Suggestions']),
            exact_native_closing_readback=True, other_runs_and_all_commands_unchanged=True,
            retained_replay_sha256=REPLAY_SHA, next_legacy_capture_sha256=entry1['legacy_capture_sha256'],
            next_day_actions_submitted=False)
    except Exception as exc:
        result['error'] = repr(exc)
        raise
    finally:
        (target / 'receipt.json').write_text(json.dumps(result, indent=2))
        print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
