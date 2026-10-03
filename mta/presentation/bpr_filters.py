"""BPR Commons filters over raw canonical join owners, before projection.

Authority: pinned deployed Commons filterQueryForReports(vf,a,a,c,d,sla).
Grid/count/analytics have no trend join; export does. Invalid legacy SQL is
reported as unavailable, never repaired into a different business predicate.
"""
from collections import defaultdict

from mta.presentation.context import PublicationUnavailable
from mta.presentation.rrr import sql_key
from mta.presentation.rrr_filters import OPERATORS, compare
from mta.runtime.relational_state import CATALOG


def unavailable(detail):
    raise PublicationUnavailable('LEG-BPR-FILTER-INVALID-SQL:' + detail)


class BprPredicate:
    def __init__(self, payload, locations, *, export=False):
        filters = payload.get('filters') or {}
        if not isinstance(filters, dict):
            raise ValueError('invalid_filter_groups')
        self.constraints, self.children, self.locations = [], [], locations
        schemas = dict(_a='BPR/BPR_Table', _vf='BPR/vf_RationedReqReport',
            _sku='Importer/SkuAttributeData', _location='Importer/LocationAttributeData',
            _pair='Importer/SkuLocAttributeData', _standard='Importer/SKULocStandardAttributes')
        if export:
            schemas['_trend'] = 'BTR/BufferTrendPhysicalInv'

        def items(group):
            value = filters.get(group)
            if value is None: return []
            if not isinstance(value, dict) or not isinstance(value.get('filters'), list):
                raise ValueError('invalid_filter_group')
            result = []
            for item in value['filters']:
                if not isinstance(item, dict): raise ValueError('invalid_filter')
                if item.get('attributeName') == '': continue
                if not isinstance(item.get('attributeName'), str) or not isinstance(item.get('value'), str):
                    unavailable('noncanonical attribute/value')
                result.append(item)
            return result

        def get(owner, field):
            candidates = [(table, name) for table, schema in schemas.items()
                if owner is None or table == owner
                for name, _ in CATALOG['tables'][schema] if name.casefold() == field.casefold()]
            if len(candidates) != 1:
                unavailable(('ambiguous' if candidates else 'missing') + ' column ' + field)
            table, name = candidates[0]
            return lambda row: row[table].get(name)

        def clause(getter, op, wanted):
            if op not in OPERATORS: unavailable('unknown deployed operator')
            def matched(row):
                try: return compare(getter(row), op, wanted)
                except PublicationUnavailable as exc: unavailable(str(exc).partition(':')[2])
            return matched

        def in_list(getter, values):
            self.constraints.append(lambda row: any(sql_key(getter(row)) == sql_key(value)
                and sql_key(value) is not None for value in values))

        def grouped(entries, mapper):
            groups = defaultdict(list)
            for item in entries: groups[item['attributeName']].append(item)
            for attribute, specs in groups.items():
                getter = mapper(attribute)
                predicates = [clause(getter, p.get('operator'), p['value']) for p in specs]
                self.constraints.append(lambda row, predicates=predicates: any(p(row) for p in predicates))

        supply = defaultdict(list)
        for item in items('supplyChainFilter'):
            supply[item['attributeName'].lower()].append(item['value'])
        for name, owner, field in (('forlocation',None,'LocationType'),
                ('forlocationlocationcode','_a','WhCode'),('forchildrenlocationcode','_a','ParentWhCode')):
            if supply[name]: in_list(get(owner, field), supply[name])
        self.children = supply['forchildren']

        for group, special, code in (('productFilter','sku','SKUCode'),
                                    ('locationFilter','location','WhCode')):
            entries = items(group)
            codes = [p['value'] for p in entries if p['attributeName'].lower() == special]
            if codes: in_list(get('_a', code), codes)
            def mapper(attribute, group=group):
                return get(None, attribute.replace('p','sl') if group == 'productFilter' else 'l'+attribute)
            grouped([p for p in entries if p['attributeName'].lower() != special], mapper)

        lists = defaultdict(list)
        for item in items('availabilityFilter'):
            name = item['attributeName'].lower()
            if name in ('norm','stock','git','availability','virtualnorm'):
                self.constraints.append(clause(get('_vf' if name == 'virtualnorm' else '_a', name),
                                               item.get('operator'), item['value']))
            elif name == 'category': unavailable('missing alias b for category')
            elif name in ('pic','ohic','pipo,seasonality'): lists[name].append(item['value'])
        for name, owner, field in (('pic','_vf','DispatchColor'),
                ('ohic','_vf','PhysicalInventoryColor'),('pipo,seasonality',None,'Tags')):
            if lists[name]: in_list(get(owner, field), lists[name])

        for item in items('colorFilter'):
            if item.get('type') == 'colorage': unavailable('missing alias btd')
            if item.get('type') == 'colorcount':
                names = ['BlackCount','RedCount'] if item['attributeName'] == 'black/red' else [item['attributeName']+'Count']
                predicates = [clause(get(None, name), item.get('operator'), item['value']) for name in names]
                self.constraints.append(lambda row, predicates=predicates: any(p(row) for p in predicates))
        coverage = [p['value'] for p in items('coverageFilter') if p['attributeName'].lower() == 'coverage']
        if coverage: in_list(get(None, 'coverage'), coverage)

        custom = [p for p in items('customAttributeFilter')
                  if any(prefix in p['attributeName'].lower() for prefix in ('skulocattr','skuattr','locattr'))]
        def custom_mapper(attribute):
            lower = attribute.lower()
            for prefix, owner in (('skulocattr','_pair'),('skuattr','_sku'),('locattr','_location')):
                if prefix in lower: return get(owner, lower.replace(prefix,'c'))
        grouped(custom, custom_mapper)

    def __call__(self, row):
        if not all(predicate(row) for predicate in self.constraints): return 0
        if not self.children: return 1
        parent = sql_key(row['_a']['ParentWhCode'])
        return sum(parent is not None and parent == sql_key(loc['WHCode'])
            and any(sql_key(loc['LocationType']) == sql_key(value) and sql_key(value) is not None
                    for value in self.children) for loc in self.locations)

    def select(self, rows):
        return [row for row in rows for _ in range(self(row))]
