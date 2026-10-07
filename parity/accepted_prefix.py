"""Receipt-only prefix verification before one fresh next-day comparison."""
import hashlib
import json
from pathlib import Path
from mta.runtime.receipt_integrity import BOUNDARIES

CONTRACTS = (*BOUNDARIES, *('calculation/'+name for name in (
    'pick_remaining','additional_master','stock','routes','order_bpp','advance_stock',
    'git_advance','requirements','bands','pso_ration','normal_ration','bifurcation',
    'supplier_bor','bor_oa','logistic_pick')),
    'master/dbm_master','master/norm_change_export','master/importer_master',
    'master/norm_change_export_remaining','master/bpr_master','emitted-reports')


def read_bound(item):
    raw = Path(item['path']).read_bytes()
    if hashlib.sha256(raw).hexdigest() != item['sha256']:
        raise ValueError('Accepted prefix receipt digest differs')
    return json.loads(raw)


def normalized(execution):
    return [{**day, 'execution_revision':day.get('execution_revision',execution['revision'])}
            for day in execution['days']]


def verify_prefix(descriptors, modern, lineage, *, require_next=True):
    from parity.replay_temporal import independent_contracts_pass
    if len(descriptors) != len(lineage)-int(require_next) or len(modern['days']) != len(lineage):
        raise ValueError('Comparison must target exactly the next unaccepted day')
    expected = [*CONTRACTS, 'own-action-selection', 'post-action-state']
    result = []
    for index, item in enumerate(descriptors):
        if item.get('day_index') != index:
            raise ValueError('Accepted prefix has a gap or duplicate')
        accepted, replay, rrr, execution = [read_bound(item[k]) for k in
                                           ('accepted','replay','rrr','execution')]
        path, capture = lineage[index]
        if (accepted.get('status') != 'PASS'
                or accepted.get('replay_sha256') != item['replay']['sha256']
                or accepted.get('rrr_sha256') != item['rrr']['sha256']
                or Path(accepted['modern']).resolve() != Path(item['execution']['path']).resolve().parent
                or Path(accepted['legacy']).resolve() != path.parent
                or replay.get('modern_execution_sha256') != item['execution']['sha256']
                or replay.get('input_sha256') != modern['artifact_sha256']
                or replay.get('action_policy') != modern['action_policy']
                or replay.get('status') not in ('PASS','COMPLETE_WITH_LEGACY_FLAWS')
                or replay.get('requested_days') != index+1
                or len(replay.get('days',[])) != index+1
                or execution.get('artifact_sha256') != modern['artifact_sha256']
                or execution.get('action_policy') != modern['action_policy']
                or normalized(execution) != normalized(modern)[:index+1]):
            raise ValueError('Accepted prefix counterpart/input identity differs')
        entry = replay['days'][index]
        day = modern['days'][index]
        checks = entry.get('comparisons',[])
        qualification = 'PASS_WITH_LEGACY_FLAWS' if any(c.get('status')=='LEGACY_FLAW' for c in checks) else 'PASS'
        if (entry.get('day_index') != index or entry.get('date') != day['date']
                or entry.get('status') != qualification
                or entry.get('modern_run') != day['run_id']
                or entry.get('modern_output_digest') != day['output_digest']
                or entry.get('capture_receipt') != dict(path=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest())
                or entry.get('closing_digest') != capture['closing_digest']
                or entry.get('post_action_state_digest') != capture['post_action_state_digest']
                or [c.get('contract') for c in checks] != expected
                or not independent_contracts_pass(checks)
                or rrr.get('status') != 'PASS' or rrr.get('run_id') != day['run_id']
                or rrr.get('output_digest') != day['output_digest']):
            raise ValueError('Accepted prefix contracts/source proof differ')
        if replay['days'][:index] != result:
            raise ValueError('Accepted prefix history drift')
        result.append(entry)
    return result
