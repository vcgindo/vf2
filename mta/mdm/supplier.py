"""Master4/5 configuration and native raw-master current projections."""
import json
from pathlib import Path
from decimal import Decimal

from django.db import connection
from mta.mdm.supplier_permissions import sql_permissions as _permissions
from mta.presentation.rrr_sql import equal, key, like_pattern
from mta.runtime.mdm_models import (MdmSkuAttributes, MdmLocationAttributes,
                                    MdmSkuDescription, MdmLocationDescription)
from mta.runtime.mdm_supplier_models import (MdmSupplierConfiguration, MdmSobRaw,
    MdmMoqRaw1, MdmMoqRaw2, MdmSobApproved)

CONFIG = {mid: json.loads((Path(__file__).resolve().parents[1] /
    ('config/mdm_' + name + '.json')).read_text()) for mid, name in ((4, 'sob'), (5, 'moq'))}


def configuration(master_id, screen_type):
    config = CONFIG[master_id]
    mapper = config['MasterMapper'][0]
    flag = {'add': 'IsAdd', 'modify': 'IsModify', 'remove': 'IsRemove'}.get(screen_type)
    if flag and not mapper[flag]:
        return []
    fields = [dict(displayName=r['Header'], key=r['Col_Code'],
        col_Position=str(r['Col_Position']), visible=r['Visible'], isAdd=r['IsAdd'],
        isEdit=r['IsEdit'], isDelete=r['IsDelete'], isDownload=r['IsDownload'],
        isApplicable=r['IsApplicable'], dataType=r['DataType']) for r in config['UI_MDMConfig']]
    return [dict(id=str(master_id), name=mapper['MasterName'], fields=fields)]


def setting(source):
    return MdmSupplierConfiguration.objects.get(source=source).moq_format


def _column(master_id, alias):
    names = {r['Col_Code']: r['TableField'] for r in CONFIG[master_id]['UI_MDMConfig']}
    name = names[alias]
    if name == 'WhCode':
        name = 'WHCode'
    owner = 'sd' if alias == 'sd' else 'wd' if alias == 'wd' else 'a'
    return owner + '.' + connection.ops.quote_name(name)


def _filters(master_id, items):
    clauses, params = [], []
    for item in items or []:
        alias, op = item['attributeName'], item['op']
        col = _column(master_id, alias)
        numeric = alias in ('sb', 'mq')
        if op in ('hasValue', 'hasNoValue'):
            empty = '(' + col + ' IS NULL OR ' + col + ('=0)' if numeric else "::text ~ '^ *$')")
            clauses.append(('NOT ' if op == 'hasValue' else '') + empty)
        elif op in ('contains', 'startsWith', 'endsWith', 'Notcontains', 'NotstartsWith', 'NotendsWith'):
            value = '' if item.get('value') is None else str(item['value'])
            pattern = ('%' if op.endswith(('contains', 'endsWith')) else '') + value
            pattern += '%' if op.endswith(('contains', 'startsWith')) else ''
            clauses.append(col + ('::text !~* %s' if op.startswith('Not') else '::text ~* %s'))
            params.append(like_pattern(pattern))
        else:
            if op not in ('=', '!=', '<>', '>', '>=', '<', '<='):
                raise ValueError('unsupported MDM filter operator')
            value = '' if item.get('value') is None else item['value']
            expression = col + op + '%s' if numeric else key(col) + op + key('%s')
            if op == '<>':
                expression = '(' + col + ' IS NULL OR ' + expression + ')'
            clauses.append(expression)
            params.append(Decimal(str(value) or '0') if numeric else value)
    return ' AND '.join(clauses) or 'TRUE', params


def read(source, payload, *, count=False):
    master_id = int(payload['id'])
    if master_id not in (4, 5):
        raise ValueError('Not a supplier family')
    product_ids = payload.get('product_permissions') or []
    location_ids = payload.get('location_permissions') or []
    if not product_ids or (master_id == 4 and not location_ids):
        return '' if count else None
    table = lambda model: connection.ops.quote_name(model._meta.db_table)
    product_sql, params = _permissions('products', product_ids)
    product_join = ' AND '.join('lower(btrim(s."SL%d",\' \'))=p.p%d' % (i, i) for i in range(1, 4))
    prefix = ('WITH product_permissions(p1,p2,p3) AS (' + product_sql + '), '
        'skus AS (SELECT s."SKUCode" FROM ' + table(MdmSkuAttributes) +
        ' s JOIN product_permissions p ON ' + product_join +
        " WHERE s.source_id=%s AND s.owner='Importer')")
    params.append(source.pk)
    if master_id == 4:
        location_sql, location_params = _permissions('locations', location_ids)
        params += location_params
        location_join = ' AND '.join('lower(btrim(l."LL%d",\' \'))=p.p%d' % (i, i) for i in range(1, 4))
        prefix += (', location_permissions(p1,p2,p3) AS (' + location_sql + '), '
            'locations AS (SELECT l."WHCode" FROM ' + table(MdmLocationAttributes) +
            ' l JOIN location_permissions p ON ' + location_join +
            " WHERE l.source_id=%s AND l.owner='Importer')")
        params.append(source.pk)
        model = MdmSobRaw
    else:
        model = MdmMoqRaw2 if setting(source) == 'WithDestLoc' else MdmMoqRaw1
    base = ' FROM ' + table(model) + ' a JOIN skus s ON ' + equal('a."SKUCode"', 's."SKUCode"')
    if not count:
        base += (' LEFT JOIN ' + table(MdmSkuDescription) + ' sd ON ' +
        equal('a."SKUCode"', 'sd."SKUCode"') + " AND sd.source_id=a.source_id AND sd.owner='Importer'")
    if master_id == 4:
        base += ' JOIN locations l ON ' + equal('a."WHCode"', 'l."WHCode"')
        if not count:
            base += (' LEFT JOIN ' + table(MdmLocationDescription) + ' wd ON ' +
            equal('a."WHCode"', 'wd."WHCode"') +
            " AND wd.source_id=a.source_id AND wd.owner='Importer'")
        if not count:
            base += ' LEFT JOIN ' + table(MdmSobApproved) + ' q ON q.source_id=a.source_id AND '
            base += ' AND '.join(equal('a.' + connection.ops.quote_name(a), 'q.' + connection.ops.quote_name(b))
            for a, b in (('SKUCode', 'SKUCode'), ('WHCode', 'WhCode'), ('SupplierCode', 'SupplierCode')))
    where, values = _filters(master_id, payload.get('filters'))
    base += ' WHERE a.source_id=%s AND ' + where
    params += [source.pk, *values]
    if count:
        sql = prefix + ' SELECT count(*)' + base
    else:
        requested = [f['key'] for f in payload['fields']]
        ordered = ('sc', 'wc', 'spc') if master_id == 4 else ('sc',)
        if not requested or any(alias not in requested for alias in ordered):
            return None
        selected = ','.join(_column(master_id, alias) + ' AS ' + connection.ops.quote_name(alias) for alias in requested)
        sql = prefix + ' SELECT json_agg(json_strip_nulls(row_to_json(r))) FROM (SELECT ' + selected + base
        if payload.get('paginationParameter') is not None:
            paging = payload['paginationParameter']; page, size = int(paging['pageNumber']), int(paging['recordsPerPage'])
            sql += ' ORDER BY ' + ','.join(key(_column(master_id, alias)) + ' DESC NULLS LAST' for alias in ordered)
            lower, upper = (page - 1) * size + 1, page * size
            sql += ' LIMIT %s OFFSET %s'
            params += [max(0, upper - max(1, lower) + 1), max(0, lower - 1)]
        sql += ') r'
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        result = cursor.fetchone()[0]
    return str(result) if count else result
