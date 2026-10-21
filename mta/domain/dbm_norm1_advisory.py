"""Selected three-RLT positive-sale ancillary advisory.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
from copy import deepcopy
from datetime import date,timedelta
from mta.domain.ordinal_lookup import OrderedIndex
from mta.domain.sql_identity_keys import row_join_key, value_join_key


def norm1_advisory(today,state,*,_owned=False):
    today=date.fromisoformat(today) if isinstance(today,str) else today
    if state['LastBatchRunTbl']!=[{'LastRunDate':today.isoformat()+'T00:00:00'}]:
        raise ValueError('Norm1 advisory requires singleton midnight business date')
    excluded={value_join_key(r['SKUCode']) for t in ('PhaseInTbl','PhaseOutTbl') for r in state[t]}
    groups={}
    spellings={}
    def consume(m,observations):
        key=row_join_key(m)
        for r in observations:
            day=date.fromisoformat(r['ReportDate']) if isinstance(r['ReportDate'],str) else r['ReportDate']
            if row_join_key(r)!=key or r['Consumption'] is None or r['Consumption']<=0 or day<=today-timedelta(days=3*m['RLT']):continue
            spelling=m['SKUCode'],m['WhCode']
            if key in spellings and spellings[key]!=spelling:
                raise ValueError('SOURCE_ORDER_AMBIGUITY: Norm1 advisory grouped key spelling')
            spellings[key]=spelling
            bucket=2 if day>today-timedelta(days=m['RLT']) else 1 if day>today-timedelta(days=2*m['RLT']) else 0
            groups.setdefault(key,[0,0,0])[bucket]+=r['Consumption']
    first=False
    with OrderedIndex(state['DailyConsumption']) as daily_index:
        for m in state['DBMMaster']:
            if m['Norm']!=1 or value_join_key(m['SKUCode']) in excluded:continue
            if not first:
                # The legacy predicate parses every history date before checking
                # its key. Keep that first complete ordered pass so unrelated
                # invalid dates and earlier matching-row errors retain precedence.
                consume(m,state['DailyConsumption'])
                first=True
            else:
                consume(m,daily_index.candidates((m['SKUCode'],m['WhCode'])))
    rows=[]
    for key,b in groups.items():
        if not (all(x>0 for x in b) or b[2]>1 or sum(b)>1 and b[2]>0):continue
        sku,wh=spellings[key]
        rows.append({'SKUCode':sku,'WhCode':wh,'SaleInBucket1':b[0],'SaleInBucket2':b[1],
            'SaleInBucket3':b[2],'SaleInAllBuckets':sum(b),**{c:None for c in ('S1','S2','S3','V1','V2','V3','V4','V5')}})
    result=dict(state) if _owned else deepcopy(state)
    result['Norm1IncreaseSuggestions']=rows
    result['IntermediateTables']=[{'table':r['table'],'rows':[]} for r in state['IntermediateTables']]
    return result
