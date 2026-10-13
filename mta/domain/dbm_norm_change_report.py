"""Configured Norm-change export typed projection, before CSV packaging."""
from copy import deepcopy
from mta.domain.dbm_report_dates import report_cutoff, row_date

HEADER=['SKUCode','Location','New Norm','Old Norm','Norm Change Date','Reason']


def norm_change_report(today,state,horizon):
    lower=report_cutoff(today,state,horizon,inclusive=True);rows=[]
    for r in state['NormChangeLogTbl']:
        day=row_date(r['NormChangeDate'])
        if r['NormChangeReason'] is None or r['NormChangeReason']>=100 or day is None or day<lower:continue
        reasons=[v['Reason'] for v in state['ReasonCodes'] if v['Id']==r['NormChangeReason']]
        for reason in reasons or [None]:
            rows.append({'values':[r['SKUCode'],r['WHCode'],r['NewNorm'],r['OldNorm'],day.isoformat(),
                None if reason is None else '"'+reason+'"']})
    return {**deepcopy(state),'ReportHeader':[{'values':HEADER.copy()}],'ReportRows':rows}
