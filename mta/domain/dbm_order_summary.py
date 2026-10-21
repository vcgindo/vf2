"""Selected unconditional OrderRuleSummary to dated history producer."""
from copy import deepcopy
from datetime import date,timedelta
from itertools import chain
from mta.row_sequences import history_rows


def update_order_summary(today,state,*,_owned=False):
    today=date.fromisoformat(today) if isinstance(today,str) else today
    result=dict(state) if _owned else deepcopy(state)
    def day(v):return date.fromisoformat(v) if isinstance(v,str) else v
    retained=(r for r in result['OrderDataSummary']
        if day(r['ImportDate'])>=today-timedelta(days=90) and day(r['ImportDate'])!=today)
    current=({**{k:r[k] for k in
        ('SKUCode','WhCode','NodeOrderCount','CummOrderCount','NodeConsumption')},'ImportDate':today.isoformat()}
        for r in state['OrderRuleSummary'])
    result['OrderDataSummary']=history_rows(chain(retained,current),like=state['OrderDataSummary'])
    return result
