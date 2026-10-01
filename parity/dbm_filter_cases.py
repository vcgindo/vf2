"""Frozen DBM request roster; unchanged retained shallow business inputs."""
from copy import deepcopy
from parity.rrr_filter_cases import cases as rrr_cases


def cases():
    roster=rrr_cases()
    for case in roster:
        case['sql_error']=case.pop('canonical_sql_error') or case['id'] in (
            'positive-stock','git-zero','virtual-norm','pipeline-color','physical-color')
        # The deployed method only enters Commons when a standard group exists.
        if 'customAttributeFilter' in case['payload']['filters']:
            case['payload']['filters']['productFilter']=dict(filters=[])
    for name,operator in (('custom-only-ignored','equalto'),('custom-only-invalid-operator-ignored','invented')):
        case=deepcopy(roster[0]);case['id']=name
        case['payload']['filters']=dict(customAttributeFilter=dict(filters=[
            dict(attributeName='SKUAttr1',operator=operator,value='Missing')]))
        roster.append(case)
    return roster
