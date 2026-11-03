"""R1-02/04 CollectPhaseInData and ProcessPhaseIn, after phase-out."""
from collections import defaultdict, Counter
from copy import deepcopy
from math import floor
from decimal import Decimal, InvalidOperation
from mta.application.history_removals import retain_norm_log


def phase_start_percent(value):
    """Normalize configured decimal text to the selected SQL FLOAT operation."""
    if value is None:
        return None
    if type(value) not in (str, int, float):
        raise ValueError('Explicit phase percentage required')
    try:
        parsed = Decimal(str(value))
    except InvalidOperation as error:
        raise ValueError('Finite phase percentage required') from error
    if not parsed.is_finite() or not 0 <= parsed <= 100:
        raise ValueError('Phase percentage must be between 0 and 100')
    return float(parsed)
from mta.application.r1_norm_updates import key


def collect_phase_in(state, day, *, from_ui, start_percent):
    start_percent = phase_start_percent(start_percent)
    out = deepcopy(state)
    image = [r for r in out['phase_in_requests'] if not from_ui or r['Approved'] != 0]
    phase_keys = {key(r) for r in out['phase_in']}
    image_keys = {key(r) for r in image}
    out['phase_in_norms'] = [r for r in out['phase_in_norms'] if key(r) not in phase_keys | image_keys]
    out['phase_in_norms'].extend({f: r[f] for f in ('SKUCode', 'WhCode', 'TargetNorm')} for r in image)
    grouped = defaultdict(list)
    for row in out['phase_map']:
        if row['PhaseInSKUCode'] is not None:
            grouped[key(dict(SKUCode=row['PhaseInSKUCode'], WhCode=row['WhCode']))].append(row)
    out['phase_in'] = [r for r in out['phase_in'] if key(r) in grouped]
    existing = {key(r) for r in out['phase_in']}
    new_keys = set(grouped) - existing
    for k, rows in grouped.items():
        if k not in new_keys:
            continue
        original = sum(r['PhaseOutSKUOrigNorm'] for r in rows)
        targets = [r['TargetNorm'] for r in out['phase_in_norms'] if key(r) == k]
        if len(targets) > 1:
            raise ValueError('Canonical duplicate phase-in target UPDATE; no invented winner')
        target = targets[0] if targets else original
        if target is None:
            raise ValueError('Canonical PhaseInTbl rejects NULL TargetNorm')
        opening = [r for r in out['importer_master'] if key(r) == k] or [dict(Norm=None)]
        for master in opening:
            out['phase_in'].append(dict(SKUCode=rows[0]['PhaseInSKUCode'], WhCode=rows[0]['WhCode'],
                PhaseOutSKUOrigNorm=original, TargetNorm=target,
                OldNorm=master['Norm'] if master['Norm'] is not None else -1, NewNorm=0,
                PhaseInStartDate=day, LastProcessedDate=None))
    if any(n > 1 for n in Counter(key(r) for r in out['phase_in']).values()):
        raise ValueError('Canonical phase-in update has duplicate keys; no invented winner')
    for row in out['phase_in']:
        combined = 0
        for mapping in grouped[key(row)]:
            old_key = key(dict(SKUCode=mapping['PhaseOutSKUCode'], WhCode=mapping['WhCode']))
            phases = [p for p in out['phase_out'] if key(p) == old_key] or [dict(NewNorm=None)]
            masters = [m for m in out['dbm_master'] if key(m) == old_key] or [dict(Norm=None)]
            for phase in phases:
                for master in masters:
                    combined += (phase['NewNorm'] if phase['NewNorm'] is not None
                                 else master['Norm'] if master['Norm'] is not None else 0)
        candidate = max(row['TargetNorm'] - combined, 0)
        qualifies = start_percent is None or floor(row['PhaseOutSKUOrigNorm'] / 100.0 * (100 - start_percent)) >= combined
        # Preserve the source's AND-before-OR predicate; no inferred parentheses.
        if (key(row) not in new_keys and row['LastProcessedDate'] is None
                or row['LastProcessedDate'] is not None and row['LastProcessedDate'] < day):
            row['OldNorm'] = row['NewNorm']
        if qualifies:
            row['NewNorm'] = candidate
        row['LastProcessedDate'] = day
    return out


def process_phase_in(state, day, *, norm_log_removals=None):
    out = deepcopy(state)
    phases = out['phase_in']
    keys = {key(r) for r in phases}
    for master in out['dbm_master']:
        for row in phases:
            if key(master) == key(row):
                if row['NewNorm'] is not None:
                    master['Norm'] = row['NewNorm']
                    if row['TargetNorm'] <= row['NewNorm']:
                        master['SKUIntroDate'] = day
    out['log'] = retain_norm_log(out['log'], lambda r: key(r) in keys
        and r['NormChangeDate'] == day and r['NormChangeReason'] == 103, norm_log_removals)
    changed = [r for r in phases if r['OldNorm'] is not None and r['NewNorm'] is not None and r['OldNorm'] != r['NewNorm']]
    out['log'].extend(dict(SKUCode=r['SKUCode'], WhCode=r['WhCode'], OldNorm=r['OldNorm'],
                          NewNorm=r['NewNorm'], NormChangeDate=day, NormChangeReason=103) for r in changed)
    keys = {key(r) for r in changed}
    out['triggers'] = [r for r in out['triggers'] if key(r) not in keys] + [
        dict(SKUCode=r['SKUCode'], WhCode=r['WhCode'], NewNorm=r['NewNorm'], Reason=103) for r in changed]
    return out
