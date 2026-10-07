"""Ordered selected DBM recommendation rules."""
from copy import deepcopy
from mta.domain.ordinal_lookup import indexed_state, matching
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_CEILING


def spike_recommendation(today, state):
    """Rule6 counts historical joins plus today's spike memberships."""
    today = date.fromisoformat(today) if isinstance(today, str) else today
    runs = state['LastBatchRunTbl']
    if len(runs) != 1:
        raise ValueError('Rule6 requires one LastBatchRun row')
    last = runs[0]['LastRunDate']
    last = datetime.fromisoformat(last) if isinstance(last, str) else last
    if last.date() != today or last.time() != datetime.min.time():
        raise ValueError('LastBatchRun must equal business date at midnight')
    settings = {}
    for parameter in ('SpikeRuleHorizon','SpikeRuleParCount'):
        values = [r['Value'] for r in state['DBMSettingsTbl'] if r['Parameter'] == parameter]
        if len(values) != 1:
            raise ValueError('BASELINE_UNVERIFIED: Rule6 needs one selected setting ' + parameter)
        settings[parameter] = int(values[0])
    key = lambda row: (row['SKUCode'],row['WhCode'])
    as_day = lambda value: date.fromisoformat(value) if isinstance(value,str) else value
    result = deepcopy(state)
    suggestions = [r for r in result['Suggestions'] if r['Type'] < 6]
    excluded = {key(r) for r in suggestions} | {key(r) for r in state['SuspendConsumptionType'] if r['RedEnabled'] == 0}
    masters = [r for r in state['DBMMaster'] if key(r) not in excluded]
    eligible = {key(r) for r in masters}
    counts = {}
    lower = today - timedelta(days=settings['SpikeRuleHorizon'])
    for row in state['SpikeReport']:
        day = as_day(row['SuspendFromDate'])
        if key(row) not in eligible or day <= lower or day == today:
            continue
        for member in state['SuspendConsumptionType']:
            resume = as_day(member['RedResumeDate'])
            if key(member) == key(row) and resume is not None and day >= resume:
                counts[key(row)] = counts.get(key(row),0) + 1
    for row in state['SuspendSpikeTbl']:
        if key(row) in eligible and as_day(row['WaitStartDate']) == today:
            counts[key(row)] = counts.get(key(row),0) + 1
    for master in masters:
        if key(master) not in counts or counts[key(master)] < settings['SpikeRuleParCount']:
            continue
        norm = int((Decimal('1.333333') * master['Norm']).to_integral_value(rounding=ROUND_CEILING))
        if not -(2**31) <= norm < 2**31:
            raise OverflowError('Canonical Suggestions.NewNorm int overflow')
        suggestions.append(dict(SKUCode=master['SKUCode'],WhCode=master['WhCode'],Type=6,NewNorm=norm))
    result['Suggestions'] = suggestions
    result['IntermediateTables'] = [{'table':r['table'],'rows':[]} for r in state['IntermediateTables']]
    return result


def stockout_rules_one_six(today, state):
    return spike_recommendation(today, stockout_rules_one_five(today, state))


@indexed_state('DailyConsumption', 'SuspendStockType')
def too_much_in_green(today, state):
    """Rule5 preserves unbounded future rows, nongreen resets and group joins."""
    today = date.fromisoformat(today) if isinstance(today, str) else today
    runs = state['LastBatchRunTbl']
    if len(runs) != 1:
        raise ValueError('Rule5 requires one LastBatchRun row')
    last = runs[0]['LastRunDate']
    last = datetime.fromisoformat(last) if isinstance(last, str) else last
    if last.date() != today or last.time() != datetime.min.time():
        raise ValueError('LastBatchRun must equal business date at midnight')
    key = lambda row: (row['SKUCode'], row['WhCode'])
    result = deepcopy(state)
    suggestions = [r for r in result['Suggestions'] if r['Type'] < 5]
    excluded = {key(r) for r in suggestions} | {key(r) for r in state['SuspendStockType'] if r['GreenEnabled'] == 0}
    groups = {}
    for master in state['DBMMaster']:
        if key(master) in excluded:
            continue
        start = today - timedelta(days=2 * master['GCP'])
        for fact in matching(state, 'DailyConsumption', key(master)):
            if key(fact) != key(master):
                continue
            day = fact['ReportDate']
            day = date.fromisoformat(day) if isinstance(day, str) else day
            for member in matching(state, 'SuspendStockType', key(master)):
                resume = member['GreenResumeDate']
                resume = date.fromisoformat(resume) if isinstance(resume, str) else resume
                if key(member) != key(master) or resume is None or day <= start or day < resume:
                    continue
                green = (fact['Stock'] is not None
                         and Decimal(fact['Stock']) > (Decimal(2) * master['Norm'] / 3).quantize(Decimal('.000001'))
                         and fact['Stock'] <= master['Norm'] + fact['BlueZone'])
                groups.setdefault(key(master), []).append((day,master['GCP'],green,start))
    for entity, rows in groups.items():
        nongreen = [r[0] for r in rows if not r[2]]
        reset = max(nongreen) if nongreen else None
        counts = {}
        for day,gcp,green,start in rows:
            if day > (reset if reset is not None else start):
                counts[gcp] = counts.get(gcp,0) + 1
        for gcp,count in counts.items():
            if count < gcp:
                continue
            for master in state['DBMMaster']:
                if key(master) != entity:
                    continue
                new_norm = int((Decimal('0.666666') * master['Norm']).to_integral_value(rounding=ROUND_CEILING))
                if not -(2**31) <= new_norm < 2**31:
                    raise OverflowError('Canonical Suggestions.NewNorm int overflow')
                suggestions.append(dict(SKUCode=entity[0],WhCode=entity[1],Type=5,NewNorm=new_norm))
    result['Suggestions'] = suggestions
    result['IntermediateTables'] = [{'table':r['table'],'rows':[]} for r in state['IntermediateTables']]
    return result


def stockout_rules_one_five(today, state):
    """Fixed Rules1-5 sequence, each consuming its own preceding output."""
    return too_much_in_green(today, stockout_rules_one_four(today, state))


@indexed_state('DailyConsumption', 'SuspendStockType')
def too_much_in_red(today, state):
    """Rule4 counts red observations exactly equal to maximum RCP after earlier winners."""
    today = date.fromisoformat(today) if isinstance(today, str) else today
    runs = state['LastBatchRunTbl']
    if len(runs) != 1:
        raise ValueError('Rule4 requires one LastBatchRun row')
    last = runs[0]['LastRunDate']
    last = datetime.fromisoformat(last) if isinstance(last, str) else last
    if last.date() != today or last.time() != datetime.min.time():
        raise ValueError('LastBatchRun must equal business date at midnight')
    key = lambda row: (row['SKUCode'], row['WhCode'])
    result = deepcopy(state)
    suggestions = [r for r in result['Suggestions'] if r['Type'] < 4]
    excluded = {key(r) for r in suggestions} | {key(r) for r in state['SuspendStockType'] if r['RedEnabled'] == 0}
    groups = {}
    for master in state['DBMMaster']:
        if key(master) in excluded:
            continue
        start = today - timedelta(days=master['RCP'] - 1)
        for fact in matching(state, 'DailyConsumption', key(master)):
            if key(fact) != key(master):
                continue
            day = fact['ReportDate']
            day = date.fromisoformat(day) if isinstance(day, str) else day
            for member in matching(state, 'SuspendStockType', key(master)):
                resume = member['RedResumeDate']
                resume = date.fromisoformat(resume) if isinstance(resume, str) else resume
                if key(member) == key(master) and resume is not None and start <= day <= today and resume <= day:
                    is_red = fact['Stock'] is not None and Decimal(fact['Stock']) <= (Decimal(master['Norm']) / 3).quantize(Decimal('.000001'))
                    groups.setdefault(key(master), []).append((master['Norm'],master['RCP'],int(is_red)))
    for (sku, location), rows in groups.items():
        if sum(r[2] for r in rows) != max(r[1] for r in rows):
            continue
        norm = max(r[0] for r in rows)
        new_norm = int((Decimal('1.333333') * norm).to_integral_value(rounding=ROUND_CEILING))
        if not -(2**31) <= new_norm < 2**31:
            raise OverflowError('Canonical Suggestions.NewNorm int overflow')
        suggestions.append(dict(SKUCode=sku, WhCode=location, Type=4, NewNorm=new_norm))
    result['Suggestions'] = suggestions
    result['IntermediateTables'] = [{'table': r['table'], 'rows': []} for r in state['IntermediateTables']]
    return result


def stockout_rules_one_four(today, state):
    """Fixed Rules1-4 order using independently computed preceding state."""
    return too_much_in_red(today, stockout_rules_one_three(today, state))


@indexed_state('DailyConsumption', 'SuspendStockType')
def stockout_type_b(today, state):
    """Rule3 groups qualifying zero-stock observations after earlier winners."""
    today = date.fromisoformat(today) if isinstance(today, str) else today
    runs = state['LastBatchRunTbl']
    if len(runs) != 1:
        raise ValueError('Rule3 requires one LastBatchRun row')
    last = runs[0]['LastRunDate']
    last = datetime.fromisoformat(last) if isinstance(last, str) else last
    if last.date() != today or last.time() != datetime.min.time():
        raise ValueError('LastBatchRun must equal business date at midnight')
    key = lambda row: (row['SKUCode'], row['WhCode'])
    result = deepcopy(state)
    suggestions = [r for r in result['Suggestions'] if r['Type'] < 3]
    excluded = {key(r) for r in suggestions} | {key(r) for r in state['SuspendStockType'] if r['RedEnabled'] == 0}
    norms = {}
    for master in state['DBMMaster']:
        if key(master) in excluded:
            continue
        start = today - timedelta(days=master['RCP'] - 1)
        for fact in matching(state, 'DailyConsumption', key(master)):
            if key(fact) != key(master) or fact['Stock'] != 0:
                continue
            day = fact['ReportDate']
            day = date.fromisoformat(day) if isinstance(day, str) else day
            for member in matching(state, 'SuspendStockType', key(master)):
                resume = member['RedResumeDate']
                resume = date.fromisoformat(resume) if isinstance(resume, str) else resume
                if key(member) == key(master) and resume is not None and start <= day <= today and resume <= day:
                    norms[key(master)] = max(norms.get(key(master), master['Norm']), master['Norm'])
    for (sku, location), norm in norms.items():
        new_norm = int((Decimal('1.333333') * norm).to_integral_value(rounding=ROUND_CEILING))
        if not -(2**31) <= new_norm < 2**31:
            raise OverflowError('Canonical Suggestions.NewNorm int overflow')
        suggestions.append(dict(SKUCode=sku, WhCode=location, Type=3, NewNorm=new_norm))
    result['Suggestions'] = suggestions
    result['IntermediateTables'] = [{'table': r['table'], 'rows': []} for r in state['IntermediateTables']]
    return result


def stockout_rules_one_three(today, state):
    """Fixed Rules1-3 order using independently computed preceding state."""
    return stockout_type_b(today, stockout_rules_one_two(today, state))


@indexed_state('DailyConsumption', 'SuspendStockType')
def virtual_stockout(today, state):
    """Rule2 uses integer per-row depletion and preserves earlier winners."""
    today = date.fromisoformat(today) if isinstance(today, str) else today
    runs = state['LastBatchRunTbl']
    if len(runs) != 1:
        raise ValueError('Rule2 requires one LastBatchRun row')
    last = runs[0]['LastRunDate']
    last = datetime.fromisoformat(last) if isinstance(last, str) else last
    if last.date() != today or last.time() != datetime.min.time():
        raise ValueError('LastBatchRun must equal business date at midnight')
    key = lambda row: (row['SKUCode'], row['WhCode'])
    result = deepcopy(state)
    suggestions = [r for r in result['Suggestions'] if r['Type'] < 2]
    excluded = {key(r) for r in suggestions} | {key(r) for r in state['SuspendStockType'] if r['RedEnabled'] == 0}
    groups = {}
    for master in state['DBMMaster']:
        if key(master) in excluded:
            continue
        start = today - timedelta(days=master['RCP'] - 1)
        for fact in matching(state, 'DailyConsumption', key(master)):
            if key(fact) != key(master) or fact['Stock'] is None:
                continue
            day = fact['ReportDate']
            day = date.fromisoformat(day) if isinstance(day, str) else day
            for member in matching(state, 'SuspendStockType', key(master)):
                resume = member['RedResumeDate']
                resume = date.fromisoformat(resume) if isinstance(resume, str) else resume
                if key(member) != key(master) or resume is None or not (start <= day <= today and resume <= day):
                    continue
                third = (Decimal(master['Norm']) / 3).quantize(Decimal('.000001'))
                depletion = 0 if fact['Stock'] <= 0 else int(max(third - fact['Stock'], 0))
                groups.setdefault(key(master), []).append((day, fact['Stock'], master['Norm'], depletion))
    for (sku, location), rows in groups.items():
        zeros = [r[0] for r in rows if r[1] == 0]
        reset = max(zeros) if zeros else date.min
        total = sum(r[3] for r in rows if r[0] >= reset)
        norm = max(r[2] for r in rows)
        if total >= (Decimal(norm) / 3).quantize(Decimal('.000001')):
            new_norm = int((Decimal('1.333333') * norm).to_integral_value(rounding=ROUND_CEILING))
            if not -(2**31) <= new_norm < 2**31:
                raise OverflowError('Canonical Suggestions.NewNorm int overflow')
            suggestions.append(dict(SKUCode=sku, WhCode=location, Type=2, NewNorm=new_norm))
    result['Suggestions'] = suggestions
    result['IntermediateTables'] = [{'table': r['table'], 'rows': []} for r in state['IntermediateTables']]
    return result


def stockout_rules_one_two(today, state):
    """Fixed canonical order; each rule consumes this engine's prior output."""
    return virtual_stockout(today, stockout_type_a(today, state))


def stockout_type_a(today, state):
    """Rule1 resets Suggestions before proposing current zero-stock increases."""
    today = date.fromisoformat(today) if isinstance(today, str) else today
    runs = state['LastBatchRunTbl']
    if len(runs) != 1:
        raise ValueError('Rule1 requires one LastBatchRun row')
    last = runs[0]['LastRunDate']
    last = datetime.fromisoformat(last) if isinstance(last, str) else last
    if last.date() != today or last.time() != datetime.min.time():
        raise ValueError('LastBatchRun must equal business date at midnight')
    key = lambda row: (row['SKUCode'], row['WhCode'])
    disabled = {key(r) for r in state['SuspendStockType'] if r['RedEnabled'] == 0}
    masters = [r for r in state['DBMMaster'] if key(r) not in disabled]
    result = deepcopy(state)
    suggestions = []
    for fact in state['DailyConsumption']:
        day = fact['ReportDate']
        day = date.fromisoformat(day) if isinstance(day, str) else day
        if day != today or fact['Stock'] != 0:
            continue
        for master in masters:
            if key(master) != key(fact):
                continue
            # SQL 1/3.0 has six fractional digits; exact rational 4/3 differs.
            norm = int((Decimal('1.333333') * master['Norm']).to_integral_value(rounding=ROUND_CEILING))
            if not -(2**31) <= norm < 2**31:
                raise OverflowError('Canonical Suggestions.NewNorm int overflow')
            suggestions.append({'SKUCode': fact['SKUCode'], 'WhCode': fact['WhCode'],
                                'Type': 1, 'NewNorm': norm})
    result['Suggestions'] = suggestions
    result['IntermediateTables'] = [{'table': r['table'], 'rows': []} for r in state['IntermediateTables']]
    return result
