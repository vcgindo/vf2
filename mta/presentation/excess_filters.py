"""Planning Excess's deployed Commons filterQuery(sa,la,sla) contract."""
from collections import defaultdict

from mta.presentation.context import PublicationUnavailable
from mta.presentation.dbm_filters import STANDARD_GROUPS
from mta.presentation.rrr import sql_key
from mta.presentation.rrr_filters import OPERATORS, compare


def unavailable(detail):
    raise PublicationUnavailable('LEG-EXCESS-FILTER-INVALID-SQL:' + detail)


def predicate(payload, importer):
    filters = payload.get('filters') or {}
    if not isinstance(filters, dict):
        raise ValueError('invalid_filter_groups')
    if not any(filters.get(group) is not None for group in STANDARD_GROUPS):
        return lambda a, pair, sku, loc: 1
    constraints = []

    def items(group):
        value = filters.get(group)
        if value is None:
            return []
        if not isinstance(value, dict) or not isinstance(value.get('filters'), list):
            raise ValueError('invalid_filter_group')
        rows = []
        for item in value['filters']:
            if not isinstance(item, dict):
                raise ValueError('invalid_filter')
            if item.get('attributeName') == '':
                continue
            if not isinstance(item.get('attributeName'), str) or not isinstance(item.get('value'), str):
                unavailable('noncanonical attribute/value')
            rows.append(item)
        return rows

    def get(owner, field):
        def value(*rows):
            row = rows[owner]
            key = next((k for k in row if k.casefold() == field.casefold()), None)
            if key is None:
                unavailable('missing column ' + field)
            return row[key]
        return value

    def clause(getter, operator, wanted):
        if operator not in OPERATORS:
            unavailable('unknown deployed operator')
        def matched(*rows):
            try:
                return compare(getter(*rows), operator, wanted)
            except PublicationUnavailable as exc:
                unavailable(str(exc).partition(':')[2])
        return matched

    def in_list(getter, values):
        if values:
            constraints.append(lambda *rows: any(sql_key(getter(*rows)) == sql_key(v)
                and sql_key(v) is not None for v in values))

    def grouped(entries, mapper):
        groups = defaultdict(list)
        for item in entries:
            groups[item['attributeName']].append(item)
        for name, specs in groups.items():
            getter = mapper(name)
            clauses = [clause(getter, item.get('operator'), item['value']) for item in specs]
            constraints.append(lambda *rows, clauses=clauses: any(c(*rows) for c in clauses))

    supply = defaultdict(list)
    for item in items('supplyChainFilter'):
        supply[item['attributeName'].lower()].append(item['value'])
    for name, owner, field in (('forlocation', 3, 'LocationType'), ('forlocationlocationcode', 0, 'WhCode'),
                                ('forchildrenlocationcode', 0, 'ParentWhCode')):
        in_list(get(owner, field), supply[name])
    for group, special, code, owner in (('locationFilter', 'location', 'WhCode', 3),
                                        ('productFilter', 'sku', 'SKUCode', 2)):
        entries = items(group)
        in_list(get(0, code), [i['value'] for i in entries if i['attributeName'].lower() == special])
        def mapper(name, group=group, owner=owner):
            field = name.replace('p', 'sl') if group == 'productFilter' else 'l' + name
            if field.lower() not in {('sl' if owner == 2 else 'll') + str(i) for i in range(1, 6)}:
                unavailable('missing hierarchy column ' + field)
            return get(owner, field)
        grouped([i for i in entries if i['attributeName'].lower() != special], mapper)
    availability = items('availabilityFilter')
    for item in availability:
        name = item['attributeName'].lower()
        if name in ('norm', 'stock', 'git', 'virtualnorm'):
            constraints.append(clause(get(0, name), item.get('operator'), item['value']))
        elif name in ('availability', 'category'):
            unavailable('missing selected Excess column/alias ' + name)
    for name, field in (('pic', 'PipelineInventoryColor'), ('ohic', 'PhysicalInventoryColor'),
                        ('pipo,seasonality', 'Tags')):
        in_list(get(0, field), [i['value'] for i in availability if i['attributeName'].lower() == name])
    for item in items('colorFilter'):
        if item.get('type') in ('colorage', 'colorcount'):
            unavailable('missing btd/Age/colour-count column')
        if constraints:
            unavailable('dangling AND for unknown colour filter type')
    if any(i['attributeName'].lower() == 'coverage' for i in items('coverageFilter')):
        unavailable('missing column coverage')
    def custom(name):
        for prefix, owner in (('skulocattr', 1), ('skuattr', 2), ('locattr', 3)):
            if prefix in name.lower():
                field = name.lower().replace(prefix, 'c')
                if field not in {'c'+str(i) for i in range(1, 16)}:
                    unavailable('missing custom column ' + field)
                return get(owner, field)
    grouped([i for i in items('customAttributeFilter') if any(p in i['attributeName'].lower()
        for p in ('skulocattr', 'skuattr', 'locattr'))], custom)

    def matched(a, pair, sku, loc):
        if not all(c(a, pair, sku, loc) for c in constraints):
            return 0
        if not supply['forchildren']:
            return 1
        parent = sql_key(a['ParentWhCode'])
        return sum(parent is not None and parent == sql_key(row['WHCode']) and
            any(sql_key(row['LocationType']) == sql_key(v) and sql_key(v) is not None for v in supply['forchildren'])
            for row in importer['LocationAttributeData'])
    return matched
