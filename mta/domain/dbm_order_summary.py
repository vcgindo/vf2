"""Selected unconditional OrderRuleSummary to dated history producer."""
from copy import deepcopy
from datetime import date,timedelta


def update_order_summary(today,state):
    today=date.fromisoformat(today) if isinstance(today,str) else today
    result=deepcopy(state)
    def day(v):return date.fromisoformat(v) if isinstance(v,str) else v
    result['OrderDataSummary']=[r for r in result['OrderDataSummary']
        if day(r['ImportDate'])>=today-timedelta(days=90) and day(r['ImportDate'])!=today]
    result['OrderDataSummary'].extend({**{k:r[k] for k in
        ('SKUCode','WhCode','NodeOrderCount','CummOrderCount','NodeConsumption')},'ImportDate':today.isoformat()}
        for r in state['OrderRuleSummary'])
    return result
