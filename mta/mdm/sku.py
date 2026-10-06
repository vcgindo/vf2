"""Pinned SKU configuration and scoped SQL reads (MDMProcessor master1).

The grid's two attribute joins and LEFT description join intentionally differ
from the count's direct permission and INNER description joins.
"""
import json
from decimal import Decimal
from pathlib import Path

from django.db import connection
from mta.presentation.context import permission_catalogue
from mta.presentation.rrr_sql import equal, key, like_pattern
from mta.runtime.mdm_models import MdmSkuAttributes, MdmSkuDescription

CONFIG = json.loads((Path(__file__).resolve().parents[1] / 'config/mdm_sku.json').read_text())
FIELDS = {row['Col_Code']: row for row in CONFIG['UI_MDMConfig']}
ALIASES = {alias: row['TableField'] for alias, row in FIELDS.items()}


def configuration(screen_type):
    mapper = CONFIG['MasterMapper'][0]
    flag = {'add': 'IsAdd', 'modify': 'IsModify', 'remove': 'IsRemove'}.get(screen_type)
    if flag and not mapper[flag]:
        return []
    fields = []
    for alias, row in FIELDS.items():
        fields.append(dict(displayName=row['Header'], key=alias,
            col_Position=str(row['Col_Position']), visible=row['Visible'],
            isAdd=row['IsAdd'], isEdit=row['IsEdit'], isDelete=row['IsDelete'],
            isDownload=row['IsDownload'], isApplicable=row['IsApplicable'], dataType=row['DataType']))
    return [dict(id=str(mapper['MasterId']), name=mapper['MasterName'], fields=fields)]


def column(alias):
    name = ALIASES[alias]
    return ('d.' if alias == 'sd' else 'a.') + connection.ops.quote_name(name)


def filters(items):
    clauses, params = [], []
    for item in items or []:
        alias, operator = item['attributeName'], item['op']
        col = column(alias)
        numeric = alias in ('ec', 'wt', 'vm')
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


def read(source, payload, *, count=False):
    if int(payload['id']) != 1:
        raise ValueError('MDM family is not delivered')
    permissions = payload.get('product_permissions') or []
    # Native empty IDs fail conversion in the SQL helper; preserve its result.
    if not permissions:
        return '' if count else None
    tuples = [tuple(row['level_' + str(i)] for i in range(1, 4))
        for row in permission_catalogue()['products']['records'] if row['id'] in permissions]
    permission_sql = 'SELECT NULL::text AS p1,NULL::text AS p2,NULL::text AS p3 WHERE FALSE'
    params = []
    if tuples:
        permission_sql = 'VALUES ' + ','.join('(%s::text,%s::text,%s::text)' for _ in tuples)
        params = [value for row in tuples for value in row]
    attr = connection.ops.quote_name(MdmSkuAttributes._meta.db_table)
    desc = connection.ops.quote_name(MdmSkuDescription._meta.db_table)
    hierarchy_join = ' AND '.join(equal('a."SL' + str(i) + '"', 'p.p' + str(i)) for i in range(1, 4))
    prefix = 'WITH permissions(p1,p2,p3) AS (' + permission_sql + ') '
    where, values = filters(payload.get('filters'))
    if count:
        sql = prefix + 'SELECT count(*) FROM ' + attr + ' a JOIN permissions p ON ' + hierarchy_join
        sql += ' JOIN ' + desc + ' d ON ' + equal('a."SKUCode"', 'd."SKUCode"')
        sql += " AND d.source_id=a.source_id AND d.owner=a.owner WHERE a.owner='Importer' AND a.source_id=%s AND " + where
        params += [source.pk, *values]
    else:
        requested = [field['key'] for field in payload['fields']]
        if not requested or 'sc' not in requested:
            return None  # Native derived-table ORDER BY sc is otherwise invalid.
        prefix = prefix.rstrip() + ', skus AS (SELECT a."SKUCode" FROM ' + attr
        prefix += ' a JOIN permissions p ON ' + hierarchy_join + " WHERE a.owner='Importer' AND a.source_id=%s) "
        params.append(source.pk)
        select = ','.join(column(alias) + ' AS ' + connection.ops.quote_name(alias) for alias in requested)
        sql = prefix + 'SELECT json_agg(json_strip_nulls(row_to_json(result))) FROM (SELECT ' + select
        sql += ' FROM ' + attr + ' a LEFT JOIN ' + desc + ' d ON ' + equal('a."SKUCode"', 'd."SKUCode"')
        sql += ' AND d.source_id=a.source_id AND d.owner=a.owner JOIN skus s ON ' + equal('a."SKUCode"', 's."SKUCode"')
        sql += " WHERE a.owner='Importer' AND a.source_id=%s AND " + where
        params += [source.pk, *values]
        paging = payload.get('paginationParameter')
        if paging is not None:
            sql += ' ORDER BY ' + key('a."SKUCode"') + ' DESC'
            page, size = int(paging['pageNumber']), int(paging['recordsPerPage'])
            # Native BETWEEN accepts nonpositive endpoints without inventing defaults.
            lower, upper = (page - 1) * size + 1, page * size
            sql += ' LIMIT %s OFFSET %s'
            params += [max(0, upper - max(1, lower) + 1), max(0, lower - 1)]
        sql += ') result'
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        value = cursor.fetchone()[0]
    return str(value) if count else value
