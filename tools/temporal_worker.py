"""F2 validation only: one fresh worker, one day, original production boundary.

Kept outside mta/parity so accepted engine/oracle source pins do not change.
An explicit attempt revision preserves failed identities; accepted predecessors
are never recalculated, rewritten or populated from an oracle capture.
"""
import argparse
from copy import deepcopy
import gc
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
# Exact earlier orchestration version: preserve its day-ten receipt/source while
# removing only unused artifact references from subsequent fresh workers.
RETAINED_WORKER = 'b49e199734dda06bd125d8970dbd3b4fbd64526e0fa8457ad1040ff4d95d04ce'
RETAINED_RELEASE_WORKER = '63ca58fc8bf8d54b8ecd1bbe1181a4c88fdf659d9efa44d45e7a565201d6e9a9'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def sequence(record, case, expected_sha):
    from parity.temporal_policy import POLICY
    if record['artifact_sha256'] != expected_sha or record['action_policy'] != POLICY:
        raise ValueError('Retained input/action identity differs')
    days = record['days']
    if not days or len(days) > len(case['days']):
        raise ValueError('Missing or excessive retained prefix')
    if record['requested_days'] != len(case['days']) or record['artifact_days'] != len(case['days']):
        raise ValueError('Frozen horizon differs')
    for index, entry in enumerate(days):
        if (entry['day_index'] != index or entry['date'] != case['days'][index]['business_date']
                or entry['status'] != 'COMPUTED_NOT_YET_PARITY'
                or entry['input_sha256'] != expected_sha):
            raise ValueError('Noncontiguous or incomplete modern prefix')
    return len(days)


def verify_sources(directory):
    source = json.loads((directory/'source.json').read_text())
    if any(sha(ROOT/name) != value for name, value in source['files'].items()):
        raise ValueError('Pinned engine/evidence dependency changed')
    orchestration = source.get('one_day_worker')
    if orchestration:
        current = dict(path='tools/temporal_worker.py', sha256=sha(__file__))
        if orchestration != current:
            archived = directory/'worker-source.py'
            if (orchestration.get('path') != 'tools/temporal_worker.py'
                    or orchestration.get('sha256') not in (RETAINED_WORKER, RETAINED_RELEASE_WORKER)
                    or not archived.is_file() or sha(archived) != orchestration['sha256']):
                raise ValueError('Unpinned one-day orchestration change')
    return source


def select_day_inputs(case, index):
    """Keep precisely what execute_day and the unchanged action policy consume.

The initial opening and other days' external facts are not a resumed day's
inputs. Do not keep their parsed object graph alive alongside engine traces.
    """
    day = {**deepcopy(case['days'][index]), **deepcopy(case['static_day'])}
    policy_case = dict(days=[{'business_date':d['business_date']} for d in case['days']],
                       commands=deepcopy(case['commands']))
    return case['profile'], day, policy_case


def predecessor_process(previous):
    """Await the same integrity checks, then release their entire process heap."""
    result = subprocess.run([sys.executable, str(Path(__file__).resolve()),
        'verify-predecessor', '--previous', str(previous)],
        check=True, capture_output=True, text=True)
    return json.loads(result.stdout)


def verify_predecessor(options):
    from mta.runtime.models import CalculationRun
    from mta.runtime.services import read_outputs
    from mta.runtime.temporal import command_state
    from mta.serialization import digest

    verify_sources(options.previous)
    prior = json.loads((options.previous/'execution.json').read_text())['days'][-1]
    parent = CalculationRun.objects.get(pk=prior['run_id'])
    opening = read_outputs(parent)
    state, events = command_state(parent, opening['DBMFinal'][0])
    if digest(opening['ClosingState']) != prior['closing_digest'] or digest(state) != prior['post_action_state_digest']:
        raise ValueError('Committed predecessor closing/action state differs')
    print(json.dumps(dict(status='VERIFIED', process_id=os.getpid(), parent_process_id=os.getppid(),
        predecessor_id=str(parent.pk), closing_digest=prior['closing_digest'],
        post_action_state_digest=prior['post_action_state_digest'])))


def run_one(options):
    from mta.runtime.models import CalculationRun
    from mta.runtime.services import read_outputs
    from mta.runtime.temporal import execute_day, record_command, command_state
    from mta.runtime.validation_storage import export_run
    from mta.runtime.management.commands.prove_sizeable_storage import resources
    from mta.serialization import digest
    from parity.output_archive import OutputArchive
    from parity.temporal_ledger import validate
    from parity.temporal_policy import POLICY, commands_for_day

    previous, target = options.previous.resolve(), options.destination.resolve()
    source = verify_sources(previous)
    # The child exits BEFORE loading inputs or entering the unchanged engine.
    # This preserves every guard without retaining its allocator high-water mark.
    verification = predecessor_process(previous)
    if sha(options.artifact) != options.sha256:
        raise ValueError('Frozen artifact bytes changed')
    artifact = json.loads(options.artifact.read_text())
    validate(artifact)
    case = artifact['case']
    original = json.loads((previous/'execution.json').read_text())
    index = sequence(original, case, options.sha256)
    if index != options.day or index >= len(case['days']):
        raise ValueError('Worker must execute exactly the next frozen day')
    profile, day, policy_case = select_day_inputs(case, index)
    del artifact, case
    gc.collect()
    prior = original['days'][-1]
    parent = CalculationRun.objects.get(pk=prior['run_id'])
    expected_revision = prior.get('execution_revision', original['revision'])
    if (parent.execution_revision != expected_revision or parent.output_digest != prior['output_digest']
            or parent.input_digest != prior['input_digest'] or parent.business_date.isoformat() != prior['date']):
        raise ValueError('Committed predecessor identity differs')
    if verification['predecessor_id'] != str(parent.pk):
        raise ValueError('Verified predecessor identity differs')
    before = resources()
    target.mkdir(parents=True, exist_ok=False)
    # Reference immutable accepted archives; copy only the exact action receipts
    # required by the existing comparator's fixed filename interface.
    record = deepcopy(original)
    for entry in record['days']:
        entry['output_archive'] = os.path.relpath(previous/entry['output_archive'], target)
        name = 'actions-%03d.json.gz' % entry['day_index']
        shutil.copyfile(previous/name, target/name)
        if sha(previous/name) != sha(target/name):
            raise ValueError('Retained action receipt copy differs')
    source['one_day_worker'] = dict(path='tools/temporal_worker.py', sha256=sha(__file__))
    (target/'source.json').write_text(json.dumps(source, indent=2), encoding='utf-8')
    shutil.copyfile(__file__, target/'worker-source.py')
    if sha(target/'worker-source.py') != source['one_day_worker']['sha256']:
        raise ValueError('Worker source archive differs')
    record['continuation'] = dict(path=str(previous/'execution.json'), sha256=sha(previous/'execution.json'))
    entry = dict(day_index=index, date=day['business_date'], status='RUNNING',
                 input_sha256=options.sha256, execution_revision=options.attempt_revision,
                 predecessor_verification=verification)
    started = time.monotonic()
    try:
        run = execute_day(day=day, profile=profile, execution_revision=options.attempt_revision,
                          predecessor=parent, report_exceptions=original['report_exceptions'])
        manifest = export_run(run, target/('day-%03d' % index))
        archive = OutputArchive(manifest)
        output = read_outputs(run)
        entry.update(status='COMPUTED_NOT_YET_PARITY', run_id=str(run.pk),
            predecessor_id=str(run.predecessor_id), input_digest=run.input_digest,
            output_digest=run.output_digest, closing_digest=digest(output['ClosingState']),
            output_archive=str(manifest.relative_to(target)),
            boundaries=[row['boundary'] for row in archive.iter_rows('MajorBoundaries')],
            suggestions=len(output['DBMFinal'][0]['Suggestions']), commands=[])
        commands = commands_for_day(policy_case, index, output['DBMFinal'][0]['Suggestions'])
        del output
        for position, command in enumerate(commands):
            event = record_command(run, operation=command['operation'], selected=command['selected'],
                timestamp=command['timestamp'], actor='retained-synthetic-trial',
                idempotency_key=POLICY+'-command-'+str(position))
            entry['commands'].append(dict(id=event.pk, command=command, digest=event.digest,
                                          before=event.before_digest, after=event.after_digest))
        state, events = command_state(run, read_outputs(run)['DBMFinal'][0])
        with gzip.open(target/('actions-%03d.json.gz' % index), 'wt', encoding='utf-8', compresslevel=1) as stream:
            json.dump(dict(state=state, events=events), stream, sort_keys=True, separators=(',', ':'))
        entry['post_action_state_digest'] = digest(state)
        entry['resources'] = dict(before=before, after=resources())
    except Exception as error:
        entry.update(status='FAILED', error_type=type(error).__name__, error=str(error))
        raise
    finally:
        entry['seconds'] = round(time.monotonic()-started, 3)
        record['days'].append(entry)
        (target/'execution.json').write_text(json.dumps(record, indent=2), encoding='utf-8')
        print(json.dumps({k:entry.get(k) for k in ('day_index','date','status','run_id','seconds','error')}), flush=True)


def attach(options):
    """Metadata linkage only, with the original contract/qualification verifier.

The old command assumes a single attempt revision. This continuation retains
that trial identity and records explicit per-day revisions for new attempts.
No comparison is executed, altered, inferred or waived here.
"""
    from django.db import transaction
    from mta.runtime.models import CalculationRun
    from mta.runtime.services import read_outputs
    from mta.runtime.temporal import BOUNDARIES
    from mta.runtime.management.commands.record_parity import CONTRACTS
    from parity.replay_temporal import independent_contracts_pass
    from parity.temporal_policy import POLICY

    verify_sources(options.modern.parent)
    modern = json.loads(options.modern.read_text())
    replay = json.loads(options.replay.read_text())
    if (replay['modern_execution_sha256'] != sha(options.modern)
            or replay['input_sha256'] != modern['artifact_sha256']
            or replay['action_policy'] != modern['action_policy'] or modern['action_policy'] != POLICY):
        raise ValueError('Comparison/input/action identity differs')
    expected = list(CONTRACTS)+['own-action-selection','post-action-state']
    qualified = any(day['status']=='PASS_WITH_LEGACY_FLAWS' for day in replay['days'])
    aggregate = 'COMPLETE_WITH_LEGACY_FLAWS' if qualified else 'PASS'
    if (not replay['days'] or len(replay['days']) != replay['requested_days']
            or len(replay['days']) > len(modern['days']) or replay['status'] != aggregate):
        raise ValueError('Comparison span/aggregate differs')
    root = Path(os.environ['VF_EVIDENCE_ROOT']).resolve().parent
    if not options.replay.resolve().is_relative_to(root) or not options.modern.resolve().is_relative_to(root):
        raise ValueError('Receipt outside owned evidence root')
    with transaction.atomic():
        for index, entry in enumerate(replay['days']):
            current = modern['days'][index]
            checks = entry['comparisons']
            status = 'PASS_WITH_LEGACY_FLAWS' if any(c['status']=='LEGACY_FLAW' for c in checks) else 'PASS'
            if (entry['day_index'] != index or current['day_index'] != index
                    or [c['contract'] for c in checks] != expected or not independent_contracts_pass(checks)
                    or entry['status'] != status):
                raise ValueError('Incomplete or misqualified comparison roster')
            run = CalculationRun.objects.select_for_update().get(pk=current['run_id'])
            if (str(run.pk) != entry['modern_run'] or run.output_digest != entry['modern_output_digest']
                    or run.output_digest != current['output_digest'] or run.input_digest != current['input_digest']
                    or run.business_date.isoformat() != entry['date']
                    or run.execution_revision != current.get('execution_revision', modern['revision'])):
                raise ValueError('Compared run/attempt identity differs')
            read_outputs(run)
            run.parity_summary = dict(receipt=str(options.replay.resolve().relative_to(root)),
                sha256=sha(options.replay), day_index=index, artifact_sha256=replay['input_sha256'],
                status=status, boundaries=list(BOUNDARIES), comparisons={c['contract']:c['status'] for c in checks},
                legacy_flaw_is_parity=False)
            run.save(update_fields=['parity_summary'])
    print('Recorded %s qualified run summaries; no populations imported.' % len(replay['days']))


if __name__ == '__main__':
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
    import django
    django.setup()
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    one = commands.add_parser('one')
    for name in ('artifact','previous','destination'):
        one.add_argument('--'+name, type=Path, required=True)
    one.add_argument('--sha256', required=True)
    one.add_argument('--day', type=int, required=True)
    one.add_argument('--attempt-revision', required=True)
    link = commands.add_parser('attach')
    link.add_argument('--modern', type=Path, required=True)
    link.add_argument('--replay', type=Path, required=True)
    verify = commands.add_parser('verify-predecessor')
    verify.add_argument('--previous', type=Path, required=True)
    options = parser.parse_args()
    {'one': run_one, 'attach': attach, 'verify-predecessor': verify_predecessor}[options.command](options)
