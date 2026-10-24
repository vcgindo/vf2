"""Canonical paged GIT custom grid over sealed typed daily sources."""
from django.db import connection

from mta.presentation.context import PublicationUnavailable
from mta.presentation.daily_git_preparation import (
    DESCRIPTION_PATH, NMS_PATH, TRANSIT_PATH, TRANSPORTER_PATH, sources,
)
from mta.presentation.excess_read import CUSTOM_COLUMNS
from mta.presentation.rrr_sql import equal, key


FIELDS = (
    ('sc', 'A."SKUCode"'), ('wc', 'A."WhCode"'),
    ('sd', 'C."SKUDescription"'), ('wd', 'C."WHDescription"'),
    ('dd', 'abs(B."TLT"-B."SLT")'), ('ss', 'A."SKUStatus"'),
    ('s', 'A."Status"'), ('pwc', 'A."ParentWhCode"'),
    ('pn', 'G."WHDescription"'), ('n', 'C."Norm"'), ('mn', 'C."MinNorm"'),
    ('rlt', 'C."RLT"'), ('rcp', 'C."RCP"'), ('gcp', 'C."GCP"'),
    ('ocp', 'C."OCP"'), ('moc', 'C."MinOrderCount"'), ('rq', 'D."Req"'),
    ('ps', 'C."PackSize"'), ('frf', 'C."FGRMFlag"'), ('da', 'C."DBMActive"'),
    ('odn', 'A."OrderNo"'), ('ts', 'A."TruckStatus"'),
    ('tn', 'A."TransporterName"'), ('tc', 'A."TransporterCode"'),
    ('fl', 'C."ParentWhCode"'), ('itq', 'A."InTransitQty"'),
    ('tct', 'A."TransporterContact"'), ('cd', 'A."CreationDate"'),
    ('slt', 'A."SLT"'), ('ag', 'A."Ageing"'), ('eta', 'A."ETA"'),
    ('cl', 'A."CurrentLocation"'), ('rmk', 'A."Remark"'), ('lc', 'A."LRCode"'),
    *(('sl' + str(i), 'C."SL' + str(i) + '"') for i in range(1, 6)),
    *(('ll' + str(i), 'C."LL' + str(i) + '"') for i in range(1, 6)),
)


def custom(run, products, locations, paging,*,read_binding=None):
    config = [dict(header=h, colCode=c, colPosition=p) for h, c, p in CUSTOM_COLUMNS]
    options={} if read_binding is None else dict(read_binding=read_binding)
    relations, _, _ = sources(run, chart=False,**options)
    if not products or not locations:
        return dict(data=[], uiConfig=config)
    ctes, params = [], []
    for alias, name in (('A', TRANSPORTER_PATH), ('D', 'git_master'),
                        ('B', TRANSIT_PATH), ('C', NMS_PATH), ('G', DESCRIPTION_PATH)):
        query, values = relations[name]
        ctes.append(alias + ' AS (' + query + ')')
        params.extend(values)
    for alias, codes in (('P', products), ('L', locations)):
        members = sorted(codes)
        ctes.append(alias + '(code,weight) AS (VALUES ' +
                     ','.join(['(%s::text,%s::bigint)'] * len(members)) + ')')
        params.extend(value for code in members
                      for value in (code, codes.multiplicities[code]))
    projection = ','.join(value + ' AS "' + name + '"' for name, value in FIELDS)
    joined = ('SELECT ' + projection + ' FROM A JOIN D ON ' +
        equal('A."SKUCode"', 'D."SKUCode"') + ' AND ' + equal('A."WhCode"', 'D."WhCode"') +
        ' JOIN P ON ' + equal('A."SKUCode"', 'P.code') +
        ' JOIN L ON ' + equal('A."WhCode"', 'L.code') +
        ' CROSS JOIN LATERAL generate_series(1,P.weight*L.weight) permission_copy(n) '
        'JOIN B ON ' + equal('A."SKUCode"', 'B."SKUCode"') + ' AND ' + equal('A."WhCode"', 'B."WhCode"') +
        ' JOIN C ON ' + equal('B."SKUCode"', 'C."SKUCode"') + ' AND ' + equal('B."WhCode"', 'C."WhCode"') +
        ' JOIN G ON ' + equal('A."ParentWhCode"', 'G."WHCode"'))
    ctes.append('J AS (' + joined + ')')
    # Native ROW_NUMBER orders only by SKU/location. Unequal rows at one key
    # have no qualified relative order, even without paging; exact duplicate
    # occurrences are safe because every possible ordering has the same bag.
    projected = ','.join('"' + name + '"' for name, _ in FIELDS)
    ambiguity = ('WITH ' + ','.join(ctes) + ' SELECT ' + key('"sc"') + ',' +
        key('"wc"') + ',count(*),count(DISTINCT ROW(' + projected + ')) FROM J '
        'GROUP BY ' + key('"sc"') + ',' + key('"wc"'))
    with connection.cursor() as cursor:
        cursor.execute(ambiguity, params)
        groups = cursor.fetchall()
    if any(distinct > 1 for _, _, _, distinct in groups):
        raise PublicationUnavailable(
            'LEG-GIT-CUSTOM-UNORDERED-TIE: unequal rows share SKU/location order key')
    ctes.append('R AS (SELECT row_number() OVER (ORDER BY "sc","wc") AS "RN",J.* FROM J)')
    sql = 'WITH ' + ','.join(ctes) + ' SELECT * FROM R'
    if paging is not None:
        page, size = paging
        sql += ' WHERE "RN" BETWEEN %s AND %s'
        params.extend(((page - 1) * size + 1, page * size))
    sql += ' ORDER BY "RN"'
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        names = [column[0] for column in cursor.description]
        rows = [dict(zip(names, row)) for row in cursor.fetchall()]
    return dict(data=[{key: value for key, value in row.items() if value is not None}
                      for row in rows], uiConfig=config)
