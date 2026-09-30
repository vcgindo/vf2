"""R1-02/04 deployed seasonal collector/process/apply, not multi-day rollover."""
from copy import deepcopy
from datetime import date, timedelta
from decimal import Decimal, ROUND_CEILING
import json

from mta.application.r1_norm_updates import key

REQUEST_FIELDS = ('SKUCode','WhCode','StartDate','EndDate','TargetNorm',
                  'DeltaNormPercentage','UpperLowerCap','BuildupDuration','ActivateDBM','Approved')
SEASON_FIELDS = REQUEST_FIELDS[:7] + ('OrigNorm','NewNorm') + REQUEST_FIELDS[7:9] + (
    'Type','Status','Comment','LastProcessedOn')
STATE_FIELDS = {'season_requests': REQUEST_FIELDS, 'seasonality': SEASON_FIELDS,
                'log': ('SKUCode','WhCode','OldNorm','NewNorm','NormChangeDate','NormChangeReason')}


def validate_season_input(source, day):
    if not isinstance(source, dict) or set(source) != {'opening_date','season_requests','seasonality'}:
        raise ValueError('Invalid seasonal source contract')
    if date.fromisoformat(source['opening_date']) >= date.fromisoformat(day):
        raise ValueError('Seasonal opening must precede business date')
    for name, fields in (('season_requests', REQUEST_FIELDS), ('seasonality', SEASON_FIELDS)):
        if not isinstance(source[name], list):
            raise ValueError('Seasonal inputs must be source row lists')
        seen = set()
        for row in source[name]:
            if not isinstance(row, dict) or set(row) != set(fields):
                raise ValueError('Invalid seasonal fields: ' + name)
            if any(not isinstance(row[f], str) or not row[f].strip() for f in ('SKUCode','WhCode')):
                raise ValueError('Seasonal identity required')
            if key(row) in seen:
                raise ValueError('Ambiguous seasonal UPDATE grain; no invented winner')
            seen.add(key(row))
            for field, value in row.items():
                if value is None or field in ('SKUCode','WhCode','Comment'):
                    continue
                if field in ('StartDate','EndDate','LastProcessedOn'):
                    date.fromisoformat(value)
                elif type(value) is not int or not -2147483648 <= value <= 2147483647:
                    raise ValueError('Seasonal numeric source must be SQL integer or null')
            if row['StartDate'] is None:
                raise ValueError('Seasonal start date required')
            if name == 'seasonality' and row['LastProcessedOn'] is not None and row['LastProcessedOn'] > source['opening_date']:
                raise ValueError('Current-day seasonal result cannot be seeded as opening')


def seasonal_checkpoint(state):
    return [dict(table=name, rows=sorted([{f:r[f] for f in fields} for r in state[name]],
                key=lambda r: json.dumps(r, sort_keys=True))) for name, fields in STATE_FIELDS.items()]


def _lt(a, b):
    return a is not None and b is not None and a < b


def collect_seasons(state, day):
    out = deepcopy(state)
    masters = {key(r):r for r in out['importer_master']}
    incoming = []
    for request in out['season_requests']:
        if request['Approved'] != 1:
            continue
        row = {f:request[f] for f in REQUEST_FIELDS if f != 'Approved'}
        row.update(OrigNorm=None, NewNorm=None, Type=1 if row['EndDate'] else 2,
                   Status=-1, Comment=None, LastProcessedOn=None)
        master = masters.get(key(row))
        if master is not None and (_lt(row['TargetNorm'], master['Norm']) or _lt(row['DeltaNormPercentage'], 0)):
            row['Type'] += 2
        incoming.append(row)
    replaced = {key(r) for r in incoming}
    out['seasonality'] = [r for r in out['seasonality'] if key(r) not in replaced] + incoming
    present = {key(r) for r in out['seasonality']}
    out['season_requests'] = [r for r in out['season_requests'] if key(r) not in present]
    phase_out, phase_in = ({key(r) for r in out[name]} for name in ('phase_out','phase_in'))
    for row in out['seasonality']:
        if row['Status'] == 21:
            row['Status'] = -1
        if row['Status'] in (7,22,23) or row['Status'] is None:
            continue
        master = masters.get(key(row))
        reasons = []
        if master and row['Type'] == 3 and _lt(row['BuildupDuration'], master['RLT']):
            reasons.append('Aborted as Buildup duration is less than RLT. Applicable for Lower Norm during Season type only')
        if master is None:
            reasons.append('Aborted as the item is not present in the master')
        if key(row) in phase_out:
            reasons.append('Aborted as the item is under Phase-out')
        if key(row) in phase_in:
            reasons.append('Aborted as the item is under Phase-in')
        if row['Type'] in (1,2) and _lt(row['TargetNorm'], row['OrigNorm']):
            reasons.append('Aborted as Target norm is less than Original norm')
        if row['Type'] in (3,4) and _lt(row['OrigNorm'], row['TargetNorm']):
            reasons.append('Aborted as Target norm is greater than Original norm')
        if reasons:
            row.update(Status=21, Comment=reasons[-1], LastProcessedOn=day)
    return out


def process_seasons(state, day):
    out = deepcopy(state)
    today = date.fromisoformat(day)
    masters = {key(r):r for r in out['importer_master']}
    fmt = lambda d: d.strftime('%Y.%m.%d')
    ceil = lambda n: int(n.to_integral_value(rounding=ROUND_CEILING))
    for row in out['seasonality']:
        master = masters.get(key(row))
        if master is None or row['Status'] in (7,21,22,23) or row['Status'] is None:
            continue
        start = date.fromisoformat(row['StartDate'])
        end = date.fromisoformat(row['EndDate']) if row['EndDate'] else None
        typ, build, rlt = row['Type'], row['BuildupDuration'], master['RLT']
        high = typ in (1,2)
        status = None
        if high and build is not None and today < start-timedelta(days=build): status = 1
        elif not high and today < start-timedelta(days=rlt): status = 1
        elif not high and today < start: status = 3
        elif high and today <= start-timedelta(days=rlt): status = 2
        elif today < start: status = 3
        elif typ in (2,4): status = 7
        elif typ == 1 and today <= max(end-timedelta(days=rlt), start): status = 4
        elif typ == 3 and build is not None and today <= end-timedelta(days=build): status = 4
        elif typ == 3 and today <= end-timedelta(days=rlt): status = 5
        elif end is not None and today < end: status = 6
        elif end is not None and today > end: status = 7
        # Canonical exact-EndDate hole: retain the existing row, not a repair.
        if status is None:
            continue
        row.update(Status=status, LastProcessedOn=day)
        if status > 1 and row['OrigNorm'] is None and row['TargetNorm'] is not None:
            row['OrigNorm'] = master['Norm']
        if status > 1 and row['TargetNorm'] is None:
            delta = row['DeltaNormPercentage']
            row['TargetNorm'] = None if delta is None else ceil(Decimal(master['Norm']) * (1+Decimal(delta)/100))
            row['OrigNorm'] = master['Norm']
            cap = row['UpperLowerCap']
            if cap is not None and row['TargetNorm'] is not None and (
                    high and row['TargetNorm'] > cap or not high and row['TargetNorm'] < cap):
                row['TargetNorm'] = cap
        original, target = row['OrigNorm'], row['TargetNorm']
        if (high and _lt(target,original)) or (not high and _lt(original,target)):
            row.update(Status=21, Comment='Aborted as Target norm is '+('less than' if high else 'greater than')+' Original norm')
            continue
        if status == 1:
            begins = start-timedelta(days=build if high else rlt)
            row['Comment'] = 'Seasonality logic will activate on '+fmt(begins)
        elif status in (2,5):
            if status == 2 and build is None:
                build = row['BuildupDuration'] = (start-today).days
            duration = max(build-rlt, 1)
            endpoint = start if status == 2 else end
            elapsed = build-(endpoint-today).days
            a,b = (original,target) if status == 2 else (target,original)
            row['NewNorm'] = None if a is None or b is None else a+ceil(Decimal(elapsed)*(b-a)/duration)
            row['Comment'] = None if b is None else ('Norm will be set to Target norm value (' if status == 2 else 'Norm will be reset to Original norm value (')+str(b)+') by '+fmt(endpoint-timedelta(days=rlt))
        elif status in (3,4):
            row['NewNorm'] = target
            if status == 3:
                row['Comment'] = 'Norm is set to Target Norm value. Season starts on '+fmt(start)
            else:
                reset = max(end-timedelta(days=rlt),start) if high else end-timedelta(days=build)
                row['Comment'] = None if original is None else 'Season in progress. Norm will be reset to Original norm value ('+str(original)+') on '+fmt(reset)
        elif status == 6:
            row.update(NewNorm=original, Comment='Norm is reset to original norm value. Season ends on '+fmt(end))
        elif status == 7:
            if typ in (1,3): row['NewNorm'] = original
            row['Comment'] = 'Seasonality over'
    return out


def apply_seasons(state, day):
    out = deepcopy(state)
    masters = {key(r):r for r in out['dbm_master']}
    changes = []
    for row in out['seasonality']:
        if row['Status'] is None or row['Status'] in (-1,21,22,23) or row['LastProcessedOn'] != day or row['NewNorm'] is None:
            continue
        master = masters.get(key(row))
        old = master['Norm'] if master else -1
        if row['NewNorm'] == old: continue
        if master: master['Norm'] = row['NewNorm']
        changes.append(dict(SKUCode=row['SKUCode'],WhCode=row['WhCode'],OldNorm=old,
                            NewNorm=row['NewNorm'],NormChangeDate=day,NormChangeReason=104))
    changed = {key(r) for r in changes}
    out['log'] = [r for r in out['log'] if not (key(r) in changed and r['NormChangeDate'] == day and r['NormChangeReason'] == 104)] + changes
    out['triggers'] = [r for r in out['triggers'] if key(r) not in changed] + [
        dict(SKUCode=r['SKUCode'],WhCode=r['WhCode'],NewNorm=r['NewNorm'],Reason=104) for r in changes]
    return out
