"""Pinned RRROA consumer joins over the separately admitted daily source.

PlanningProcessor SHA bf716c4f84e43920b5f2ab302e3d3c78ec685f5d714471c53047d377537d3486;
GenericFunction SHA 6850a0bf2eadb4a38a2998e96ef70a264a2bc529d0de5c433c066d76c1933420.
"""
from django.db import connection
from mta.presentation import hierarchy
from mta.presentation.context import permission_catalogue, scope, PublicationUnavailable
from mta.presentation.boroa_filters import BorOaFilters, BorOaQueryError
from mta.presentation.rrr_sql import equal, key
from mta.presentation.selective import image_rows, image_query
from mta.presentation.daily_rrr_colour import OUTPUT_FIELDS
from mta.runtime.relational_state import CATALOG, quote


class Filters(BorOaFilters):
    def __init__(self, payload):
        # Both RRROA count and grid use C for product attributes. The shared
        # Commons builder's only alias difference from BOROA is F -> A.
        super().__init__(payload, count=False)

    def column(self, owner, name):
        owner = 'A' if owner == 'F' else owner
        if owner == 'A':
            fields = {field.casefold(): (field, 'nvarchar' if field in (
                'SKUCode', 'WhCode', 'ParentWhCode', 'AllocationFor', 'DispatchColor')
                else 'int') for field in OUTPUT_FIELDS}
        else:
            table = {'B': 'SkuLocAttributeData', 'C': 'SkuAttributeData',
                     'D': 'LocationAttributeData'}[owner]
            fields = {field.casefold(): (field, kind) for field, kind in CATALOG['tables']['Importer/'+table]}
        if name.casefold() not in fields:
            raise BorOaQueryError('native RRROA filter column missing: '+owner+'.'+name)
        field, kind = fields[name.casefold()]
        return owner+'.'+quote(field), kind


def projection():
    result = [(field, 'A.'+quote(field)) for field in OUTPUT_FIELDS]
    for index, code in enumerate(('SKUDescription', 'WHDescription', 'ParentWhDesc'), 1):
        result.append((code, 'S'+str(index)+'.'+quote('SKUDescription' if index == 1 else 'WHDescription')))
    result.extend((prefix+str(i), alias+'.'+quote(prefix+str(i)))
                  for prefix, alias in (('sl', 'C'), ('ll', 'D')) for i in range(1, 6))
    # Operational hierarchy columns retain their native upper-case spelling.
    result = [(name, expression.replace('"sl', '"SL').replace('"ll', '"LL'))
              for name, expression in result]
    result.extend((prefix+str(i), 'COALESCE('+alias+'.'+quote('c'+str(i))+",'-')")
                  for prefix, alias in (('SKULocAttr', 'B'), ('SKUAttr', 'C'), ('LocAttr', 'D'))
                  for i in range(1, 16))
    return result


def read(run, payload, *, count=False, export=False):
    from django.conf import settings
    from mta.presentation import native_publication
    native = native_publication.enabled()
    if native:
        native_publication.require_mode()
        from mta.runtime.production_report_storage import PATHS
        source_path = PATHS['RRR_OrderAllocation']
        # Full typed source/checksum admission precedes the bounded SQL reader.
        image_rows(run, source_path)
        source_sql, source_params = image_query(run, source_path)
    else:
        from mta.presentation.offline_rrr import VERSION as OFFLINE_VERSION
        if getattr(settings, 'VF_MTA_RRR_COLOUR_EXTENSION', '') == OFFLINE_VERSION:
            from mta.presentation.offline_rrr import read_published as read_source
            from mta.runtime.offline_rrr_models import OfflineRrrColourRow as DailyRrrColourRow
        else:
            from mta.presentation.daily_rrr_storage import read as read_source
            from mta.runtime.daily_rrr_models import DailyRrrColourRow
        read_source(run)
        source_sql = ('SELECT * FROM mta.' + quote(DailyRrrColourRow._meta.db_table)
                      + ' WHERE receipt_id=%s')
        source_params = [run.pk]
    importer = {name: image_rows(run, 'closing/importer/'+name)
                for name in ('SkuAttributeData', 'LocationAttributeData')}
    manifest = hierarchy.selected_manifest(run)
    if manifest or not native:
        importer = hierarchy.project_attributes(importer, permission_catalogue(), manifest)
    products, locations = scope(payload, attributes=importer)
    ctes = ['A AS (' + source_sql + ')']
    params = list(source_params)
    for alias, table in (('B', 'SkuLocAttributeData'), ('C', 'SkuAttributeData'),
                         ('D', 'LocationAttributeData'), ('S1', 'SKUDescriptionTbl'),
                         ('S2', 'SiteDescriptionTbl'), ('S3', 'SiteDescriptionTbl')):
        sql, values = image_query(run, 'closing/importer/'+table)
        ctes.append(alias+'native AS ('+sql+')')
        params.extend(values)
        if alias in ('C', 'D'):
            prefix = 'SL' if alias == 'C' else 'LL'
            rows = importer[table]
            if not rows:
                raise PublicationUnavailable('daily_rrr_hierarchy_population_missing')
            ctes.append(alias+'h(ordinal,h1,h2,h3) AS (VALUES '+
                        ','.join(['(%s::bigint,%s::text,%s::text,%s::text)']*len(rows))+')')
            params.extend(v for i, row in enumerate(rows) for v in
                          (i, row[prefix+'1'], row[prefix+'2'], row[prefix+'3']))
            columns = ['H.h'+field[-1]+' AS '+quote(field) if field in
                       (prefix+'1', prefix+'2', prefix+'3') else 'N.'+quote(field)
                       for field, _ in CATALOG['tables']['Importer/'+table]]
            ctes.append(alias+' AS (SELECT '+','.join(columns)+' FROM '+alias+
                        'native N JOIN '+alias+'h H ON H.ordinal=N.vf_ordinal)')
        else:
            ctes.append(alias+' AS (SELECT * FROM '+alias+'native)')
    for alias, codes in (('P', products), ('L', locations)):
        members = sorted(codes)
        if members:
            ctes.append(alias+'w(code,weight) AS (VALUES '+','.join(['(%s::text,%s::bigint)']*len(members))+')')
            params.extend(v for code in members for v in (code, codes.multiplicities[code]))
            ctes.append(alias+' AS (SELECT code FROM '+alias+'w CROSS JOIN LATERAL generate_series(1,weight))')
        else:
            ctes.append(alias+' AS (SELECT NULL::text AS code WHERE FALSE)')
    joins = ' FROM A JOIN P ON '+equal('A."SKUCode"', 'P.code')+' JOIN L ON '+equal('A."WhCode"', 'L.code')
    for alias, left, right in (('B', 'SKUCode', 'SKUCode'), ('C', 'SKUCode', 'SKUCode'), ('D', 'WhCode', 'WHCode')):
        joins += ' LEFT JOIN '+alias+' ON '+equal('A.'+quote(left), alias+'.'+quote(right))
        if alias == 'B':
            joins += ' AND '+equal('A."WhCode"', 'B."LocCode"')
    if not count:
        for alias, left, right in (('S1', 'SKUCode', 'SKUCode'), ('S2', 'WhCode', 'WHCode'), ('S3', 'ParentWhCode', 'WHCode')):
            joins += ' LEFT JOIN '+alias+' ON '+equal('A.'+quote(left), alias+'.'+quote(right))
    filters = Filters(payload)
    where = filters.compile()
    if filters.children:
        joins += (' JOIN Dnative parent ON '+equal('A."ParentWhCode"', 'parent."WHCode"')+' AND ('+
            ' OR '.join(equal('parent."LocationType"', '%s') for _ in filters.children)+')')
        params.extend(filters.children)
    selected = 'count(*)' if count else (
        'row_number() OVER (ORDER BY '+key('A."SKUCode"')+' ASC NULLS FIRST,'+
        key('A."WhCode"')+' DESC NULLS LAST)::integer AS "RN",'+
        ','.join(expression+' AS '+quote(name) for name, expression in projection()))
    sql = 'WITH '+','.join(ctes)+' SELECT '+selected+joins+' WHERE '+where
    params.extend(filters.params)
    if not count:
        sql = 'SELECT * FROM ('+sql+') ranked'
        paging = payload.get('paginationParameter')
        if paging is not None and not export:
            if not isinstance(paging, dict) or any(type(paging.get(name)) is not int
                    for name in ('pageNumber', 'recordsPerPage')):
                raise ValueError('native RRROA pagination invalid')
            sql += ' WHERE "RN" BETWEEN %s AND %s'
            params.extend(((paging['pageNumber']-1)*paging['recordsPerPage']+1,
                           paging['pageNumber']*paging['recordsPerPage']))
        sql += ' ORDER BY "RN"'
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        if count:
            return cursor.fetchone()[0]
        fields = [column[0] for column in cursor.description]
        return [dict(zip(fields, row)) for row in cursor.fetchall()]
