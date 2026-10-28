"""Canonical final-family history and contributor reason arithmetic.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend
presentation and behavior. No frontend redesign, substitute screens, refactoring
or MTO changes. Any future exception requires explicit human authorization.
"""
from copy import deepcopy
from datetime import date,timedelta
from itertools import chain
from mta.domain.ordinal_lookup import OrdinalLookup
from mta.domain.sql_identity_keys import row_join_key
from mta.row_sequences import RecordRows, history_rows

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
    key=row_join_key
    day=lambda v:date.fromisoformat(v) if isinstance(v,str) else v
    result=dict(state) if _owned else deepcopy(state)
    previous=(r for r in result['SuspendHistory'] if day(r['ReportDate'])>today-timedelta(days=90) and day(r['ReportDate'])!=today)
    def joined_rows():
        with OrdinalLookup(state['SuspendConsumptionType']) as consumption_index:
            for stock in state['SuspendStockType']:
                for consumption in consumption_index.matching(state['SuspendConsumptionType'], key(stock)):
                    if key(stock)!=key(consumption):continue
                    yield {'SKUCode':stock['SKUCode'],'WhCode':stock['WhCode'],
                        'RedEnabledStockType':stock['RedEnabled'],'GreenEnabledStockType':stock['GreenEnabled'],
                        'RedEnabledConsumptionType':consumption['RedEnabled'],'GreenEnabledConsumptionType':consumption['GreenEnabled'],
                        **{c:0 for c in REASONS},'ReportDate':today.isoformat()}
    current=RecordRows.from_rows(joined_rows()) if _owned else list(joined_rows())
    for table,bit,indices in CONTRIBUTORS:
        with OrdinalLookup(state[table]) as contributor_index:
            if _owned and not state[table]:
                continue
            def apply_contributor(rows):
                for original in rows:
                    row=deepcopy(original) if _owned else original
                    outcomes={tuple(bit if r['IsRedEnabled' if i%2==0 else 'IsGreenEnabled']==0 else 0 for i in indices)
                              for r in contributor_index.matching(state[table], key(row)) if key(r)==key(row)}
                    if len(outcomes)>1:raise ValueError('SOURCE_ORDER_AMBIGUITY: conflicting suspension history contributor '+table)
                    if outcomes:
                        for i,amount in zip(indices,outcomes.pop()):row[REASONS[i]]+=amount
                    yield row
            # Retain contributor-first/row-second error order. Each owned
            # generation is sealed before the next contributor; no full list.
            if _owned:
                current=RecordRows.from_rows(apply_contributor(current))
            else:
                for _ in apply_contributor(current):pass
    from mta.application.native_output_contracts import validate_produced_rows
    validate_produced_rows(current,'DBM/SuspendHistory',stage='dbm/suspension-history')
    result['SuspendHistory']=history_rows(chain(previous,current),like=state['SuspendHistory'],immutable=_owned)
    return result
