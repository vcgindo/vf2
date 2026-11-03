"""Qualify the reference roster against the display that will serve it."""
from django.db import connection

from mta.presentation.context import PublicationUnavailable
from mta.runtime.models import BtrPresentationRow


FORMAT = 'btr-display-reference-v1'
TABLE = 'mta.' + BtrPresentationRow._meta.db_table


class RequiresPhysicalReferences(Exception):
    """The canonical bag requires the existing physical reference builder."""


def private_references(run, generation):
    from mta.presentation import btr_reporting as ref
    name = connection.ops.quote_name('vf_btr_canonical_' + generation.pk.hex)
    with connection.cursor() as c:
        c.execute('CREATE TEMP TABLE '+name+' (LIKE '+ref.REF_TABLE+') ON COMMIT DROP')
        # Use a private sequence; no production reference IDs are consumed.
        c.execute('ALTER TABLE '+name+' ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY')
    table = 'pg_temp.'+name
    ref._populate(run, generation, target=table)
    with connection.cursor() as c:
        c.execute('ANALYZE '+table)
    return table


def relation(generation, branch, export, bounds, *, pair=None):
    from mta.presentation.btr_reporting import ORDINALS
    if branch not in ('tech','eco') or type(export) is not bool:
        raise ValueError('Invalid BTR reference branch')
    fields = ','.join('NULL::bigint AS sla_ordinal' if export and field=='sla_ordinal' else field
                      for field in ORDINALS.values())
    low, high = bounds[branch]
    columns = ('id,generation_id,branch,%s::boolean AS export,filter_a_skucode AS sku_code,'
               'filter_a_whcode AS location_code,sku_key,location_key,'+fields)
    if pair is None:
        return ('SELECT '+columns+' FROM '+TABLE+' WHERE generation_id=%s AND branch=%s AND id BETWEEN %s AND %s',
                [export,generation.pk,branch,low,high])
    from mta.presentation.rrr_sql import key
    # A new UUID can estimate one occurrence for the entire generation. Bind
    # all four index keys together without expanding broad permission sets.
    return ('WITH sought(g,b,s,l) AS MATERIALIZED (VALUES (%s::uuid,%s::text,'+key('%s::text')+','+
            key('%s::text')+')) SELECT found.* FROM sought CROSS JOIN LATERAL (SELECT '+columns+
            ' FROM '+TABLE+' WHERE generation_id=g AND branch=b AND sku_key=s AND location_key=l OFFSET 0) found',
            [generation.pk,branch,*pair,export])


def certify(run, generation, temporary, populations):
    """Compare complete typed occurrences in original ID order before sealing."""
    from mta.presentation.btr_reporting import ROW_FIELDS
    fields = ','.join(ROW_FIELDS)
    bounds = dict.fromkeys(('tech','eco'), (None,None))
    with connection.cursor() as c:
        c.execute('SELECT branch,min(id),max(id) FROM '+TABLE+' WHERE generation_id=%s GROUP BY branch',
                  [generation.pk])
        for branch, low, high in c.fetchall():
            bounds[branch] = (low, high)
        for branch in bounds:
            for export in (False, True):
                projected, args = relation(generation, branch, export, bounds)
                original = 'SELECT * FROM '+temporary+' WHERE generation_id=%s AND branch=%s AND export=%s'
                params = [generation.pk,branch,export,*args]
                sources = 'WITH original AS ('+original+'), projected AS ('+projected+') '
                ordered = 'row_number() OVER (ORDER BY id) AS position,'+fields
                def differs(columns):
                    c.execute(sources+'SELECT EXISTS ((SELECT '+columns+' FROM original EXCEPT ALL SELECT '+
                              columns+' FROM projected) UNION ALL (SELECT '+columns+
                              ' FROM projected EXCEPT ALL SELECT '+columns+' FROM original))', params)
                    return c.fetchone()[0]
                if differs(ordered):
                    if export and not differs(fields):
                        raise RequiresPhysicalReferences(branch)
                    raise PublicationUnavailable('btr_projected_reference_occurrences_differ')
            if populations[branch] != generation.lineage['images'][branch+'_A']['count']:
                raise PublicationUnavailable('btr_projected_reference_population_differs')
    return dict(format=FORMAT, bounds=bounds)
