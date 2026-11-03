"""Selected BTR count/key-page/rejoin queries over typed persisted relations.

BORProcessor source80ceb491 / deployed DLL0222eb96. Keep count's full report E
distinct from grid's five-field requirement projection. No whole-run reader,
other-branch grid work, calculation, cache, or new ordering for tied keys.
"""
from collections import defaultdict
import logging
from django.db import connection

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


def read_btr(run, payload, *, paging, count=False, export=False, read_binding=None):
    from mta.presentation import btr_reporting
    if read_binding is not None and read_binding.run.pk != run.pk:
        raise PublicationUnavailable('btr_phase_binding_run_differs')
    def source_rows(path):
        return image_rows(run, path) if read_binding is None else read_binding.rows(path)
    def source_query(path):
        return image_query(run, path) if read_binding is None else read_binding.query(path)
    generation = btr_reporting.selected_generation(run) if read_binding is None else None
    if generation is not None and generation.version in (2,3,4):
        from mta.presentation.btr_snapshot import read_snapshot, reference_generation
        if not count and (not export) and (payload.get('displayPrepared') is True):
            return read_snapshot(run, generation, payload, paging)
        if generation.version != 4:
            generation = reference_generation(run, generation)
    columns = tuple((f'D{i}' for i in range(1, 91))) if export else btr.horizon_columns(run.business_date.isoformat(), payload)
    attributes = {name: source_rows('closing/btr/' + name) for name in ('SkuAttributeData', 'LocationAttributeData')}
    try:
        manifest = hierarchy.selected_manifest(run)
        if manifest:
            attributes = hierarchy.project_attributes(attributes, permission_catalogue(), manifest)
    except hierarchy.HierarchyUnavailable as exc:
        raise PublicationUnavailable(str(exc)) from exc
    if export:
        for item in (payload.get('filters', {}).get('customAttributeFilter') or {}).get('filters', []):
            if 'skulocattr' in item.get('attributeName', '').lower():
                raise PublicationUnavailable('LEG-BTR-EXPORT-MISSING-SLA: deployed export has no sla join')
    BtrPredicate(payload, attributes['LocationAttributeData'], count=count or export)
    products, locations = scope(payload, attributes=attributes)
    reporting = btr_reporting.eligible_request(generation, products, locations)
    if generation:
        logging.getLogger(__name__).info('BTR reader=%s generation=%s count=%s export=%s', 'reporting' if reporting else 'accepted-fallback', generation.pk, count, export)
    result = {'TechCount': '0', 'EcoCount': '0'} if count else {'tech': [], 'eco': []}
    if not count:
        dates = source_rows('closing/btr/BufferTrendDates')
        result['labels'] = [{c: row[c] for c in columns} for row in dates]
    if not products or not locations:
        return (iter(()), dates) if export else result
    ctes, params = ([], [])
    inline = ''

    def add(alias, query, values):
        ctes.append(alias + ' AS ' + inline + '(' + query + ')')
        params.extend(values)

    def image(alias, path):
        query, values = source_query(path)
        add(alias, query, values)
    for alias, table, prefix in (('sa', 'SkuAttributeData', 'SL'), ('la', 'LocationAttributeData', 'LL')):
        if manifest:
            image(alias + 'native', 'closing/btr/' + table)
            rows = attributes[table]
            add(alias + 'hierarchy', 'VALUES ' + ','.join(['(%s,%s,%s,%s)'] * len(rows)), [v for ordinal, row in enumerate(rows) for v in (ordinal, *[row[prefix + str(i)] for i in (1, 2, 3)])])
            fields = [n for n, _ in CATALOG['tables']['BTR/' + table] if n not in [prefix + str(i) for i in (1, 2, 3)]]
            add(alias, 'SELECT ' + ('N.vf_ordinal,' if reporting else '') + ','.join(('N.' + quote(n) for n in fields)) + ',' + ','.join(('H.column' + str(i + 1) + ' AS ' + quote(prefix + str(i)) for i in (1, 2, 3))) + ' FROM ' + alias + 'native N JOIN ' + alias + 'hierarchy H ON N.vf_ordinal=H.column1', [])
        else:
            image(alias, 'closing/btr/' + table)
    if not export:
        image('sla', 'closing/btr/SkuLocAttributeData')
    image('B', 'closing/dbm/SKULocStandardAttributes')
    image('R', 'reports/bpr/vf_RationedReqReport')
    requirement_fields = ('SKUCode', 'WhCode', 'ParentWhCode', 'Norm', 'VirtualNorm')
    if export:
        requirement_fields += ('Stock', 'GIT', 'DispatchColor', 'PhysicalInventoryColor')
    add('E', 'SELECT ' + ('*' if count else ('vf_ordinal,' if reporting else '') + ','.join((quote(n) for n in requirement_fields))) + ' FROM R', [])
    for alias, codes in (('P', products), ('L', locations)):
        members = [code for code in sorted(codes) for _ in range(codes.multiplicities[code])]
        add(alias, 'VALUES ' + ','.join(['(%s)'] * len(members)), members)
    if not count:
        image('sd', 'closing/importer/SKUDescriptionTbl')
        image('ld', 'closing/importer/SiteDescriptionTbl')
        categories = source_rows('closing/consumer_context/CategoryColDescription')
        standards = source_rows('closing/dbm/SKULocStandardAttributes')
        aliases = [(value, btr.category_alias_text(value, categories)) for value in dict.fromkeys((row['Category'] for row in standards))]
        add('cd', 'VALUES ' + ','.join(['(%s::text,%s::text)'] * len(aliases)) if aliases else 'SELECT NULL::text,NULL::text WHERE FALSE', [v for pair in aliases for v in pair])
    filters = BtrFilters(payload)
    try:
        where = filters.compile()
    except PublicationUnavailable as exc:
        unavailable(str(exc).partition(':')[2])
    parent_join = ''
    if filters.children:
        parent_join = ' JOIN la parent ON ' + equal('E."ParentWhCode"', 'parent."WHCode"') + ' AND (' + ' OR '.join((equal('parent."LocationType"', '%s') for _ in filters.children)) + ')'
    joins = ' LEFT JOIN btd ON ' + equal('A."SKUCode"', 'btd."SKUCode"') + ' AND ' + equal('A."WhCode"', 'btd."WhCode"') + ' LEFT JOIN E ON ' + equal('A."SKUCode"', 'E."SKUCode"') + ' AND ' + equal('A."WhCode"', 'E."WhCode"') + ('' if export else ' LEFT JOIN sla ON ' + equal('A."SKUCode"', 'sla."SKUCode"') + ' AND ' + equal('A."WhCode"', 'sla."LocCode"')) + ' LEFT JOIN sa ON ' + equal('A."SKUCode"', 'sa."SKUCode"') + ' LEFT JOIN la ON ' + equal('A."WhCode"', 'la."WHCode"') + ' LEFT JOIN B ON ' + equal('A."SKUCode"', 'B."SKUCode"') + ' AND ' + equal('A."WhCode"', 'B."WhCode"') + parent_join
    auth = ' JOIN P ON ' + equal('A."SKUCode"', 'P.column1') + ' JOIN L ON ' + equal('A."WhCode"', 'L.column1')
    order = key('A."SKUCode"') + ' NULLS FIRST,' + key('A."WhCode"') + ' NULLS FIRST'
    for name, trend in (('tech', 'PhysicalInv'), ('eco', 'Dispatch')):
        selected_name = ('tech' if payload.get('name', '').lower() == 'tech' else 'eco') if export else str(payload.get('name', 'both')).lower()
        if not count and selected_name not in (name, 'both'):
            continue
        local_ctes, values = (list(ctes), list(params))
        for alias, table in (('A', 'BPPTrend' + trend), ('btd', 'BufferTrend' + trend)):
            query, bound = source_query('closing/btr/' + table)
            local_ctes.append(alias + ' AS ' + inline + '(' + query + ')')
            values.extend(bound)
        if reporting:
            if generation.version == 4:
                from mta.presentation.btr_reference_projection import relation
                pair = (next(iter(products)), next(iter(locations))) if len(products)==len(locations)==1 else None
                source, reference_params = relation(generation,name,export,generation.qualification['reference_projection']['bounds'],pair=pair)
                local_ctes.append('J AS NOT MATERIALIZED ('+source+')')
                values.extend(reference_params)
            else:
                local_ctes.append('J AS NOT MATERIALIZED (SELECT * FROM ' + btr_reporting.REF_TABLE + ' WHERE generation_id=%s AND branch=%s AND export=%s)')
                values.extend([generation.pk, name, export])
            selected_where = btr_reporting.substitute_keys(where)
            selected_auth = ' JOIN P ON J.sku_key=' + key('P.column1') + ' JOIN L ON J.location_key=' + key('L.column1')
            selected_order = 'J.sku_key NULLS FIRST,J.location_key NULLS FIRST'
            selected_from = btr_reporting.reference_from(selected_where, parent_join=parent_join)
        if count:
            query = 'WITH ' + ','.join(local_ctes) + ' SELECT count(*) FROM A' + joins + auth + ' WHERE ' + where
            if reporting:
                query = 'WITH ' + ','.join(local_ctes) + ' SELECT count(*) FROM ' + selected_from + selected_auth + ' WHERE ' + selected_where
            values.extend(filters.children + filters.params)
        else:
            if not export:
                selected = 'SELECT A."SKUCode",A."WhCode" FROM A' + joins + auth + ' WHERE ' + where + ' ORDER BY ' + order + ' LIMIT %s OFFSET %s'
                if reporting:
                    selected = 'SELECT J.sku_code AS "SKUCode",J.location_code AS "WhCode" FROM ' + selected_from + selected_auth + ' WHERE ' + selected_where + ' ORDER BY ' + selected_order + ' LIMIT %s OFFSET %s'
                local_ctes.append('selected AS (' + selected + ')')
                values.extend(filters.children + filters.params + [paging[1], (paging[0] - 1) * paging[1]])
            projection = [('Source', "'" + name + "'"), ('Category', 'cd.column2'), ('Availability', 'NULL'), ('Tags', 'B."Tags"'), ('SKUCode', 'A."SKUCode"'), ('SKUDescription', 'sd."SKUDescription"'), ('WhCode', 'A."WhCode"'), ('LocationName', 'ld."WHDescription"'), ('Norm', 'E."Norm"'), ('VirtualNorm', 'E."VirtualNorm"'), ('pc', 'btd."ParentWhCode"'), ('pn', 'pld."WHDescription"')]
            if export:
                projection = projection[1:]
                projection += [(c, 'replace(A.' + quote(c) + "::text,'-99999999.00','')") for c in columns]
            else:
                projection += [(c, 'A.' + quote(c)) for c in columns] + [('C' + c, 'btd.' + quote(c)) for c in columns]
            projection += [(alias, 'btd.' + quote(field)) for alias, field in (('age', 'Age'), ('bc', 'BlackCount'), ('rc', 'RedCount'), ('yc', 'YellowCount'), ('gc', 'GreenCount'), ('blc', 'BlueCount'), ('wc', 'WhiteCount'))]
            query = 'WITH ' + ','.join(local_ctes) + ' SELECT ' + ','.join((value + ' AS ' + quote(alias) for alias, value in projection)) + (' FROM A' if export else ' FROM selected t JOIN A ON ' + equal('t."SKUCode"', 'A."SKUCode"') + ' AND ' + equal('t."WhCode"', 'A."WhCode"')) + joins + ' LEFT JOIN sd ON ' + equal('A."SKUCode"', 'sd."SKUCode"') + ' LEFT JOIN ld ON ' + equal('A."WhCode"', 'ld."WHCode"') + ' LEFT JOIN ld pld ON ' + equal('E."ParentWhCode"', 'pld."WHCode"') + ' LEFT JOIN cd ON ' + equal('B."Category"', 'cd.column1') + (auth + ' WHERE ' + where if export else '') + ' ORDER BY ' + order + ('' if export else ' LIMIT %s')
            values.extend(filters.children + (filters.params if export else [paging[1]]))
            if not export and reporting:
                daily = set(columns) | {'C' + column for column in columns}
                narrow = [(alias, value) for alias, value in projection if alias not in daily]
                final_from = ' FROM selected t JOIN A ON ' + equal('t."SKUCode"', 'A."SKUCode"') + ' AND ' + equal('t."WhCode"', 'A."WhCode"') + joins + ' LEFT JOIN sd ON ' + equal('A."SKUCode"', 'sd."SKUCode"') + ' LEFT JOIN ld ON ' + equal('A."WhCode"', 'ld."WHCode"') + ' LEFT JOIN ld pld ON ' + equal('E."ParentWhCode"', 'pld."WHCode"') + ' LEFT JOIN cd ON ' + equal('B."Category"', 'cd.column1')
                identities = 'A.vf_ordinal AS ao,btd.vf_ordinal AS bo,'
                sorting = key('A."SKUCode"') + ' AS sort_sku,' + key('A."WhCode"') + ' AS sort_loc,'
                final_order = order
                if reporting:
                    narrow = [(alias, btr_reporting.substitute_keys(value)) for alias, value in narrow]
                    reference = btr_reporting.reference_from(','.join((value for _, value in narrow)) + ' E.', parent_join=parent_join)
                    final_from = ' FROM selected t JOIN J ON ' + key('t."SKUCode"') + '=J.sku_key AND ' + key('t."WhCode"') + '=J.location_key' + reference[1:] + ' LEFT JOIN sd ON ' + equal('J.sku_code', 'sd."SKUCode"') + ' LEFT JOIN ld ON ' + equal('J.location_code', 'ld."WHCode"') + ' LEFT JOIN ld pld ON ' + equal('E."ParentWhCode"', 'pld."WHCode"') + ' LEFT JOIN cd ON ' + equal('B."Category"', 'cd.column1')
                    identities = 'J.a_ordinal AS ao,J.btd_ordinal AS bo,'
                    sorting = 'J.sku_key AS sort_sku,J.location_key AS sort_loc,'
                    final_order = selected_order
                local_ctes.append('final_keys AS (SELECT ' + identities + sorting + ','.join((value + ' AS ' + quote(alias) for alias, value in narrow)) + final_from + ' ORDER BY ' + final_order + ' LIMIT %s)')
                fetched = ','.join((quote(column) for column in columns))
                query = 'WITH ' + ','.join(local_ctes) + ' SELECT ' + ','.join((('AD.' + quote(alias) if alias in columns else 'TD.' + quote(alias[1:]) if alias in daily else 'K.' + quote(alias)) + ' AS ' + quote(alias) for alias, _ in projection)) + ' FROM final_keys K JOIN LATERAL (SELECT ' + fetched + ' FROM A WHERE vf_ordinal=K.ao OFFSET 0) AD ON TRUE' + ' LEFT JOIN LATERAL (SELECT ' + fetched + ' FROM btd WHERE vf_ordinal=K.bo OFFSET 0) TD ON TRUE' + ' ORDER BY K.sort_sku NULLS FIRST,K.sort_loc NULLS FIRST'
            if export:
                if reporting:
                    projection = [(alias, btr_reporting.substitute_keys(value)) for alias, value in projection]
                    reference = btr_reporting.reference_from(','.join((value for _, value in projection)) + selected_where + ' E.', parent_join=parent_join)
                    query = 'WITH ' + ','.join(local_ctes) + ' SELECT ' + ','.join((value + ' AS ' + quote(alias) for alias, value in projection)) + ' FROM ' + reference + ' LEFT JOIN sd ON ' + equal('J.sku_code', 'sd."SKUCode"') + ' LEFT JOIN ld ON ' + equal('J.location_code', 'ld."WHCode"') + ' LEFT JOIN ld pld ON ' + equal('E."ParentWhCode"', 'pld."WHCode"') + ' LEFT JOIN cd ON ' + equal('B."Category"', 'cd.column1') + selected_auth + ' WHERE ' + selected_where + ' ORDER BY ' + selected_order
                return (iter_rows(query, values), dates)
        with connection.cursor() as cursor:
            cursor.execute(query, values)
            if count:
                result['TechCount' if name == 'tech' else 'EcoCount'] = str(cursor.fetchone()[0])
            else:
                names = [c[0] for c in cursor.description]
                result[name] = [{n: '' if v is None else str(v) for n, v in zip(names, row)} for row in cursor.fetchall()]
    return result


def iter_rows(query, values):
    """Stream rows from the pinned PostgreSQL transaction when serving an export."""
    open_cursor = (connection.chunked_cursor if connection.vendor=='postgresql' and connection.in_atomic_block
                   else connection.cursor)
    with open_cursor() as cursor:
        cursor.execute(query, values)
        names = [c[0] for c in cursor.description]
        while rows := cursor.fetchmany(256):
            for row in rows:
                yield dict(zip(names, row))


def export_chunks(rows, headers):
    from mta.presentation.rrr_export import csv_chunks
    try:
        yield from csv_chunks(rows, headers)
    finally:
        close = getattr(rows, 'close', None)
        if close:
            close()
