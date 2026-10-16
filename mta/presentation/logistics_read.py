"""Nine-route tranche: canonical logistics reads over admitted typed sources."""
from datetime import date, datetime, timezone
from django.db import connection
from mta.presentation import daily_transit, logistics_live
from mta.presentation.context import PublicationUnavailable, scope
from mta.presentation.selective import image_query, image_rows
from mta.presentation.bpr_sql import _projected_attributes
from mta.presentation.planning_grid_sql import GridFilters
from mta.presentation.rrr_sql import equal, key
from mta.presentation.rrr import sql_key
from mta.presentation.excess_read import pagination
from mta.runtime.models import DailyTransitRow, DailyOpenRequest, ExpediteRow
from mta.runtime.relational_state import quote


class TargetDenied(PermissionError):
    pass


def native_wire(value):
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).replace(tzinfo=None).isoformat(
            timespec='milliseconds' if value.microsecond else 'seconds')
    if isinstance(value, date):
        return value.isoformat()
    return value


def omit_nulls(row):
    return {k: native_wire(v) for k, v in row.items() if v is not None}


def attributes_scope(run, payload):
    importer, manifest = _projected_attributes(run)
    if manifest:
        raise PublicationUnavailable('logistics_native_hierarchy_required')
    return importer, *scope(payload, attributes=importer)


def authorize_targets(rows, products, locations, *, location='WhCode'):
    if not rows or any(not any(sql_key(r.get('SKUCode')) == sql_key(p) for p in products)
                       or not any(sql_key(r.get(location)) == sql_key(l) for l in locations)
                       for r in rows):
        raise TargetDenied('logistics_target_scope_denied')


def authorize_order(run, payload, order):
    importer, products, locations = attributes_scope(run, payload)
    rows = [r for r in logistics_live.transit_rows(run)
            if sql_key(r.get('OrderNo')) == sql_key(order) and sql_key(order) is not None]
    authorize_targets(rows, products, locations)
    return rows


def authorize_pair(run, payload, sku, location):
    importer, products, locations = attributes_scope(run, payload)
    authorize_targets([dict(SKUCode=sku, WhCode=location)], products, locations)
    return importer


def _fetch(sql, params):
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        names = [d[0] for d in cursor.description]
        return [dict(zip(names, row)) for row in cursor.fetchall()]


def _dispatch_relation(run):
    """BPR calculated report, distinct from the narrower BTR ageing history."""
    from mta.presentation.expedite_storage import read_expedite
    from mta.presentation.expedite import FIELDS
    output=dict(ClosingState=[dict(
        importer={'MasterData':image_rows(run,'closing/importer/MasterData')},
        dbm={'SKULocStandardAttributes':image_rows(run,'closing/dbm/SKULocStandardAttributes')},
        btr={'ExpediteDispatches':image_rows(run,'closing/btr/ExpediteDispatches')})],
        BPRReports=[{'vf_RationedReqReport':image_rows(run,'reports/bpr/vf_RationedReqReport')}])
    read_expedite(run,output=output)
    return ('SELECT ordinal AS vf_ordinal,'+','.join(map(quote,FIELDS))+
            ' FROM mta.'+quote(ExpediteRow._meta.db_table)+' WHERE run_id=%s'),[run.pk]


def _transit_relation(run):
    sql, params = image_query(run, daily_transit.PATH)
    if not logistics_live.enabled():
        return sql,params
    # Validate any current overlay before joining; NULL edits must not fall
    # through to the old source, hence CASE on annotation identity, not COALESCE.
    logistics_live.transit_rows(run)
    columns = ['S.vf_ordinal']
    edits = {'CurrentLocationCode', 'ETA', 'Remark'}
    for field in daily_transit.processor.TRANSIT_FIELDS:
        expression = ('CASE WHEN X.id IS NULL THEN S.'+quote(field)+' ELSE X.'+quote(field)+' END'
                      if field in edits else 'S.'+quote(field))
        columns.append(expression+' AS '+quote(field))
    return ('SELECT '+','.join(columns)+' FROM ('+sql+') S LEFT JOIN '
        'mta.fresh_mta_transitannotation X ON X.generation_id=%s AND X.source_ordinal=S.vf_ordinal'), [*params, run.pk]


def _relation(run, payload, *, transit):
    importer, products, locations = attributes_scope(run, payload)
    filtered = payload if transit else dict(payload, filters=payload)
    # Same deployed Commons filterQuery(sa/la/sla). Preserve invalid column
    # branches rather than invent missing availability facts on these sources.
    from mta.presentation.excess_filters import predicate
    predicate(filtered, importer)
    filters = GridFilters(filtered, 'logistics', DailyTransitRow if transit else DailyOpenRequest)
    where = filters.compile()
    ctes, params = [], []
    if transit:
        sql, values = _transit_relation(run)
    else:
        owner, _ = logistics_live.current_requests()
        fields = ('ordinal AS vf_ordinal', *map(quote, __import__(
            'mta.presentation.daily_requests', fromlist=['FIELDS']).FIELDS))
        sql = 'SELECT '+','.join(fields)+' FROM mta.fresh_mta_dailyopenrequest WHERE owner_id=%s'
        values = [owner.pk]
    ctes.append('A AS ('+sql+')'); params.extend(values)
    for alias, path in (('B', daily_transit.TRANSPORTER_PATH if transit else None),
                        ('C', 'closing/importer/SkuAttributeData'),
                        ('D', 'closing/importer/LocationAttributeData'),
                        ('E', 'closing/importer/SkuLocAttributeData')):
        query, values = image_query(run,path) if path is not None else _dispatch_relation(run)
        # Existing filter compiler calls the pair alias B; this query owns B as
        # the canonical transporter/dispatch join, so translate only that alias.
        ctes.append(alias+' AS ('+query+')'); params.extend(values)
    where = where.replace('B.', 'E.')
    joins = (' FROM A '+('LEFT' if transit else 'INNER')+' JOIN B ON '+
             equal('A."SKUCode"', 'B."SKUCode"')+' AND '+equal('A."WhCode"', 'B."WhCode"'))
    if transit:
        joins += ' AND '+equal('A."ParentWhCode"','B."ParentWhCode"')+' AND '+equal('A."OrderNo"','B."OrderNo"')
    joins += (' INNER JOIN C ON '+equal('A."SKUCode"','C."SKUCode"')+
              ' INNER JOIN D ON '+equal('A."WhCode"','D."WHCode"')+
              ' LEFT JOIN E ON '+equal('A."SKUCode"','E."SKUCode"')+' AND '+equal('A."WhCode"','E."LocCode"'))
    if transit:
        query, values = image_query(run, 'closing/importer/SKUDescriptionTbl')
        ctes.append('N AS ('+query+')'); params.extend(values)
        joins += ' INNER JOIN N ON '+equal('A."SKUCode"','N."SKUCode"')
    for alias, codes in (('P',products), ('L',locations)):
        if codes:
            ctes.append(alias+'(code,weight) AS (VALUES '+','.join(['(%s::text,%s::bigint)']*len(codes))+')')
            params.extend(v for code in codes for v in (code,codes.multiplicities[code]))
        else:
            ctes.append(alias+'(code,weight) AS (SELECT NULL::text,0::bigint WHERE FALSE)')
    joins += ' INNER JOIN P ON '+equal('A."SKUCode"','P.code')+' INNER JOIN L ON '+equal('A."WhCode"','L.code')
    if filters.children:
        joins += ' INNER JOIN D parent ON '+equal('A."ParentWhCode"','parent."WHCode"')+' AND ('+' OR '.join(
            equal('parent."LocationType"','%s') for _ in filters.children)+')'
        params.extend(filters.children)
    joins += ' CROSS JOIN LATERAL generate_series(1,P.weight*L.weight) copies(n)'
    params.extend(filters.params)
    return ctes, params, joins+' WHERE '+where


def transit_grid(run, payload, *, count=False):
    ctes, params, joins = _relation(run, payload, transit=True)
    if count:
        return int(_fetch('WITH '+','.join(ctes)+' SELECT count(*) AS n'+joins,params)[0]['n'])
    columns = dict(RN='row_number() OVER (ORDER BY '+key('A."OrderNo"')+' NULLS FIRST)',
        OrderNo='A."OrderNo"', SKUCode='A."SKUCode"', SKUDescription='N."SKUDescription"',
        ReceiverLoc='A."WhCode"', SenderLocation='A."ParentWhCode"', DispatchDate='A."GateOutDate"',
        Ageing='B."Ageing"', CurrentLoc='A."CurrentLocationCode"', Action='A."Remark"', ETA='A."ETA"',
        Qty='sum(A."InTransitQty") OVER (PARTITION BY '+key('A."OrderNo"')+')',
        skuDetails='(SELECT json_agg(json_strip_nulls(json_build_object(\'SKUCode\',Z."SKUCode",'
            '\'SKUDescription\',N."SKUDescription",\'InTransitQty\',Z."InTransitQty",'
            '\'PhysicalInventoryColor\',B."PhysicalInventoryColor"))) FROM A Z WHERE '+
            equal('Z."OrderNo"','A."OrderNo"')+')')
    ctes.append('selected AS (SELECT '+','.join(v+' AS '+quote(k) for k,v in columns.items())+joins+')')
    sql = 'WITH '+','.join(ctes)+' SELECT * FROM selected'
    page = pagination(payload)
    if page is not None:
        sql += ' WHERE "RN" BETWEEN %s AND %s'; params.extend(((page[0]-1)*page[1]+1,page[0]*page[1]))
    rows = _fetch(sql+' ORDER BY "RN"',params)
    # Correlated SKU details and history are order-wide in the deployed API.
    # The approved scope disposition disallows exposing denied sibling targets.
    for order in {r.get('OrderNo') for r in rows}:
        authorize_order(run,payload,order)
    return [omit_nulls(row) for row in rows]


def contacts(run, payload):
    order = payload.get('orderNo')
    authorize_order(run,payload,order)
    sql, params = image_query(run,daily_transit.TRANSPORTER_PATH)
    rows = _fetch('SELECT "SKUCode","WhCode","TransporterName","TransporterContact" FROM ('+
        sql+') A WHERE '+equal('A."OrderNo"','%s'),[*params,order])
    _, products, locations = attributes_scope(run,payload)
    if rows:
        authorize_targets(rows,products,locations)
    return [omit_nulls({k:r[k] for k in ('TransporterName','TransporterContact')}) for r in rows]


def transit_history(run, payload):
    authorize_order(run,payload,payload.get('orderNo'))
    owner = logistics_live.history_owner()
    return [omit_nulls(row) for row in _fetch('SELECT "Remarks","ETA","CurrentLocation",'
        '"RemarksDate","UserId" AS "UserName" FROM mta.fresh_mta_transitremarkhistory A '
        'WHERE owner_id=%s AND '+equal('A."OrderNo"','%s')+' ORDER BY "RemarksDate" DESC NULLS LAST',
        [owner.pk,payload.get('orderNo')])]


def open_requests(run, payload):
    ctes, params, joins = _relation(run,payload,transit=False)
    columns = dict(sc='A."SKUCode"',wc='A."WhCode"',pwc='A."ParentWhCode"',
        qty='B."RationedQty"',pic='B."PipelineInventoryColor"',br='B."BRAge"',
        plpd='B."PotentialLossPerDay"',eta='A."ETA"',rk='A."Request"')
    rows = _fetch('WITH '+','.join(ctes)+' SELECT '+','.join(v+' AS '+quote(k) for k,v in columns.items())+joins,params)
    config = [('SKUCode','sc'),('Receiver Location','wc'),('Sender Location','pwc'),('RR Qty','qty'),
              ('RECV Priority','pic'),('BRAge','br'),('PotentialLossPerDay','plpd'),('ETA','eta'),('Remark','rk')]
    return dict(uiConfig=[dict(header=h,colCode=c) for h,c in config],
                data=[omit_nulls(row) for row in rows])


def expedite_history(run,payload):
    sku, location = payload.get('skucode'), payload.get('whcode')
    authorize_pair(run,payload,sku,location)
    owner = logistics_live.history_owner()
    rows = _fetch('SELECT row_number() OVER (ORDER BY "RemarkDate" DESC NULLS LAST) AS "RN",'
        '"Remark" AS r,"RemarkDate" AS rd,"UserId","ETA" AS eta FROM '
        'mta.fresh_mta_expediteremarkhistory A WHERE owner_id=%s AND '+equal('A."SKUCode"','%s')+
        ' AND '+equal('A."WHCode"','%s'),[owner.pk,sku,location])
    return [{k: '' if v is None else str(native_wire(v)) for k,v in row.items()} for row in rows]
