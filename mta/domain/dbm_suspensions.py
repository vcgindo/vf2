"""Ordered DBM suspension state; selected SQL semantics without rule dispatch."""
from copy import deepcopy
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_CEILING


def _key(row):
    return row['SKUCode'], row.get('WhCode', row.get('WHCode'))


def _flags(row, red=False, green=False):
    return {'SKUCode': row['SKUCode'], 'WhCode': _key(row)[1],
            'IsRedEnabled': red, 'IsGreenEnabled': green}


def suppress_insufficient_data(today, state):
    """DAG step26: preserve SQL joined-row counts and post-resume suppression."""
    today = date.fromisoformat(today) if isinstance(today, str) else today
    runs = state['LastBatchRunTbl']
    if len(runs) != 1:
        raise ValueError('Insufficient-data seam requires one LastBatchRun row')
    last = runs[0]['LastRunDate']
    last = datetime.fromisoformat(last) if isinstance(last, str) else last
    if last.date() != today or last.time() != datetime.min.time():
        raise ValueError('LastBatchRun must equal the run business date at midnight')
    result = deepcopy(state)
    sufficient = {}
    for period in ('RCP', 'GCP'):
        counts = {}
        for master in state['DBMMaster']:
            group = (_key(master), master[period])
            start = today - timedelta(days=2 * master[period] - 1)
            for fact in state['DailyConsumption']:
                report = fact['ReportDate']
                report = date.fromisoformat(report) if isinstance(report, str) else report
                if _key(master) == _key(fact) and start <= report <= today:
                    counts[group] = counts.get(group, 0) + 1
        sufficient[period] = {key for (key, length), count in counts.items() if count >= length}
    rows = []
    for master in state['DBMMaster']:
        red = _key(master) in sufficient['RCP']
        green = _key(master) in sufficient['GCP']
        if not (red and green):
            rows.append(_flags(master, red, green))
    result['SuspendInsuffDataPointsTbl'] = rows
    flags = {_key(r): r for r in rows}
    for table in ('SuspendStockType', 'SuspendConsumptionType'):
        for row in result[table]:
            suppression = flags.get(_key(row))
            if suppression:
                row['RedEnabled'] = row['RedEnabled'] == 1 and suppression['IsRedEnabled']
                row['GreenEnabled'] = row['GreenEnabled'] == 1 and suppression['IsGreenEnabled']
    return result


def finalize_order_suspensions(today, state):
    """DAG step25: PRE-driven release dates after common/order intersection."""
    today = date.fromisoformat(today) if isinstance(today, str) else today
    result = deepcopy(state)
    master_keys = {_key(r) for r in state['DBMMaster']}
    rows = [r for r in result['SuspendOrderType'] if _key(r) in master_keys]
    existing_keys = {_key(r) for r in rows}
    for row in rows:
        row['RedEnabled'] = row['GreenEnabled'] = True
    for master in state['DBMMaster']:
        if _key(master) not in existing_keys:
            rows.append({'SKUCode': master['SKUCode'], 'WhCode': master['WhCode'],
                         'RedEnabled': True, 'GreenEnabled': True,
                         'RedResumeDate': master['SKUIntroDate'],
                         'GreenResumeDate': master['SKUIntroDate'], 'SuggestionStartDate': None})
    for table in ('SuspendAggrCommonWithOrderType',):
        sources = {}
        for source in state[table]:
            sources.setdefault(_key(source), []).append(source)
        for row in rows:
            outcomes = {(row['RedEnabled'] and r['IsRedEnabled'] == 1,
                         row['GreenEnabled'] and r['IsGreenEnabled'] == 1)
                        for r in sources.get(_key(row), [])}
            if len(outcomes) > 1:
                raise ValueError('SOURCE_ORDER_AMBIGUITY: conflicting final order flags in ' + table)
            if outcomes:
                row['RedEnabled'], row['GreenEnabled'] = outcomes.pop()
        result[table] = [r for r in result[table]
                         if not (r['IsRedEnabled'] == 1 and r['IsGreenEnabled'] == 1)]
    for color in ('Red', 'Green'):
        disabled = {_key(r) for r in state['SuspendOrderTypePre'] if r['Is' + color + 'Enabled'] == 0}
        for row in rows:
            if _key(row) in disabled and row[color + 'Enabled']:
                row[color + 'ResumeDate'] = today.isoformat()
                row['SuggestionStartDate'] = None
    changed = {_key(r) for r in state['NormChangeLogTbl']
               if str(r['NormChangeDate']) == today.isoformat()}
    for row in rows:
        if _key(row) in changed:
            row['RedResumeDate'] = row['GreenResumeDate'] = today.isoformat()
            row['SuggestionStartDate'] = None
    result['IntermediateTables'] = [{'table':r['table'],'rows':[]} for r in state['IntermediateTables']]
    result['SuspendOrderType'] = rows
    return result


def finalize_consumption_suspensions(today, state):
    """DAG step24: PRE-driven release dates after common/consumption intersection."""
    today = date.fromisoformat(today) if isinstance(today, str) else today
    last_runs = state['LastBatchRunTbl']
    if len(last_runs) != 1:
        raise ValueError('Final consumption requires exactly one LastBatchRun date')
    last = last_runs[0]['LastRunDate']
    last = datetime.fromisoformat(last) if isinstance(last, str) else last
    if last.date() != today or last.time() != datetime.min.time():
        raise ValueError('LastBatchRun must equal the run business date at midnight')
    result = deepcopy(state)
    master_keys = {_key(r) for r in state['DBMMaster']}
    rows = [r for r in result['SuspendConsumptionType'] if _key(r) in master_keys]
    existing_keys = {_key(r) for r in rows}
    for row in rows:
        row['RedEnabled'] = row['GreenEnabled'] = True
    for master in state['DBMMaster']:
        if _key(master) not in existing_keys:
            rows.append({'SKUCode': master['SKUCode'], 'WhCode': master['WhCode'],
                         'RedEnabled': True, 'GreenEnabled': True,
                         'RedResumeDate': master['SKUIntroDate'],
                         'GreenResumeDate': master['SKUIntroDate']})
    for table in ('SuspendAggrCommon', 'SuspendAggrConsumptionType'):
        sources = {}
        for source in state[table]:
            sources.setdefault(_key(source), []).append(source)
        for row in rows:
            outcomes = {(row['RedEnabled'] and r['IsRedEnabled'] == 1,
                         row['GreenEnabled'] and r['IsGreenEnabled'] == 1)
                        for r in sources.get(_key(row), [])}
            if len(outcomes) > 1:
                raise ValueError('SOURCE_ORDER_AMBIGUITY: conflicting final consumption flags in ' + table)
            if outcomes:
                row['RedEnabled'], row['GreenEnabled'] = outcomes.pop()
        result[table] = [r for r in result[table]
                         if not (r['IsRedEnabled'] == 1 and r['IsGreenEnabled'] == 1)]
    for color in ('Red', 'Green'):
        disabled = {_key(r) for r in state['SuspendConsumptionTypePre'] if r['Is' + color + 'Enabled'] == 0}
        for row in rows:
            if _key(row) in disabled and row[color + 'Enabled']:
                row[color + 'ResumeDate'] = today.isoformat()
    result['SuspendConsumptionType'] = rows
    return result


def finalize_stock_suspensions(today, state):
    """DAG step23: PRE-driven release dates after common/stock intersection."""
    today = date.fromisoformat(today) if isinstance(today, str) else today
    last_runs = state['LastBatchRunTbl']
    if len(last_runs) != 1:
        raise ValueError('Final stock requires exactly one LastBatchRun date')
    last = last_runs[0]['LastRunDate']
    last = datetime.fromisoformat(last) if isinstance(last, str) else last
    if last.date() != today or last.time() != datetime.min.time():
        raise ValueError('LastBatchRun must equal the run business date at midnight')
    result = deepcopy(state)
    master_keys = {_key(r) for r in state['DBMMaster']}
    rows = [r for r in result['SuspendStockType'] if _key(r) in master_keys]
    existing_keys = {_key(r) for r in rows}
    for row in rows:
        row['RedEnabled'] = row['GreenEnabled'] = True
    for master in state['DBMMaster']:
        if _key(master) not in existing_keys:
            rows.append({'SKUCode': master['SKUCode'], 'WhCode': master['WhCode'],
                         'RedEnabled': True, 'GreenEnabled': True,
                         'RedResumeDate': master['SKUIntroDate'],
                         'GreenResumeDate': master['SKUIntroDate']})
    for table in ('SuspendAggrCommon', 'SuspendAggrStockType'):
        sources = {}
        for source in state[table]:
            sources.setdefault(_key(source), []).append(source)
        for row in rows:
            outcomes = {(row['RedEnabled'] and r['IsRedEnabled'] == 1,
                         row['GreenEnabled'] and r['IsGreenEnabled'] == 1)
                        for r in sources.get(_key(row), [])}
            if len(outcomes) > 1:
                raise ValueError('SOURCE_ORDER_AMBIGUITY: conflicting final stock flags in ' + table)
            if outcomes:
                row['RedEnabled'], row['GreenEnabled'] = outcomes.pop()
        result[table] = [r for r in result[table]
                         if not (r['IsRedEnabled'] == 1 and r['IsGreenEnabled'] == 1)]
    for color in ('Red', 'Green'):
        disabled = {_key(r) for r in state['SuspendStockTypePre'] if r['Is' + color + 'Enabled'] == 0}
        for row in rows:
            if _key(row) in disabled and row[color + 'Enabled']:
                row[color + 'ResumeDate'] = today.isoformat()
    result['SuspendStockType'] = rows
    return result


def aggregate_consumption_family(state):
    """DAG step22: intersect flags and clean released contributor memberships."""
    result=deepcopy(state)
    rows=[_flags(r,True,True) for r in state['DBMMaster']]
    for table in ('SuspendAcceptedNormsConsumptionType',):
        sources={}
        for source in result[table]:
            sources.setdefault(_key(source),[]).append(source)
        for row in rows:
            outcomes={(row['IsRedEnabled'] and r['IsRedEnabled']==1,
                       row['IsGreenEnabled'] and r['IsGreenEnabled']==1)
                      for r in sources.get(_key(row),[])}
            if len(outcomes)>1:
                raise ValueError('SOURCE_ORDER_AMBIGUITY: conflicting consumption aggregate outcomes in '+table)
            if outcomes:
                row['IsRedEnabled'],row['IsGreenEnabled']=outcomes.pop()
        result[table]=[r for r in result[table]
                       if not (r['IsRedEnabled']==1 and r['IsGreenEnabled']==1)]
    result['SuspendAggrConsumptionType']=[r for r in rows if not (r['IsRedEnabled'] and r['IsGreenEnabled'])]
    return result

def aggregate_stock_family(state):
    """DAG step21: intersect flags and clean released contributor memberships."""
    result=deepcopy(state)
    rows=[_flags(r,True,True) for r in state['DBMMaster']]
    for table in ('SuspendNewSKUTbl','SuspendSpikeTbl','SuspendSupplyIssueTbl',
                  'SuspendNormsForceChangedTbl','SuspendAcceptedNormsStockType'):
        red_only=table in ('SuspendSpikeTbl','SuspendSupplyIssueTbl')
        supply=table=='SuspendSupplyIssueTbl'
        sources={}
        for source in result[table]:
            sources.setdefault(_key(source),[]).append(source)
        for row in rows:
            outcomes={(row['IsRedEnabled'] and r['IsRedEnabled']==1,
                       row['IsGreenEnabled'] if red_only else row['IsGreenEnabled'] and r['IsGreenEnabled']==1)
                      for r in sources.get(_key(row),[])}
            if len(outcomes)>1:
                raise ValueError('SOURCE_ORDER_AMBIGUITY: conflicting stock aggregate outcomes in '+table)
            if outcomes:
                row['IsRedEnabled'],row['IsGreenEnabled']=outcomes.pop()
        result[table]=[r for r in result[table]
                       if not (r['IsRedEnabled']==1 and (supply or r['IsGreenEnabled']==1))]
    result['SuspendAggrStockType']=[r for r in rows if not (r['IsRedEnabled'] and r['IsGreenEnabled'])]
    return result

def aggregate_common(state):
    """DAG step20: intersect flags and clean released contributor memberships."""
    result=deepcopy(state)
    rows=[_flags(r,True,True) for r in state['DBMMaster']]
    for table in ('SuspendStepOneTbl','SuspendNormsInSleepModeTbl',
                  'SuspendExistingDisabledNormsTbl','SuspendPhaseInTbl',
                  'SuspendPhaseOutTbl','SuspendSeasonalityTbl','SuspendWhitesTbl'):
        white=table=='SuspendWhitesTbl'
        sources={}
        for source in result[table]:
            sources.setdefault(_key(source),[]).append(source)
        for row in rows:
            outcomes={(row['IsRedEnabled'] and r['IsRedEnabled']==1,
                       row['IsGreenEnabled'] if white else row['IsGreenEnabled'] and r['IsGreenEnabled']==1)
                      for r in sources.get(_key(row),[])}
            if len(outcomes)>1:
                raise ValueError('SOURCE_ORDER_AMBIGUITY: conflicting common aggregate outcomes in '+table)
            if outcomes:
                row['IsRedEnabled'],row['IsGreenEnabled']=outcomes.pop()
        result[table]=[r for r in result[table]
                       if not (r['IsRedEnabled']==1 and (white or r['IsGreenEnabled']==1))]
    result['SuspendAggrCommon']=[r for r in rows if not (r['IsRedEnabled'] and r['IsGreenEnabled'])]
    return result


def aggregate_order_common(state):
    """DAG step19; ordered independent red/green intersection per master row."""
    result=deepcopy(state)
    rows=[_flags(r,True,True) for r in state['DBMMaster']]
    for table in ('SuspendAcceptedNormsStockType','SuspendNormsInSleepModeTbl',
                  'SuspendPhaseInTbl','SuspendPhaseOutTbl','SuspendSeasonalityTbl',
                  'SuspendStepOneOrderTypeTbl'):
        sources={}
        for source in state[table]:
            sources.setdefault(_key(source),[]).append(source)
        for row in rows:
            matches=sources.get(_key(row),[])
            outcomes={(row['IsRedEnabled'] and r['IsRedEnabled']==1,
                       row['IsGreenEnabled'] and r['IsGreenEnabled']==1) for r in matches}
            if len(outcomes)>1:
                raise ValueError('SOURCE_ORDER_AMBIGUITY: conflicting aggregate join outcomes in '+table)
            if outcomes:
                row['IsRedEnabled'],row['IsGreenEnabled']=outcomes.pop()
    result['SuspendAggrCommonWithOrderType']=rows
    return result


def apply_seasonality_suspension(state):
    """DAG step18: rebuild seasonal membership from statuses 2 through 6."""
    result=deepcopy(state)
    result['SuspendSeasonalityTbl']=[
        {'SKUCode':r['SKUCode'],'WHCode':r['WhCode'],
         'IsRedEnabled':False,'IsGreenEnabled':False} for r in state['Seasonality']
        if r['Status'] in (2,3,4,5,6)]
    return result


def apply_phasein_suspension(state):
    """DAG step17: rebuild from strict TargetNorm > NewNorm, SQL NULL rules."""
    result=deepcopy(state)
    result['SuspendPhaseInTbl']=[
        {'SKUCode':r['SKUCode'],'WHCode':r['WHCode'],
         'IsRedEnabled':False,'IsGreenEnabled':False} for r in state['PhaseInTbl']
        if r['NewNorm'] is not None and r['TargetNorm'] > r['NewNorm']]
    return result


def apply_phaseout_suspension(state):
    """DAG step16: unconditional phase-out projection, preserving source bag."""
    result=deepcopy(state)
    result['SuspendPhaseOutTbl']=[
        {'SKUCode':r['SKUCode'],'WHCode':r['WHCode'],
         'IsRedEnabled':False,'IsGreenEnabled':False} for r in state['PhaseOutTbl']]
    return result


def apply_supply(today, state):
    """DAG step15: window nominations, stock exclusions, receipt-date release."""
    def day(value):
        return date.fromisoformat(value) if isinstance(value,str) else value
    def limit(norm):
        return int((Decimal(norm)/3).to_integral_value(rounding=ROUND_CEILING))
    today=day(today)
    runs=state['LastBatchRunTbl']
    if len(runs)!=1:
        raise ValueError('Supply seam requires one LastBatchRun row')
    stamp=runs[0]['LastRunDate']
    stamp=datetime.fromisoformat(stamp) if isinstance(stamp,str) else stamp
    if stamp!=datetime.combine(today,datetime.min.time()):
        raise ValueError('Supply seam requires midnight business date')
    result=deepcopy(state)
    windows={}
    valid_stock=set()
    for master in state['DBMMaster']:
        key=_key(master)
        group=(key,master['Norm'])
        for fact in state['DailyConsumption']:
            if key==_key(fact) and today-timedelta(days=master['RLT']) < day(fact['ReportDate']) <= today:
                windows.setdefault(group,[]).append(fact['Receipts'])
                if fact['Stock'] is not None and Decimal(fact['Stock']) > Decimal(2)*master['Norm']/3:
                    valid_stock.add(key)
    nominated=[key for (key,norm),values in windows.items()
               if sum(values)<limit(norm) and key not in valid_stock]
    keys=set(nominated)
    rows=[r for r in result['SuspendSupplyIssueTbl'] if _key(r) not in keys]
    rows.extend({'SKUCode':key[0],'WhCode':key[1],'SuspendDate':today.isoformat(),
                 'ReceiptDate':None,'IsRedEnabled':False} for key in nominated)
    # Joined unresolved memberships multiply the grouped receipt values.
    solved=set()
    for (key,norm),values in windows.items():
        multiplicity=sum(_key(r)==key and r['ReceiptDate'] is None for r in rows)
        if multiplicity and sum(values)*multiplicity>=limit(norm):
            solved.add(key)
    for row in rows:
        if _key(row) in solved:
            row['ReceiptDate']=today.isoformat()
    master_keys={_key(r) for r in state['DBMMaster']}
    for row in rows:
        if _key(row) in master_keys and row['ReceiptDate'] is not None and day(row['ReceiptDate'])<=today:
            row['IsRedEnabled']=True
    result['SuspendSupplyIssueTbl']=rows
    result['IntermediateTables']=[{'table':r['table'],'rows':[]} for r in state['IntermediateTables']]
    return result


def apply_white(today, state):
    """DAG step14: rebuild today's white keys and release other memberships."""
    today = date.fromisoformat(today) if isinstance(today, str) else today
    runs = state['LastBatchRunTbl']
    if len(runs) != 1:
        raise ValueError('White seam requires one LastBatchRun row')
    stamp = runs[0]['LastRunDate']
    stamp = datetime.fromisoformat(stamp) if isinstance(stamp, str) else stamp
    if stamp != datetime.combine(today, datetime.min.time()):
        raise ValueError('White seam requires midnight business date')
    whites = []
    for master in state['DBMMaster']:
        for fact in state['DailyConsumption']:
            day = fact['ReportDate']
            day = date.fromisoformat(day) if isinstance(day, str) else day
            if (_key(master) == _key(fact) and day == today and fact['Stock'] is not None
                    and fact['Stock'] > master['Norm'] + fact['BlueZone']):
                whites.append({'SKUCode':master['SKUCode'], 'WhCode':_key(master)[1],
                               'IsRedEnabled':False})
    result = deepcopy(state)
    keys = {_key(r) for r in whites}
    rows = [r for r in result['SuspendWhitesTbl'] if _key(r) not in keys]
    for row in rows:
        row['IsRedEnabled'] = True
    result['SuspendWhitesTbl'] = rows + whites
    return result


def apply_spike(today, state):
    """DAG step 13: replace today's spikes, then release from later receipts."""
    def day(value):
        return date.fromisoformat(value) if isinstance(value, str) else value
    def threshold(norm):
        return int((Decimal(norm) / 3).to_integral_value(rounding=ROUND_CEILING))
    today = day(today)
    runs = state['LastBatchRunTbl']
    if len(runs) != 1:
        raise ValueError('Spike seam requires one LastBatchRun row')
    stamp = runs[0]['LastRunDate']
    stamp = datetime.fromisoformat(stamp) if isinstance(stamp, str) else stamp
    if stamp != datetime.combine(today, datetime.min.time()):
        raise ValueError('Spike seam requires midnight business date')
    spikes = []
    for master in state['DBMMaster']:
        limit = threshold(master['Norm'])
        for fact in state['DailyConsumption']:
            if (_key(master) == _key(fact) and day(fact['ReportDate']) == today
                    and fact['Consumption'] is not None and fact['Consumption'] > limit
                    and fact['Stock'] is not None and fact['Stock'] <= limit):
                spikes.append(master)
    result = deepcopy(state)
    replaced = {_key(r) for r in spikes}
    rows = [r for r in result['SuspendSpikeTbl'] if _key(r) not in replaced]
    rows.extend({**_flags(r, False, True), 'WaitStartDate':today.isoformat(),
                 'WaitTillDate':today.isoformat()} for r in spikes)
    # SQL groups joined membership/facts/master rows by key AND Norm.
    receipts = {}
    for row in rows:
        for master in state['DBMMaster']:
            if _key(master) != _key(row):
                continue
            for fact in state['DailyConsumption']:
                if (_key(fact) == _key(row)
                        and day(row['WaitStartDate']) < day(fact['ReportDate']) <= today):
                    group = (_key(row), master['Norm'])
                    receipts.setdefault(group, [])
                    if fact['Receipts'] is not None:
                        receipts[group].append(fact['Receipts'])
    released = {key for (key,norm), values in receipts.items()
                if values and sum(values) >= threshold(norm)}
    for row in rows:
        if _key(row) in released:
            row['IsRedEnabled'] = True
    result['SuspendSpikeTbl'] = rows
    return result


def apply_existing_disabled(today, state):
    """DAG step 12: strict wait expiry then positive today's receipt by key."""
    today = date.fromisoformat(today) if isinstance(today, str) else today
    runs = state['LastBatchRunTbl']
    if len(runs) != 1:
        raise ValueError('Existing-disabled seam requires one LastBatchRun row')
    stamp = runs[0]['LastRunDate']
    stamp = datetime.fromisoformat(stamp) if isinstance(stamp, str) else stamp
    if stamp != datetime.combine(today, datetime.min.time()):
        raise ValueError('Existing-disabled seam requires midnight business date')
    result = deepcopy(state)
    rows = result['SuspendExistingDisabledNormsTbl']
    for row in rows:
        end = row['WaitTillDate']
        end = date.fromisoformat(end) if isinstance(end, str) else end
        if end < today:
            row['WaitForReceipt'] = True
    waiting = {_key(r) for r in rows if r['WaitForReceipt']}
    release = set()
    for fact in state['DailyConsumption']:
        day = fact['ReportDate']
        day = date.fromisoformat(day) if isinstance(day, str) else day
        if day == today and fact['Receipts'] is not None and fact['Receipts'] > 0 and _key(fact) in waiting:
            release.add(_key(fact))
    for row in rows:
        if _key(row) in release:
            row['IsRedEnabled'] = True
            row['IsGreenEnabled'] = True
    return result


def apply_sleep(today, state):
    """DAG step 11: retain existing waits, insert new commands, expire waits."""
    today = date.fromisoformat(today) if isinstance(today, str) else today
    runs = state['LastBatchRunTbl']
    if len(runs) != 1:
        raise ValueError('Sleep seam requires one LastBatchRun row')
    stamp = runs[0]['LastRunDate']
    stamp = datetime.fromisoformat(stamp) if isinstance(stamp, str) else stamp
    if stamp != datetime.combine(today, datetime.min.time()):
        raise ValueError('Sleep seam requires midnight business date')
    result = deepcopy(state)
    opening_keys = {_key(r) for r in state['SuspendNormsInSleepModeTbl']}
    rows = result['SuspendNormsInSleepModeTbl']
    for command in state['NormsInSleepModeTbl']:
        if _key(command) in opening_keys:
            continue
        start = command['StartDate']
        start = date.fromisoformat(start) if isinstance(start, str) else start
        for master in state['DBMMaster']:
            if _key(master) == _key(command):
                rows.append({**_flags(command), 'WaitStartDate': start.isoformat(),
                    'WaitTillDate': (start + timedelta(days=min(master['RLT'], 7))).isoformat(),
                    'WaitForReceipts': False})
    for row in rows:
        end = row['WaitTillDate']
        end = date.fromisoformat(end) if isinstance(end, str) else end
        if end is not None and end <= today:
            row['IsRedEnabled'] = True
            row['IsGreenEnabled'] = True
    result['NormsInSleepModeTbl'] = []
    return result


def apply_forced_norm_consumption(today, state):
    """DAG step 10; reason101 resets existing monitoring without insertion."""
    today = date.fromisoformat(today) if isinstance(today, str) else today
    runs = state['LastBatchRunTbl']
    if len(runs) != 1:
        raise ValueError('Forced-consumption requires one LastBatchRun row')
    stamp = runs[0]['LastRunDate']
    stamp = datetime.fromisoformat(stamp) if isinstance(stamp, str) else stamp
    if stamp != datetime.combine(today, datetime.min.time()):
        raise ValueError('Forced-consumption requires midnight business date')
    keys = {_key(row) for row in state['NormChangeLogTbl']
            if row['NormChangeReason'] == 101 and
            (date.fromisoformat(row['NormChangeDate']) if isinstance(row['NormChangeDate'], str)
             else row['NormChangeDate']) == today}
    result = deepcopy(state)
    for row in result['SuspendConsumptionType']:
        if _key(row) in keys:
            row['RedResumeDate'] = today.isoformat()
            row['GreenResumeDate'] = today.isoformat()
    return result


def apply_forced_norm_stock(today, state):
    """DAG step 9, preserving the selected SQL's ordered wait updates."""
    def day(value):
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.date()
        return date.fromisoformat(value) if isinstance(value, str) else value

    today = day(today)
    runs = state['LastBatchRunTbl']
    if len(runs) != 1:
        raise ValueError('Forced stock requires one LastBatchRun row')
    stamp = runs[0]['LastRunDate']
    stamp = datetime.fromisoformat(stamp) if isinstance(stamp, str) else stamp
    if stamp != datetime.combine(today, datetime.min.time()):
        raise ValueError('Forced stock requires midnight business date')
    result = deepcopy(state)
    masters = {}
    for row in state['DBMMaster']:
        if _key(row) in masters:
            raise ValueError('SOURCE_ORDER_AMBIGUITY: duplicate forced-stock master')
        masters[_key(row)] = row
    changes = [r for r in state['ForcedNormChangeTbl'] if r['NewNorm'] != r['OldNorm']]
    replaced = {_key(r) for r in changes}
    suspended = [deepcopy(r) for r in state['SuspendNormsForceChangedTbl'] if _key(r) not in replaced]
    for change in changes:
        master = masters.get(_key(change))
        if master is None:
            continue
        wait = today + timedelta(days=master['RCP']) if change['NewNorm'] > change['OldNorm'] else None
        suspended.append({**_flags(change), 'WaitStartDate': today.isoformat(),
            'WaitTillDate': wait.isoformat() if wait is not None else None,
            'WaitForReceipts': False, 'ReqReceipts': change['NewNorm'] - change['OldNorm']})
    green_reset = {_key(r) for r in suspended if not r['IsGreenEnabled']}
    for row in result['SuspendStockType']:
        if _key(row) in green_reset:
            row['GreenResumeDate'] = today.isoformat()
    for row in suspended:
        row['IsGreenEnabled'] = True
        master = masters.get(_key(row))
        if row['WaitTillDate'] is not None and master is not None:
            row['WaitTillDate'] = (day(row['WaitStartDate']) + timedelta(days=master['RCP'])).isoformat()
    result['ForcedNormChangeTbl'] = []
    # SUM groups the suspension-to-facts join by SKU/location. Multiple opening
    # memberships contribute independently, including differing start dates.
    receipts = {}
    for row in suspended:
        key = _key(row)
        matching = [r['Receipts'] for r in state['DailyConsumption']
                    if _key(r) == key and day(row['WaitStartDate']) <= day(r['ReportDate']) <= today]
        if matching:
            receipts.setdefault(key, [])
            receipts[key].extend(v for v in matching if v is not None)
    totals = {k: sum(v) if v else None for k, v in receipts.items()}
    for row in suspended:
        key = _key(row)
        wait = day(row['WaitTillDate'])
        row['WaitForReceipts'] = wait is not None and wait <= today
        stocks = [r['Stock'] for r in state['DailyConsumption']
                  if _key(r) == key and day(r['ReportDate']) == today]
        master = masters.get(key)
        if key not in totals or not stocks or master is None:
            continue
        outcomes = set()
        for stock in stocks:
            if row['WaitForReceipts']:
                outcomes.add(totals[key] is not None and totals[key] >= row['ReqReceipts'])
            else:
                outcomes.add(wait is None and stock is not None and stock <= master['Norm'])
        if len(outcomes) != 1:
            raise ValueError('SOURCE_ORDER_AMBIGUITY: conflicting forced-stock daily rows')
        row['IsRedEnabled'] = outcomes.pop()
    red_reset = {_key(r) for r in suspended if r['IsRedEnabled']}
    for row in result['SuspendStockType']:
        if _key(row) in red_reset:
            row['RedResumeDate'] = today.isoformat()
    result['SuspendNormsForceChangedTbl'] = suspended
    return result


def apply_accepted_norm_consumption(today, state):
    """DAG step 8: reset monitoring, rebuild today's Type6 membership bag."""
    today = date.fromisoformat(today) if isinstance(today, str) else today
    runs = state['LastBatchRunTbl']
    if len(runs) != 1:
        raise ValueError('Accepted-consumption seam requires one LastBatchRun row')
    last_run = runs[0]['LastRunDate']
    if isinstance(last_run, str):
        last_run = datetime.fromisoformat(last_run)
    if last_run != datetime.combine(today, datetime.min.time()):
        raise ValueError('Accepted-consumption run date must equal midnight business date')
    result = deepcopy(state)
    logs = [row for row in state['NormChangeLogTbl']
            if (date.fromisoformat(row['NormChangeDate'])
                if isinstance(row['NormChangeDate'], str) else row['NormChangeDate']) == today]
    resets = {_key(row) for row in logs if row['NormChangeReason'] <= 100}
    for row in result['SuspendConsumptionType']:
        if _key(row) in resets:
            row['RedResumeDate'] = today.isoformat()
            row['GreenResumeDate'] = today.isoformat()
    # SQL clears the entire contributor, including unrelated stale rows.
    # SELECT has no DISTINCT: duplicate Type6 source rows survive insertion.
    result['SuspendAcceptedNormsConsumptionType'] = [
        _flags(row, False, True) for row in logs if row['NormChangeReason'] == 6]
    return result


def _pre(masters, *aggregates):
    rows = [_flags(row, True, True) for row in masters]
    for aggregate in aggregates:
        lookup = {}
        for source in aggregate:
            key = _key(source)
            flags = source['IsRedEnabled'], source['IsGreenEnabled']
            if key in lookup and lookup[key] != flags:
                raise ValueError('SOURCE_ORDER_AMBIGUITY: conflicting suspension aggregate flags')
            lookup[key] = flags
        for row in rows:
            if _key(row) in lookup:
                red, green = lookup[_key(row)]
                row['IsRedEnabled'] = row['IsRedEnabled'] and red == 1
                row['IsGreenEnabled'] = row['IsGreenEnabled'] and green == 1
    return [row for row in rows if not (row['IsRedEnabled'] and row['IsGreenEnabled'])]


def prepare_suspensions(state):
    """DAG steps 1–5, retaining other families and inputs untouched."""
    result = deepcopy(state)
    masters = state['DBMMaster']
    custom = state['SuspendCustomSKUTbl']
    result['SuspendStockTypePre'] = _pre(
        masters, state['SuspendAggrCommon'], state['SuspendAggrStockType'])
    result['SuspendConsumptionTypePre'] = _pre(
        masters, state['SuspendAggrCommon'], state['SuspendAggrConsumptionType'])
    result['SuspendOrderTypePre'] = _pre(masters, state['SuspendAggrCommonWithOrderType'])

    minimum = [dict(SKUCode=row['SKUCode'], WhCode=_key(row)[1])
               for row in masters if row['Norm'] < row['MinNorm']]
    step = [_flags(row) for row in masters
            if row['RLT'] < 3 or row['RCP'] < 3 or row['GCP'] < 3 or row['Norm'] < 2]
    custom_keys = {_key(row) for row in custom}
    step = [row for row in step if _key(row) not in custom_keys]
    step.extend(_flags(row) for row in custom)
    minimum_keys = {_key(row) for row in minimum}
    step = [row for row in step if _key(row) not in minimum_keys]
    step.extend(_flags(row) for row in minimum)
    result['SuspendMinNormTbl'] = minimum
    result['SuspendStepOneTbl'] = step

    order = [_flags(row) for row in masters if row['Norm'] == 0
             and (row['RLT'] < 3 or row['OCP'] is None
                  or (row['MinOrderCount'] if row['MinOrderCount'] is not None else 0) < 1)]
    order.extend(_flags(row) for row in masters if row['Norm'] > 2)
    existing_keys = {_key(row) for row in order}
    # Evaluate the anti-join against the statement's prior table: duplicate
    # custom rows both survive when the key was previously absent.
    order.extend(_flags(row) for row in custom if _key(row) not in existing_keys)
    result['SuspendStepOneOrderTypeTbl'] = order
    return result


def suspend_introductions(today, state):
    """DAG step6; existing memberships remain after receipt/stock release."""
    def day(value):
        if value is None:
            return None
        return date.fromisoformat(value) if isinstance(value, str) else value

    today = day(today)
    result = deepcopy(state)
    masters, daily = state['DBMMaster'], state['DailyConsumption']
    percentages = state['FirstReplenishmentPercentageTbl']
    if len(percentages) != 1:
        raise ValueError('Selected introduction profile requires one replenishment percentage')
    ratio = percentages[0]['ReplenishmentPercentage']
    new = [row for row in masters if day(row['SKUIntroDate']) == today]
    new_keys = {_key(row) for row in new}
    suspended = [deepcopy(row) for row in state['SuspendNewSKUTbl'] if _key(row) not in new_keys]
    suspended.extend({**_flags(row, False, True), 'ReplenishmentRatio': ratio} for row in new)

    def threshold(percentage, norm):
        return int((Decimal(percentage) * Decimal(norm) / 100).to_integral_value(rounding=ROUND_CEILING))

    for row in suspended:
        matching = [master for master in masters if _key(master) == _key(row)]
        if len(matching) > 1:
            raise ValueError('SOURCE_ORDER_AMBIGUITY: duplicate introduction master')
        if not matching:
            continue
        master = matching[0]
        if _key(row) in new_keys:
            stocks = {observation['Stock'] for observation in daily
                      if _key(observation) == _key(row) and day(observation['ReportDate']) == today}
            outcomes = {(0 if stock is None else stock) >= threshold(ratio, master['Norm'])
                        for stock in stocks}
            if len(outcomes) > 1:
                raise ValueError('SOURCE_ORDER_AMBIGUITY: introduction stock outcomes differ')
            if outcomes:
                row['IsRedEnabled'] = outcomes.pop()
        intro = day(master['SKUIntroDate'])
        receipts = [observation['Receipts'] for observation in daily
                    if _key(observation) == _key(row) and intro is not None
                    and intro <= day(observation['ReportDate']) <= today
                    and observation['Receipts'] is not None]
        # SQL groups the joined suspension rows; preserve multiplicity rather
        # than silently deduplicating retained opening memberships.
        multiplicity = sum(_key(other) == _key(row) for other in suspended)
        if receipts and sum(receipts) * multiplicity >= threshold(row['ReplenishmentRatio'], master['Norm']):
            row['IsRedEnabled'] = True
    result['SuspendNewSKUTbl'] = suspended
    return result


def suspend_accepted_norm_stock(today, state):
    """DAG step7; consume accepted-Norm stock waits in selected SQL order."""
    def day(value):
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, str):
            try:
                return date.fromisoformat(value)
            except ValueError:
                return datetime.fromisoformat(value).date()
        return value

    today = day(today)
    last_runs = state['LastBatchRunTbl']
    if len(last_runs) != 1 or day(last_runs[0]['LastRunDate']) != today:
        raise ValueError('Accepted-Norm seam requires one LastBatchRun date equal to the run date')

    result = deepcopy(state)
    masters_by_key = {}
    for master in state['DBMMaster']:
        key = _key(master)
        if key in masters_by_key:
            raise ValueError('SOURCE_ORDER_AMBIGUITY: duplicate DBMMaster key')
        masters_by_key[key] = master

    acceptances = state['NormAcceptanceTbl']
    accepted_keys = {_key(row) for row in acceptances}
    suspended = [deepcopy(row) for row in state['SuspendAcceptedNormsStockType']
                 if _key(row) not in accepted_keys]
    for acceptance in acceptances:
        key = _key(acceptance)
        master = masters_by_key.get(key)
        if master is None:
            continue
        upward = acceptance['NewNorm'] > acceptance['OldNorm']
        wait_start = today
        wait_till = (wait_start + timedelta(days=master['RCP'])) if upward else None
        suspended.append({
            'SKUCode': key[0], 'WhCode': key[1],
            'DeltaNorm': acceptance['NewNorm'] - acceptance['OldNorm'] if upward else None,
            'WaitStartDate': wait_start.isoformat(),
            'WaitTillDate': wait_till.isoformat() if wait_till is not None else None,
            'WaitForReceipts': False, 'HasStockComeOutOfRed': False,
            'IsRedEnabled': False, 'IsGreenEnabled': False,
        })
    result['SuspendAcceptedNormsStockType'] = suspended
    result['NormAcceptanceTbl'] = []

    def records_for_key(rows, key):
        return [row for row in rows if _key(row) == key]

    current_stock = {}
    for row in state['DailyConsumption']:
        if day(row['ReportDate']) != today:
            continue
        key = _key(row)
        if key not in masters_by_key:
            continue
        value = (row['Stock'], row['BlueZone'], masters_by_key[key]['Norm'])
        if key in current_stock and current_stock[key] != value:
            raise ValueError('SOURCE_ORDER_AMBIGUITY: conflicting same-day accepted-Norm stock rows')
        current_stock[key] = value

    # WaitForReceipts is recalculated for every membership, even when today's
    # stock/receipt joins are absent.
    for row in suspended:
        wait_till = day(row['WaitTillDate'])
        row['WaitForReceipts'] = wait_till is not None and wait_till <= today

    current_receipts = {}
    for row in suspended:
        key = _key(row)
        start = day(row['WaitStartDate'])
        matches = [fact for fact in state['DailyConsumption']
                   if _key(fact) == key and start <= day(fact['ReportDate']) <= today]
        if matches:
            current_receipts[key] = current_receipts.get(key, 0) + sum(
                fact['Receipts'] for fact in matches)

    for row in suspended:
        key = _key(row)
        stock = current_stock.get(key)
        master = masters_by_key.get(key)
        receipts = current_receipts.get(key)
        if stock is None or master is None or receipts is None:
            continue
        stock_value, blue_zone, norm = stock
        if stock_value is not None and stock_value > int(
                (Decimal(norm) / Decimal(3)).to_integral_value(rounding=ROUND_CEILING)):
            row['HasStockComeOutOfRed'] = True

        wait_till = day(row['WaitTillDate'])
        if wait_till is not None and wait_till <= today and row['HasStockComeOutOfRed']:
            delta = row['DeltaNorm']
            row['IsRedEnabled'] = delta is not None and receipts >= delta
        elif wait_till is None and stock_value is not None and stock_value <= norm + blue_zone:
            row['IsRedEnabled'] = True
        else:
            row['IsRedEnabled'] = False

    horizon_receipts = {}
    for row in suspended:
        key = _key(row)
        master = masters_by_key.get(key)
        if master is None:
            continue
        wait_start = day(row['WaitStartDate'])
        horizon_start = today - timedelta(days=master['RLT']) + timedelta(days=1)
        if horizon_start < wait_start:
            horizon_start = wait_start
        matches = [fact for fact in state['DailyConsumption']
                   if _key(fact) == key and day(fact['ReportDate']) >= horizon_start]
        if matches:
            horizon_receipts[key] = horizon_receipts.get(key, 0) + sum(
                fact['Receipts'] for fact in matches)

    for row in suspended:
        key = _key(row)
        if (day(row['WaitTillDate']) is not None and key in horizon_receipts
                and horizon_receipts[key] >= masters_by_key[key]['Norm']):
            row['IsRedEnabled'] = True
        row['IsGreenEnabled'] = row['IsRedEnabled']

    resumed = {_key(row) for row in suspended if row['IsRedEnabled']}
    for row in result['SuspendStockType']:
        if _key(row) in resumed:
            row['RedResumeDate'] = today.isoformat()
            row['GreenResumeDate'] = today.isoformat()
    return result


def apply_accepted_norm_stock(today, state):
    """DAG step 7; consume accepted-Norm stock waits in selected SQL order."""
    def day(value):
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, str):
            try:
                return date.fromisoformat(value)
            except ValueError:
                return datetime.fromisoformat(value).date()
        return value

    today = day(today)
    last_runs = state['LastBatchRunTbl']
    if len(last_runs) != 1 or day(last_runs[0]['LastRunDate']) != today:
        raise ValueError('Accepted-Norm seam requires one LastBatchRun date equal to the run date')

    result = deepcopy(state)
    masters_by_key = {}
    for master in state['DBMMaster']:
        key = _key(master)
        if key in masters_by_key:
            raise ValueError('SOURCE_ORDER_AMBIGUITY: duplicate DBMMaster key')
        masters_by_key[key] = master

    acceptances = state['NormAcceptanceTbl']
    accepted_keys = {_key(row) for row in acceptances}
    suspended = [deepcopy(row) for row in state['SuspendAcceptedNormsStockType']
                 if _key(row) not in accepted_keys]
    for acceptance in acceptances:
        key = _key(acceptance)
        master = masters_by_key.get(key)
        if master is None:
            continue
        upward = acceptance['NewNorm'] > acceptance['OldNorm']
        wait_start = today
        wait_till = wait_start + timedelta(days=master['RCP']) if upward else None
        suspended.append({
            'SKUCode': key[0], 'WhCode': key[1],
            'DeltaNorm': acceptance['NewNorm'] - acceptance['OldNorm'] if upward else None,
            'WaitStartDate': wait_start.isoformat(),
            'WaitTillDate': wait_till.isoformat() if wait_till is not None else None,
            'WaitForReceipts': False, 'HasStockComeOutOfRed': False,
            'IsRedEnabled': False, 'IsGreenEnabled': False,
        })
    result['SuspendAcceptedNormsStockType'] = suspended
    result['NormAcceptanceTbl'] = []

    current_stock = {}
    for fact in state['DailyConsumption']:
        if day(fact['ReportDate']) != today:
            continue
        key = _key(fact)
        master = masters_by_key.get(key)
        if master is None:
            continue
        value = (fact['Stock'], fact['BlueZone'], master['Norm'])
        if key in current_stock and current_stock[key] != value:
            raise ValueError('SOURCE_ORDER_AMBIGUITY: conflicting same-day accepted-Norm stock rows')
        current_stock[key] = value

    for row in suspended:
        master = masters_by_key.get(_key(row))
        wait_till = day(row['WaitTillDate'])
        if wait_till is not None and master is not None:
            wait_start = day(row['WaitStartDate'])
            wait_till = wait_start + timedelta(days=master['RCP'])
            row['WaitTillDate'] = wait_till.isoformat()
        row['WaitForReceipts'] = wait_till is not None and wait_till <= today

    current_receipts = {}
    for row in suspended:
        key = _key(row)
        start = day(row['WaitStartDate'])
        matches = [fact for fact in state['DailyConsumption']
                   if _key(fact) == key and start <= day(fact['ReportDate']) <= today]
        if matches:
            current_receipts[key] = current_receipts.get(key, 0) + sum(
                fact['Receipts'] for fact in matches)

    for row in suspended:
        key = _key(row)
        stock = current_stock.get(key)
        master = masters_by_key.get(key)
        receipts = current_receipts.get(key)
        if stock is None or master is None or receipts is None:
            continue
        stock_value, blue_zone, norm = stock
        red_threshold = int((Decimal(norm) / Decimal(3)).to_integral_value(rounding=ROUND_CEILING))
        if stock_value is not None and stock_value > red_threshold:
            row['HasStockComeOutOfRed'] = True

        wait_till = day(row['WaitTillDate'])
        if wait_till is not None and wait_till <= today and row['HasStockComeOutOfRed']:
            delta = row['DeltaNorm']
            row['IsRedEnabled'] = delta is not None and receipts >= delta
        elif wait_till is None and stock_value is not None and stock_value <= norm + blue_zone:
            row['IsRedEnabled'] = True
        else:
            row['IsRedEnabled'] = False

    horizon_receipts = {}
    for row in suspended:
        key = _key(row)
        master = masters_by_key.get(key)
        if master is None:
            continue
        wait_start = day(row['WaitStartDate'])
        horizon_start = today - timedelta(days=master['RLT']) + timedelta(days=1)
        if horizon_start < wait_start:
            horizon_start = wait_start
        matches = [fact for fact in state['DailyConsumption']
                   if _key(fact) == key and day(fact['ReportDate']) >= horizon_start]
        if matches:
            horizon_receipts[key] = horizon_receipts.get(key, 0) + sum(
                fact['Receipts'] for fact in matches)

    for row in suspended:
        key = _key(row)
        if (day(row['WaitTillDate']) is not None and key in horizon_receipts
                and horizon_receipts[key] >= masters_by_key[key]['Norm']):
            row['IsRedEnabled'] = True
        row['IsGreenEnabled'] = row['IsRedEnabled']

    resumed = {_key(row) for row in suspended if row['IsRedEnabled']}
    for row in result['SuspendStockType']:
        if _key(row) in resumed:
            row['RedResumeDate'] = today.isoformat()
            row['GreenResumeDate'] = today.isoformat()
    return result
