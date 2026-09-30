"""Recheck complete retained captures after comparator-only guard changes.

This reads captured SQL outputs; it does not claim a new SQL execution and does
not make an old run resumable under changed adapter semantics.
"""
import argparse
import json
from pathlib import Path

from mta.serialization import digest
from parity.replay_temporal import compare_day, load_gzip, sha, source_files
from parity.temporal_contract import validate_state
from parity.temporal import differences


def captured(directory, index):
    path=directory/f'legacy-{index:03d}.json.gz'
    if path.exists():return path
    receipt=json.loads((directory/'replay.json').read_text())
    parent=receipt.get('prefix_receipt')
    if parent is None or sha(Path(parent['path']))!=parent['sha256']:
        raise ValueError('Missing capture or prefix receipt changed')
    return captured(Path(parent['path']).parent,index)


def recompare(replay, modern_execution, destination, as_prefix=False):
    from parity.adapters.legacy.temporal_delivery import prepare
    prepare()  # canonical source/metadata pins, read-only
    prior=json.loads((replay/'replay.json').read_text())
    modern=json.loads((modern_execution/'execution.json').read_text())
    if prior['status'] not in ('PASS','DIVERGENCE') or prior['input_sha256']!=modern['artifact_sha256']:
        raise ValueError('Original captured receipt is not a matched input')
    before=json.loads((replay/'source.json').read_text())['files']
    current_sources=source_files()
    for path,value in before.items():
        if path.startswith('parity/adapters/legacy/') or path=='parity/legacy_isolation.py':
            if current_sources.get(path.replace('\\','/'))!=value:
                raise ValueError('Canonical capture adapter changed; cannot refresh its prefix: '+path)
    automatic=modern.get('action_policy','retained-fixed-actions')!='retained-fixed-actions'
    result=dict(status='PASS',kind='RECOMPARE_CAPTURED_SQL_NOT_NEW_EXECUTION',
                input_sha256=prior['input_sha256'],original_receipt_sha256=sha(replay/'replay.json'),
                prefix_receipt=dict(path=str(replay/'replay.json'),sha256=sha(replay/'replay.json')),
                sources=current_sources,action_policy=modern.get('action_policy','retained-fixed-actions'),
                requested_days=len(prior['days']),artifact_days=prior['artifact_days'],days=[])
    for entry in prior['days']:
        index=entry['day_index']
        path=captured(replay,index)
        legacy=load_gzip(path)
        actual=load_gzip(modern_execution/f'day-{index:03d}.json.gz')
        if digest(legacy['closing'])!=entry['closing_digest'] or digest(actual)!=entry['modern_output_digest']:
            raise ValueError('Captured state differs from original receipt')
        if entry['modern_output_digest']!=modern['days'][index]['output_digest']:
            raise ValueError('Modern execution lineage differs')
        validate_state(legacy['closing']);validate_state(actual['ClosingState'][0])
        checks=compare_day(legacy,actual)
        if automatic:
            post=load_gzip(modern_execution/f'actions-{index:03d}.json.gz')['state']
            if digest(post)!=modern['days'][index]['post_action_state_digest']:
                raise ValueError('Captured post-action state differs')
            for name,left,right in (
                ('own-action-selection',legacy['post_commands'],[r['command'] for r in modern['days'][index]['commands']]),
                ('post-action-state',legacy['post_command_state'],post)):
                delta=differences(left,right,'/'+name)
                checks.append(dict(contract=name,status='FAIL' if delta else 'PASS',differences=delta))
        passed=len(checks)==(31 if automatic else 29) and all(r['status']=='PASS' for r in checks)
        result['days'].append({**entry,'status':'PASS' if passed else 'FAIL',
            'original_status':entry['status'],'legacy_capture_path':str(path),
            'legacy_closing_path':str(path.parent/f'legacy-closing-{index:03d}.json.gz'),
            'legacy_capture_sha256':sha(path),'comparisons':checks})
        if not passed:
            result['status']='FAIL'
            break
    destination.parent.mkdir(parents=True,exist_ok=True)
    with destination.open('x',encoding='utf-8') as stream:json.dump(result,stream,indent=2)
    if as_prefix:
        if destination.name!='replay.json' or result['status']!='PASS':
            raise ValueError('A refreshed continuation prefix requires complete passing captures')
        with (destination.parent/'source.json').open('x',encoding='utf-8') as stream:
            json.dump(dict(files=current_sources,kind='validated-capture-recomparison'),stream,indent=2)
    print(json.dumps(dict(status=result['status'],days=len(result['days']),
        comparisons=sum(len(d['comparisons']) for d in result['days']))))
    return result['status']=='PASS'


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    for name in ('replay','modern-execution','destination'):
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--as-prefix',action='store_true')
    raise SystemExit(0 if recompare(**vars(parser.parse_args())) else 1)
