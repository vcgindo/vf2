"""One-time parent Expedite NMS/remark and grid/Pick match ingredients."""
import hashlib
import inspect
import json
from datetime import date, datetime
from decimal import Decimal

from django.db import connection
from mta.presentation import fixture
from mta.presentation.planning_expedite_grids import admitted_expedite_grids
from mta.presentation.rrr_sql import equal, key
from mta.presentation.selective import image_query
from mta.serialization import digest

PICK_TABLE = 'stage_demo_bpr_1."dbo__vf_PickListReport"'
REMARK_TABLE = 'stage_demo_bpr_1."dbo__BPRReport_RemarkDetails"'


def encoded(row):
    values = [v.isoformat() if isinstance(v,(date,datetime)) else str(v) if isinstance(v,Decimal) else v for v in row]
    return (json.dumps(values,ensure_ascii=False,separators=(',',':'),allow_nan=False)+'\n').encode()


def pick_source(*, verify_values=False):
    """Frozen staging is the retained full Pick source, not the narrower PickPost."""
    fixture.binding()
    with connection.cursor() as c:
        c.execute('SELECT values_sha256,row_count FROM stage2_owner.tables '
                  'WHERE source=%s AND table_name=%s', ['Demo_BPR_1','vf_PickListReport'])
        receipt = c.fetchone()
        if receipt is None or receipt[1] != 8063:
            raise ValueError('Planning retained Pick population changed')
        if verify_values:
            c.execute('SELECT * FROM '+PICK_TABLE+' ORDER BY vf_source_ordinal')
            fields = [column[0] for column in c.description]
            if fields[0] != 'vf_source_ordinal' or not {'SKUCode','WhCode','ParentStockForRationing'} <= set(fields):
                raise ValueError('Planning retained Pick columns changed')
            checksum, count = hashlib.sha256(), 0
            for row in c:
                if row[0] != count:
                    raise ValueError('Planning retained Pick ordinal changed')
                checksum.update(encoded(row[1:])); count += 1
            if (checksum.hexdigest(),count) != receipt:
                raise ValueError('Planning retained Pick values changed')
    return receipt[0]


def base_query(run):
    # This verifies the real retained five-row remark source, not a supplement.
    fixture.bpr_ancillary(run)
    nms, params = image_query(run, 'closing/consumer_context/NMSAllItems')
    query = ('WITH N AS ('+nms+') SELECT '
        'row_number() OVER (ORDER BY N.vf_ordinal,R.vf_source_ordinal NULLS FIRST)-1 AS ordinal,'
        'N.vf_ordinal AS nms_ordinal,R.vf_source_ordinal AS remark_ordinal,'
        'N."SKUCode" AS sku_code,N."WhCode" AS location_code,'
        +key('N."SKUCode"')+' AS sku_key,'+key('N."WhCode"')+' AS location_key,'
        'N."RLT" AS rlt,R."Remark" AS remark,'+key('R."Remark"')+' AS remark_key '
        'FROM N LEFT JOIN '+REMARK_TABLE+' R ON '+equal('N."SKUCode"','R."SKUCode"')+
        ' AND '+equal('N."WhCode"','R."WhCode"'))
    return query, params


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


def recipe_digest():
    return digest(dict(version=1,base=inspect.getsource(base_query),matches=inspect.getsource(match_query),
                       pick=inspect.getsource(pick_source),encoding=inspect.getsource(encoded),
                       pick_table=PICK_TABLE,remarks=REMARK_TABLE))
