"""R1-02/04 accepted/forced update stages, after their upstream collectors.

Canonical UpdateAcceptedNorms, UpdateForceChangedNorms, UpdateNormChanges.
This stage consumes independently produced control tables, not replacement
current-day Norms. Full NormChangesRun collectors remain a separate obligation.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend
presentation and behavior. No frontend redesign, substitute screens, refactoring
or MTO changes. Any future exception requires explicit human authorization.
"""
from collections import Counter
from copy import deepcopy

from mta.application.history_removals import retain_norm_log


def key(row):
    return (row['SKUCode'].rstrip().casefold(), row['WhCode'].rstrip().casefold())


def import_forced_norms(state, *, from_ui, ignore_master_norm, nms_active):
    """Canonical ImportForceNormChange; run BEFORE accepted updates.

    Flags are the selected SQL COUNT(*) == 1 results, not inferred defaults.
    Raw master and approved requests are source facts, never expected Norms.
    """
    out = deepcopy(state)
    approved = [r for r in out['force_requests'] if r['Approved'] == 1]
    if from_ui and not approved:
        return out  # canonical early return retains the previous force table
    masters = {key(r): r for r in out['dbm_master']}
    if len(masters) != len(out['dbm_master']):
        raise ValueError('Ambiguous DBM master key')
    out['forced'] = []
    for request in approved:
        k = key(request)
        if k not in masters:
            continue
        raw = [r for r in out['raw_master'] if r['SKUCode'] is not None
               and r['WhCode'] is not None and key(r) == k]
        matches = [None] if ignore_master_norm or nms_active else [
            r for r in raw if r['Norm'] is not None and request['NewNorm'] is not None
            and r['Norm'] == request['NewNorm']]
        for _ in matches:
            out['forced'].append(dict(SKUCode=request['SKUCode'], WhCode=request['WhCode'],
                                      OldNorm=masters[k]['Norm'], NewNorm=request['NewNorm']))
    for k in {key(r) for r in out['forced']}:
        raw = [r for r in out['raw_master'] if r['SKUCode'] is not None
               and r['WhCode'] is not None and key(r) == k]
        if len(raw) > 1:
            raise ValueError('Legacy ambiguous raw-master MinNorm UPDATE; no invented winner')
        if raw:
            masters[k]['MinNorm'] = raw[0]['MinNorm']
    return out


def clear_force_requests(state, *, from_ui, ignore_master_norm, nms_active):
    """Canonical ClearForceNormChange, after export/failed-force reporting."""
    out = deepcopy(state)
    if not from_ui:
        out['force_requests'] = []
    elif any(r['Approved'] == 1 for r in out['force_requests']) and (
            out['raw_master'] or ignore_master_norm or nms_active):
        out['force_requests'] = [r for r in out['force_requests'] if r['Approved'] != 1
            and not any(key(r) == key(master) and r['NewNorm'] is not None
                        and master['Norm'] is not None and r['NewNorm'] == master['Norm']
                        for master in out['dbm_master'])]
    return out


def apply_norm_updates(state, day, *, norm_log_removals=None):
    out = deepcopy(state)
    masters = {key(r): r for r in out['dbm_master']}
    if len(masters) != len(out['dbm_master']):
        raise ValueError('Ambiguous DBM master key')
    suggestions = out['suggestions']
    phase_out = {key(r) for r in out['phase_out']}
    accepted = list(out['acceptance'])
    for row in out['accepted']:
        k = key(row)
        if k in masters:
            for suggestion in suggestions:
                if key(suggestion) == k:
                    accepted.append(dict(SKUCode=masters[k]['SKUCode'], WhCode=masters[k]['WhCode'],
                                         OldNorm=masters[k]['Norm'], NewNorm=suggestion['NewNorm'], AcceptanceDate=day))
    accepted = [r for r in accepted if key(r) not in phase_out]
    counts = Counter(key(r) for r in accepted)
    accepted = [r for r in accepted if counts[key(r)] == 1 and any(key(s) == key(r) for s in suggestions)]
    changes = []
    for row in accepted:
        for suggestion in suggestions:
            if key(row) == key(suggestion):
                for reason in out['reason_codes']:
                    if suggestion['Type'] == reason['Id']:
                        changes.append(dict({f: row[f] for f in ('SKUCode','WhCode','OldNorm','NewNorm')},
                                            NormChangeDate=day, NormChangeReason=reason['Id']))
    from mta.application.native_output_contracts import validate_produced_rows
    validate_produced_rows([{('WHCode' if name=='WhCode' else name):value for name,value in row.items()}
                   for row in changes], 'DBM/NormChangeLogTbl', stage='controls/accepted-log')
    changed = {key(r) for r in changes}
    out['log'] = retain_norm_log(out['log'], lambda r: key(r) in changed and r['NormChangeDate'] == day
        and r['NormChangeReason'] is not None and r['NormChangeReason'] < 100, norm_log_removals) + changes
    for row in accepted:
        if key(row) in masters:
            masters[key(row)]['Norm'] = row['NewNorm']
    out['triggers'] = [r for r in out['triggers'] if key(r) not in changed] + [
        dict(SKUCode=r['SKUCode'], WhCode=r['WhCode'], NewNorm=r['NewNorm'], Reason=r['NormChangeReason']) for r in changes]
    out['acceptance'] = accepted
    out['accepted_checkpoint'] = deepcopy(dict(master=out['dbm_master'], log=out['log'], triggers=out['triggers']))

    blocked = phase_out | {key(r) for r in out['phase_in']} | {
        key(r) for r in out['seasonality'] if r['Status'] in (2, 3, 4, 5, 6)}
    forced = [r for r in out['forced'] if key(r) in masters and key(r) not in blocked
              and not (r['OldNorm'] is not None and r['NewNorm'] is not None and r['OldNorm'] == r['NewNorm'])]
    counts = Counter(key(r) for r in forced)
    forced = [r for r in forced if counts[key(r)] == 1]
    forced_changes = [dict(r, NormChangeDate=day, NormChangeReason=101) for r in forced]
    validate_produced_rows([{('WHCode' if name=='WhCode' else name):value for name,value in row.items()}
                   for row in forced_changes], 'DBM/NormChangeLogTbl', stage='controls/forced-log')
    changed = {key(r) for r in forced}
    out['log'] = retain_norm_log(out['log'], lambda r: key(r) in changed
        and r['NormChangeDate'] == day and r['NormChangeReason'] == 101, norm_log_removals) + forced_changes
    for row in out['upload_log']:
        if key(row) in masters:
            row['OldNorm'] = masters[key(row)]['Norm']
    for row in forced:
        masters[key(row)]['Norm'] = row['NewNorm']
    out['triggers'] = [r for r in out['triggers'] if key(r) not in changed] + [
        dict(SKUCode=r['SKUCode'], WhCode=r['WhCode'], NewNorm=r['NewNorm'], Reason=101) for r in forced]
    out['forced'] = forced
    out['export'] = deepcopy(out['triggers'])
    by_key = {}
    for row in out['triggers']:
        if key(row) in by_key:
            raise ValueError('Legacy ambiguous Norm trigger UPDATE; no invented winner')
        by_key[key(row)] = row
    for row in out['importer_master']:
        if key(row) in by_key:
            row['Norm'] = by_key[key(row)]['NewNorm']
            if key(row) in masters:
                row['MinNorm'] = masters[key(row)]['MinNorm']
    out['triggers'] = []
    return out
