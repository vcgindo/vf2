"""Live canonical GIT chart aggregates over sealed typed daily sources."""
from django.db import connection

from mta.presentation.daily_git_charts import BASE_CONFIG, response
from mta.presentation.daily_git_preparation import (
    DESCRIPTION_PATH, LOCATION_PATH, TRANSIT_PATH, TRANSPORTER_PATH, sources,
)
from mta.presentation.rrr_sql import equal, key


def _permissions(products, locations):
    ctes, params = [], []
    for alias, codes in (('P', products), ('L', locations)):
        members = sorted(codes)
        if not members:
            return None, None
        ctes.append(alias + '(code,weight) AS (VALUES ' +
                     ','.join(['(%s::text,%s::bigint)'] * len(members)) + ')')
        params.extend(value for code in members
                      for value in (code, codes.multiplicities[code]))
    return ctes, params


def _relations(run):
    relations, bindings, dynamic_config = sources(run, chart=True)
    ctes, params = [], []
    for alias, name in (('A', TRANSPORTER_PATH), ('B', TRANSIT_PATH),
                        ('G', 'git_master'), ('D', DESCRIPTION_PATH),
                        ('X', LOCATION_PATH)):
        query, values = relations[name]
        ctes.append(alias + ' AS (' + query + ')')
        params.extend(values)
    return ctes, params, bindings, dynamic_config


def _location_columns(bindings):
    selected = [('Details', "replace(D.\"WHDescription\",'''','')"),
                ('LogisticsLocation', 'X."LogisticsLocation"')]
    selected.extend((alias, 'X."' + column + '"') for alias, column in bindings)
    selected.extend(('ll' + str(index), 'X."LL' + str(index) + '"')
                    for index in range(1, 6))
    return selected


def _fetch(sql, params):
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        names = [column[0] for column in cursor.description]
        return [dict(zip(names, row)) for row in cursor.fetchall()]


def _delay_query(ctes, location, *, partition):
    permission_joins = (' JOIN P ON ' + equal('A."SKUCode"', 'P.code') +
                        ' JOIN L ON ' + equal('A."WhCode"', 'L.code') +
                        ' CROSS JOIN LATERAL generate_series(1,P.weight*L.weight) permission_copy(n)')
    joined = (' FROM A JOIN B ON ' + equal('A."SKUCode"', 'B."SKUCode"') +
              ' AND ' + equal('A."WhCode"', 'B."WhCode"') + permission_joins +
              ' WHERE A."IsReceiving" AND B."TLT">B."SLT"')
    ctes = [*ctes,
        'M AS (SELECT A."SKUCode",A."WhCode",A."ParentWhCode",A."TransporterCode",'
        'A."OrderNo",(B."TLT"-B."SLT") AS delay' + joined + ')',
        'S AS (SELECT "' + partition + '" AS code,'
        'CAST(percentile_cont(0.5) WITHIN GROUP (ORDER BY delay) AS numeric(13,2)) AS "Median",'
        'CAST(percentile_cont(0.25) WITHIN GROUP (ORDER BY delay) AS numeric(13,2)) AS "Q1",'
        'CAST(percentile_cont(0.75) WITHIN GROUP (ORDER BY delay) AS numeric(13,2)) AS "Q3" '
        'FROM M GROUP BY "' + partition + '")']
    outer = (' FROM A JOIN D ON ' + equal('A."WhCode"', 'D."WHCode"') +
             ' JOIN X ON ' + equal('A."WhCode"', 'X."WHCode"') +
             ' JOIN M ON ' + ' AND '.join(equal('A."' + name + '"', 'M."' + name + '"')
                                                for name in ('SKUCode', 'WhCode', 'ParentWhCode',
                                                             'TransporterCode', 'OrderNo')) +
             ' JOIN S ON ' + equal('A."' + partition + '"', 'S.code'))
    aggregate = [('LRCount', 'count(A."LRCode")'), ('MinDelayDays', 'min(M.delay)'),
                 ('MaxDelayDays', 'max(M.delay)'),
                 ('Mean', 'CAST(avg(CAST(M.delay AS numeric(13,2))) AS numeric(13,2))'),
                 ('Median', 'max(S."Median")'), ('Q1', 'max(S."Q1")'),
                 ('Q3', 'max(S."Q3")')]
    if partition == 'WhCode':
        fields = [('WhCode', 'A."WhCode"'), *aggregate, *location]
        groups = ['A."WhCode"', *[value for _, value in location]]
    else:
        fields = [('TransporterCode', 'A."TransporterCode"'), *aggregate,
                  ('TransporterName', 'A."TransporterName"')]
        groups = ['A."TransporterCode"', 'A."TransporterName"']
    return ('WITH ' + ','.join(ctes) + ' SELECT ' +
            ','.join(value + ' AS "' + name + '"' for name, value in fields) + outer +
            ' GROUP BY ' + ','.join(groups))


def graph(run, products, locations):
    """Return the deployed four-table GIT chart wire for one resolved scope."""
    relation_ctes, relation_params, bindings, dynamic_config = _relations(run)
    permission_ctes, permission_params = _permissions(products, locations)
    config = [*dynamic_config, *[dict(item) for item in BASE_CONFIG]]
    if permission_ctes is None:
        return response(dict(tables=[[], [], [], []], ui_config=config))
    ctes = [*relation_ctes, *permission_ctes]
    params = [*relation_params, *permission_params]
    location = _location_columns(bindings)

    eligible = ('E AS (SELECT G."SKUCode",G."WhCode" FROM G '
        'JOIN P ON ' + equal('G."SKUCode"', 'P.code') +
        ' JOIN L ON ' + equal('G."ParentWhCode"', 'L.code') +
        ' CROSS JOIN LATERAL generate_series(1,P.weight*L.weight) permission_copy(n) '
        'WHERE ' + key('G."PhysicalInventoryColor"') + " IN ('red','black') "
        'AND G."Git">0 AND G."IsParent")')
    status_fields = [('counts', 'count(A."SKUCode")'), ('WhCode', 'A."WhCode"'),
                     *location, ('SKUStatus', 'A."SKUStatus"')]
    status_sql = ('WITH ' + ','.join([*ctes, eligible]) + ' SELECT ' +
        ','.join(value + ' AS "' + name + '"' for name, value in status_fields) +
        ' FROM A JOIN D ON ' + equal('A."WhCode"', 'D."WHCode"') +
        ' JOIN X ON ' + equal('A."WhCode"', 'X."WHCode"') +
        ' JOIN E ON ' + equal('A."SKUCode"', 'E."SKUCode"') +
        ' AND ' + equal('A."WhCode"', 'E."WhCode"') +
        ' GROUP BY ' + ','.join(['A."WhCode"', *[value for _, value in location],
                                 'A."SKUStatus"']) +
        ' ORDER BY A."WhCode",count(A."SKUCode") DESC')
    transporter_status = ('WITH ' + ','.join(ctes) +
        ' SELECT count(A."LRCode") AS counts,A."TransporterCode",A."TruckStatus",A."TransporterName" '
        'FROM A JOIN P ON ' + equal('A."SKUCode"', 'P.code') +
        ' JOIN L ON ' + equal('A."WhCode"', 'L.code') +
        ' CROSS JOIN LATERAL generate_series(1,P.weight*L.weight) permission_copy(n) '
        'WHERE ' + key('A."PhysicalInventoryColor"') + " IN ('red','black') "
        'GROUP BY A."TransporterCode",A."TruckStatus",A."TransporterName" '
        'ORDER BY counts DESC')
    tables = [_fetch(status_sql, params),
              _fetch(_delay_query(ctes, location, partition='WhCode'), params),
              _fetch(transporter_status, params),
              _fetch(_delay_query(ctes, location, partition='TransporterCode'), params)]
    return response(dict(tables=tables, ui_config=config))
