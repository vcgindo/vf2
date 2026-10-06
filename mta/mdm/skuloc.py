"""Pinned master-3 configuration and multiplicity-preserving current reads."""
import json
from decimal import Decimal
from pathlib import Path

from django.db import connection

from mta.presentation.context import permission_catalogue
from mta.presentation.rrr_sql import equal, key, like_pattern
from mta.runtime.mdm_models import MdmLocationAttributes, MdmSkuAttributes
from mta.runtime.mdm_skuloc_models import MdmSkuLocCurrent

CONFIG = json.loads((Path(__file__).resolve().parents[1] / 'config/mdm_skuloc.json').read_text())
FIELDS = {row['Col_Code']: row for row in CONFIG['UI_MDMConfig']}
ALIASES = {alias: ({'StockPercentForRat':'StockPercentForRationing','WHCode':'WhCode'}
                   .get(row['TableField'],row['TableField'])) for alias, row in FIELDS.items()}
DRAFT_ALIASES = {alias: ({'WHCode':'WhCode'}.get(row['TableField'],row['TableField']))
                 for alias, row in FIELDS.items()}
NUMERIC = {alias for alias, row in FIELDS.items() if row['DataType'] == 'Number'}


def configuration(screen_type):
    mapper = CONFIG['MasterMapper'][0]
    flag = {'add': 'IsAdd', 'modify': 'IsModify', 'remove': 'IsRemove'}.get(screen_type)
    if flag and not mapper[flag]:
        return []
    fields = [dict(displayName=row['Header'], key=alias,
        col_Position=str(row['Col_Position']), visible=row['Visible'],
        isAdd=row['IsAdd'], isEdit=row['IsEdit'], isDelete=row['IsDelete'],
        isDownload=row['IsDownload'], isApplicable=row['IsApplicable'], dataType=row['DataType'])
        for alias, row in FIELDS.items()]
    return [dict(id=str(mapper['MasterId']), name=mapper['MasterName'], fields=fields)]


def column(alias, owner='n'):
    return owner + '.' + connection.ops.quote_name(ALIASES[alias])


def filters(items):
    clauses, params = [], []
    for item in items or []:
        alias, operator = item['attributeName'], item['op']
        col = column(alias)
        numeric = alias in NUMERIC
        if operator in ('hasValue', 'hasNoValue'):
            empty = '(' + col + ' IS NULL OR ' + col + ('=0)' if numeric else "::text ~ '^ *$')")
            clauses.append(('NOT ' if operator == 'hasValue' else '') + empty)
        elif operator in ('contains', 'startsWith', 'endsWith', 'Notcontains', 'NotstartsWith', 'NotendsWith'):
            value = str(item['value']) if item.get('value') is not None else ''
            pattern = ('%' if operator.endswith(('contains', 'endsWith')) else '') + value
            pattern += '%' if operator.endswith(('contains', 'startsWith')) else ''
            clauses.append(col + ('::text !~* %s' if operator.startswith('Not') else '::text ~* %s'))
            params.append(like_pattern(pattern))
        else:
            if operator not in ('=', '!=', '<>', '>', '>=', '<', '<='):
                raise ValueError('unsupported MDM filter operator')
            value = item['value'] if item.get('value') is not None else ''
            if numeric:
                value = Decimal(str(value) or '0')
                expression = col + operator + '%s'
            else:
                expression = key(col) + operator + key('%s')
            if operator == '<>':
                expression = '(' + col + ' IS NULL OR ' + expression + ')'
            clauses.append(expression)
            params.append(value)
    return ' AND '.join(clauses) or 'TRUE', params


def _permissions(kind, ids):
    records = permission_catalogue()[kind]['records']
    prefix = 'level_'
    tuples = [tuple(row[prefix + str(i)] for i in range(1, 4)) for row in records if row['id'] in ids]
    if not tuples:
        return 'SELECT NULL::text,NULL::text,NULL::text WHERE FALSE', []
    return ('VALUES ' + ','.join('(%s::text,%s::text,%s::text)' for _ in tuples),
            [value for row in tuples for value in row])


def read(source, payload, *, count=False):
    if int(payload['id']) != 3:
        raise ValueError('MDM family is not delivered')
    product_ids = payload.get('product_permissions') or []
    location_ids = payload.get('location_permissions') or []
    if not product_ids or not location_ids:
        return '' if count else None
    product_sql, params = _permissions('products', product_ids)
    location_sql, location_params = _permissions('locations', location_ids)
    params += location_params
    current = connection.ops.quote_name(MdmSkuLocCurrent._meta.db_table)
    sku = connection.ops.quote_name(MdmSkuAttributes._meta.db_table)
    location = connection.ops.quote_name(MdmLocationAttributes._meta.db_table)
    sku_join = ' AND '.join(equal('s."SL%d"' % i, 'p.p%d' % i) for i in range(1, 4))
    loc_join = ' AND '.join(equal('l."LL%d"' % i, 'q.p%d' % i) for i in range(1, 4))
    prefix = ('WITH product_permissions(p1,p2,p3) AS (' + product_sql + '), '
              'location_permissions(p1,p2,p3) AS (' + location_sql + '), '
              'skus AS (SELECT s."SKUCode" FROM ' + sku + ' s JOIN product_permissions p ON ' + sku_join +
              " WHERE s.source_id=%s AND s.owner='Importer'), "
              'locations AS (SELECT l."WHCode" FROM ' + location + ' l JOIN location_permissions q ON ' + loc_join +
              " WHERE l.source_id=%s AND l.owner='Importer') ")
    params += [source.pk, source.pk]
    where, values = filters(payload.get('filters'))
    base = (' FROM ' + current + ' n JOIN skus s ON ' + equal('n."SKUCode"', 's."SKUCode"') +
            ' JOIN locations l ON ' + equal('n."WhCode"', 'l."WHCode"') +
            " WHERE n.source_id=%s AND n.owner='Importer' AND " + where)
    params += [source.pk, *values]
    if count:
        sql = prefix + 'SELECT count(*)' + base
    else:
        requested = [field['key'] for field in payload['fields']]
        if not requested:
            return None
        select = ','.join(column(alias) + ' AS ' + connection.ops.quote_name(alias) for alias in requested)
        projected = ','.join(connection.ops.quote_name(alias) for alias in requested)
        order = ','.join((column(alias) if alias in NUMERIC else key(column(alias))) + ' ASC NULLS FIRST'
                         for alias in requested)
        ranked = 'SELECT ' + select + ',RANK() OVER (ORDER BY ' + order + ') AS native_rn' + base
        paging = payload.get('paginationParameter')
        if paging is None:
            # Native leaves the unpaged bag unordered; its computed RN is not
            # projected or filtered and therefore has no consumer effect.
            sql = prefix + 'SELECT json_agg(json_strip_nulls(row_to_json(projected))) FROM (SELECT ' + select + base + ') projected'
        else:
            page, size = int(paging['pageNumber']), int(paging['recordsPerPage'])
            lower, upper = (page - 1) * size + 1, page * size
            sql = prefix + 'SELECT json_agg(json_strip_nulls(row_to_json(projected))) FROM (SELECT ' + projected + ' FROM (' + ranked
            sql += ') ranked WHERE native_rn BETWEEN %s AND %s) projected'
            params += [lower, upper]
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        value = cursor.fetchone()[0]
    return str(value) if count else value
