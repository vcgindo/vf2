"""Canonical final-family history and contributor reason arithmetic."""
from copy import deepcopy
from datetime import date,timedelta
from itertools import chain
from mta.domain.ordinal_lookup import OrdinalLookup
from mta.row_sequences import history_rows

REASONS=('RedReasonStockType','GreenReasonStockType','RedReasonConsumptionType','GreenReasonConsumptionType')
CONTRIBUTORS=(('SuspendCustomSKUTbl',1,(0,1,2,3)),('SuspendNormsInSleepModeTbl',2,(0,1,2,3)),
    ('SuspendPhaseInTbl',4,(0,1,2,3)),('SuspendPhaseOutTbl',8,(0,1,2,3)),
    ('SuspendStepOneTbl',16,(0,1,2,3)),('SuspendInsuffDataPointsTbl',32,(0,1,2,3)),
    ('SuspendWhitesTbl',64,(0,2)),('SuspendSupplyIssueTbl',128,(0,)),
    ('SuspendNewSKUTbl',256,(0,1)),('SuspendAcceptedNormsStockType',512,(0,1)),
    ('SuspendNormsForceChangedTbl',1024,(0,1)),('SuspendSpikeTbl',2048,(0,1)),
    ('SuspendAcceptedNormsConsumptionType',4096,(2,3)),('SuspendSeasonalityTbl',8192,(0,1,2,3)))


def gather_suspension_history(today,state,*,_owned=False):
    today=date.fromisoformat(today) if isinstance(today,str) else today
    if state['LastBatchRunTbl']!=[{'LastRunDate':today.isoformat()+'T00:00:00'}]:
        raise ValueError('History requires singleton midnight run date')
    key=lambda r:(r['SKUCode'],r.get('WhCode',r.get('WHCode')))
    day=lambda v:date.fromisoformat(v) if isinstance(v,str) else v
    result=dict(state) if _owned else deepcopy(state)
    previous=(r for r in result['SuspendHistory'] if day(r['ReportDate'])>today-timedelta(days=90) and day(r['ReportDate'])!=today)
    current=[]
    with OrdinalLookup(state['SuspendConsumptionType']) as consumption_index:
        for stock in state['SuspendStockType']:
            for consumption in consumption_index.matching(state['SuspendConsumptionType'], key(stock)):
                if key(stock)!=key(consumption):continue
                current.append({'SKUCode':stock['SKUCode'],'WhCode':stock['WhCode'],
                    'RedEnabledStockType':stock['RedEnabled'],'GreenEnabledStockType':stock['GreenEnabled'],
                    'RedEnabledConsumptionType':consumption['RedEnabled'],'GreenEnabledConsumptionType':consumption['GreenEnabled'],
                    **{c:0 for c in REASONS},'ReportDate':today.isoformat()})
    for table,bit,indices in CONTRIBUTORS:
        with OrdinalLookup(state[table]) as contributor_index:
            for row in current:
                outcomes={tuple(bit if r['IsRedEnabled' if i%2==0 else 'IsGreenEnabled']==0 else 0 for i in indices)
                          for r in contributor_index.matching(state[table], key(row)) if key(r)==key(row)}
                if len(outcomes)>1:raise ValueError('SOURCE_ORDER_AMBIGUITY: conflicting suspension history contributor '+table)
                if outcomes:
                    for i,amount in zip(indices,outcomes.pop()):row[REASONS[i]]+=amount
    result['SuspendHistory']=history_rows(chain(previous,current),like=state['SuspendHistory'])
    return result
