from mta.presentation.native_mode import removed_mode
"""One-time native RRR occurrence membership for the retained April fixture."""
import inspect
import re

from mta.presentation.rrr_sql import equal, key
from mta.presentation.selective import image_query
from mta.runtime.relational_state import CATALOG, quote
from mta.serialization import digest


SOURCES = (
    ('R', 'reports/bpr/vf_RationedReqReport'),
    ('S', 'closing/dbm/SKULocStandardAttributes'),
    ('B', 'closing/importer/SkuLocAttributeData'),
    ('C', 'closing/importer/SkuAttributeData'),
    ('D', 'closing/importer/LocationAttributeData'),
)


def source_signatures(run):
    """Bind the recipe to exact admitted native dimensions and Pick projection."""
    if getattr(run, 'kind', None) == 'DAILY_CHAIN':
        from mta.presentation.daily_preparation import source_digest
        from mta.presentation.selective import image_metadata
        from mta.runtime.models import PickProjection
        source_digest(run)
        dimensions = {path: image_metadata(run, path) for _, path in SOURCES}
        pick = PickProjection.objects.filter(run=run).values('version', 'calculation_digest', 'rows_digest', 'row_count', 'provenance').get()
    else:
        dimensions = removed_mode('historical_fixture')
        pick = removed_mode('historical_fixture')
    return (digest(dimensions), digest(pick))


def bands_query(run):
    from mta.presentation.pick_storage import read_pick_bands
    bands = read_pick_bands(run)
    if not bands:
        if getattr(run, 'kind', None) == 'DAILY_CHAIN':
            # read_pick_bands has verified the real zero-row producer receipt.
            # Keep the native INNER join grain; never manufacture a Pick row.
            kinds = ('bigint', 'text', 'text', 'text', *(['bigint'] * 5))
            return ('SELECT ' + ','.join('NULL::' + kind + ' AS column' + str(i)
                                        for i, kind in enumerate(kinds, 1)) + ' WHERE FALSE'), []
        raise ValueError('RRR preparation requires the published Pick population')
    query = 'VALUES ' + ','.join(['(%s,%s,%s,%s,%s,%s,%s,%s,%s)'] * len(bands))
    values = []
    for ordinal, band in enumerate(bands):
        values.extend((ordinal, band['sku_code'], band['location_code'],
                       band['parent_location_code'], *[int(band[name]) for name in
                       ('to_black', 'to_red', 'to_yellow', 'to_green', 'to_blue')]))
    return query, values


def validate_positions(cursor, run, bands_sql, bands_params):
    """Move the exact unique-position/parent guard to admission once per identity."""
    positions, params = image_query(run, 'reports/bpr/vf_RationedReqReport')
    cursor.execute(
        'WITH R AS (' + positions + '),K AS (' + bands_sql + '),'
        'selected AS (SELECT DISTINCT column2,column3,column4 FROM K) '
        'SELECT K.column2,K.column3 FROM selected K LEFT JOIN R ON '
        + equal('R."SKUCode"', 'K.column2') + ' AND ' + equal('R."WhCode"', 'K.column3')
        + ' GROUP BY K.column2,K.column3,K.column4 HAVING count(R.vf_ordinal)<>1 OR '
        '(NOT ' + equal('K.column3', 'K.column4') + ' AND bool_and('
        + equal('R."ParentWhCode"', 'K.column4') + ') IS DISTINCT FROM TRUE)',
        [*params, *bands_params])
    if cursor.fetchone():
        raise ValueError('Pick band requires its unique produced rationed-report position/parent')


def membership_query(run, bands_sql, bands_params):
    """Return the exact stable INNER/LEFT occurrence grain; no auth or filter."""
    ctes, params = [], []
    for alias, path in SOURCES:
        query, values = image_query(run, path)
        ctes.append(alias + ' AS NOT MATERIALIZED (' + query + ')')
        params.extend(values)
    ctes.append('K AS (' + bands_sql + ')')
    params.extend(bands_params)
    virtual = equal('K.column3', 'K.column4')
    fields = (
        ('band_ordinal', 'K.column1'), ('rationed_ordinal', 'R.vf_ordinal'),
        ('standard_ordinal', 'S.vf_ordinal'), ('pair_ordinal', 'B.vf_ordinal'),
        ('sku_ordinal', 'C.vf_ordinal'), ('location_ordinal', 'D.vf_ordinal'),
        ('left_pair_ordinal', 'sla.vf_ordinal'), ('sku_key', key('R."SKUCode"')),
        ('location_key', key('R."WhCode"')), ('parent_key', key('R."ParentWhCode"')),
        ('virtual', virtual), ('dispatch_color_sequence', 'R."DispatchColorSequence"'),
        ('dispatch_pen', 'R."DispatchPen"'),
    )
    joins = (' FROM R JOIN K ON ' + equal('R."SKUCode"', 'K.column2')
             + ' AND ' + equal('R."WhCode"', 'K.column3')
             + ' JOIN S ON ' + equal('R."SKUCode"', 'S."SKUCode"')
             + ' AND ' + equal('R."WhCode"', 'S."WhCode"')
             + ' JOIN B ON ' + equal('R."SKUCode"', 'B."SKUCode"')
             + ' AND ' + equal('R."WhCode"', 'B."LocCode"')
             + ' JOIN C ON ' + equal('R."SKUCode"', 'C."SKUCode"')
             + ' JOIN D ON ' + equal('R."WhCode"', 'D."WHCode"')
             + ' LEFT JOIN B sla ON ' + equal('R."SKUCode"', 'sla."SKUCode"')
             + ' AND ' + equal('R."WhCode"', 'sla."LocCode"'))
    return ('WITH ' + ','.join(ctes) + ' SELECT '
            + ','.join(expression + ' AS ' + quote(name) for name, expression in fields)
            + joins), params


def a_selections():
    """Exact current virtual-row aliases/literals, shared by preparation receipt and reader."""
    copies = dict(ParentWhCode='WhCode', ParentWhName='WhName', ParentNorm='Norm',
        TechPenParent='TechPen', TechColorParent='TechColor', EcoPenParent='EcoPen',
        EcoColorParent='EcoColor', LeftoverParentStock='LeftoverStock',
        ParentPackSize='PackSize', AvgSiblingsNorm='AvgChildrenNorm',
        ParentStockPercentageForRationing='StockPercentageForRationing',
        ParentNormPercentReservation='NormPercentReservation')
    zero = {'Req', 'AllocatedForVirtualNormReq', 'AllocatedForNormReq',
            'AllocatedForSnPReq', 'RationedReq', 'RationedCasePacks',
            'LeftoverStock', 'SpikeOverdueAtParent', 'ResidualChildrenSnP',
            'AvgChildrenNorm'}
    selections = []
    for name, _ in CATALOG['tables']['BPR/vf_RationedReqReport']:
        original = 'R.' + quote(name)
        if name in copies:
            expression = 'CASE WHEN H.virtual THEN R.' + quote(copies[name]) + ' ELSE ' + original + ' END'
        elif name in zero or name == 'IsNormed':
            expression = 'CASE WHEN H.virtual THEN ' + ('FALSE' if name == 'IsNormed' else '0') + ' ELSE ' + original + ' END'
        elif name == 'AllocatedForDirectOrders':
            expression = 'CASE WHEN H.virtual THEN ' + original + ' ELSE 0 END'
        else:
            expression = original
        selections.append(expression + ' AS ' + quote(name))
    for name, source in zip(('TOR_B', 'TOR_R', 'TOY', 'TOG', 'TOBlue'),
                            ('to_black', 'to_red', 'to_yellow', 'to_green', 'to_blue')):
        selections.append('K.' + quote(source) + ' AS ' + quote(name))
    return selections


def recipe_digest(run=None):
    retained = dict(version=1, sources=SOURCES,
                       membership=inspect.getsource(membership_query),
                       validation=inspect.getsource(validate_positions),
                       virtual=inspect.getsource(a_selections))
    if getattr(run, 'kind', None) == 'DAILY_CHAIN':
        retained.update(version=2, bands=inspect.getsource(bands_query))
    return digest(retained)


FORWARD = r"""
CREATE FUNCTION mta.guard_rrr_prepared_build() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE owner uuid; k text; s text; d date;
BEGIN
  owner := nullif(current_setting('fresh.rrr_prepared_build',true),'')::uuid;
  IF owner IS NULL THEN RAISE EXCEPTION 'RRR preparation required'; END IF;
  SELECT kind,status,business_date INTO k,s,d FROM mta.fresh_mta_calculationrun WHERE id=owner FOR UPDATE;
  IF k IS DISTINCT FROM 'LEGACY_UI_FIXTURE' OR s IS DISTINCT FROM 'FIXTURE_BLOCKED'
     OR d IS DISTINCT FROM DATE '2026-04-07' THEN
    RAISE EXCEPTION 'RRR preparation requires the retained April fixture';
  END IF;
  IF EXISTS(SELECT 1 FROM mta.fresh_mta_rrrpreparedprojection WHERE run_id=owner) THEN
    RAISE EXCEPTION 'RRR prepared receipt already sealed';
  END IF;
  RETURN NULL;
END $$;
CREATE FUNCTION mta.guard_rrr_prepared_row() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF current_setting('fresh.rrr_prepared_build',true) IS DISTINCT FROM NEW.run_id::text THEN
    RAISE EXCEPTION 'RRR prepared row owner mismatch';
  END IF;
  RETURN NEW;
END $$;
CREATE FUNCTION mta.guard_rrr_prepared_receipt() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF current_setting('fresh.rrr_prepared_build',true) IS DISTINCT FROM NEW.run_id::text THEN
    RAISE EXCEPTION 'RRR prepared receipt owner mismatch';
  END IF;
  IF NEW.row_count IS DISTINCT FROM (SELECT count(*) FROM mta.fresh_mta_rrrpreparedmembership WHERE run_id=NEW.run_id) THEN
    RAISE EXCEPTION 'RRR prepared receipt population differs';
  END IF;
  RETURN NEW;
END $$;
CREATE FUNCTION mta.deny_rrr_prepared_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'RRR prepared rows and receipts are immutable'; END $$;
"""

BINDINGS = (
    ('rrr_prepared_member', 'fresh_mta_rrrpreparedmembership', 'guard_rrr_prepared_row'),
    ('rrr_prepared_receipt', 'fresh_mta_rrrpreparedprojection', 'guard_rrr_prepared_receipt'),
)
for _prefix, _table, _function in BINDINGS:
    FORWARD += f'''
CREATE TRIGGER {_prefix}_build BEFORE INSERT ON mta.{_table} FOR EACH STATEMENT EXECUTE FUNCTION mta.guard_rrr_prepared_build();
CREATE TRIGGER {_prefix}_insert BEFORE INSERT ON mta.{_table} FOR EACH ROW EXECUTE FUNCTION mta.{_function}();
CREATE TRIGGER {_prefix}_immutable BEFORE UPDATE OR DELETE OR TRUNCATE ON mta.{_table} FOR EACH STATEMENT EXECUTE FUNCTION mta.deny_rrr_prepared_mutation();
'''

REVERSE = '\n'.join(f'DROP TRIGGER {_prefix}_{suffix} ON mta.{_table};'
                    for _prefix, _table, _ in BINDINGS
                    for suffix in ('build', 'insert', 'immutable'))
REVERSE += '\n' + '\n'.join('DROP FUNCTION mta.' + name + '();' for name in (
    'guard_rrr_prepared_build', 'guard_rrr_prepared_row',
    'guard_rrr_prepared_receipt', 'deny_rrr_prepared_mutation'))


def verify_guards(connection):
    expected = {}
    for prefix, table, function in BINDINGS:
        for suffix, bits, target in (('build', 6, 'guard_rrr_prepared_build'),
                ('insert', 7, function), ('immutable', 58, 'deny_rrr_prepared_mutation')):
            expected[prefix + '_' + suffix] = (table, 'O', bits, target, None, 0)
    bodies = dict(re.findall(r'CREATE FUNCTION mta\.(\w+)\(\).*?AS \$\$(.*?)\$\$;', FORWARD, re.S))
    with connection.cursor() as cursor:
        cursor.execute('SELECT t.tgname,c.relname,t.tgenabled,t.tgtype,p.proname,t.tgqual::text,t.tgnargs '
                       'FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid '
                       'JOIN pg_namespace n ON n.oid=c.relnamespace JOIN pg_proc p ON p.oid=t.tgfoid '
                       'JOIN pg_namespace pn ON pn.oid=p.pronamespace '
                       "WHERE n.nspname='mta' AND pn.nspname='mta' AND t.tgname=ANY(%s)", [list(expected)])
        if {name: tuple(row) for name, *row in cursor.fetchall()} != expected:
            raise ValueError('RRR prepared trigger contract differs')
        cursor.execute('SELECT p.proname,p.prosrc,p.prolang=l.oid,p.prosecdef FROM pg_proc p '
                       "JOIN pg_namespace n ON n.oid=p.pronamespace JOIN pg_language l ON l.lanname='plpgsql' "
                       "WHERE n.nspname='mta' AND p.proname=ANY(%s) AND p.pronargs=0", [list(bodies)])
        from mta.runtime.daily_prepared_schema import installed_bodies
        bodies = installed_bodies(connection, bodies)
        if {name: tuple(row) for name, *row in cursor.fetchall()} != {
                name: (body, True, False) for name, body in bodies.items()}:
            raise ValueError('RRR prepared function contract differs')
