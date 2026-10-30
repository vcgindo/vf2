"""Private, short-lived join operands for parent Expedite transit preparation.

Callers retain source/run/phase admission and the atomic receipt boundary. Each
relation remains an occurrence bag; Full and scoped callers supply their own
Pick grain. No business state or request-time projection is stored here.
"""
from contextlib import contextmanager
import inspect
from uuid import uuid4

from django.db import connection, transaction, DatabaseError
from mta.application.stage_observation import stage, summary
from mta.presentation.rrr_sql import key, equal
from mta.serialization import digest


def recipe_digest():
    return digest(dict(version=1, source=inspect.getsource(inspect.getmodule(recipe_digest)),
                       key=inspect.getsource(key), equal=inspect.getsource(equal)))


@contextmanager
def prepared_match(*, base, remarks, facts, grids, pick):
    """Evaluate narrow operands once, independent of shared new-owner estimates.

    Relations are (SQL, parameters) from already admitted callers. In particular
    Pick source ordinals must not be collapsed to a business-key dictionary.
    """
    if not connection.in_atomic_block:
        raise ValueError('Transit preparation requires its caller transaction')
    names = []
    prefix = 'vf_transit_' + uuid4().hex + '_'
    try:
        bsql, bp = base
        rsql, rp = remarks
        asql, ap = facts
        gsql, gp = grids
        psql, pp = pick
        operands = (
            ('base', 'SELECT B.ordinal,B.remark_ordinal FROM (' + bsql + ') B', bp,
             '(remark_ordinal)'),
            ('parent', 'WITH R AS (' + rsql + '),A AS (' + asql + '),G AS (' + gsql + ') '
             'SELECT R.vf_ordinal AS remark_ordinal,G.branch,G.ordinal AS grid_ordinal,'
             + key('A."SKUCode"') + ' AS sku_key,' + key('A."WhCode"') + ' AS location_key '
             'FROM R JOIN A ON ' + equal('A."SKUCode"', 'R."SKUCode"') + ' AND '
             + equal('A."WhCode"', 'R."WhCode"')
             + " JOIN G ON G.direction='parent' AND G.run_id=A.run_id AND G.fact_ordinal=A.ordinal",
             [*rp, *ap, *gp], '(remark_ordinal)'),
            ('pick', 'SELECT P.vf_source_ordinal AS pick_ordinal,' + key('P."SKUCode"')
             + ' AS sku_key,' + key('P."WhCode"') + ' AS location_key,'
             'P."ParentStockForRationing" AS parent_stock FROM (' + psql + ') P', pp,
             '(sku_key,location_key)'),
        )
        relations = {}
        for name, sql, params, index in operands:
            quoted = connection.ops.quote_name(prefix + name)
            relation = 'pg_temp.' + quoted
            with stage('transit_join_operand', operand=name), connection.cursor() as cursor:
                cursor.execute('CREATE TEMP TABLE ' + quoted + ' ON COMMIT DROP AS ' + sql, params)
                names.append(relation)
                summary('transit_join_rows', operand=name, rows=cursor.rowcount)
                cursor.execute('CREATE INDEX ON ' + relation + ' ' + index)
                cursor.execute('ANALYZE ' + relation)
            relations[name] = relation
        yield ('WITH candidates AS (SELECT B.ordinal AS base_ordinal,G.branch,G.grid_ordinal,'
               'P.pick_ordinal,P.parent_stock FROM ' + relations['base'] + ' B JOIN '
               + relations['parent'] + ' G ON G.remark_ordinal=B.remark_ordinal LEFT JOIN '
               + relations['pick'] + ' P ON P.sku_key=G.sku_key AND P.location_key=G.location_key) '
               'SELECT row_number() OVER (ORDER BY base_ordinal,branch,grid_ordinal,'
               'pick_ordinal NULLS FIRST)-1 AS ordinal,base_ordinal,branch,grid_ordinal,'
               'pick_ordinal,parent_stock FROM candidates', [])
    except DatabaseError:
        transaction.set_rollback(True)
        raise
    finally:
        # A failed SQL transaction drops its CREATEs when the caller rolls back.
        # Otherwise release even inside a longer enclosing atomic operation.
        if names and not connection.needs_rollback:
            with connection.cursor() as cursor:
                cursor.execute('DROP TABLE ' + ','.join(names))
