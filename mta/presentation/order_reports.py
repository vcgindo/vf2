"""Read existing immutable order images through the retained report contracts.

No producer, materialized report, mutation or whole-run reconstruction. Source
and intentional presentation corrections are recorded in LEGACY_EXCEPTIONS.
"""
from decimal import Decimal

from django.db import connection

from mta.presentation.context import scope, selected_run
from mta.presentation.rrr_sql import equal, key
from mta.presentation.selective import image_query, image_rows
from mta.presentation.supplier_allocation import SupplierFilters
from mta.runtime.relational_state import CATALOG, quote
from mta.runtime.production_report_storage import TABLES


class AllocationFilters(SupplierFilters):
    """Same Commons FilterType overload; resolve only columns actually joined.

    In particular do not invent WhCode, ParentWhCode, stock, norm or colours
    absent from AllocatedOrders. The caller discards forchildren's join SQL.
    """
    def column(self, owner, name):
        fields = (TABLES['production/AllocatedOrders'] if owner == 'A' else
                  CATALOG['tables'][{'B': 'Importer/SkuLocAttributeData',
                      'C': 'Importer/SkuAttributeData',
                      'D': 'Importer/LocationAttributeData'}[owner]])
        matches = [(field, kind) for field, kind in fields if field.casefold() == name.casefold()]
        if len(matches) != 1:
            raise ValueError('native allocation filter column missing:' + owner + '.' + name)
        field, kind = matches[0]
        return owner + '.' + quote(field), kind


PATHS = {
    'A': 'sources/production/AllocatedOrders',
    'B': 'closing/importer/SkuLocAttributeData',
    'C': 'closing/importer/SkuAttributeData',
    'D': 'closing/importer/LocationAttributeData',
    'E': 'closing/importer/SKUDescriptionTbl',
    'F': 'closing/importer/SiteDescriptionTbl',
}


def _relations(run, paths, products, locations):
    ctes, params = [], []
    for alias, path in paths.items():
        sql, values = image_query(run, path)
        ctes.append(alias + ' AS (' + sql + ')')
        params.extend(values)
    # One value per distinct code with its exact permission-join multiplicity.
    for alias, codes in (('P', products), ('L', locations)):
        values = [(code, codes.multiplicities[code]) for code in sorted(codes)]
        sql = ','.join('(%s::text,%s::integer)' for _ in values)
        ctes.append(alias + '(code,weight) AS (' + ('VALUES ' + sql if values else
            'SELECT NULL::text,0::integer WHERE FALSE') + ')')
        params.extend(v for row in values for v in row)
    return ctes, params


def _permissions(location):
    return (' JOIN P ON ' + equal('A."SKUCode"', 'P.code') +
            ' JOIN L ON ' + equal(location, 'L.code') +
            ' CROSS JOIN LATERAL generate_series(1,P.weight) AS product_occurrence'
            ' CROSS JOIN LATERAL generate_series(1,L.weight) AS location_occurrence')


def _page(sql, params, payload):
    sql = 'SELECT * FROM (' + sql + ') ranked'
    paging = payload.get('paginationParameter')
    if paging is not None:
        if not isinstance(paging, dict) or any(type(paging.get(k)) is not int
                for k in ('pageNumber', 'recordsPerPage')):
            raise ValueError('native order pagination invalid')
        sql += ' WHERE "RN" BETWEEN %s AND %s'
        params += [(paging['pageNumber'] - 1) * paging['recordsPerPage'] + 1,
                   paging['pageNumber'] * paging['recordsPerPage']]
    return sql + ' ORDER BY "RN"', params


def allocation_query(run, payload, products, locations, *, count=False):
    paths = {a: p for a, p in PATHS.items() if not count or a not in ('E', 'F')}
    ctes, params = _relations(run, paths, products, locations)
    filters = AllocationFilters(payload, count=True)
    where = filters.compile()
    attrs_join = ' JOIN ' if count else ' LEFT JOIN '
    joins = (' FROM A' + attrs_join + 'C ON ' + equal('A."SKUCode"', 'C."SKUCode"') +
        attrs_join + 'D ON ' + equal('A."DestWhCode"', 'D."WHCode"') +
        ' LEFT JOIN B ON ' + equal('A."SKUCode"', 'B."SKUCode"') + ' AND ' +
        equal('A."DestWhCode"', 'B."LocCode"'))
    if count:
        select = 'count(*)'
    else:
        joins += (' LEFT JOIN E ON ' + equal('A."SKUCode"', 'E."SKUCode"') +
            ' LEFT JOIN F ON ' + equal('A."DestWhCode"', 'F."WHCode"') +
            ' LEFT JOIN F G ON ' + equal('A."SrcWhCode"', 'G."WHCode"'))
        columns = [('SKUCode', 'A."SKUCode"'), ('SKUDescription', 'E."SKUDescription"'),
            ('DestWhCode', 'A."DestWhCode"'), ('WHDescription', 'F."WHDescription"'),
            ('SrcWhCode', 'A."SrcWhCode"'), ('ParentWhDesc', 'G."WHDescription"')]
        columns += [(n, 'A.' + quote(n)) for n in ('OrderKey', 'DueDate', 'CustomerOrderId',
            'IsSpike', 'Qty', 'OrderColor', 'BPP', 'OrderWiseAllocatedQty', 'PackSizeWiseAllocatedQty')]
        columns += [(f'sl{i}', 'C.' + quote(f'SL{i}')) for i in range(1, 6)]
        columns += [(f'll{i}', 'D.' + quote(f'LL{i}')) for i in range(1, 6)]
        for prefix, owner in (('SKULocAttr', 'B'), ('SKUAttr', 'C'), ('LocAttr', 'D')):
            columns += [(prefix + str(i), 'COALESCE(' + owner + '.' + quote('c' + str(i)) + ",'-')")
                        for i in range(1, 16)]
        select = ('row_number() OVER (ORDER BY ' + key('A."SKUCode"') + ' ASC NULLS FIRST,' +
                  key('A."DestWhCode"') + ' DESC NULLS LAST)::integer AS "RN",' +
                  ','.join(expression + ' AS ' + quote(name) for name, expression in columns))
    sql = ('WITH ' + ','.join(ctes) + ' SELECT ' + select + joins +
           _permissions('A."DestWhCode"') + ' WHERE A."OrderColor" IS NOT NULL AND (' + where + ')')
    params += filters.params
    return (sql, params) if count else _page(sql, params, payload)


def elephant_query(run, payload, products, locations, *, count=False):
    paths = {'A': 'closing/orders/ElephantOrders'}
    if not count:
        paths.update(B=PATHS['E'], C=PATHS['F'])
    ctes, params = _relations(run, paths, products, locations)
    joins = ' FROM A'
    if count:
        select = 'count(*)'
    else:
        joins += (' LEFT JOIN B ON ' + equal('A."SKUCode"', 'B."SKUCode"') +
            ' LEFT JOIN C ON ' + equal('A."WhCode"', 'C."WHCode"') +
            ' LEFT JOIN C D ON ' + equal('A."TopmostWhCode"', 'D."WHCode"'))
        fields = [(n, 'A.' + quote(n)) for n in ('CustomerOrderID', 'SKUCode')]
        fields += [('SKUDescription', 'COALESCE(B."SKUDescription",\'-\')')]
        fields += [(n, 'A.' + quote(n)) for n in ('WhCode', 'Qty', 'TopmostWhCode')]
        fields += [('WHDescription', 'COALESCE(D."WHDescription",\'-\')')]
        fields += [(n, 'A.' + quote(n)) for n in ('TopmostWhNorm', 'RLTUptoSuppOrPlant')]
        fields += [(n, 'A.' + quote(n) + '::date::text') for n in ('IntroDate', 'CustomerExpectedDate')]
        fields += [('EPD', '(A."IntroDate"::date+A."RLTUptoSuppOrPlant"::integer)::text'),
                   ('DueDate', 'A."DueDate"')]
        select = ('row_number() OVER (ORDER BY A."IntroDate" DESC NULLS LAST) AS "RN",' +
                  ','.join(expression + ' AS ' + quote(name) for name, expression in fields))
    # The deployed Elephant reader intentionally does not apply request filters.
    sql = 'WITH ' + ','.join(ctes) + ' SELECT ' + select + joins + _permissions('A."WhCode"')
    return (sql, params) if count else _page(sql, params, payload)


def read(payload, *, elephant=False, count=False):
    run = selected_run()
    attrs = {name: image_rows(run, 'closing/importer/' + name)
             for name in ('SkuAttributeData', 'LocationAttributeData')}
    products, locations = scope(payload, attributes=attrs)
    query = elephant_query if elephant else allocation_query
    sql, params = query(run, payload, products, locations, count=count)
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        if count:
            return cursor.fetchone()[0]
        names = [item[0] for item in cursor.description]
        return [{name: (int(value) if value == value.to_integral_value() else float(value))
                 if isinstance(value, Decimal) else value
                 for name, value in zip(names, row)} for row in cursor.fetchall()]
