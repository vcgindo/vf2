"""Pinned master-13 configuration and native Force Norm current projection."""
import json
from decimal import Decimal
from pathlib import Path

from django.db import connection

from mta.mdm.supplier_permissions import sql_permissions
from mta.presentation.rrr_sql import equal, key, like_pattern
from mta.runtime.mdm_models import MdmLocationAttributes, MdmSkuAttributes
from mta.runtime.mdm_skuloc_models import MdmSkuLocCurrent


CONFIG = json.loads((Path(__file__).resolve().parents[1] / 'config/mdm_force.json').read_text())
FIELDS = {row['Col_Code']: row for row in CONFIG['UI_MDMConfig']}
ALIASES = {alias: row['TableField'] for alias, row in FIELDS.items()}
DRAFT_ALIASES = dict(ALIASES)
NUMERIC = {'nn'}


def configuration(screen_type):
    mapper = CONFIG['MasterMapper'][0]
    flag = {'add': 'IsAdd', 'modify': 'IsModify', 'remove': 'IsRemove'}.get(screen_type)
    if flag and not mapper[flag]:
        return []
    fields = [dict(displayName=row['Header'], key=alias,
        col_Position=str(row['Col_Position']), visible=row['Visible'],
        isAdd=row['IsAdd'], isEdit=row['IsEdit'], isDelete=row['IsDelete'],
        isDownload=row['IsDownload'], isApplicable=row['IsApplicable'],
        dataType=row['DataType']) for alias, row in FIELDS.items()]
    return [dict(id=str(mapper['MasterId']), name=mapper['MasterName'], fields=fields)]


def _column(alias):
    # The configured NewNorm projection is sourced from NMSAllItems.Norm.
    name = 'Norm' if alias == 'nn' else ALIASES[alias]
    return 'n.' + connection.ops.quote_name(name)


def _filters(items):
    clauses, params = [], []
    for item in items or []:
        alias, operator = item['attributeName'], item['op']
        column = _column(alias)
        numeric = alias in NUMERIC
        if operator in ('hasValue', 'hasNoValue'):
            empty = '(' + column + (' IS NULL OR ' + column + '=0)' if numeric else " IS NULL OR " + column + "::text ~ '^ *$')")
            clauses.append(('NOT ' if operator == 'hasValue' else '') + empty)
        elif operator in ('contains', 'startsWith', 'endsWith',
                          'Notcontains', 'NotstartsWith', 'NotendsWith'):
            value = '' if item.get('value') is None else str(item['value'])
            pattern = ('%' if operator.endswith(('contains', 'endsWith')) else '') + value
            pattern += '%' if operator.endswith(('contains', 'startsWith')) else ''
            clauses.append(column + ('::text !~* %s' if operator.startswith('Not') else '::text ~* %s'))
            params.append(like_pattern(pattern))
        else:
            if operator not in ('=', '!=', '<>', '>', '>=', '<', '<='):
                raise ValueError('unsupported MDM filter operator')
            value = '' if item.get('value') is None else item['value']
            expression = column + operator + '%s' if numeric else key(column) + operator + key('%s')
            if operator == '<>':
                expression = '(' + column + ' IS NULL OR ' + expression + ')'
            clauses.append(expression)
            params.append(Decimal(str(value) or '0') if numeric else value)
    return ' AND '.join(clauses) or 'TRUE', params


def read(source, payload, *, count=False):
    if int(payload['id']) != 13:
        raise ValueError('MDM family is not delivered')
    product_ids = payload.get('product_permissions') or []
    location_ids = payload.get('location_permissions') or []
    if not product_ids or not location_ids:
        return '' if count else None
    product_sql, params = sql_permissions('products', product_ids)
    location_sql, location_params = sql_permissions('locations', location_ids)
    params += location_params
    from mta.mdm.force_display import current_model
    current = current_model(source)
    table = lambda model: connection.ops.quote_name(model._meta.db_table)
    sku_join = ' AND '.join("lower(btrim(s.\"SL%d\",' '))=p.p%d" % (i, i) for i in range(1, 4))
    location_join = ' AND '.join("lower(btrim(l.\"LL%d\",' '))=q.p%d" % (i, i) for i in range(1, 4))
    prefix = ('WITH product_permissions(p1,p2,p3) AS (' + product_sql + '), '
        'location_permissions(p1,p2,p3) AS (' + location_sql + '), '
        'skus AS (SELECT s."SKUCode" FROM ' + table(MdmSkuAttributes) + ' s '
        'JOIN product_permissions p ON ' + sku_join + " WHERE s.source_id=%s AND s.owner='Importer'), "
        'locations AS (SELECT l."WHCode" FROM ' + table(MdmLocationAttributes) + ' l '
        'JOIN location_permissions q ON ' + location_join + " WHERE l.source_id=%s AND l.owner='Importer') ")
    params += [source.pk, source.pk]
    where, values = _filters(payload.get('filters'))
    base = (' FROM ' + table(current) + ' n '
        'JOIN skus s ON ' + equal('n."SKUCode"', 's."SKUCode"') +
        ' JOIN locations l ON ' + equal('n."WhCode"', 'l."WHCode"') +
        " WHERE n.source_id=%s AND n.owner='Importer' AND " + where)
    params += [source.pk, *values]
    if count:
        sql = prefix + 'SELECT count(*)' + base
    else:
        requested = [field['key'] for field in payload['fields']]
        if not requested:
            return None
        selected = ','.join(_column(alias) + ' AS ' + connection.ops.quote_name(alias)
                            for alias in requested)
        paging = payload.get('paginationParameter')
        if paging is None:
            sql = prefix + ('SELECT json_agg(json_strip_nulls(row_to_json(projected))) '
                'FROM (SELECT ' + selected + base + ') projected')
        else:
            order = ','.join((_column(alias) if alias in NUMERIC else key(_column(alias)))
                             for alias in requested)
            projected = ','.join(connection.ops.quote_name(alias) for alias in requested)
            page, size = int(paging['pageNumber']), int(paging['recordsPerPage'])
            lower, upper = (page - 1) * size + 1, page * size
            sql = prefix + ('SELECT json_agg(json_strip_nulls(row_to_json(projected))) FROM '
                '(SELECT ' + projected + ' FROM (SELECT ' + selected + ',RANK() OVER (ORDER BY ' +
                order + ') AS native_rn' + base + ') ranked WHERE native_rn BETWEEN %s AND %s) projected')
            params += [lower, upper]
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        result = cursor.fetchone()[0]
    return str(result) if count else result
