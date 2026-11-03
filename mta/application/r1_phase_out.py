"""R1-02/04 canonical CollectPhaseOutData -> ProcessPhaseOut state stages.

No tomorrow simulation, approval workflow or replacement calculation. Tables
are source facts/prior state; collection generates today's phase state itself.
"""
from collections import Counter
from copy import deepcopy
from mta.application.history_removals import retain_norm_log
from mta.application.r1_norm_updates import key


def collect_phase_out(state, day, timestamp, *, from_ui):
    out = deepcopy(state)
    masters = {key(r): r for r in out['dbm_master']}
    if len(masters) != len(out['dbm_master']):
        raise ValueError('Ambiguous DBM master key')
    phases = out['phase_out']
    mapping = out['phase_map']
    exceptions = []
    image = [r for r in out['phase_requests'] if not from_ui or r['Approved'] != 0]
    counts = Counter(key(r) for r in image)
    image = [r for r in image if counts[key(r)] == 1 and key(r) in masters
             and not any(key(p) == key(r) for p in phases)]

    def phase_in_key(row):
        return None if row['PhaseInSKUCode'] is None else key(dict(SKUCode=row['PhaseInSKUCode'], WhCode=row['WhCode']))

    def reject_conflicts(rows):
        allowed_names = ('Rejected', 'Finished', 'Stopped', 'Aborted', 'Not Started')
        allowed = []
        for name in allowed_names:
            values = [r['Id'] for r in out['season_status'] if r['Status'] == name]
            if len(values) > 1:
                raise ValueError('Canonical season-status scalar query has multiple rows')
            allowed.append(values[0] if values else None)
        for row in rows:
            own, replacement = key(row), phase_in_key(row)
            reasons = ['Phase-out cannot be done as Phase-in is in process'
                       for p in out['phase_in'] if key(p) == own]
            reasons += ['Phase-in cannot be done as Phase-out is in process'
                        for p in phases if replacement is not None and key(p) == replacement and p['PhaseOutFinished'] == 0]
            # SQL NOT IN is UNKNOWN when any status lookup is NULL.
            for target, label in ((own, 'Phase-out'), (replacement, 'Phase-in')):
                reasons += [label + ' cannot be done as Seasonality is in process'
                            for s in out['seasonality'] if target is not None and key(s) == target
                            and s['Status'] is not None and None not in allowed and s['Status'] not in allowed]
            targets = [p['TargetNorm'] for p in out['phase_in_norms']
                       if replacement is not None and key(p) == replacement] or [None]
            for reason in reasons:
                for norm in targets:
                    exceptions.append(dict(PhaseOutSKUCode=row['SKUCode'], WhCode=row['WhCode'],
                        PhaseInSKUCode=row['PhaseInSKUCode'], TargetNorm=norm, Reason=reason, Log_Date=timestamp))
        def rejected(row):
            return any(key(dict(SKUCode=e['PhaseOutSKUCode'], WhCode=e['WhCode'])) == key(row)
                       and (e['PhaseInSKUCode'] or '-') == (row['PhaseInSKUCode'] or '-') for e in exceptions)
        return [r for r in rows if not rejected(r)]

    image = reject_conflicts(image)
    stop = {key(r) for r in out['phase_stops']}
    phases[:] = [r for r in phases if key(r) in masters and key(r) not in stop]
    def map_key(row):
        return key(dict(SKUCode=row['PhaseOutSKUCode'], WhCode=row['WhCode']))
    mapping[:] = [r for r in mapping if map_key(r) not in stop]

    def new_phase(row):
        return dict(SKUCode=row['SKUCode'], WhCode=row['WhCode'], OldNorm=None,
                    NewNorm=masters[key(row)]['Norm'], PhaseOutFinished=0,
                    PhaseOutStartDate=day, LastProcessedDate=None, PhaseInSKUCode=row['PhaseInSKUCode'])
    phases.extend(new_phase(r) for r in image)

    def add_map(rows):
        existing = {map_key(r) for r in mapping}
        mapping.extend(dict(PhaseOutSKUCode=r['SKUCode'], WhCode=r['WhCode'],
                            PhaseInSKUCode=r['PhaseInSKUCode'], PhaseOutSKUOrigNorm=masters[key(r)]['Norm'])
                       for r in rows if key(r) not in existing and key(r) in masters)
    add_map(image)
    for row in phases:
        if row['LastProcessedDate'] == day:
            row['PhaseOutFinished'] = 0
    kept = {key(r) for r in phases if r['PhaseOutFinished'] != 1}
    mapping[:] = [r for r in mapping if map_key(r) in kept]
    phases[:] = [r for r in phases if r['PhaseOutFinished'] != 1]
    start = []
    for row in phases:
        daily = [r for r in out['daily'] if key(r) == key(row) and r['ReportDate'] == day]
        attrs = [r for r in out['attributes'] if key(r) == key(row)] or [dict(PackSize=None)]
        for d in daily:
            for a in attrs:
                if d['Stock'] is not None and d['GIT'] is not None and d['Stock'] + d['GIT'] < (a['PackSize'] if a['PackSize'] is not None else 1):
                    start.append(row)
    started = {key(r) for r in start}
    for row in phases:
        if key(row) in started:
            row['PhaseOutFinished'] = 1
    children = []
    for parent in start:
        for master in out['dbm_master']:
            if master['ParentWhCode'] is not None and key(dict(SKUCode=master['SKUCode'], WhCode=master['ParentWhCode'])) == key(parent):
                children.append(dict(new_phase(dict(master, PhaseInSKUCode=parent['PhaseInSKUCode'])), ParentWhCode=master['ParentWhCode']))
    child_keys = {key(r) for r in children}
    phases[:] = [r for r in phases if key(r) not in child_keys]
    children = reject_conflicts(children)
    out['phase_exceptions'].extend(exceptions)
    phases.extend({k: v for k, v in r.items() if k != 'ParentWhCode'} for r in children)
    image = []
    for child in children:
        if child['PhaseInSKUCode'] is None:
            image.append(child)
        else:
            for m in mapping:
                if m['PhaseInSKUCode'] == child['PhaseInSKUCode'] and m['WhCode'] == child['ParentWhCode']:
                    image.append(dict(SKUCode=m['PhaseOutSKUCode'], WhCode=child['WhCode'], PhaseInSKUCode=child['PhaseInSKUCode']))
    add_map(image)
    for row in phases:
        if row['LastProcessedDate'] is None or row['LastProcessedDate'] < day:
            row['OldNorm'] = masters[key(row)]['Norm']
        candidates = [d['Stock'] + d['GIT'] for d in out['daily'] if key(d) == key(row)
                      and d['ReportDate'] == day and d['Stock'] is not None and d['GIT'] is not None
                      and (row['NewNorm'] or 0) > d['Stock'] + d['GIT']]
        if len(set(candidates)) > 1:
            raise ValueError('Canonical duplicate daily UPDATE is ambiguous; no invented winner')
        if candidates:
            row['NewNorm'] = candidates[0]
        if key(row) in started:
            row['NewNorm'] = 0
        row['LastProcessedDate'] = day
    return out


def process_phase_out(state, day, *, norm_log_removals=None):
    out = deepcopy(state)
    phases = out['phase_out']
    counts = Counter(key(r) for r in phases)
    if any(n > 1 for n in counts.values()):
        raise ValueError('Canonical phase UPDATE has duplicate keys; no invented winner')
    for master in out['dbm_master']:
        for row in phases:
            if key(master) == key(row) and row['NewNorm'] is not None:
                master['Norm'] = row['NewNorm']
    out['log'] = retain_norm_log(out['log'], lambda r: key(r) in counts
        and r['NormChangeDate'] == day and r['NormChangeReason'] == 102, norm_log_removals)
    changed = [r for r in phases if r['OldNorm'] is not None and r['NewNorm'] is not None and r['OldNorm'] != r['NewNorm']]
    out['log'].extend(dict(SKUCode=r['SKUCode'], WhCode=r['WhCode'], OldNorm=r['OldNorm'],
                          NewNorm=r['NewNorm'], NormChangeDate=day, NormChangeReason=102) for r in changed)
    keys = {key(r) for r in changed}
    out['triggers'] = [r for r in out['triggers'] if key(r) not in keys] + [
        dict(SKUCode=r['SKUCode'], WhCode=r['WhCode'], NewNorm=r['NewNorm'], Reason=102) for r in changed]
    return out
