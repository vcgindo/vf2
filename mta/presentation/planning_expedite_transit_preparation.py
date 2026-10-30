from mta.presentation.native_mode import removed_mode
"""One-time parent Expedite NMS/remark and grid/Pick match ingredients."""
import hashlib
import inspect
import json
from datetime import date, datetime
from decimal import Decimal

from django.db import connection
from mta.presentation.planning_expedite_grids import admitted_expedite_grids
from mta.presentation.rrr_sql import equal, key
from mta.presentation.selective import image_query
from mta.serialization import digest

PICK_TABLE = 'stage_demo_bpr_1."dbo__vf_PickListReport"'
REMARK_TABLE = 'stage_demo_bpr_1."dbo__BPRReport_RemarkDetails"'
# Immutable receipts made before the native builder identity was corrected.
# Their original run/source/Pick/value bindings remain mandatory on admission.
RETAINED_PRODUCTION_RECIPE = 'aa950d454662a4f9bb9ba6d53e466a689e7ad2ba627b143118802c33f03e9aae'


def production_pick_query(run):
    """Exact produced Pick rows from sealed rationed/band occurrence identity."""
    from mta.presentation.rrr_preparation import a_selections
    from mta.runtime.models import PickBand, RrrPreparedMembership
    from mta.runtime.relational_state import quote
    rationed, params = image_query(run, 'reports/bpr/vf_RationedReqReport')
    members = 'mta.' + quote(RrrPreparedMembership._meta.db_table)
    bands = 'mta.' + quote(PickBand._meta.db_table)
    return ('WITH R AS (' + rationed + '),H AS (SELECT * FROM ' + members
        + ' WHERE run_id=%s),K AS (SELECT * FROM ' + bands + ' WHERE run_id=%s) '
        'SELECT H.ordinal AS vf_source_ordinal,' + ','.join(a_selections())
        + ' FROM H JOIN R ON R.vf_ordinal=H.rationed_ordinal'
        ' JOIN K ON K.ordinal=H.band_ordinal'), [*params, run.pk, run.pk]


def production_pick_digest(run):
    from mta.runtime.models import PickProjection, RrrPreparedProjection
    from mta.serialization import digest as value_digest
    pick = PickProjection.objects.get(run=run)
    rrr = RrrPreparedProjection.objects.get(run=run)
    return value_digest(dict(pick=pick.rows_digest, pick_count=pick.row_count,
                             rrr=rrr.rows_digest, rrr_count=rrr.row_count))


def pick_binding(run, *, verify_values=False):
    if getattr(run, 'kind', None) == 'DAILY_CHAIN':
        return production_pick_digest(run)
    return pick_source(verify_values=verify_values)


def encoded(row):
    values = [v.isoformat() if isinstance(v,(date,datetime)) else str(v) if isinstance(v,Decimal) else v for v in row]
    return (json.dumps(values,ensure_ascii=False,separators=(',',':'),allow_nan=False)+'\n').encode()


def pick_source(*, verify_values=False):
    """Frozen staging is the retained full Pick source, not the narrower PickPost."""
    removed_mode('historical_fixture')
    with connection.cursor() as c:
        c.execute('SELECT values_sha256,row_count FROM stage2_owner.tables WHERE source=%s AND table_name=%s', ['Demo_BPR_1', 'vf_PickListReport'])
        receipt = c.fetchone()
        if receipt is None or receipt[1] != 8063:
            raise ValueError('Planning retained Pick population changed')
        if verify_values:
            c.execute('SELECT * FROM ' + PICK_TABLE + ' ORDER BY vf_source_ordinal')
            fields = [column[0] for column in c.description]
            if fields[0] != 'vf_source_ordinal' or not {'SKUCode', 'WhCode', 'ParentStockForRationing'} <= set(fields):
                raise ValueError('Planning retained Pick columns changed')
            checksum, count = (hashlib.sha256(), 0)
            for row in c:
                if row[0] != count:
                    raise ValueError('Planning retained Pick ordinal changed')
                checksum.update(encoded(row[1:]))
                count += 1
            if (checksum.hexdigest(), count) != receipt:
                raise ValueError('Planning retained Pick values changed')
    return receipt[0]


def base_query(run):
    removed_mode('historical_fixture')
    nms, params = image_query(run, 'closing/consumer_context/NMSAllItems')
    query = 'WITH N AS (' + nms + ') SELECT row_number() OVER (ORDER BY N.vf_ordinal,R.vf_source_ordinal NULLS FIRST)-1 AS ordinal,N.vf_ordinal AS nms_ordinal,R.vf_source_ordinal AS remark_ordinal,N."SKUCode" AS sku_code,N."WhCode" AS location_code,' + key('N."SKUCode"') + ' AS sku_key,' + key('N."WhCode"') + ' AS location_key,N."RLT" AS rlt,R."Remark" AS remark,' + key('R."Remark"') + ' AS remark_key FROM N LEFT JOIN ' + REMARK_TABLE + ' R ON ' + equal('N."SKUCode"', 'R."SKUCode"') + ' AND ' + equal('N."WhCode"', 'R."WhCode"')
    return (query, params)


def match_query(run):
    grids, params = admitted_expedite_grids(run)['row']
    query = ('WITH G AS ('+grids+'), candidates AS (SELECT '
        'B.ordinal AS base_ordinal,G.branch,G.ordinal AS grid_ordinal,'
        'P.vf_source_ordinal AS pick_ordinal,P."ParentStockForRationing" AS parent_stock '
        'FROM mta.fresh_mta_planningexpeditetransitbase B '
        'JOIN '+REMARK_TABLE+' R ON R.vf_source_ordinal=B.remark_ordinal '
        'JOIN mta.fresh_mta_expediterow A ON A.run_id=B.run_id AND '
        +equal('A."SKUCode"','R."SKUCode"')+' AND '+equal('A."WhCode"','R."WhCode"')+
        " JOIN G ON G.direction='parent' AND G.fact_ordinal=A.ordinal "
        'LEFT JOIN '+PICK_TABLE+' P ON '+equal('P."SKUCode"','A."SKUCode"')+
        ' AND '+equal('P."WhCode"','A."WhCode"')+' WHERE B.run_id=%s) '
        'SELECT row_number() OVER (ORDER BY base_ordinal,branch,grid_ordinal,pick_ordinal NULLS FIRST)-1 AS ordinal,'
        'base_ordinal,branch,grid_ordinal,pick_ordinal,parent_stock FROM candidates')
    return query, [*params,run.pk]


def production_base_query(run):
    nms, params = image_query(run, 'closing/consumer_context/NMSAllItems')
    remarks, remark_params = image_query(run, 'sources/bpr/BPRReport_RemarkDetails')
    query = ('WITH N AS ('+nms+'),R AS ('+remarks+') SELECT '
        'row_number() OVER (ORDER BY N.vf_ordinal,R.vf_ordinal NULLS FIRST)-1 AS ordinal,'
        'N.vf_ordinal AS nms_ordinal,R.vf_ordinal AS remark_ordinal,'
        'N."SKUCode" AS sku_code,N."WhCode" AS location_code,'
        +key('N."SKUCode"')+' AS sku_key,'+key('N."WhCode"')+' AS location_key,'
        'N."RLT" AS rlt,R."Remark" AS remark,'+key('R."Remark"')+' AS remark_key '
        'FROM N LEFT JOIN R ON '+equal('N."SKUCode"','R."SKUCode"')+
        ' AND '+equal('N."WhCode"','R."WhCode"'))
    return query, [*params,*remark_params]


def production_match_query(run):
    grids, params = admitted_expedite_grids(run)['row']
    remarks, remark_params = image_query(run, 'sources/bpr/BPRReport_RemarkDetails')
    pick, pick_params = production_pick_query(run)
    query = ('WITH G AS ('+grids+'),R AS ('+remarks+'),P AS ('+pick+'), candidates AS (SELECT '
        'B.ordinal AS base_ordinal,G.branch,G.ordinal AS grid_ordinal,'
        'P.vf_source_ordinal AS pick_ordinal,P."ParentStockForRationing" AS parent_stock '
        'FROM mta.fresh_mta_planningexpeditetransitbase B '
        'JOIN R ON R.vf_ordinal=B.remark_ordinal '
        'JOIN mta.fresh_mta_expediterow A ON A.run_id=B.run_id AND '
        +equal('A."SKUCode"','R."SKUCode"')+' AND '+equal('A."WhCode"','R."WhCode"')+
        " JOIN G ON G.direction='parent' AND G.fact_ordinal=A.ordinal "
        'LEFT JOIN P ON '+equal('P."SKUCode"','A."SKUCode"')+
        ' AND '+equal('P."WhCode"','A."WhCode"')+' WHERE B.run_id=%s) '
        'SELECT row_number() OVER (ORDER BY base_ordinal,branch,grid_ordinal,pick_ordinal NULLS FIRST)-1 AS ordinal,'
        'base_ordinal,branch,grid_ordinal,pick_ordinal,parent_stock FROM candidates')
    return query, [*params,*remark_params,*pick_params,run.pk]


def prepared_production_match(run):
    from mta.presentation.expedite_transit_join import prepared_match
    return prepared_match(
        base=('SELECT ordinal,remark_ordinal FROM mta.fresh_mta_planningexpeditetransitbase WHERE run_id=%s', [run.pk]),
        remarks=image_query(run, 'sources/bpr/BPRReport_RemarkDetails'),
        facts=('SELECT * FROM mta.fresh_mta_expediterow WHERE run_id=%s', [run.pk]),
        grids=admitted_expedite_grids(run)['row'], pick=production_pick_query(run))


def recipe_digest():
    return digest(dict(version=1,base=inspect.getsource(base_query),matches=inspect.getsource(match_query),
                       pick=inspect.getsource(pick_source),encoding=inspect.getsource(encoded),
                       pick_table=PICK_TABLE,remarks=REMARK_TABLE))


def production_recipe_digest():
    from mta.presentation import expedite_transit_join
    return digest(dict(version=3, base=inspect.getsource(production_base_query),
        matches=inspect.getsource(prepared_production_match), join=expedite_transit_join.recipe_digest(),
        pick=inspect.getsource(production_pick_query),
        remarks='sources/bpr/BPRReport_RemarkDetails'))
