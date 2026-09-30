"""Selected three-RLT positive-sale ancillary advisory."""
from copy import deepcopy
from datetime import date,timedelta


def norm1_advisory(today,state):
    today=date.fromisoformat(today) if isinstance(today,str) else today
    if state['LastBatchRunTbl']!=[{'LastRunDate':today.isoformat()+'T00:00:00'}]:
        raise ValueError('Norm1 advisory requires singleton midnight business date')
    excluded={r['SKUCode'] for t in ('PhaseInTbl','PhaseOutTbl') for r in state[t]}
    groups={}
    for m in state['DBMMaster']:
        if m['Norm']!=1 or m['SKUCode'] in excluded:continue
        key=(m['SKUCode'],m['WhCode'])
        for r in state['DailyConsumption']:
            day=date.fromisoformat(r['ReportDate']) if isinstance(r['ReportDate'],str) else r['ReportDate']
            if (r['SKUCode'],r['WhCode'])!=key or r['Consumption'] is None or r['Consumption']<=0 or day<=today-timedelta(days=3*m['RLT']):continue
            bucket=2 if day>today-timedelta(days=m['RLT']) else 1 if day>today-timedelta(days=2*m['RLT']) else 0
            groups.setdefault(key,[0,0,0])[bucket]+=r['Consumption']
    rows=[]
    for (sku,wh),b in groups.items():
        if not (all(x>0 for x in b) or b[2]>1 or sum(b)>1 and b[2]>0):continue
        rows.append({'SKUCode':sku,'WhCode':wh,'SaleInBucket1':b[0],'SaleInBucket2':b[1],
            'SaleInBucket3':b[2],'SaleInAllBuckets':sum(b),**{c:None for c in ('S1','S2','S3','V1','V2','V3','V4','V5')}})
    result=deepcopy(state);result['Norm1IncreaseSuggestions']=rows
    result['IntermediateTables']=[{'table':r['table'],'rows':[]} for r in state['IntermediateTables']]
    return result
