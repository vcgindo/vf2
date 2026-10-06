"""Pinned Location configuration and scoped master2 reads."""
import json
from pathlib import Path

from django.db import connection

from mta.presentation.context import permission_catalogue
from mta.presentation.rrr_sql import equal, key, like_pattern
from mta.runtime.mdm_models import MdmLocationAttributes, MdmLocationDescription

CONFIG = json.loads((Path(__file__).resolve().parents[1] / 'config/mdm_location.json').read_text())
FIELDS = {row['Col_Code']: row for row in CONFIG['UI_MDMConfig']}
ALIASES = {alias: row['TableField'] for alias, row in FIELDS.items()}


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


def column(alias):
    name = ALIASES[alias]
    return ('d.' if alias == 'wd' else 'a.') + connection.ops.quote_name(name)


def filters(items):
    clauses, params = [], []
    for item in items or []:
        alias, operator = item['attributeName'], item['op']
        col = column(alias)
        if operator in ('hasValue', 'hasNoValue'):
            empty = '(' + col + " IS NULL OR " + col + "::text ~ '^ *$')"
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
            expression = key(col) + operator + key('%s')
            if operator == '<>':
                expression = '(' + col + ' IS NULL OR ' + expression + ')'
            clauses.append(expression)
            params.append(value)
    return ' AND '.join(clauses) or 'TRUE', params


def read(source, payload, *, count=False):
    if int(payload['id']) != 2:
        raise ValueError('MDM family is not delivered')
    permissions = payload.get('location_permissions') or []
    if not permissions:
        return '' if count else None
    tuples = [tuple(row['level_' + str(i)] for i in range(1, 4))
        for row in permission_catalogue()['locations']['records'] if row['id'] in permissions]
    permission_sql = 'SELECT NULL::text AS p1,NULL::text AS p2,NULL::text AS p3 WHERE FALSE'
    params = []
    if tuples:
        permission_sql = 'VALUES ' + ','.join('(%s::text,%s::text,%s::text)' for _ in tuples)
        params = [value for row in tuples for value in row]
    attr = connection.ops.quote_name(MdmLocationAttributes._meta.db_table)
    desc = connection.ops.quote_name(MdmLocationDescription._meta.db_table)
    hierarchy_join = ' AND '.join(equal('a."LL' + str(i) + '"', 'p.p' + str(i)) for i in range(1, 4))
    prefix = 'WITH permissions(p1,p2,p3) AS (' + permission_sql + '), locations AS (SELECT a."WHCode" FROM ' + attr
    prefix += ' a JOIN permissions p ON ' + hierarchy_join + " WHERE a.owner='Importer' AND a.source_id=%s) "
    params.append(source.pk)
    where, values = filters(payload.get('filters'))
    if count:
        sql = prefix + 'SELECT count(*) FROM ' + attr + ' a JOIN locations l ON ' + equal('a."WHCode"', 'l."WHCode"')
        sql += ' JOIN ' + desc + ' d ON ' + equal('a."WHCode"', 'd."WHCode"')
        sql += " AND d.source_id=a.source_id AND d.owner=a.owner WHERE a.owner='Importer' AND a.source_id=%s AND " + where
        params += [source.pk, *values]
    else:
        requested = [field['key'] for field in payload['fields']]
        if not requested or 'wc' not in requested:
            return None
        select = ','.join(column(alias) + ' AS ' + connection.ops.quote_name(alias) for alias in requested)
        paging = payload.get('paginationParameter')
        aliases = ','.join(connection.ops.quote_name(alias) for alias in requested)
        if paging is not None:
            sql = prefix + 'SELECT json_agg(json_strip_nulls(row_to_json(result))) FROM (SELECT ' + aliases
            sql += ' FROM (SELECT ' + select + ',row_number() OVER (ORDER BY ' + key('a."WHCode"') + ' DESC) AS rn'
        else:
            sql = prefix + 'SELECT json_agg(json_strip_nulls(row_to_json(result))) FROM (SELECT ' + select
        sql += ' FROM ' + desc + ' d LEFT JOIN ' + attr + ' a ON ' + equal('a."WHCode"', 'd."WHCode"')
        sql += ' AND a.source_id=d.source_id AND a.owner=d.owner JOIN locations l ON ' + equal('a."WHCode"', 'l."WHCode"')
        sql += " WHERE d.owner='Importer' AND d.source_id=%s AND " + where
        params += [source.pk, *values]
        if paging is not None:
            page, size = int(paging['pageNumber']), int(paging['recordsPerPage'])
            lower, upper = (page - 1) * size + 1, page * size
            sql += ') ranked WHERE rn BETWEEN %s AND %s'
            params += [lower, upper]
        else:
            sql += ''
        sql += ') result'
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        value = cursor.fetchone()[0]
    return str(value) if count else value
