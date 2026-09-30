"""Selected Norm-change export typed projection, before CSV packaging."""
from copy import deepcopy
from datetime import date,timedelta

HEADER=['SKUCode','Location','New Norm','Old Norm','Norm Change Date','Reason']


def norm_change_report(today,state,horizon):
    today=date.fromisoformat(today) if isinstance(today,str) else today
    if state['LastBatchRunTbl']!=[{'LastRunDate':today.isoformat()+'T00:00:00'}]:
        raise ValueError('Norm-change export requires singleton midnight date')
    if horizon!=1:raise ValueError('Selected Norm-change report horizon is one')
    lower=today-timedelta(days=horizon-1);rows=[]
    for r in state['NormChangeLogTbl']:
        day=date.fromisoformat(r['NormChangeDate']) if isinstance(r['NormChangeDate'],str) else r['NormChangeDate']
        if r['NormChangeReason']>=100 or day<lower:continue
        reasons=[v['Reason'] for v in state['ReasonCodes'] if v['Id']==r['NormChangeReason']]
        for reason in reasons or [None]:
            rows.append({'values':[r['SKUCode'],r['WHCode'],r['NewNorm'],r['OldNorm'],day.isoformat(),
                None if reason is None else '"'+reason+'"']})
    return {**deepcopy(state),'ReportHeader':[{'values':HEADER.copy()}],'ReportRows':rows}
