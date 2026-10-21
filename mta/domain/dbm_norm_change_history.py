"""Configured change history projection, date-descending groups.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
from copy import deepcopy
from contextlib import ExitStack
from mta.domain.dbm_report_dates import report_cutoff, row_date
from mta.domain.ordinal_lookup import OrderedIndex
from mta.domain.sql_identity_keys import value_join_key

HEADER=['SKUCode','SKU Name','Loc Code','Loc Name','OldNorm','NewNorm','NormChangeDate','Reason']


def norm_change_history(today,state,horizon,*,_owned=False):
    lower=report_cutoff(today,state,horizon,inclusive=False)
    rows=[]
    def same(left,right):
        return left is not None and right is not None and value_join_key(left)==value_join_key(right)
    def description(value):
        return None if value is None else value.replace(',',' ')
    exact=lambda value:(value,)
    with ExitStack() as stack:
        sku_index=stack.enter_context(OrderedIndex(state['SKUDescriptionTbl'],
            key=lambda v:(v['SKUCode'],),key_contract=value_join_key))
        site_index=stack.enter_context(OrderedIndex(state['SiteDescriptionTbl'],
            key=lambda v:(v['WHCode'],),key_contract=value_join_key))
        reason_index=stack.enter_context(OrderedIndex(state['ReasonCodes'],
            key=lambda v:(v['Id'],),key_contract=exact))
        for r in state['NormChangeLogTbl']:
            day=row_date(r['NormChangeDate'])
            if day is None or day<=lower:continue
            skus=[description(v['SKUDescription']) for v in sku_index.candidates_for(r,'SKUCode') if same(v['SKUCode'],r['SKUCode'])] or [None]
            sites=[description(v['WHDescription']) for v in site_index.candidates_for(r,'WHCode') if same(v['WHCode'],r['WHCode'])] or [None]
            reasons=[v['Reason'] for v in reason_index.candidates_for(r,'NormChangeReason')
                     if r['NormChangeReason'] is not None and v['Id']==r['NormChangeReason']] or [None]
            for sku in skus:
                for site in sites:
                    for reason in reasons:rows.append({'values':[r['SKUCode'],sku,r['WHCode'],site,r['OldNorm'],r['NewNorm'],day.isoformat(),reason]})
    rows.sort(key=lambda r:r['values'][6],reverse=True)
    return {**(dict(state) if _owned else deepcopy(state)),'ReportHeader':[{'values':HEADER.copy()}],'ReportRows':rows}
