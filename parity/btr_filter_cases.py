"""Finite BTR request roster over retained facts, not new synthetic data."""
from parity.rrr_filter_cases import cases as rrr_cases


def cases():
    result=rrr_cases()
    for index,case in enumerate(result):
        case.pop('canonical_sql_error')
        case['payload']['name']=('both','tech','eco')[index%3]
        case['payload']['filters']['horizonFilter']=dict(filters=[
            dict(attributeName='startDate',value='2026-06-06'),
            dict(attributeName='endDate',value='2026-06-17')])
        both=case['id'] in ('missing-availability','missing-coverage','invalid-operator','invalid-hierarchy-column')
        case['sql_errors']=['GetBTRDataCount','GetBTRData'] if both else ['GetBTRData'] if case['id'] in (
            'positive-stock','git-zero','pipeline-color','physical-color') else []
    for name,group,attribute,op,value,extra in (
        ('category-code','availabilityFilter','category','equalto','5',{}),
        ('red-positive-count','colorFilter','red','greaterthan','0',dict(type='colorcount')),
        ('black-red-positive-count','colorFilter','black/red','greaterthan','0',dict(type='colorcount')),
        ('green-count-zero','colorFilter','green','equalto','0',dict(type='colorcount')),
        ('black-red-age','colorFilter','black/red','greaterthanequalto','0',dict(type='colorage')),
        ('green-age','colorFilter','green','greaterthanequalto','0',dict(type='colorage')),
        ('black-red-invalid-multi-column','colorFilter','black/red','hasvalue','',dict(type='colorcount'))):
        from copy import deepcopy
        case=deepcopy(result[0]); case['id']=name
        case['payload']['filters'][group]=dict(filters=[dict(attributeName=attribute,operator=op,value=value,**extra)])
        case['sql_errors']=['GetBTRDataCount','GetBTRData'] if name=='black-red-invalid-multi-column' else []
        result.append(case)
    return result
