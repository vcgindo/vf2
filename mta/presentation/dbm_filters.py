"""Deployed DBM filterQuery(e,i,f), applied to raw rows before SELECT/RN."""
from collections import defaultdict
from mta.presentation.context import PublicationUnavailable
from mta.presentation.rrr import sql_key
from mta.presentation.rrr_filters import OPERATORS, compare

STANDARD_GROUPS=('availabilityFilter','supplyChainFilter','coverageFilter',
                 'productFilter','locationFilter','colorFilter')


def unavailable(detail):
    raise PublicationUnavailable('LEG-DBM-FILTER-INVALID-SQL:'+detail)


def dbm_predicate(payload,state):
    filters=payload.get('filters') or {}
    if not isinstance(filters,dict): raise ValueError('invalid_filter_groups')
    # This is the actual DBMProcessor call gate, not a corrected interpretation.
    if not any(filters.get(group) is not None for group in STANDARD_GROUPS):
        return lambda a,b,e,i,f:1
    constraints=[]; children=[]

    def items(group):
        value=filters.get(group)
        if value is None: return []
        if not isinstance(value,dict) or not isinstance(value.get('filters'),list): raise ValueError('invalid_filter_group')
        result=[]
        for item in value['filters']:
            if not isinstance(item,dict): raise ValueError('invalid_filter')
            if item.get('attributeName')=='': continue
            if not isinstance(item.get('attributeName'),str) or not isinstance(item.get('value'),str):
                unavailable('noncanonical attribute/value')
            result.append(item)
        return result

    def get(table,field):
        def value(a,b,e,i,f):
            values=(a,b,e,i,f)[table]
            name=next((k for k in values if k.casefold()==field.casefold()),None)
            return values[name] if name is not None else None
        return value

    def clause(getter,op,wanted):
        if op not in OPERATORS: unavailable('unknown deployed operator')
        def matched(a,b,e,i,f):
            try:return compare(getter(a,b,e,i,f),op,wanted)
            except PublicationUnavailable as exc:unavailable(str(exc).partition(':')[2])
        return matched

    def in_list(getter,values):
        constraints.append(lambda a,b,e,i,f:any(sql_key(getter(a,b,e,i,f))==sql_key(v)
            and sql_key(v) is not None for v in values))

    def grouped(entries,mapper):
        groups=defaultdict(list)
        for item in entries: groups[item['attributeName']].append(item)
        for attribute,specs in groups.items():
            getter=mapper(attribute)
            clauses=[clause(getter,p.get('operator'),p['value']) for p in specs]
            constraints.append(lambda a,b,e,i,f,clauses=clauses:any(p(a,b,e,i,f) for p in clauses))

    supply=defaultdict(list)
    for item in items('supplyChainFilter'): supply[item['attributeName'].lower()].append(item['value'])
    for name,table,column in (('forlocation',3,'LocationType'),('forlocationlocationcode',0,'WhCode'),
                              ('forchildrenlocationcode',1,'ParentWhCode')):
        if supply[name]: in_list(get(table,column),supply[name])
    children=supply['forchildren']
    for group,special,code,table in (('productFilter','sku','SKUCode',2),('locationFilter','location','WhCode',3)):
        entries=items(group);codes=[p['value'] for p in entries if p['attributeName'].lower()==special]
        if codes:in_list(get(0,code),codes)
        def mapper(attribute,group=group,table=table):
            field=attribute.replace('p','sl') if group=='productFilter' else 'l'+attribute
            if field.casefold() not in {('sl' if group=='productFilter' else 'll')+str(n) for n in range(1,6)}:
                unavailable('missing hierarchy column '+field)
            return get(table,field)
        grouped([p for p in entries if p['attributeName'].lower()!=special],mapper)
    for item in items('availabilityFilter'):
        name=item['attributeName'].lower()
        if name=='norm': constraints.append(clause(get(1,'Norm'),item.get('operator'),item['value']))
        elif name in ('stock','git','virtualnorm','availability','pic','ohic','category','pipo,seasonality'):
            unavailable('missing selected DBM column '+name)
    if items('colorFilter'): unavailable('DBM has no btd/Age/colour-count join')
    if any(p['attributeName'].lower()=='coverage' for p in items('coverageFilter')):
        unavailable('DBM has no coverage column')

    def custom(attribute):
        lower=attribute.lower()
        for prefix,table in (('skulocattr',4),('skuattr',2),('locattr',3)):
            if prefix in lower:
                field=lower.replace(prefix,'c')
                if field not in {'c'+str(n) for n in range(1,16)}:unavailable('missing custom column '+field)
                return get(table,field)
    grouped([p for p in items('customAttributeFilter') if any(prefix in p['attributeName'].lower()
        for prefix in ('skulocattr','skuattr','locattr'))],custom)

    def matched(a,b,e,i,f):
        if not all(p(a,b,e,i,f) for p in constraints):return 0
        if not children:return 1
        parent=sql_key(b.get('ParentWhCode'))
        return sum(parent is not None and parent==sql_key(loc['WHCode']) and
            any(sql_key(loc['LocationType'])==sql_key(v) and sql_key(v) is not None for v in children)
            for loc in state['LocationAttributeData'])
    return matched
