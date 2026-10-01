"""Deployed BTR Commons predicates before key paging, preserving raw join bags.

Count E is the full rationed report; grid E has only five requirement fields.
Source-invalid filters are guarded, not repaired or scored as parity.
"""
from collections import defaultdict
from mta.presentation.context import PublicationUnavailable
from mta.presentation.rrr import sql_key
from mta.presentation.rrr_filters import OPERATORS, compare, sql_like


def unavailable(detail):
    raise PublicationUnavailable('LEG-BTR-FILTER-INVALID-SQL:'+detail)


class BtrPredicate:
    def __init__(self,payload,locations,*,count=False):
        filters=payload.get('filters') or {}
        if not isinstance(filters,dict): raise ValueError('invalid_filter_groups')
        self.constraints=[]; self.children=[]; self.locations=locations

        def items(group):
            value=filters.get(group)
            if value is None: return []
            if not isinstance(value,dict) or not isinstance(value.get('filters'),list):
                raise ValueError('invalid_filter_group')
            result=[]
            for item in value['filters']:
                if not isinstance(item,dict): raise ValueError('invalid_filter')
                if item.get('attributeName')=='': continue
                if not isinstance(item.get('attributeName'),str) or not isinstance(item.get('value'),str):
                    unavailable('noncanonical attribute/value')
                result.append(item)
            return result

        def get(table,field):
            def value(row):
                values=row[table]
                key=next((k for k in values if k.casefold()==field.casefold()),None)
                return values[key] if key is not None else None
            return value

        def operator(op):
            if op not in OPERATORS: unavailable('unknown deployed operator')
            return op

        def predicate(getter,op,wanted):
            op=operator(op)
            def matched(row):
                try: return compare(getter(row),op,wanted)
                except PublicationUnavailable as exc: unavailable(str(exc).partition(':')[2])
            return matched

        def in_list(getter,values):
            self.constraints.append(lambda row:any(sql_key(getter(row))==sql_key(v)
                and sql_key(v) is not None for v in values))

        def grouped(entries,mapper):
            groups=defaultdict(list)
            for item in entries: groups[item['attributeName']].append(item)
            for attribute,specs in groups.items():
                getter=mapper(attribute)
                clauses=[predicate(getter,p.get('operator'),p['value']) for p in specs]
                self.constraints.append(lambda row,clauses=clauses:any(p(row) for p in clauses))

        supply=defaultdict(list)
        for item in items('supplyChainFilter'): supply[item['attributeName'].lower()].append(item['value'])
        for name,table,column in (('forlocation','_la','LocationType'),('forlocationlocationcode','_bpp','WhCode'),
                                  ('forchildrenlocationcode','_req','ParentWhCode')):
            if supply[name]: in_list(get(table,column),supply[name])
        self.children=supply['forchildren']

        for group,special,code,table in (('productFilter','sku','SKUCode','_sa'),
                                       ('locationFilter','location','WhCode','_la')):
            entries=items(group)
            codes=[p['value'] for p in entries if p['attributeName'].lower()==special]
            if codes: in_list(get('_bpp',code),codes)
            def mapper(attribute,group=group,table=table):
                field=attribute.replace('p','sl') if group=='productFilter' else 'l'+attribute
                if field.casefold() not in {('sl' if group=='productFilter' else 'll')+str(i) for i in range(1,6)}:
                    unavailable('missing hierarchy column '+field)
                return get(table,field)
            grouped([p for p in entries if p['attributeName'].lower()!=special],mapper)

        lists=defaultdict(list)
        for item in items('availabilityFilter'):
            name=item['attributeName'].lower()
            if name in ('norm','stock','git','virtualnorm'):
                if not count and name in ('stock','git'): unavailable('grid E has no '+name)
                self.constraints.append(predicate(get('_req',name),item.get('operator'),item['value']))
            elif name in ('pic','ohic','category','pipo,seasonality'): lists[name].append(item['value'])
            elif name=='availability': unavailable('E has no availability')
        for name,column in (('pic','DispatchColor'),('ohic','PhysicalInventoryColor')):
            if lists[name]:
                if not count: unavailable('grid E has no '+column)
                in_list(get('_req',column),lists[name])
        if lists['pipo,seasonality']: in_list(get('_standard','Tags'),lists['pipo,seasonality'])
        if lists['category']:
            categories=lists['category']; getter=get('_standard','Category')
            self.constraints.append(lambda row:getter(row) is not None and
                any(sql_like(getter(row),'%'+value+'%') for value in categories))

        for item in items('colorFilter'):
            attribute=item['attributeName']; op=operator(item.get('operator')); wanted=item['value']
            colours=('black','red') if attribute=='black/red' else (attribute.lower(),)
            if any(c not in ('black','red','yellow','green','blue','white') for c in colours):
                unavailable('missing colour column '+attribute)
            if item.get('type')=='colorage':
                age=predicate(get('_trend','Age'),op,wanted); colour=get('_trend','D90')
                self.constraints.append(lambda row,age=age,colour=colour,colours=colours:
                    any(sql_key(colour(row))==sql_key(c) for c in colours) and age(row))
            elif item.get('type')=='colorcount':
                if attribute=='black/red' and op in ('hasvalue','hasnovalue','notequalto',
                    'doesnotcontain','doesnotstartwith','doesnotendwith'):
                    unavailable('deployed OR token repeated inside multi-column operator')
                clauses=[predicate(get('_trend',c+'Count'),op,wanted) for c in colours]
                self.constraints.append(lambda row,clauses=clauses:any(p(row) for p in clauses))
            else: unavailable('invalid colour type')
        if any(p['attributeName'].lower()=='coverage' for p in items('coverageFilter')):
            unavailable('BTR has no coverage column')

        def mapper(attribute):
            lower=attribute.lower()
            for prefix,table in (('skulocattr','_sla'),('skuattr','_sa'),('locattr','_la')):
                if prefix in lower:
                    field=lower.replace(prefix,'c')
                    if field not in {'c'+str(i) for i in range(1,16)}: unavailable('missing custom column '+field)
                    return get(table,field)
        grouped([p for p in items('customAttributeFilter') if any(prefix in p['attributeName'].lower()
            for prefix in ('skulocattr','skuattr','locattr'))],mapper)

    def join_multiplicity(self,row):
        if not self.children: return 1
        parent=sql_key(row['_req'].get('ParentWhCode'))
        return sum(parent is not None and parent==sql_key(loc['WHCode']) and
            any(sql_key(loc['LocationType'])==sql_key(v) and sql_key(v) is not None for v in self.children)
            for loc in self.locations)

    def __call__(self,row):
        return self.join_multiplicity(row) if all(p(row) for p in self.constraints) else 0
