"""Frozen pre-refinement functions from 1ccef40; differential reference only."""
from copy import deepcopy
from datetime import date,datetime,timedelta
from decimal import Decimal,ROUND_CEILING
from itertools import groupby

def _key(row):
    return row['SKUCode'], row.get('WhCode', row.get('WHCode'))

def _flags(row, red=False, green=False):
    return {'SKUCode': row['SKUCode'], 'WhCode': _key(row)[1],
            'IsRedEnabled': red, 'IsGreenEnabled': green}

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

def _day(value):
    if value is None:
        return None
    if type(value) is date:
        return value
    return date.fromisoformat(value)

def calculate_extended_ocp(today, attributes, masters, daily):
    """Match SQL observation groups, inclusive lower bound, and NULL OCP."""
    today = _day(today)
    result = deepcopy(attributes)
    for attr in result:
        matching = [row for row in masters if _key(row) == _key(attr)]
        if not matching:
            continue
        if len(matching) != 1:
            raise ValueError('SOURCE_ORDER_AMBIGUITY: duplicate DBMMaster for ExtendedOCP')
        master = matching[0]
        ocp, rlt = master['OCP'], master['RLT']
        attr['ExtendedOCP'] = ocp
        if ocp is None:
            continue
        observations = sorted(
            (row for row in daily if _key(row) == _key(master)
             and _day(row['ReportDate']) >= today - timedelta(days=ocp)),
            key=lambda row: _day(row['ReportDate']),
        )
        for _, group in groupby(observations, key=lambda row: _day(row['ReportDate'])):
            # ROW_NUMBER orders only by date in both windows. Never manufacture
            # a deterministic order for differently classified tied observations.
            if len({row['Stock'] == 0 for row in group}) > 1:
                raise ValueError('SOURCE_ORDER_AMBIGUITY: tied zero/nonzero observations')
        current = longest = 0
        for row in observations:
            current = current + 1 if row['Stock'] == 0 else 0
            longest = max(longest, current)
        if longest > rlt:
            attr['ExtendedOCP'] = ocp + longest - rlt
    return result

REASONS=('RedReasonStockType','GreenReasonStockType','RedReasonConsumptionType','GreenReasonConsumptionType')

CONTRIBUTORS=(('SuspendCustomSKUTbl',1,(0,1,2,3)),('SuspendNormsInSleepModeTbl',2,(0,1,2,3)),
    ('SuspendPhaseInTbl',4,(0,1,2,3)),('SuspendPhaseOutTbl',8,(0,1,2,3)),
    ('SuspendStepOneTbl',16,(0,1,2,3)),('SuspendInsuffDataPointsTbl',32,(0,1,2,3)),
    ('SuspendWhitesTbl',64,(0,2)),('SuspendSupplyIssueTbl',128,(0,)),
    ('SuspendNewSKUTbl',256,(0,1)),('SuspendAcceptedNormsStockType',512,(0,1)),
    ('SuspendNormsForceChangedTbl',1024,(0,1)),('SuspendSpikeTbl',2048,(0,1)),
    ('SuspendAcceptedNormsConsumptionType',4096,(2,3)),('SuspendSeasonalityTbl',8192,(0,1,2,3)))

def gather_suspension_history(today,state):
    today=date.fromisoformat(today) if isinstance(today,str) else today
    if state['LastBatchRunTbl']!=[{'LastRunDate':today.isoformat()+'T00:00:00'}]:
        raise ValueError('History requires singleton midnight run date')
    key=lambda r:(r['SKUCode'],r.get('WhCode',r.get('WHCode')))
    day=lambda v:date.fromisoformat(v) if isinstance(v,str) else v
    result=deepcopy(state)
    previous=[r for r in result['SuspendHistory'] if day(r['ReportDate'])>today-timedelta(days=90) and day(r['ReportDate'])!=today]
    current=[]
    for stock in state['SuspendStockType']:
        for consumption in state['SuspendConsumptionType']:
            if key(stock)!=key(consumption):continue
            current.append({'SKUCode':stock['SKUCode'],'WhCode':stock['WhCode'],
                'RedEnabledStockType':stock['RedEnabled'],'GreenEnabledStockType':stock['GreenEnabled'],
                'RedEnabledConsumptionType':consumption['RedEnabled'],'GreenEnabledConsumptionType':consumption['GreenEnabled'],
                **{c:0 for c in REASONS},'ReportDate':today.isoformat()})
    for table,bit,indices in CONTRIBUTORS:
        for row in current:
            outcomes={tuple(bit if r['IsRedEnabled' if i%2==0 else 'IsGreenEnabled']==0 else 0 for i in indices)
                      for r in state[table] if key(r)==key(row)}
            if len(outcomes)>1:raise ValueError('SOURCE_ORDER_AMBIGUITY: conflicting suspension history contributor '+table)
            if outcomes:
                for i,amount in zip(indices,outcomes.pop()):row[REASONS[i]]+=amount
    result['SuspendHistory']=previous+current
    return result
