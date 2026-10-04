"""Guided Commons filters on native join owners, before aggregation.

Alias/call gates are captured from the pinned DLL in Guided*-filters.json.
Missing and ambiguous SQL columns stay unavailable, including on empty inputs.
"""
from collections import defaultdict

from mta.presentation.context import PublicationUnavailable
from mta.presentation.rrr import sql_key
from mta.presentation.rrr_filters import OPERATORS, compare
from mta.runtime.relational_state import CATALOG
from mta.presentation.excess import FIELDS as EXCESS_FIELDS


class InsightFilterUnavailable(PublicationUnavailable):
    """Canonical processor SQL failure, distinct from missing publication data."""


def unavailable(detail):
    raise InsightFilterUnavailable('LEG-GUIDED-FILTER-INVALID-SQL:' + detail)


class InsightPredicate:
    def __init__(self, payload, locations, *, kind):
        excess = kind in ('excess-sku', 'excess-value')
        nested = excess or kind in ('availability-trend', 'availability-ageing', 'chronic-grid')
        filters = (payload.get('filters') or {}) if nested else payload
        if not isinstance(filters, dict):
            raise ValueError('invalid_filter_groups')
        self.constraints, self.children, self.locations = [], [], locations
        self.sql_terms = []
        self.parent_owner = '_master' if kind in ('loc', 'sku', 'pie', 'ageing') else '_a'
        if not any(filters.get(group) is not None for group in (
                'availabilityFilter', 'supplyChainFilter', 'coverageFilter',
                'productFilter', 'locationFilter', 'colorFilter')):
            return
        schemas = dict(_sku='BTR/SkuAttributeData', _location='BTR/LocationAttributeData',
                       _pair='BTR/SkuLocAttributeData')
        if excess:
            schemas = {owner: name.replace('BTR/', 'Importer/') for owner, name in schemas.items()}
        schemas['_a'] = ('BTR/BPR' if kind.startswith('availability-') else
            'BTR/ChronicUnavalabilityData' if kind.startswith('chronic-') else
            'BTR/DBMNormSuggestionsData')
        if kind == 'availability-ageing':
            schemas['_snapshot'] = 'BTR/BTRSnapshotForUI'
        if kind == 'chronic-grid':
            schemas['_description'] = 'Importer/NMSAllItems'
        elif kind.endswith('loc'):
            schemas['_description'] = 'BTR/SiteDescriptionTbl'
        elif kind.endswith('sku') and not excess:
            schemas['_description'] = 'BTR/SKUDescriptionTbl'
        if self.parent_owner == '_master':
            schemas['_master'] = 'DBM/DBMMaster'
        columns = {owner: [name for name, _ in CATALOG['tables'][schema]] for owner, schema in schemas.items()}
        if excess:
            columns['_a'] = EXCESS_FIELDS
        # Commons emits b.category literally, independently of its attribute aliases.
        category_owner = ('_location' if kind in ('loc', 'pie', 'chronic-loc', 'availability-trend')
            else '_sku' if kind in ('sku', 'ageing', 'chronic-sku')
            else '_snapshot' if kind == 'availability-ageing' else '_description')
        if excess:
            category_owner = '_location'

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
            candidates = [(table, name) for table, names in columns.items()
                if owner is None or table == owner
                for name in names if name.casefold() == field.casefold()]
            if len(candidates) != 1:
                unavailable(('ambiguous' if candidates else 'missing') + ' column ' + field)
            table, name = candidates[0]
            getter = lambda row: row[table].get(name)
            getter.column = (table, name)
            return getter

        def clause(getter, op, wanted):
            if op not in OPERATORS: unavailable('unknown deployed operator')
            def matched(row):
                try: return compare(getter(row), op, wanted)
                except PublicationUnavailable as exc: unavailable(str(exc).partition(':')[2])
            matched.term = ('compare', getter.column, op, wanted)
            return matched

        def add(matched, term=None):
            self.constraints.append(matched)
            self.sql_terms.append(matched.term if term is None else term)

        def in_list(getter, values):
            add(lambda row: any(sql_key(getter(row)) == sql_key(value)
                and sql_key(value) is not None for value in values), ('in', getter.column, values))

        def grouped(entries, mapper):
            groups = defaultdict(list)
            for item in entries: groups[item['attributeName']].append(item)
            for attribute, specs in groups.items():
                getter = mapper(attribute)
                predicates = [clause(getter, p.get('operator'), p['value']) for p in specs]
                add(lambda row, predicates=predicates: any(p(row) for p in predicates),
                    ('or', [p.term for p in predicates]))

        supply = defaultdict(list)
        for item in items('supplyChainFilter'):
            supply[item['attributeName'].lower()].append(item['value'])
        for name, owner, field in (('forlocation',None,'LocationType'),
                ('forlocationlocationcode','_a','WhCode'),('forchildrenlocationcode',self.parent_owner,'ParentWhCode')):
            if supply[name]: in_list(get(owner, field), supply[name])
        self.children = supply['forchildren']
        if self.children: get(self.parent_owner, 'ParentWhCode')

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
                add(clause(get(None, name),
                                               item.get('operator'), item['value']))
            elif name == 'category':
                add(clause(get(category_owner, 'category'), item.get('operator'), item['value']))
            elif name in ('pic','ohic','pipo,seasonality'): lists[name].append(item['value'])
        for name, owner, field in (('pic',None,'pic'),
                ('ohic',None,'ohic'),('pipo,seasonality',None,'Tags')):
            if lists[name]: in_list(get(owner, field), lists[name])

        for item in items('colorFilter'):
            if item.get('type') == 'colorage': unavailable('missing alias btd')
            if item.get('type') == 'colorcount':
                names = ['BlackCount','RedCount'] if item['attributeName'] == 'black/red' else [item['attributeName']+'Count']
                predicates = [clause(get(None, name), item.get('operator'), item['value']) for name in names]
                add(lambda row, predicates=predicates: any(p(row) for p in predicates),
                    ('or', [p.term for p in predicates]))
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
        parent = sql_key(row[self.parent_owner].get('ParentWhCode'))
        return sum(parent is not None and parent == sql_key(loc['WHCode'])
            and any(sql_key(loc['LocationType']) == sql_key(value) and sql_key(value) is not None
                    for value in self.children) for loc in self.locations)

    def select(self, rows):
        return [row for row in rows for _ in range(self(row))]
