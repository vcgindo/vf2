"""RRR-only deployed Commons filter semantics on pre-SELECT joined values.

Authority: DLL0222eb..., CommonsProcessor6a79e4cd..., GenericFunction6850a0bf...
Do not filter ISNULL display aliases or change calculation/report populations.
Other report aliases/joins need their own acceptance before reusing this adapter.
"""
from collections import defaultdict
from decimal import Decimal, InvalidOperation
import re

from mta.presentation.context import PublicationUnavailable
from mta.presentation.rrr import sql_key


OPERATORS = frozenset(('equalto','notequalto','greaterthan','greaterthanequalto',
    'smallerthan','smallerthanequalto','contains','doesnotcontain','startswith',
    'doesnotstartwith','endswith','doesnotendwith','hasvalue','hasnovalue'))


def unavailable(detail):
    raise PublicationUnavailable('LEG-RRR-FILTER-INVALID-SQL:' + detail)


def sql_like(value, pattern):
    """Selected case-insensitive SQL LIKE, retaining %, _, bracket patterns."""
    parts, i = [], 0
    while i < len(pattern):
        char = pattern[i]
        if char == '%': parts.append('.*')
        elif char == '_': parts.append('.')
        elif char == '[':
            end = pattern.find(']', i + 2 if pattern[i+1:i+2] == ']' else i + 1)
            if end == -1: parts.append(r'\[')
            else:
                content = pattern[i+1:end]
                negate = '^' if content.startswith('^') else ''
                content = content[1:] if negate else content
                parts.append('[' + negate + content.replace('\\',r'\\') + ']')
                i = end
        else: parts.append(re.escape(char))
        i += 1
    return re.fullmatch(''.join(parts), str(value), flags=re.IGNORECASE|re.DOTALL) is not None


def compare(actual, operator, wanted):
    if operator not in OPERATORS:
        unavailable('unknown deployed operator')
    numeric = isinstance(actual, (int, float, Decimal)) and not isinstance(actual, bool)
    if operator in ('hasvalue','hasnovalue'):
        empty = actual is None or (actual == 0 if numeric else str(actual).rstrip(' ') == '')
        return not empty if operator == 'hasvalue' else empty
    if operator in ('contains','doesnotcontain','startswith','doesnotstartwith','endswith','doesnotendwith'):
        if actual is None: return operator.startswith('doesnot')
        pattern = (wanted+'%' if operator.endswith('startwith') or operator=='startswith' else
                   '%'+wanted if operator.endswith('endwith') or operator=='endswith' else '%'+wanted+'%')
        matched = sql_like(actual, pattern)
        return not matched if operator.startswith('doesnot') else matched
    if actual is None: return operator == 'notequalto'
    if numeric or operator in ('greaterthan','greaterthanequalto','smallerthan','smallerthanequalto'):
        try:
            left, right = Decimal(str(actual)), Decimal(wanted)
            if not left.is_finite() or not right.is_finite(): raise InvalidOperation
        except (InvalidOperation, ValueError):
            unavailable('canonical numeric conversion')
        # Quoted equality to an INT is an INT conversion in SQL, not DECIMAL.
        if isinstance(actual,int) and operator in ('equalto','notequalto') and right!=right.to_integral_value():
            unavailable('canonical INT conversion')
    else:
        left, right = str(actual).rstrip(' ').casefold(), wanted.rstrip(' ').casefold()
    return {'equalto':lambda:left==right,'notequalto':lambda:left!=right,
        'greaterthan':lambda:left>right,'greaterthanequalto':lambda:left>=right,
        'smallerthan':lambda:left<right,'smallerthanequalto':lambda:left<=right}[operator]()


def rrr_predicate(payload, importer):
    """Return matched join multiplicity over raw A/B/C/D before SELECT aliases.

The deployed dictionaries group by exact attribute spelling (OR), then AND.
Supply-chain/explicit-code/color lists use IN and disregard their operator.
ForChildren is an additional parent-location join, not an existence shortcut.
"""
    filters = payload.get('filters') or {}
    if not isinstance(filters,dict): raise ValueError('invalid_filter_groups')
    constraints, children = [], []

    def items(group):
        value=filters.get(group)
        if value is None: return []
        if not isinstance(value,dict) or not isinstance(value.get('filters'),list):
            raise ValueError('invalid_filter_group')
        result=[]
        for item in value['filters']:
            if not isinstance(item,dict): raise ValueError('invalid_filter')
            if item.get('attributeName') == '': continue
            if not isinstance(item.get('attributeName'),str) or not isinstance(item.get('value'),str):
                unavailable('noncanonical attribute/value')
            result.append(item)
        return result

    def get(table, field):
        def value(a,b,c,d):
            values=(a,b,c,d)[table]
            key=next((k for k in values if k.casefold()==field.casefold()),None)
            if key is None: unavailable('missing column '+field)
            return values[key]
        return value

    def in_list(getter, values):
        constraints.append(lambda a,b,c,d: any(sql_key(getter(a,b,c,d))==sql_key(v)
            and sql_key(v) is not None for v in values))

    supply=defaultdict(list)
    for item in items('supplyChainFilter'):
        supply[item['attributeName'].lower()].append(item['value'])
    for name,table,column in (('forlocation',3,'LocationType'),('forlocationlocationcode',0,'WhCode'),
                              ('forchildrenlocationcode',0,'ParentWhCode')):
        if supply[name]: in_list(get(table,column),supply[name])
    children=supply['forchildren']

    def grouped(entries, field_mapper):
        groups=defaultdict(list)
        for item in entries: groups[item['attributeName']].append(item)
        for attribute, predicates in groups.items():
            getter=field_mapper(attribute)
            specs=[(p.get('operator'),p['value']) for p in predicates]
            if any(op not in OPERATORS for op,_ in specs): unavailable('unknown deployed operator')
            constraints.append(lambda a,b,c,d,getter=getter,specs=specs:
                any(compare(getter(a,b,c,d),op,value) for op,value in specs))

    for group,special,code in (('productFilter','sku','SKUCode'),('locationFilter','location','WhCode')):
        entries=items(group)
        codes=[p['value'] for p in entries if p['attributeName'].lower()==special]
        if codes: in_list(get(0,code),codes)
        attributes=[p for p in entries if p['attributeName'].lower()!=special]
        def mapper(attribute,group=group):
            field=attribute.replace('p','sl') if group=='productFilter' else 'l'+attribute
            if field.casefold() not in {('sl' if group=='productFilter' else 'll')+str(i) for i in range(1,6)}:
                unavailable('missing hierarchy column '+field)
            return get(2 if group=='productFilter' else 3,field)
        grouped(attributes,mapper)

    lists=defaultdict(list)
    for item in items('availabilityFilter'):
        name=item['attributeName'].lower()
        if name in ('norm','stock','git','virtualnorm'):
            getter=get(0,name)
            op=item.get('operator')
            if op not in OPERATORS: unavailable('unknown deployed operator')
            constraints.append(lambda a,b,c,d,getter=getter,op=op,wanted=item['value']:
                               compare(getter(a,b,c,d),op,wanted))
        elif name in ('pic','ohic'): lists[name].append(item['value'])
        elif name in ('category','pipo,seasonality','availability'):
            unavailable('missing RRR column '+name)
    for name,column in (('pic','DispatchColor'),('ohic','PhysicalInventoryColor')):
        if lists[name]: in_list(get(0,column),lists[name])
    if items('colorFilter'): unavailable('RRR has no btd/Age/color-count join')
    if any(i['attributeName'].lower()=='coverage' for i in items('coverageFilter')):
        unavailable('RRR has no coverage column')

    custom=[]
    for item in items('customAttributeFilter'):
        attribute=item['attributeName'].lower()
        if any(prefix in attribute for prefix in ('skulocattr','skuattr','locattr')): custom.append(item)
    def custom_mapper(attribute):
        lower=attribute.lower()
        for prefix,table in (('skulocattr',1),('skuattr',2),('locattr',3)):
            if prefix in lower:
                field=lower.replace(prefix,'c')
                if field not in {'c'+str(i) for i in range(1,16)}: unavailable('missing custom column '+field)
                return get(table,field)
    grouped(custom,custom_mapper)

    def matched(a,b,c,d):
        if not all(predicate(a,b,c,d) for predicate in constraints): return 0
        if not children: return 1
        return sum(sql_key(a['ParentWhCode'])==sql_key(loc['WHCode']) and
            any(sql_key(loc['LocationType'])==sql_key(v) and sql_key(v) is not None for v in children)
            for loc in importer['LocationAttributeData'] if sql_key(a['ParentWhCode']) is not None)
    return matched
