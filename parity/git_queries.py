"""Pinned deployed GIT SQL, with explicit owned-table bindings only."""
import json
import re

from parity.output_archive import file_sha
from parity.verify_excess_readmodel import PLAN, PLAN_SHA, literals
from parity.verify_expedite_charts import SOURCE as CHART, SOURCE_SHA as CHART_SHA


def bound(query):
    for old, new in (
        ('[VFTEST_Importer].dbo.InTransitData', '#Transit'),
        ('[VFTEST_Importer].dbo.SKULocStandardAttributes', '#Standard'),
        ('[VFTEST_Importer].dbo.NMSAllItems', '#Nms'),
        ('.[dbo].[GoodsInTransitTransporterMaster]', '#Transporter'),
        ('.[dbo].[GoodsInTransitMaster]', '#Git'),
        ('[GoodsInTransitMaster]', '#Git'),
        ('GoodsInTransitTransporterMaster', '#Transporter'),
        ('GoodsInTransitMaster', '#Git'), ('vf_RationedReqReport', '#Rationed'),
        ('SKUDescriptionTbl', '#SkuDesc'), ('SiteDescriptionTbl', '#LocDesc'),
        ('SkuLocAttributeData', '#Pair'), ('SkuAttributeData', '#Sku'),
        ('LocationAttributeData', '#Loc')):
        query = query.replace(old, new)
    return query


def method(name):
    if file_sha(PLAN) != PLAN_SHA:
        raise ValueError('Pinned PlanningProcessor differs')
    return PLAN.read_text().split('public responseMessage ' + name + '(', 1)[1].split('\n\tpublic ', 1)[0]


def blocks(body):
    return re.findall(r'string.Concat\(new string\[\d+\]\s*\{(.*?)\}\)', body, re.S)


def parts(block):
    return [json.loads(v) for v in re.findall(r'"(?:\\.|[^"\\])*"', block)]


def child_transporter_auth(payload):
    """The deployed child transporter uses direct IDs, not generic expansion."""
    products = ','.join(map(str, payload['product_permissions']))
    locations = ','.join(map(str, payload['location_permissions']))
    if any(type(v) is not int for k in ('product_permissions', 'location_permissions') for v in payload[k]):
        raise ValueError('Explicit integer permission IDs required')
    return f""";WITH cte_SKUPermissions AS (
        SELECT l1,l2,l3 FROM #ProductPermissions
        WHERE id IN (SELECT DISTINCT value FROM string_split('{products}', ','))),
        cte_whPermissions AS (SELECT l1,l2,l3 FROM #LocationPermissions
        WHERE id IN (SELECT value FROM string_split('{locations}', ','))),
        cte_SKUs AS (SELECT a.SKUCode FROM #Sku a INNER JOIN cte_SKUPermissions b
        ON a.SL1=b.l1 AND a.SL2=b.l2 AND a.SL3=b.l3),
        cte_WhCodes AS (SELECT a.WHCode FROM #Loc a INNER JOIN cte_whPermissions b
        ON a.LL1=b.l1 AND a.LL2=b.l2 AND a.LL3=b.l3) """


def queries(auth, payload):
    count = method('GetPlanningGridCount')
    line = next(line for line in count.splitlines() if 'select locationwise=(select count(1)' in line)
    location = literals(line).split('select locationwise=(', 1)[1]
    p = parts(next(b for b in blocks(count) if 'transporterwise=(select count(1)' in b))
    assert len(p) == 3
    transporter_count = (p[0] + p[1] + '[VFTEST_Importer]' + p[2]).split('transporterwise=(', 1)[1]
    parent = method('GetMonitorGITParent')
    p = parts(next(b for b in blocks(parent) if 'AgeingOrder=(select max(ageing-slt)' in b))
    assert len(p) == 5
    grid = p[0] + '[VFTEST_Importer]' + p[1] + p[2] + '[VFTEST_Importer]' + p[3] + p[4]
    result = {}
    for kind, field in (('parent', 'WHCode'), ('child', 'ParentWhCode')):
        joins = f' INNER JOIN cte_SKUs skucodes ON a.SKUCode=skucodes.SKUCode INNER JOIN cte_WhCodes whcodes ON a.{field}=whcodes.WHCode '
        where = " WHERE a.GIT>0 AND a.PhysicalInventoryColor IN ('Black','Red') "
        result[kind + '-location-count'] = bound(auth + location + joins + where)
        result[kind + '-location-grid'] = bound(auth + grid + joins + where + ')git )p ORDER BY RN FOR JSON PATH,INCLUDE_NULL_VALUES) a')
        if kind == 'child':
            result['child-transporter-count'] = bound(auth + transporter_count + joins + " WHERE a.PhysicalInventoryColor IN ('Black','Red') GROUP BY a.TransporterCode,a.OrderNo,a.ParentWhCode,a.WhCode) a")
    child = method('GetMonitorGITChildTransporter')
    p = parts(next(b for b in blocks(child) if 'SELECT  rn=Convert(int, Row_Number()' in b))
    # Empty selectAttrQuery and sqlJoinFilter are independently checked against
    # selected UI configuration and the unfiltered request by the caller.
    child_base = ''.join(p)
    child_base = child_base.replace('.dbo.SKULocStandardAttributes', '#Standard').replace('.dbo.NMSAllItems', '#Nms')
    result['child-transporter-grid'] = bound(child_transporter_auth(payload) + child_base +
        ' inner join cte_SKUs skucodes on a.SKUCode=skucodes.SKUCode inner join cte_WhCodes whcodes on a.ParentWhCode=whcodes.WHCode ' +
        " where a.PhysicalInventoryColor in ('Black','Red') group by a.TransporterCode,a.OrderNo,a.ParentWhCode,a.WhCode)git order by RN for json path,include_null_values) a")
    custom = method('GetCustomGridData')
    p = parts(next(b for b in blocks(custom) if 'dd=abs(TLT-B.SLT)' in b))
    assert len(p) == 4
    result['child-custom'] = bound(auth + p[0] + p[1] + '[VFTEST_Importer]' + p[2] + '[VFTEST_Importer]' + p[3] +
        ' for json path) data')
    if file_sha(CHART) != CHART_SHA:
        raise ValueError('Pinned GIT chart source differs')
    body = CHART.read_text().split('public responseMessage GetChildGoodsInTransitGraphDetails(', 1)[1].split('public static GoodsInTransitDataRoot', 1)[0]
    charts = []
    for line in body.splitlines():
        line = line.strip()
        if line.startswith(('strSql = strSqlAuth +', 'strSql = strSql + strSqlAuth +')):
            charts.append('')
        if not charts or not line.startswith(('strSql +=', 'strSql =')):
            continue
        p = parts(line)
        charts[-1] += p[0] + '[VFTEST_Importer]' + p[1] if 'Startup.ImporterServerName' in line else ''.join(p)
    assert len(charts) == 4
    for i, query in enumerate(charts):
        result['chart-' + str(i)] = bound(auth + ', ' + query)
    return result


def request_queries(auth, payload, compiled):
    """Insert actual DLL filter output and the source RN paging predicates."""
    selected = queries(auth, payload)
    for name in ('parent-location-count', 'child-location-count', 'child-transporter-count',
                 'parent-location-grid', 'child-location-grid', 'child-transporter-grid'):
        report = 'GitTransporter' if name == 'child-transporter-grid' else 'GitCount' if name.endswith('-count') else 'GitGrid'
        f = compiled[report]
        query = selected[name]
        table = '#Transporter' if '-transporter-' in name else '#Git'
        marker = table + ' a '
        assert query.count(marker) == 1, name
        query = query.replace(marker, marker + bound(f['sql_join_filter']) + ' ')
        if f['sql_filter']:
            # Append after the branch's fixed colour/positive-GIT WHERE,
            # before GROUP BY or derived-table closure.
            marker = " WHERE a.GIT>0 AND a.PhysicalInventoryColor IN ('Black','Red') " if '-location-' in name else " WHERE a.PhysicalInventoryColor IN ('Black','Red') " if name.endswith('-count') else " where a.PhysicalInventoryColor in ('Black','Red') "
            assert query.count(marker) == 1, name
            query = query.replace(marker, marker + ' and ' + bound(f['sql_filter']) + ' ')
        selected[name] = query
    for kind in ('parent', 'child'):
        location = selected[kind+'-location-count'].removeprefix(auth)
        wire = auth + ' select locationwise=(' + location + ')'
        if kind == 'child':
            wire += ', transporterwise=(' + selected['child-transporter-count'].removeprefix(auth) + ')'
        selected[kind+'-count-wire'] = wire + ' for json path'
    paging = payload.get('paginationParameter')
    if paging is not None:
        page, size = (int(paging[n]) for n in ('pageNumber', 'recordsPerPage'))
        predicate = f' where RN between ({page}-1)*{size}+1 and ({page}*{size}) '
        for name in ('parent-location-grid', 'child-location-grid'):
            selected[name] = selected[name].replace('ORDER BY RN FOR JSON', predicate+'ORDER BY RN FOR JSON')
        selected['child-transporter-grid'] = selected['child-transporter-grid'].replace('order by RN for json', predicate+'order by RN for json')
        selected['child-custom'] = selected['child-custom'].replace(' for json path) data', predicate+' for json path) data')
    return selected
