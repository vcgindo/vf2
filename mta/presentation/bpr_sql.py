"""Fixture-only SQL BPR grid/count reader over the sealed relational images.

The accepted Python ``ReadModel`` remains the normal reader and the differential
oracle.  This module moves only the legacy-UI fixture's grid/count joins,
filtering, permission bags and paging into PostgreSQL; it does not cache,
recalculate or mutate any source row.
"""
from decimal import Decimal

from django.db import connection

from mta.presentation import hierarchy
from mta.presentation.bpr_filters import BprPredicate
from mta.presentation.context import PublicationUnavailable, permission_catalogue, scope
from mta.presentation.rrr_sql import Filters, equal, key
from mta.presentation.selective import image_query
from mta.runtime.relational_state import CATALOG, quote


class BprSqlFilters(Filters):
    """SQL form of the already-validated BPR predicate's supported branches."""

    TABLES = {
        'A': 'BPR/BPR_Table',
        'V': 'BPR/vf_RationedReqReport',
        'S': 'Importer/SKULocStandardAttributes',
        'B': 'Importer/SkuLocAttributeData',
        'C': 'Importer/SkuAttributeData',
        'D': 'Importer/LocationAttributeData',
        'T': 'BTR/BufferTrendPhysicalInv',
    }

    def __init__(self, payload, *, export=False):
        super().__init__(payload)
        self.export = export

    def column(self, owner, name):
        fields = {field.casefold(): (field, kind)
                  for field, kind in CATALOG['tables'][self.TABLES[owner]]}
        if name.casefold() not in fields:
            # BprPredicate has already produced the canonical public failure;
            # reaching this branch means this adapter diverged from it.
            raise PublicationUnavailable('LEG-BPR-FILTER-INVALID-SQL:missing column ' + name)
        actual, kind = fields[name.casefold()]
        return owner + '.' + quote(actual), kind

    def compile(self):
        from collections import defaultdict

        supply = defaultdict(list)
        for item in self.items('supplyChainFilter'):
            supply[item['attributeName'].lower()].append(item['value'])
        for name, owner, field in (('forlocation', 'D', 'LocationType'),
                ('forlocationlocationcode', 'A', 'WhCode'),
                ('forchildrenlocationcode', 'A', 'ParentWhCode')):
            self.in_list(owner, field, supply[name])
        self.children = supply['forchildren']

        for group, special, code in (('productFilter', 'sku', 'SKUCode'),
                                     ('locationFilter', 'location', 'WhCode')):
            items = self.items(group)
            self.in_list('A', code, [item['value'] for item in items
                                      if item['attributeName'].lower() == special])
            self.grouped([item for item in items if item['attributeName'].lower() != special],
                lambda name, group=group: ('C', name.replace('p', 'sl'))
                if group == 'productFilter' else ('D', 'l' + name))

        availability = self.items('availabilityFilter')
        for item in availability:
            name = item['attributeName'].lower()
            if name in ('norm', 'stock', 'git'):
                self.where.append(self.compare('A', name, item.get('operator'), item['value']))
            elif name == 'virtualnorm':
                self.where.append(self.compare('V', 'VirtualNorm', item.get('operator'), item['value']))
        for name, owner, field in (('pic', 'V', 'DispatchColor'),
                ('ohic', 'V', 'PhysicalInventoryColor'),
                ('pipo,seasonality', 'S', 'Tags')):
            self.in_list(owner, field, [item['value'] for item in availability
                                         if item['attributeName'].lower() == name])

        custom = [item for item in self.items('customAttributeFilter')
                  if any(prefix in item['attributeName'].lower()
                         for prefix in ('skulocattr', 'skuattr', 'locattr'))]
        def custom_field(name):
            for prefix, owner in (('skulocattr', 'B'), ('skuattr', 'C'), ('locattr', 'D')):
                if prefix in name.lower():
                    return owner, name.lower().replace(prefix, 'c')
        self.grouped(custom, custom_field)
        if self.export:
            for item in self.items('colorFilter'):
                if item.get('type') == 'colorcount':
                    names = (['BlackCount', 'RedCount'] if item['attributeName'] == 'black/red'
                             else [item['attributeName'] + 'Count'])
                    clauses = [self.compare('T', name, item.get('operator'), item['value'])
                               for name in names]
                    self.where.append('(' + ' OR '.join(clauses) + ')')
        return ' AND '.join(self.where) or 'TRUE'


def _projected_attributes(run):
    from mta.presentation import native_publication
    if native_publication.enabled():
        native_publication.require_mode()
        from mta.presentation.selective import image_rows as bpr_image_rows
    importer = {name: bpr_image_rows(run, 'closing/importer/' + name) for name in ('SkuAttributeData', 'LocationAttributeData')}
    try:
        manifest = hierarchy.selected_manifest(run)
        if manifest:
            importer = hierarchy.project_attributes(importer, permission_catalogue(), manifest)
    except hierarchy.HierarchyUnavailable as exc:
        raise PublicationUnavailable(str(exc)) from exc
    return (importer, manifest)


def _values_cte(rows, columns, casts=None):
    casts = casts or {}
    if not rows:
        return ('SELECT ' + ','.join('NULL' + casts.get(name, '::text') + ' AS ' + quote(name)
                                     for name in columns) + ' WHERE FALSE', [])
    placeholders = []
    values = []
    for row in rows:
        placeholders.append('(' + ','.join('%s' + casts.get(name, '') for name in columns) + ')')
        values.extend(row.get(name) for name in columns)
    aliases = ','.join(quote(name) for name in columns)
    return 'SELECT * FROM (VALUES ' + ','.join(placeholders) + ') AS supplied(' + aliases + ')', values


def _build(run, payload, importer, manifest, ancillary, paging, count):
    ctes, params = [], []

    def add(alias, query, values):
        ctes.append(alias + ' AS NOT MATERIALIZED (' + query + ')')
        params.extend(values)

    def image(alias, path):
        query, values = image_query(run, path)
        add(alias, query, values)

    image('A', 'reports/bpr/BPR_Table')
    image('V', 'reports/bpr/vf_RationedReqReport')
    image('S', 'closing/dbm/SKULocStandardAttributes')
    image('B', 'closing/importer/SkuLocAttributeData')
    for alias, table, code, prefix in (('C', 'SkuAttributeData', 'SKUCode', 'SL'),
                                        ('D', 'LocationAttributeData', 'WHCode', 'LL')):
        query, values = image_query(run, 'closing/importer/' + table)
        if manifest:
            add(alias + 'native', query, values)
            rows = importer[table]
            hierarchy_query, hierarchy_values = _values_cte(
                [dict(ordinal=ordinal, **{prefix + str(i): row[prefix + str(i)] for i in (1, 2, 3)})
                 for ordinal, row in enumerate(rows)],
                ('ordinal', prefix + '1', prefix + '2', prefix + '3'), {'ordinal': '::bigint'})
            add(alias + 'hierarchy', hierarchy_query, hierarchy_values)
            omitted = {prefix + str(i) for i in (1, 2, 3)}
            fields = [name for name, _ in CATALOG['tables']['Importer/' + table] if name not in omitted]
            add(alias, 'SELECT N.vf_ordinal,' + ','.join('N.' + quote(name) for name in fields) + ',' +
                ','.join('H.' + quote(prefix + str(i)) for i in (1, 2, 3)) +
                ' FROM ' + alias + 'native N JOIN ' + alias + 'hierarchy H ON N.vf_ordinal=H.ordinal', [])
        else:
            add(alias, query, values)

    remarks = []
    for ordinal, row in enumerate(ancillary['BPRReport_RemarkDetails']):
        remarks.append(dict(ordinal=ordinal, SKUCode=row['SKUCode'], WhCode=row['WhCode'],
                            RemarkDate=row['RemarkDate'], Remark=row['Remark']))
    remark_query, remark_values = _values_cte(
        remarks, ('ordinal', 'SKUCode', 'WhCode', 'RemarkDate', 'Remark'),
        {'ordinal': '::bigint', 'RemarkDate': '::timestamp'})
    add('remarks', remark_query, remark_values)
    add('latest_dates', 'SELECT ' + key('"SKUCode"') + ' AS sku_key,' + key('"WhCode"') +
        ' AS loc_key,max("RemarkDate") AS latest FROM remarks GROUP BY 1,2', [])
    add('latest_remarks', 'SELECT R.* FROM remarks R JOIN latest_dates M ON ' +
        key('R."SKUCode"') + '=M.sku_key AND ' + key('R."WhCode"') +
        '=M.loc_key AND R."RemarkDate"=M.latest', [])

    products, locations = scope(payload, attributes=importer)
    if not products or not locations:
        return None, []
    for alias, codes in (('P', products), ('L', locations)):
        members = [code for code in sorted(codes) for _ in range(codes.multiplicities[code])]
        query, values = _values_cte([{'code': value} for value in members], ('code',))
        add(alias, query, values)

    filters = BprSqlFilters(payload)
    where = filters.compile()
    common = (' LEFT JOIN V ON ' + equal('A."SKUCode"', 'V."SKUCode"') +
        ' AND ' + equal('A."WhCode"', 'V."WhCode"'))
    standard = (' JOIN S ON ' if count else ' LEFT JOIN S ON ') + \
        equal('A."SKUCode"', 'S."SKUCode"') + ' AND ' + equal('A."WhCode"', 'S."WhCode"')
    dimensions = (standard +
        ' LEFT JOIN C ON ' + equal('A."SKUCode"', 'C."SKUCode"') +
        ' LEFT JOIN D ON ' + equal('A."WhCode"', 'D."WHCode"') +
        ' LEFT JOIN B ON ' + equal('A."SKUCode"', 'B."SKUCode"') +
        ' AND ' + equal('A."WhCode"', 'B."LocCode"'))
    auth = (' JOIN P ON ' + equal('A."SKUCode"', 'P.code') +
            ' JOIN L ON ' + equal('A."WhCode"', 'L.code'))
    parent = ''
    if filters.children:
        parent = (' JOIN D parent ON ' + equal('A."ParentWhCode"', 'parent."WHCode"') +
                  ' AND (' + ' OR '.join(equal('parent."LocationType"', '%s')
                                         for _ in filters.children) + ')')

    params.extend(filters.children)
    params.extend(filters.params)
    if count:
        joins = common + dimensions + \
            ' LEFT JOIN latest_remarks RM ON ' + equal('A."SKUCode"', 'RM."SKUCode"') + \
            ' AND ' + equal('A."WhCode"', 'RM."WhCode"') + auth + parent
        return 'WITH ' + ','.join(ctes) + ' SELECT count(*) FROM A' + joins + ' WHERE ' + where, params

    page, size = paging
    raw_order = ('V."PhysicalInventoryColorSequence" NULLS FIRST,'
        'V."PhysicalInventoryPen" DESC NULLS LAST,A."EcoColorSequence" NULLS FIRST,'
        'V."DispatchPen" DESC NULLS LAST,' + key('A."WhCode"') + ' DESC NULLS LAST,' +
        key('A."SKUCode"') + ' NULLS FIRST,' +
        'A.vf_ordinal,V.vf_ordinal,S.vf_ordinal,C.vf_ordinal,D.vf_ordinal,B.vf_ordinal')
    selected = ('SELECT A."SKUCode",A."WhCode" FROM A' + common + dimensions + auth + parent +
                ' WHERE ' + where + ' ORDER BY ' + raw_order + ' LIMIT %s OFFSET %s')
    params.extend((size, (page - 1) * size))
    ctes.append('selected AS (' + selected + ')')
    ctes.append('selected_counts AS (SELECT ' + key('"SKUCode"') + ' AS sku_key,' +
                 key('"WhCode"') + ' AS loc_key,count(*)::bigint AS copies FROM selected GROUP BY 1,2)')
    image('T', 'closing/btr/BufferTrendPhysicalInv')

    pen = lambda column: 'CASE WHEN ' + column + '=-99999999.00 THEN NULL ELSE ' + column + ' END'
    projection = [
        ('tags', 'S."Tags"'), ('SKUCode', 'A."SKUCode"'), ('SKUName', 'A."SKUName"'),
        ('WHCode', 'A."WhCode"'), ('WHName', 'A."WhName"'), ('ParentWhCode', 'A."ParentWhCode"'),
        ('ParentName', "COALESCE(A.\"ParentName\",'-')"), ('Stock', 'A."Stock"'), ('Norm', 'A."Norm"'),
        ('GIT', 'A."GIT"'), ('ts', 'A."TechColorSequence"'),
        ('TechPen', pen('V."PhysicalInventoryPen"')), ('es', 'A."EcoColorSequence"'),
        ('PhysicalInventoryColorSequence', 'V."PhysicalInventoryColorSequence"'),
        ('EcoPen', pen('V."DispatchPen"')), ('TechColor', 'V."PhysicalInventoryColor"'),
        ('EcoColor', 'V."DispatchColor"'), ('Req', 'COALESCE(A."Req",0)'),
        ('RationedQTY', 'COALESCE(A."RationedQTY",0)'),
        ('LeftoverParentStock', 'COALESCE(A."LeftoverParentStock",0)'),
        ('PhaseIn-Out', "CASE A.\"PhaseIn-Out\" WHEN 1 THEN 'Phase Out' WHEN 2 THEN 'Phase In' ELSE '-' END"),
        ('ResidualSnP', 'A."ResidualSnP"'), ('NormReq', 'A."NormReq"'), ('BlueReq', 'A."BlueReq"'),
        ('vn', 'V."VirtualNorm"'),
    ]
    projection += [(f'sl{i}', f'C."SL{i}"') for i in range(1, 6)]
    projection += [(f'll{i}', f'D."LL{i}"') for i in range(1, 6)]
    projection += [(f'SKULocAttr{i}', f"COALESCE(A.\"SKULocAttr{i}\",'-')") for i in range(1, 16)]
    projection += [(f'SKUAttr{i}', f"COALESCE(C.\"c{i}\",'-')") for i in range(1, 16)]
    projection += [(f'LocAttr{i}', f"COALESCE(D.\"c{i}\",'-')") for i in range(1, 16)]
    projection += [('Remark', 'RM."Remark"'), ('intransit', 'NULL'),
                   ('Availability_01_30', 'T."Availability_01_30"'),
                   ('Availability_31_60', 'T."Availability_31_60"'),
                   ('Availability_61_90', 'T."Availability_61_90"')]
    select = ','.join(expression + ' AS ' + quote(name) for name, expression in projection)
    joins = (' FROM A JOIN selected_counts K ON ' + key('A."SKUCode"') + '=K.sku_key AND ' +
        key('A."WhCode"') + '=K.loc_key' + common + dimensions +
        ' LEFT JOIN latest_remarks RM ON ' + equal('A."SKUCode"', 'RM."SKUCode"') +
        ' AND ' + equal('A."WhCode"', 'RM."WhCode"') +
        ' LEFT JOIN T ON ' + equal('A."SKUCode"', 'T."SKUCode"') +
        ' AND ' + equal('A."WhCode"', 'T."WhCode"') +
        ' CROSS JOIN LATERAL generate_series(1,K.copies) copy_ordinal')
    projected_order = ('V."PhysicalInventoryColorSequence" NULLS FIRST,' + pen('V."PhysicalInventoryPen"') +
        ' DESC NULLS LAST,A."EcoColorSequence" NULLS FIRST,' + pen('V."DispatchPen"') +
        ' DESC NULLS LAST,' + key('A."WhCode"') + ' DESC NULLS LAST,' +
        key('A."SKUCode"') + ' NULLS FIRST,' +
        'A.vf_ordinal,V.vf_ordinal,S.vf_ordinal,C.vf_ordinal,D.vf_ordinal,B.vf_ordinal,'
        'RM.ordinal,T.vf_ordinal,copy_ordinal')
    return 'WITH ' + ','.join(ctes) + ' SELECT ' + select + joins + ' ORDER BY ' + projected_order, params


def read_bpr(run, payload, *, paging=None, count=False):
    """Return the exact fixture count or final page dictionaries.

    Dispatch must remain guarded by ``run.kind == 'LEGACY_UI_FIXTURE'`` in the
    caller.  Normal reads, analytics and exports must continue through
    ``ReadModel``.
    """
    raise ValueError('BPR SQL reader is fixture-only')
