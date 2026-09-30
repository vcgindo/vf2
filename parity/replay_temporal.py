"""Fresh canonical SQL replay from its own retained closing state.

One isolated Fresh lease. No legacy output becomes modern input. Comparisons
stop at the first differing daily boundary/contract and preserve the receipt.
"""
from copy import deepcopy
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
import traceback

from mta.serialization import digest
from parity.current_day import compare as compare_calculations
from parity.legacy_isolation import exclusive_replay, MAPPING
from parity.temporal import BOUNDARIES, differences, fingerprint, legacy_states
from parity.temporal_contract import CONTRACT, roster_map, validate_state

ROOT=Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_gzip(path):
    with gzip.open(path,'rt',encoding='utf-8') as stream:return json.load(stream)


def dump_gzip(path,value):
    with gzip.open(path,'xt',encoding='utf-8',compresslevel=1) as stream:
        json.dump(value,stream,sort_keys=True,separators=(',',':'))


def compare_day(legacy,modern):
    """8 daily boundaries +20 current-day obligations + all emitted reports.

    The five master/control obligations are read at their actual producer
    boundary, not the redundant processed-input projection inside calculation.
    Their schema and timing remain those of the canonical R1 master contract.
    """
    comparisons=[]
    def exact(name,left,right):
        delta=differences(left,right,'/'+name)
        comparisons.append(dict(contract=name,status='FAIL' if delta else 'PASS',differences=delta))
        return not delta
    left=legacy_states(legacy)
    right={k:r['state'] for k,r in roster_map(modern['MajorBoundaries'],'boundary',BOUNDARIES,'Modern boundaries').items()}
    for name in BOUNDARIES:
        if not exact(name,left[name],right[name]):return comparisons
    # The adapter captures the15 native calculation outputs, including the
    # remaining Pick queue. The five state outputs have earlier control owners.
    outputs=roster_map(modern['CalculationOutputs'],'capability',CONTRACT['calculation_capabilities'],'Modern calculations')
    core=compare_calculations(legacy['output']['CalculationCheckpoints'],{k:r['rows'] for k,r in outputs.items()})
    if len(core)!=15:raise ValueError('Current-day calculation roster differs')
    for name,comparison in core.items():
        comparisons.append(dict(contract='calculation/'+name,**comparison))
        if comparison['status']!='PASS':return comparisons
    control_left={k:r['state'] for k,r in roster_map(legacy['output']['ControlStages'],'stage',CONTRACT['control_stages'],'Legacy controls').items()}
    control_right={k:r['state'] for k,r in roster_map(modern['ControlStages'],'stage',CONTRACT['control_stages'],'Modern controls').items()}
    for label,stage,table in (
        ('dbm_master','UpdateForceChangedNorms.sql','dbm_master'),
        ('norm_change_export','UpdateForceChangedNorms.sql','triggers'),
        ('importer_master','ClearForceNormChange.sql','importer_master'),
        ('norm_change_export_remaining','ClearForceNormChange.sql','triggers')):
        if not exact('master/'+label,control_left[stage][table],control_right[stage][table]):return comparisons
    if not exact('master/bpr_master',legacy['bpr_import']['BPRMaster'],modern['ClosingState'][0]['bpr']['BPRMaster']):return comparisons
    report_left=legacy['delivery']['reports']+[dict(stage='controls',tables=left['controls']['diagnostics'])]
    roster_map(report_left,'stage',CONTRACT['report_stages'],'Legacy reports')
    roster_map(modern['Reports'],'stage',CONTRACT['report_stages'],'Modern reports')
    # The stage sequence is ordered and unique (asserted above). Within each
    # report table use exact typed bags, as for every other SQL population.
    # Comparing the wrapper list would accidentally make nested rows ordered.
    exact('emitted-reports',{r['stage']:r['tables'] for r in report_left},
          {r['stage']:r['tables'] for r in modern['Reports']})
    return comparisons


def source_files():
    paths=[p for folder in ('parity','mta') for p in (ROOT/folder).rglob('*.py')]
    paths += [ROOT/'baseline/temporal-oracle-roster.json',ROOT/'baseline/temporal-oracle-reuse.json']
    return {str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in sorted(paths)}


def validate_continuation_sources(previous, current):
    # Include comparator/driver, typed encoders, static metadata and all imported
    # adapter dependencies. An older prefix must be re-compared if these differ.
    if previous != current:
        raise ValueError('Replay dependency changed after prefix proof; re-compare retained captures')


def replay(artifact, expected_sha, modern_execution, destination, through, continue_from=None, automatic_actions=False):
    from parity.adapters.legacy.temporal_day import execute_day
    destination.mkdir(parents=True,exist_ok=False)
    baseline=json.loads((ROOT/'baseline/manifest.json').read_text())
    registered={r['sha256'] for r in baseline['retained_resources']}
    if sha(artifact)!=expected_sha or expected_sha not in registered:
        raise ValueError('Use the unchanged registered temporal artifact')
    case=json.loads(artifact.read_text())['case']
    modern=json.loads((modern_execution/'execution.json').read_text())
    if modern['artifact_sha256']!=expected_sha:raise ValueError('Legacy/modern input identity differs')
    if automatic_actions:
        from parity.temporal_policy import POLICY, commands_for_day
        if modern.get('action_policy')!=POLICY:raise ValueError('Action trial policy differs')
    elif modern.get('action_policy','retained-fixed-actions')!='retained-fixed-actions':
        raise ValueError('Fixed replay cannot certify automatic actions')
    through=len(case['days'])-1 if through is None else through
    if not 0<=through<len(case['days']) or len(modern['days'])<=through:
        raise ValueError('Requested span lacks matching modern output')
    record=dict(status='RUNNING',input_sha256=expected_sha,modern_execution_sha256=sha(modern_execution/'execution.json'),
                requested_days=through+1,artifact_days=len(case['days']),databases=MAPPING,days=[],
                action_policy=POLICY if automatic_actions else 'retained-fixed-actions')
    sources=source_files()
    (destination/'source.json').write_text(json.dumps(dict(
        commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),files=sources),indent=2),encoding='utf-8')
    start=0;prior_path=None
    if continue_from is not None:
        previous=json.loads((continue_from/'replay.json').read_text())
        source_before=json.loads((continue_from/'source.json').read_text())['files']
        if previous['status']!='PASS' or previous['input_sha256']!=expected_sha or not previous['days']:
            raise ValueError('Continuation requires a passing same-input legacy prefix')
        validate_continuation_sources(source_before,sources)
        if previous.get('action_policy','retained-fixed-actions')!=record['action_policy']:
            raise ValueError('Continuation action policy differs')
        for index,entry in enumerate(previous['days']):
            if entry['day_index']!=index or entry['status']!='PASS' or len(entry['comparisons'])!=(31 if automatic_actions else 29):
                raise ValueError('Incomplete legacy prefix proof')
            if entry['modern_output_digest']!=modern['days'][index]['output_digest']:
                raise ValueError('Modern counterpart changed after prefix proof')
        record['days']=previous['days']
        start=len(record['days'])
        if start>through:raise ValueError('Continuation has no new days to execute')
        record['prefix_receipt']=dict(path=str(continue_from/'replay.json'),sha256=sha(continue_from/'replay.json'))
        prior_path=Path(previous['days'][-1].get('legacy_closing_path',
                       continue_from/f'legacy-closing-{start-1:03d}.json.gz'))
    with exclusive_replay():
        prior=deepcopy(case['opening']); opening_date=case['opening_date']
        for index in range(start,through+1):
            started=time.monotonic()
            day={**deepcopy(case['days'][index]),**deepcopy(case['static_day'])}
            commands=[c for c in case['commands'] if c['after_day']==index-1] if index else []
            entry=dict(day_index=index,date=day['business_date'],status='RUNNING',commands=commands)
            try:
                if index:
                    # Re-read only this oracle's persisted preceding close.
                    prior=load_gzip(prior_path or destination/f'legacy-closing-{index-1:03d}.json.gz')
                    if digest(prior)!=record['days'][-1]['closing_digest']:
                        raise ValueError('Legacy own-state closing drift')
                    opening_date=record['days'][-1]['date']
                    prior_path=None
                entry['opening_digest']=digest(prior)
                if automatic_actions:
                    commands=commands_for_day(case,index-1,prior['dbm']['Suggestions']) if index else []
                    entry['commands']=commands
                result=execute_day(prior,opening_date,day,case['profile'],None,commands=commands,
                    initial=index==0,post_policy=(lambda suggestions:commands_for_day(case,index,suggestions)) if automatic_actions else None)
                dump_gzip(destination/f'legacy-{index:03d}.json.gz',result)
                closing=result['closing']
                dump_gzip(destination/f'legacy-closing-{index:03d}.json.gz',closing)
                entry['legacy_capture_path']=str(destination/f'legacy-{index:03d}.json.gz')
                entry['legacy_closing_path']=str(destination/f'legacy-closing-{index:03d}.json.gz')
                current=modern['days'][index]
                if current['day_index']!=index or current['date']!=entry['date'] or current['status']!='COMPUTED_NOT_YET_PARITY':
                    raise ValueError('Modern date/status differs')
                actual=load_gzip(modern_execution/f'day-{index:03d}.json.gz')
                if digest(actual)!=current['output_digest']:raise ValueError('Modern export/readback digest differs')
                checks=compare_day(result,actual)
                if automatic_actions and all(c['status']=='PASS' for c in checks):
                    post=load_gzip(modern_execution/f'actions-{index:03d}.json.gz')['state']
                    if digest(post)!=current['post_action_state_digest']:
                        raise ValueError('Modern persisted action state digest differs')
                    for name,left,right in (
                        ('own-action-selection',result['post_commands'],[c['command'] for c in current['commands']]),
                        ('post-action-state',result['post_command_state'],post)):
                        delta=differences(left,right,'/'+name)
                        checks.append(dict(contract=name,status='FAIL' if delta else 'PASS',differences=delta))
                status='PASS' if all(c['status']=='PASS' for c in checks) else 'DIVERGENCE'
                entry.update(status=status,closing_digest=digest(closing),comparisons=checks,
                             scripts=result['scripts'],command_receipts=result['command_inputs'],
                             legacy_boundaries={k:fingerprint(v,'/'+k) for k,v in legacy_states(result).items()},
                             modern_run=current['run_id'],modern_output_digest=current['output_digest'])
                if automatic_actions:
                    entry.update(post_commands=result['post_commands'],
                                 post_command_receipts=result['post_command_receipts'],
                                 post_action_state_digest=digest(result['post_command_state']))
                prior=closing;opening_date=entry['date']
            except Exception:
                entry.update(status='HARNESS_FAILURE',error=traceback.format_exc())
            entry['seconds']=round(time.monotonic()-started,3)
            record['days'].append(entry)
            record['status']='PASS' if index==through and entry['status']=='PASS' else entry['status'] if entry['status']!='PASS' else 'RUNNING'
            (destination/'replay.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
            print(json.dumps({k:entry[k] for k in ('day_index','date','status','seconds')}|
                dict(passed=sum(c['status']=='PASS' for c in entry.get('comparisons',[])),
                     error=entry.get('error'),first_divergence=next((c['contract'] for c in entry.get('comparisons',[]) if c['status']!='PASS'),None))),flush=True)
            if entry['status']!='PASS':return False
    return True


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    for name in ('artifact','modern-execution','destination'):
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--expected-sha',required=True)
    parser.add_argument('--through',type=int)
    parser.add_argument('--continue-from',type=Path)
    parser.add_argument('--automatic-actions',action='store_true')
    options=parser.parse_args()
    os.environ['VFTEST_PROFILE']='fresh'
    raise SystemExit(0 if replay(**vars(options)) else 1)
