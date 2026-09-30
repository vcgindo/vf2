"""Selected seven-day change history projection, date-descending groups."""
from copy import deepcopy
from datetime import date,timedelta

HEADER=['SKUCode','SKU Name','Loc Code','Loc Name','OldNorm','NewNorm','NormChangeDate','Reason']


def norm_change_history(today,state,horizon):
    today=date.fromisoformat(today) if isinstance(today,str) else today
    if horizon!=7 or state['LastBatchRunTbl']!=[{'LastRunDate':today.isoformat()+'T00:00:00'}]:
        raise ValueError('Selected history requires seven-day horizon and singleton midnight run date')
    rows=[]
    for r in state['NormChangeLogTbl']:
        day=date.fromisoformat(r['NormChangeDate']) if isinstance(r['NormChangeDate'],str) else r['NormChangeDate']
        if day<=today-timedelta(days=horizon):continue
        skus=[v['SKUDescription'].replace(',',' ') for v in state['SKUDescriptionTbl'] if v['SKUCode']==r['SKUCode']] or [None]
        sites=[v['WHDescription'].replace(',',' ') for v in state['SiteDescriptionTbl'] if v['WHCode']==r['WHCode']] or [None]
        reasons=[v['Reason'] for v in state['ReasonCodes'] if v['Id']==r['NormChangeReason']] or [None]
        for sku in skus:
            for site in sites:
                for reason in reasons:rows.append({'values':[r['SKUCode'],sku,r['WHCode'],site,r['OldNorm'],r['NewNorm'],day.isoformat(),reason]})
    rows.sort(key=lambda r:r['values'][6],reverse=True)
    return {**deepcopy(state),'ReportHeader':[{'values':HEADER.copy()}],'ReportRows':rows}
