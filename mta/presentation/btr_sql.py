"""Selected BTR count/key-page/rejoin queries over typed persisted relations.

BORProcessor source80ceb491 / deployed DLL0222eb96. Keep count's full report E
distinct from grid's five-field requirement projection. No whole-run reader,
other-branch grid work, calculation, cache, or new ordering for tied keys.
"""
from collections import defaultdict
from contextlib import nullcontext

from django.db import connection, transaction

from mta.presentation import btr, hierarchy
from mta.presentation.btr_filters import BtrPredicate, unavailable
from mta.presentation.context import PublicationUnavailable, permission_catalogue, scope
from mta.presentation.rrr_sql import Filters, equal, key, like_pattern
from mta.presentation.selective import image_query, image_rows
from mta.runtime.relational_state import CATALOG, quote


class BtrFilters(Filters):
    def column(self, owner, name):
        table = {'A': 'BTR/BPPTrendPhysicalInv', 'btd': 'BTR/BufferTrendPhysicalInv',
                 'E': 'BPR/vf_RationedReqReport', 'B': 'Importer/SKULocStandardAttributes',
                 'sa': 'BTR/SkuAttributeData', 'la': 'BTR/LocationAttributeData',
                 'sla': 'BTR/SkuLocAttributeData'}[owner]
        fields = {n.casefold(): (n, t) for n, t in CATALOG['tables'][table]}
        if name.casefold() not in fields:
            unavailable('missing column ' + name)
        actual, kind = fields[name.casefold()]
        return owner + '.' + quote(actual), kind

    def compile(self):
        supply = defaultdict(list)
        for item in self.items('supplyChainFilter'):
            supply[item['attributeName'].lower()].append(item['value'])
        for name, owner, field in (('forlocation', 'la', 'LocationType'),
                ('forlocationlocationcode', 'A', 'WhCode'), ('forchildrenlocationcode', 'E', 'ParentWhCode')):
            self.in_list(owner, field, supply[name])
        self.children = supply['forchildren']
        for group, special, code, owner in (('productFilter', 'sku', 'SKUCode', 'sa'),
                                            ('locationFilter', 'location', 'WhCode', 'la')):
            items = self.items(group)
            self.in_list('A', code, [i['value'] for i in items if i['attributeName'].lower() == special])
            self.grouped([i for i in items if i['attributeName'].lower() != special],
                lambda name, group=group, owner=owner: (owner, name.replace('p', 'sl')
                    if group == 'productFilter' else 'l' + name))
        availability = self.items('availabilityFilter')
        for item in availability:
            name = item['attributeName'].lower()
            if name in ('norm', 'stock', 'git', 'virtualnorm'):
                self.where.append(self.compare('E', name, item.get('operator'), item['value']))
        for name, owner, field in (('pic', 'E', 'DispatchColor'), ('ohic', 'E', 'PhysicalInventoryColor'),
                                    ('pipo,seasonality', 'B', 'Tags')):
            self.in_list(owner, field, [i['value'] for i in availability if i['attributeName'].lower() == name])
        categories = [i['value'] for i in availability if i['attributeName'].lower() == 'category']
        if categories:
            self.where.append('(' + ' OR '.join('B."Category" ~* %s' for _ in categories) + ')')
            self.params.extend(like_pattern('%' + value + '%') for value in categories)
        for item in self.items('colorFilter'):
            colours = ('Black', 'Red') if item['attributeName'] == 'black/red' else (item['attributeName'].title(),)
            if item.get('type') == 'colorage':
                age = self.compare('btd', 'Age', item.get('operator'), item['value'])
                self.where.append('(' + age + ' AND (' + ' OR '.join(equal('btd."D90"', '%s') for _ in colours) + '))')
                self.params.extend(colours)
            else:
                self.where.append('(' + ' OR '.join(self.compare('btd', colour + 'Count',
                    item.get('operator'), item['value']) for colour in colours) + ')')
        def custom(name):
            for prefix, owner in (('skulocattr', 'sla'), ('skuattr', 'sa'), ('locattr', 'la')):
                if prefix in name.lower():
                    return owner, name.lower().replace(prefix, 'c')
        self.grouped([i for i in self.items('customAttributeFilter') if any(p in i['attributeName'].lower()
            for p in ('skulocattr', 'skuattr', 'locattr'))], custom)
        return ' AND '.join(self.where) or 'TRUE'


def read_btr(run, payload, *, paging, count=False, export=False):
    columns = tuple(f'D{i}' for i in range(1, 91)) if export else btr.horizon_columns(run.business_date.isoformat(), payload)
    attributes = {name: image_rows(run, 'closing/btr/' + name)
                  for name in ('SkuAttributeData', 'LocationAttributeData')}
    try:
        manifest = hierarchy.selected_manifest(run)
        if manifest:
            attributes = hierarchy.project_attributes(attributes, permission_catalogue(), manifest)
    except hierarchy.HierarchyUnavailable as exc:
        raise PublicationUnavailable(str(exc)) from exc
    # Retain the already accepted structural/source-invalid filter guards.
    if export:
        for item in (payload.get('filters', {}).get('customAttributeFilter') or {}).get('filters', []):
            if 'skulocattr' in item.get('attributeName', '').lower():
                raise PublicationUnavailable('LEG-BTR-EXPORT-MISSING-SLA: deployed export has no sla join')
    BtrPredicate(payload, attributes['LocationAttributeData'], count=count or export)
    products, locations = scope(payload, attributes=attributes)
    result = {'TechCount': '0', 'EcoCount': '0'} if count else {'tech': [], 'eco': []}
    if not count:
        dates = image_rows(run, 'closing/btr/BufferTrendDates')
        result['labels'] = [{c: row[c] for c in columns} for row in dates]
    if not products or not locations:
        return (iter(()), dates) if export else result

    ctes, params = [], []
    # Permit column pruning separately for key selection and wide display rows
    # in the sealed fixture; materializing all ninety days spills both passes.
    inline = 'NOT MATERIALIZED ' if getattr(run, 'kind', None) == 'LEGACY_UI_FIXTURE' else ''
    def add(alias, query, values):
        ctes.append(alias + ' AS ' + inline + '(' + query + ')')
        params.extend(values)
    def image(alias, path):
        query, values = image_query(run, path)
        add(alias, query, values)
    for alias, table, prefix in (('sa', 'SkuAttributeData', 'SL'), ('la', 'LocationAttributeData', 'LL')):
        if manifest:
            image(alias + 'native', 'closing/btr/' + table)
            rows = attributes[table]
            add(alias + 'hierarchy', 'VALUES ' + ','.join(['(%s,%s,%s,%s)'] * len(rows)),
                [v for ordinal, row in enumerate(rows) for v in (ordinal, *[row[prefix + str(i)] for i in (1, 2, 3)])])
            fields = [n for n, _ in CATALOG['tables']['BTR/' + table] if n not in [prefix + str(i) for i in (1, 2, 3)]]
            add(alias, 'SELECT ' + ','.join('N.' + quote(n) for n in fields) + ',' +
                ','.join('H.column' + str(i + 1) + ' AS ' + quote(prefix + str(i)) for i in (1, 2, 3)) +
                ' FROM ' + alias + 'native N JOIN ' + alias + 'hierarchy H ON N.vf_ordinal=H.column1', [])
        else:
            image(alias, 'closing/btr/' + table)
    if not export:
        image('sla', 'closing/btr/SkuLocAttributeData')
    image('B', 'closing/dbm/SKULocStandardAttributes')
    image('R', 'reports/bpr/vf_RationedReqReport')
    # GenerateRationReqReport copies these fields directly from terminal Req.
    # The earlier native_inputs capture predates UpdateDispatchPriority colours.
    requirement_fields = ('SKUCode', 'WhCode', 'ParentWhCode', 'Norm', 'VirtualNorm')
    if export:
        requirement_fields += ('Stock', 'GIT', 'DispatchColor', 'PhysicalInventoryColor')
    add('E', 'SELECT ' + ('*' if count else ','.join(quote(n) for n in requirement_fields)) + ' FROM R', [])
    for alias, codes in (('P', products), ('L', locations)):
        members = [code for code in sorted(codes) for _ in range(codes.multiplicities[code])]
        add(alias, 'VALUES ' + ','.join(['(%s)'] * len(members)), members)
    if not count:
        image('sd', 'closing/importer/SKUDescriptionTbl')
        image('ld', 'closing/importer/SiteDescriptionTbl')
        categories = image_rows(run, 'closing/consumer_context/CategoryColDescription')
        standards = image_rows(run, 'closing/dbm/SKULocStandardAttributes')
        aliases = [(value, btr.category_alias_text(value, categories))
                   for value in dict.fromkeys(row['Category'] for row in standards)]
        add('cd', 'VALUES ' + ','.join(['(%s::text,%s::text)'] * len(aliases)) if aliases else
            'SELECT NULL::text,NULL::text WHERE FALSE', [v for pair in aliases for v in pair])

    filters = BtrFilters(payload)
    try:
        where = filters.compile()
    except PublicationUnavailable as exc:
        unavailable(str(exc).partition(':')[2])
    parent_join = ''
    if filters.children:
        parent_join = ' JOIN la parent ON ' + equal('E."ParentWhCode"', 'parent."WHCode"') + ' AND (' + \
            ' OR '.join(equal('parent."LocationType"', '%s') for _ in filters.children) + ')'
    joins = (' LEFT JOIN btd ON ' + equal('A."SKUCode"', 'btd."SKUCode"') + ' AND ' + equal('A."WhCode"', 'btd."WhCode"') +
        ' LEFT JOIN E ON ' + equal('A."SKUCode"', 'E."SKUCode"') + ' AND ' + equal('A."WhCode"', 'E."WhCode"') +
        ('' if export else ' LEFT JOIN sla ON ' + equal('A."SKUCode"', 'sla."SKUCode"') + ' AND ' + equal('A."WhCode"', 'sla."LocCode"')) +
        ' LEFT JOIN sa ON ' + equal('A."SKUCode"', 'sa."SKUCode"') +
        ' LEFT JOIN la ON ' + equal('A."WhCode"', 'la."WHCode"') +
        ' LEFT JOIN B ON ' + equal('A."SKUCode"', 'B."SKUCode"') + ' AND ' + equal('A."WhCode"', 'B."WhCode"') + parent_join)
    auth = ' JOIN P ON ' + equal('A."SKUCode"', 'P.column1') + ' JOIN L ON ' + equal('A."WhCode"', 'L.column1')
    order = key('A."SKUCode"') + ' NULLS FIRST,' + key('A."WhCode"') + ' NULLS FIRST'
    for name, trend in (('tech', 'PhysicalInv'), ('eco', 'Dispatch')):
        selected_name = ('tech' if payload.get('name', '').lower() == 'tech' else 'eco') if export else str(payload.get('name', 'both')).lower()
        if not count and selected_name not in (name, 'both'):
            continue
        local_ctes, values = list(ctes), list(params)
        for alias, table in (('A', 'BPPTrend' + trend), ('btd', 'BufferTrend' + trend)):
            query, bound = image_query(run, 'closing/btr/' + table)
            local_ctes.append(alias + ' AS ' + inline + '(' + query + ')')
            values.extend(bound)
        if count:
            query = 'WITH ' + ','.join(local_ctes) + ' SELECT count(*) FROM A' + joins + auth + ' WHERE ' + where
            values.extend(filters.children + filters.params)
        else:
            if not export:
                selected = 'SELECT A."SKUCode",A."WhCode" FROM A' + joins + auth + ' WHERE ' + where + \
                    ' ORDER BY ' + order + ' LIMIT %s OFFSET %s'
                local_ctes.append('selected AS (' + selected + ')')
                values.extend(filters.children + filters.params + [paging[1], (paging[0] - 1) * paging[1]])
            projection = [('Source', "'" + name + "'"), ('Category', 'cd.column2'), ('Availability', 'NULL'),
                ('Tags', 'B."Tags"'), ('SKUCode', 'A."SKUCode"'), ('SKUDescription', 'sd."SKUDescription"'),
                ('WhCode', 'A."WhCode"'), ('LocationName', 'ld."WHDescription"'), ('Norm', 'E."Norm"'),
                ('VirtualNorm', 'E."VirtualNorm"'), ('pc', 'btd."ParentWhCode"'), ('pn', 'pld."WHDescription"')]
            if export:
                projection = projection[1:]
                projection += [(c, 'replace(A.' + quote(c) + "::text,'-99999999.00','')") for c in columns]
            else:
                projection += [(c, 'A.' + quote(c)) for c in columns] + [('C' + c, 'btd.' + quote(c)) for c in columns]
            projection += [(alias, 'btd.' + quote(field)) for alias, field in (('age', 'Age'), ('bc', 'BlackCount'),
                ('rc', 'RedCount'), ('yc', 'YellowCount'), ('gc', 'GreenCount'), ('blc', 'BlueCount'), ('wc', 'WhiteCount'))]
            query = 'WITH ' + ','.join(local_ctes) + ' SELECT ' + ','.join(value + ' AS ' + quote(alias) for alias, value in projection) + \
                (' FROM A' if export else ' FROM selected t JOIN A ON ' + equal('t."SKUCode"', 'A."SKUCode"') + ' AND ' + equal('t."WhCode"', 'A."WhCode"')) + joins + \
                ' LEFT JOIN sd ON ' + equal('A."SKUCode"', 'sd."SKUCode"') + \
                ' LEFT JOIN ld ON ' + equal('A."WhCode"', 'ld."WHCode"') + \
                ' LEFT JOIN ld pld ON ' + equal('E."ParentWhCode"', 'pld."WHCode"') + \
                ' LEFT JOIN cd ON ' + equal('B."Category"', 'cd.column1') + \
                (auth + ' WHERE ' + where if export else '') + ' ORDER BY ' + order + ('' if export else ' LIMIT %s')
            values.extend(filters.children + (filters.params if export else [paging[1]]))
            if export:
                return iter_rows(query, values), dates
        fixture = getattr(run, 'kind', None) == 'LEGACY_UI_FIXTURE'
        with transaction.atomic() if fixture else nullcontext(), connection.cursor() as cursor:
            if fixture:
                # This sealed population's LIMIT row estimate otherwise selects
                # repeated scans of 97k-row CTEs. Scope the planner choice to this
                # read transaction; retain the exact joins, bags and ordering.
                cursor.execute('SHOW enable_nestloop')
                previous_nestloop = cursor.fetchone()[0]
                cursor.execute('SET LOCAL enable_nestloop = off')
            cursor.execute(query, values)
            if count:
                result['TechCount' if name == 'tech' else 'EcoCount'] = str(cursor.fetchone()[0])
            else:
                names = [c[0] for c in cursor.description]
                result[name] = [{n: '' if v is None else str(v) for n, v in zip(names, row)} for row in cursor.fetchall()]
            if fixture:
                cursor.execute("SELECT set_config('enable_nestloop', %s, true)", [previous_nestloop])
    return result


def iter_rows(query, values):
    """Preserve SQL types for CsvHelper-compatible serialization in bounded batches."""
    with connection.cursor() as cursor:
        cursor.execute(query, values)
        names = [c[0] for c in cursor.description]
        while rows := cursor.fetchmany(256):
            for row in rows:
                yield dict(zip(names, row))
