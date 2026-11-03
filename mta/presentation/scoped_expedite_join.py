"""Statement-local parent operands for the runtime role, which cannot create TEMP.

The installer has its own indexed preparation path. This scoped query keeps
every input occurrence and the original join/order, without database objects,
session grants, or a persistent intermediate representation.
"""
import inspect
from contextlib import contextmanager

from django.db import connection, transaction, DatabaseError

from mta.presentation.rrr_sql import key, equal
from mta.serialization import digest


def recipe_digest():
    return digest(dict(version=1, source=inspect.getsource(inspect.getmodule(recipe_digest)),
                       key=inspect.getsource(key), equal=inspect.getsource(equal)))


@contextmanager
def prepared_match(**relations):
    if not connection.in_atomic_block:
        raise ValueError('Scoped transit preparation requires its caller transaction')
    with connection.cursor() as cursor:
        cursor.execute("SELECT current_setting('enable_nestloop')")
        previous = cursor.fetchone()[0]
        # A fresh generation can be estimated as one row despite containing a
        # full occurrence bag. All these joins have equality keys; repeated
        # scans were quadratic under that estimate. Limit this preference to
        # the match statement, retaining the caller's timeout and work_mem.
        cursor.execute("SELECT set_config('enable_nestloop','off',true)")
    try:
        yield match_query(**relations)
    except DatabaseError:
        transaction.set_rollback(True)
        raise
    finally:
        if not connection.needs_rollback:
            with connection.cursor() as cursor:
                cursor.execute("SELECT set_config('enable_nestloop',%s,true)", [previous])


def match_query(*, base, remarks, facts, grids, pick):
    """Read admitted relations once per statement; preserve raw Pick fanout."""
    bsql, bp = base
    rsql, rp = remarks
    asql, ap = facts
    gsql, gp = grids
    psql, pp = pick
    return (
        'WITH base_operand AS MATERIALIZED (SELECT B.ordinal,B.remark_ordinal FROM (' + bsql + ') B),'
        'parent_operand AS MATERIALIZED (WITH R AS (' + rsql + '),A AS (' + asql + '),G AS (' + gsql + ') '
        'SELECT R.vf_ordinal AS remark_ordinal,G.branch,G.ordinal AS grid_ordinal,'
        + key('A."SKUCode"') + ' AS sku_key,' + key('A."WhCode"') + ' AS location_key '
        'FROM R JOIN A ON ' + equal('A."SKUCode"', 'R."SKUCode"') + ' AND '
        + equal('A."WhCode"', 'R."WhCode"')
        + " JOIN G ON G.direction='parent' AND G.run_id=A.run_id AND G.fact_ordinal=A.ordinal),"
        'pick_operand AS MATERIALIZED (SELECT P.vf_source_ordinal AS pick_ordinal,'
        + key('P."SKUCode"') + ' AS sku_key,' + key('P."WhCode"') + ' AS location_key,'
        'P."ParentStockForRationing" AS parent_stock FROM (' + psql + ') P),'
        'candidates AS (SELECT B.ordinal AS base_ordinal,G.branch,G.grid_ordinal,'
        'P.pick_ordinal,P.parent_stock FROM base_operand B JOIN parent_operand G '
        'ON G.remark_ordinal=B.remark_ordinal LEFT JOIN pick_operand P '
        'ON P.sku_key=G.sku_key AND P.location_key=G.location_key) '
        'SELECT row_number() OVER (ORDER BY base_ordinal,branch,grid_ordinal,'
        'pick_ordinal NULLS FIRST)-1 AS ordinal,base_ordinal,branch,grid_ordinal,'
        'pick_ordinal,parent_stock FROM candidates', [*bp, *rp, *ap, *gp, *pp])
