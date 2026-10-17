"""SCIH colour graph over selected typed history rows; no calculation or cache.

Authority: SCIH f709a448 / deployed DLL0222eb96. Preserve the filter call gate,
join multiplicity and unparenthesized BlackCount OR RedCount expression.
"""
from collections import defaultdict
from django.conf import settings
from django.db import connection
from mta.presentation import hierarchy
from mta.presentation.context import PublicationUnavailable, permission_catalogue, scope
from mta.presentation.dbm_filters import STANDARD_GROUPS
from mta.presentation.history_native import COLOURS, graph_response
from mta.presentation.rrr_sql import Filters, equal
from mta.presentation.selective import image_query, image_rows
from mta.runtime.relational_state import CATALOG, quote


def unavailable(detail):
    raise PublicationUnavailable('LEG-BUFFER-TRENDS-FILTER-INVALID-SQL:' + detail)


class GraphFilters(Filters):
    def column(self, owner, name):
        table = {'A': 'BufferTrendPhysicalInv', 'sa': 'SkuAttributeData',
                 'la': 'LocationAttributeData', 'sla': 'SkuLocAttributeData'}[owner]
        fields = {n.casefold(): (n, t) for n, t in CATALOG['tables']['BTR/' + table]}
        if name.casefold() not in fields:
            unavailable('missing column ' + name)
        actual, kind = fields[name.casefold()]
        return owner + '.' + quote(actual), kind

    def items(self, group):
        value = self.groups.get(group)
        if value is None:
            return []
        if not isinstance(value, dict) or not isinstance(value.get('filters'), list):
            raise ValueError('invalid_filter_group')
        for row in value['filters']:
            if not isinstance(row, dict) or not isinstance(row.get('attributeName'), str):
                raise ValueError('invalid_filter')
            if row['attributeName'] and not isinstance(row.get('value'), str):
                unavailable('noncanonical attribute/value')
        return [row for row in value['filters'] if row['attributeName']]

    def compile(self):
        if not isinstance(self.groups, dict):
            raise ValueError('invalid_filter_groups')
        if not any(self.groups.get(name) is not None for name in STANDARD_GROUPS):
            return 'TRUE'
        supply = defaultdict(list)
        for item in self.items('supplyChainFilter'):
            supply[item['attributeName'].lower()].append(item['value'])
        for name, owner, field in (('forlocation', 'la', 'LocationType'),
                ('forlocationlocationcode', 'A', 'WhCode'), ('forchildrenlocationcode', 'A', 'ParentWhCode')):
            self.in_list(owner, field, supply[name])
        self.children = supply['forchildren']
        # Source order matters for the bare BlackCount OR RedCount clause.
        for group, special, code, owner in (('locationFilter', 'location', 'WhCode', 'la'),
                                            ('productFilter', 'sku', 'SKUCode', 'sa')):
            items = self.items(group)
            codes = [i['value'] for i in items if i['attributeName'].lower() == special]
            if group == 'locationFilter':
                self.in_list('A', code, codes)
            self.grouped([i for i in items if i['attributeName'].lower() != special],
                lambda name, group=group, owner=owner: (owner, name.replace('p', 'sl')
                    if group == 'productFilter' else 'l' + name))
            if group == 'productFilter':
                self.in_list('A', code, codes)
        for item in self.items('availabilityFilter'):
            name = item['attributeName'].lower()
            if name in ('norm', 'virtualnorm'):
                self.where.append(self.compare('A', name, item.get('operator'), item['value']))
            elif name in ('stock', 'git', 'availability', 'pic', 'ohic', 'category', 'pipo,seasonality'):
                unavailable('missing selected graph column/alias ' + name)
        for item in self.items('colorFilter'):
            if item.get('type') == 'colorage':
                unavailable('deployed graph has no btd alias')
            if item.get('type') == 'colorcount':
                if item['attributeName'] == 'black/red':
                    if item.get('operator') not in ('equalto', 'greaterthan', 'greaterthanequalto',
                            'smallerthan', 'smallerthanequalto', 'startswith', 'endswith'):
                        unavailable('invalid OR RedCount expression')
                    self.where.append(self.compare('A', 'BlackCount', item.get('operator'), item['value']) +
                        ' OR ' + self.compare('A', 'RedCount', item.get('operator'), item['value']))
                else:
                    self.where.append(self.compare('A', item['attributeName'] + 'Count', item.get('operator'), item['value']))
            elif self.where:
                unavailable('dangling AND for unknown colour filter type')
        if any(i['attributeName'].lower() == 'coverage' for i in self.items('coverageFilter')):
            unavailable('missing column coverage')
        def custom(name):
            for prefix, owner in (('skulocattr', 'sla'), ('skuattr', 'sa'), ('locattr', 'la')):
                if prefix in name.lower():
                    return owner, name.lower().replace(prefix, 'c')
        self.grouped([i for i in self.items('customAttributeFilter') if any(p in i['attributeName'].lower()
            for p in ('skulocattr', 'skuattr', 'locattr'))], custom)
        return ' AND '.join(self.where) or 'TRUE'


def read_graph(run, payload):
    days = int(payload.get('Days', payload.get('days', 90)))
    if not 1 <= days <= 90:
        raise ValueError('Buffer graph days outside retained columns')
    columns = tuple((f'D{i}' for i in range(91 - days, 91)))
    filters = GraphFilters(payload)
    try:
        where = filters.compile()
    except PublicationUnavailable as exc:
        unavailable(str(exc).partition(':')[2])
    metadata = None

    def rows(name):
        path = 'closing/btr/' + name
        return image_rows(run, path, **{} if metadata is None else {'metadata': metadata[path]})
    attributes = {name: rows(name) for name in ('SkuAttributeData', 'LocationAttributeData')}
    try:
        manifest = hierarchy.selected_manifest(run)
        if manifest:
            attributes = hierarchy.project_attributes(attributes, permission_catalogue(), manifest)
    except hierarchy.HierarchyUnavailable as exc:
        raise PublicationUnavailable(str(exc)) from exc
    products, locations = scope(payload, attributes=attributes)
    dates = rows('BufferTrendDates')
    from mta.presentation import history_prepared_sql
    if history_prepared_sql.admitted(run) is not None:
        return history_prepared_sql.read_graph(run, payload, columns=columns, filters=filters, where=where, attributes=attributes, manifest=manifest, products=products, locations=locations, dates=dates, **{} if metadata is None else {'metadata': metadata})
    if not products or not locations:
        return graph_response([dict(D=c, **{a: None for a, _ in COLOURS}) for c in columns], dates)
    ctes, values = ([], [])

    def add(alias, query, params):
        ctes.append(alias + ' AS (' + query + ')')
        values.extend(params)

    def image(alias, name):
        query, params = image_query(run, 'closing/btr/' + name)
        add(alias, query, params)
    kind = 'Dispatch' if str(payload.get('bufferTrendType', 'tech')).lower() == 'eco' else 'PhysicalInv'
    image('A', 'BufferTrend' + kind)
    image('sla', 'SkuLocAttributeData')
    for alias, table, prefix in (('sa', 'SkuAttributeData', 'SL'), ('la', 'LocationAttributeData', 'LL')):
        if not manifest:
            image(alias, table)
            continue
        image(alias + 'native', table)
        rows = attributes[table]
        add(alias + 'hierarchy', 'VALUES ' + ','.join(['(%s,%s,%s,%s)'] * len(rows)), [v for ordinal, row in enumerate(rows) for v in (ordinal, *[row[prefix + str(i)] for i in (1, 2, 3)])])
        fields = [n for n, _ in CATALOG['tables']['BTR/' + table] if n not in [prefix + str(i) for i in (1, 2, 3)]]
        add(alias, 'SELECT ' + ','.join(('N.' + quote(n) for n in fields)) + ',' + ','.join(('H.column' + str(i + 1) + ' AS ' + quote(prefix + str(i)) for i in (1, 2, 3))) + ' FROM ' + alias + 'native N JOIN ' + alias + 'hierarchy H ON N.vf_ordinal=H.column1', [])
    for alias, codes in (('P', products), ('L', locations)):
        members = [code for code in sorted(codes) for _ in range(codes.multiplicities[code])]
        add(alias, 'VALUES ' + ','.join(['(%s)'] * len(members)), members)
    joins = ' JOIN P ON ' + equal('A."SKUCode"', 'P.column1') + ' JOIN L ON ' + equal('A."WhCode"', 'L.column1') + ' JOIN sa ON ' + equal('A."SKUCode"', 'sa."SKUCode"') + ' JOIN la ON ' + equal('A."WhCode"', 'la."WHCode"') + ' LEFT JOIN sla ON ' + equal('A."SKUCode"', 'sla."SKUCode"') + ' AND ' + equal('A."WhCode"', 'sla."LocCode"')
    if filters.children:
        joins += ' JOIN la parent ON ' + equal('A."ParentWhCode"', 'parent."WHCode"') + ' AND (' + ' OR '.join((equal('parent."LocationType"', '%s') for _ in filters.children)) + ')'
        values.extend(filters.children)
    projection = ','.join(('sum(CASE WHEN ' + equal('A.' + quote(c), "'" + colour + "'") + ' THEN 1 ELSE 0 END)::integer' for c in columns for _, colour in COLOURS))
    with connection.cursor() as cursor:
        cursor.execute('WITH ' + ','.join(ctes) + ' SELECT ' + projection + ' FROM A' + joins + ' WHERE ' + where, values + filters.params)
        totals = cursor.fetchone()
    counts = [dict(D=c, **{a: totals[i * 6 + j] for j, (a, _) in enumerate(COLOURS)}) for i, c in enumerate(columns)]
    return graph_response(counts, dates)
