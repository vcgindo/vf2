"""Prepare one owned pre-action DBM trial; no serving switch or action submission.

Reuse prove_action_http's exact retained input, execute_day and29 comparisons.
The resulting proposal is not permission to attach a new hierarchy supplement.
"""
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
from mta.runtime.management.commands.prove_action_http import (
    INPUT_SHA, REPLAY_SHA, frozen_existing, sha,
)
from mta.runtime.models import CalculationRun
from mta.runtime.services import read_outputs
from development.temporal import execute_day
from development.validation_storage import export_run
from mta.presentation.admission import PROJECTIONS
from mta.presentation.selective import image_rows
from mta.serialization import digest
from parity.output_archive import OutputArchive
from parity.replay_temporal import compare_day, independent_contracts_pass
from parity.temporal_policy import POLICY, commands_for_day


def main():
    target, revision = Path(sys.argv[1]), sys.argv[2]
    target.mkdir(parents=True, exist_ok=False)
    result = dict(status='FAILED', serving_changes=False, commands_submitted=False)
    before = frozen_existing()
    (target / 'existing-before.json').write_text(json.dumps(before, indent=2))
    try:
        input_path = Path('/inputs/representative-bridge-input.json')
        replay_path = Path('/evidence/f2-auto-sql-012/replay.json')
        assert sha(input_path) == INPUT_SHA and sha(replay_path) == REPLAY_SHA
        case = json.loads(input_path.read_text())['case']
        replay = json.loads(replay_path.read_text())
        assert replay['status'] == 'PASS' and replay['action_policy'] == POLICY
        entry = replay['days'][0]
        assert len(entry['comparisons']) == 31 and independent_contracts_pass(entry['comparisons'])
        registered = entry['legacy_capture_path'].replace('\\', '/')
        assert registered.startswith('D:/freshvcf-build/evidence/')
        capture_path = Path('/evidence') / registered[len('D:/freshvcf-build/evidence/'):]
        assert sha(capture_path) == entry['legacy_capture_sha256']
        with gzip.open(capture_path, 'rt', encoding='utf-8') as stream:
            legacy = json.load(stream)
        assert digest(legacy['closing']) == entry['closing_digest']
        day = {**deepcopy(case['days'][0]), **deepcopy(case['static_day'])}
        run = execute_day(day=day, profile=case['profile'], execution_revision=revision,
            opening=dict(state=case['opening'], opening_date=case['opening_date'],
                         identity='f3-stage2-browser-'+target.name+'-'+INPUT_SHA))
        result['run_id'] = str(run.pk)
        archive = OutputArchive(export_run(run, target / 'day-000'))
        checks = compare_day(legacy, archive)
        assert len(checks) == 29 and independent_contracts_pass(checks), checks
        current = dict(day_index=0, run_id=str(run.pk), input_digest=run.input_digest,
                       output_digest=run.output_digest)
        modern = dict(artifact_sha256=INPUT_SHA, action_policy='retained-fixed-actions',
                      revision=revision, days=[current])
        modern_path = target / 'pre-action-modern-0.json'
        modern_path.write_text(json.dumps(modern, indent=2))
        comparison = dict(status='PASS', input_sha256=INPUT_SHA, action_policy='retained-fixed-actions',
            modern_execution_sha256=sha(modern_path), requested_days=1,
            days=[dict(day_index=0, date=str(run.business_date), modern_run=str(run.pk),
                       modern_output_digest=run.output_digest, status='PASS', comparisons=checks)])
        compare_path = target / 'pre-action-comparison-0.json'
        compare_path.write_text(json.dumps(comparison, indent=2))
        call_command('record_parity', replay=compare_path, modern_execution=modern_path)
        run.refresh_from_db()
        output = read_outputs(run)
        suggestions = output['DBMFinal'][0]['Suggestions']
        native_scope = {}
        for owner in ('dbm', 'importer'):
            for table, prefix in [('SkuAttributeData', 'SL'), ('LocationAttributeData', 'LL')]:
                rows = image_rows(run, 'closing/'+owner+'/'+table)
                native_scope[owner+'/'+table] = dict(rows=len(rows), all_three_null=sum(
                    all(row.get(prefix+str(i)) is None for i in (1, 2, 3)) for row in rows))
        assert run.commands.count() == 0
        proposed = json.loads(Path('/app/baseline/presentation-hierarchy-v1.json').read_text())
        proposed['publications'] = [dict(run_id=str(run.pk), business_date=str(run.business_date),
                                         output_digest=run.output_digest)]
        proposed['authorization'] = 'PROPOSAL ONLY: requires explicit scope binding before use in the temporary DBM window.'
        proposal_path = target / 'hierarchy-proposal.json'
        proposal_path.write_text(json.dumps(proposed, indent=2))
        result.update(status='PRE_ACTION_PARITY_PASS_SCOPE_BINDING_REQUIRED',
            business_date=str(run.business_date), output_digest=run.output_digest,
            artifact_sha256=INPUT_SHA, retained_replay_sha256=REPLAY_SHA,
            comparisons=29, current_suggestions=len(suggestions), native_scope=native_scope,
            projections={m.__name__:m.objects.filter(run=run).count() for m in PROJECTIONS},
            planned_commands=commands_for_day(case, 0, suggestions),
            hierarchy_proposal_sha256=sha(proposal_path),
            hierarchy_proposal_active=False, terminal_supplement_permitted=False,
            input_snapshot=run.input_payload['path'])
        after = frozen_existing()
        assert all(after['runs'][k] == v for k, v in before['runs'].items())
        assert after['commands'] == before['commands']
        assert set(after['runs'])-set(before['runs']) == {str(run.pk)}
        (target / 'existing-after.json').write_text(json.dumps(after, indent=2))
    except Exception as exc:
        result['error'] = repr(exc)
        raise
    finally:
        (target / 'receipt.json').write_text(json.dumps(result, indent=2))
        print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
