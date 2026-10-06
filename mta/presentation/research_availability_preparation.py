"""Immutable per-occurrence Research availability band preparation."""
import inspect
import re

from mta.presentation.history_native import COLOURS
from mta.presentation.history_preparation import RUN_ID
from mta.presentation.selective import image_query
from mta.runtime.relational_state import quote
from mta.serialization import digest


SOURCE = 'closing/btr/BufferTrendPhysicalInv'
MEMBERSHIP_TABLE = 'fresh_mta_researchavailabilitymembership'
BAND_TABLE = 'fresh_mta_researchavailabilityband'
RECEIPT_TABLE = 'fresh_mta_researchavailabilitybandprojection'
BANDS = ((1, 30), (31, 60), (61, 90))
RECOGNIZED_COLOURS = tuple(colour for _, colour in COLOURS)


def _literal(value):
    return "'" + value.replace("'", "''") + "'"


def _count_expression(first, last, colours):
    accepted = ','.join(_literal(colour) for colour in colours)
    return '+'.join(
        'CASE WHEN A.' + quote('D' + str(day)) + ' IN (' + accepted + ') THEN 1 ELSE 0 END'
        for day in range(first, last + 1)
    )


def bands_query(run):
    """Return one band-count row for every sealed availability occurrence.

    The source codes stay byte-for-byte equal to the physical-history values.
    Membership already carries SKU/location dimension multiplicity, so this query
    deliberately has no dimension or pair join and performs no deduplication.
    """
    physical, params = image_query(run, SOURCE)
    fields = [
        ('ordinal', 'M.ordinal'),
        ('history_ordinal', 'M.history_ordinal'),
        ('sku_code', 'A."SKUCode"'),
        ('location_code', 'A."WhCode"'),
    ]
    for first, last in BANDS:
        suffix = f'{first:02d}_{last}'
        fields.extend((
            ('black_' + suffix, _count_expression(first, last, ('Black',))),
            ('recognized_' + suffix, _count_expression(first, last, RECOGNIZED_COLOURS)),
        ))
    sql = (
        'WITH A AS NOT MATERIALIZED (' + physical + ') SELECT '
        + ','.join(value + ' AS ' + quote(name) for name, value in fields)
        + ' FROM mta.' + quote(MEMBERSHIP_TABLE) + ' M'
        + ' JOIN A ON A.vf_ordinal=M.history_ordinal'
        + ' WHERE M.run_id=%s ORDER BY M.ordinal'
    )
    return sql, [*params, run.pk]


def recipe_digest():
    return digest(dict(
        version=1,
        source=SOURCE,
        membership_table=MEMBERSHIP_TABLE,
        bands=BANDS,
        recognized_colours=RECOGNIZED_COLOURS,
        query=inspect.getsource(bands_query),
        count_expression=inspect.getsource(_count_expression),
    ))


FORWARD = rf"""
CREATE FUNCTION mta.guard_research_availability_band_build() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE owner uuid; k text; s text; d date;
BEGIN
  owner := nullif(current_setting('fresh.research_availability_band_build',true),'')::uuid;
  IF owner IS NULL THEN RAISE EXCEPTION 'Research availability band preparation required'; END IF;
  SELECT kind,status,business_date INTO k,s,d FROM mta.fresh_mta_calculationrun WHERE id=owner FOR UPDATE;
  IF owner IS DISTINCT FROM '{RUN_ID}'::uuid
     OR k IS DISTINCT FROM 'LEGACY_UI_FIXTURE' OR s IS DISTINCT FROM 'FIXTURE_BLOCKED'
     OR d IS DISTINCT FROM DATE '2026-04-07' THEN
    RAISE EXCEPTION 'Research availability bands require the retained April fixture';
  END IF;
  IF EXISTS(SELECT 1 FROM mta.{RECEIPT_TABLE} WHERE run_id=owner) THEN
    RAISE EXCEPTION 'Research availability band receipt already sealed';
  END IF;
  RETURN NULL;
END $$;
CREATE FUNCTION mta.guard_research_availability_band_row() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF current_setting('fresh.research_availability_band_build',true) IS DISTINCT FROM NEW.run_id::text THEN
    RAISE EXCEPTION 'Research availability band row owner mismatch';
  END IF;
  RETURN NEW;
END $$;
CREATE FUNCTION mta.guard_research_availability_band_receipt() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF current_setting('fresh.research_availability_band_build',true) IS DISTINCT FROM NEW.run_id::text
     OR NEW.status IS DISTINCT FROM 'READY' THEN
    RAISE EXCEPTION 'Research availability band receipt must be ready and owner-bound';
  END IF;
  IF NEW.row_count IS DISTINCT FROM (SELECT count(*) FROM mta.{BAND_TABLE} WHERE run_id=NEW.run_id)
     OR NEW.row_count IS DISTINCT FROM (SELECT availability_count FROM mta.fresh_mta_historypreparedprojection WHERE run_id=NEW.run_id)
     OR NEW.membership_digest IS DISTINCT FROM (SELECT availability_digest FROM mta.fresh_mta_historypreparedprojection WHERE run_id=NEW.run_id)
     OR NEW.source_digest IS DISTINCT FROM (SELECT source_digest FROM mta.fresh_mta_historypreparedprojection WHERE run_id=NEW.run_id) THEN
    RAISE EXCEPTION 'Research availability band receipt source or population differs';
  END IF;
  RETURN NEW;
END $$;
CREATE FUNCTION mta.deny_research_availability_band_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'Research availability band rows and receipt are immutable'; END $$;
"""

BINDINGS = (
    ('research_availability_band', BAND_TABLE, 'guard_research_availability_band_row'),
    ('research_availability_band_receipt', RECEIPT_TABLE, 'guard_research_availability_band_receipt'),
)
for _prefix, _table, _function in BINDINGS:
    FORWARD += f'''\nCREATE TRIGGER {_prefix}_build BEFORE INSERT ON mta.{_table} FOR EACH STATEMENT EXECUTE FUNCTION mta.guard_research_availability_band_build();
CREATE TRIGGER {_prefix}_insert BEFORE INSERT ON mta.{_table} FOR EACH ROW EXECUTE FUNCTION mta.{_function}();
CREATE TRIGGER {_prefix}_immutable BEFORE UPDATE OR DELETE OR TRUNCATE ON mta.{_table} FOR EACH STATEMENT EXECUTE FUNCTION mta.deny_research_availability_band_mutation();\n'''

REVERSE = '\n'.join(
    f'DROP TRIGGER {_prefix}_{suffix} ON mta.{_table};'
    for _prefix, _table, _ in BINDINGS for suffix in ('build', 'insert', 'immutable')
)
REVERSE += '\n' + '\n'.join('DROP FUNCTION mta.' + name + '();' for name in (
    'guard_research_availability_band_build',
    'guard_research_availability_band_row',
    'guard_research_availability_band_receipt',
    'deny_research_availability_band_mutation',
))


def verify_guards(connection):
    expected = {}
    for prefix, table, function in BINDINGS:
        for suffix, bits, target in (
            ('build', 6, 'guard_research_availability_band_build'),
            ('insert', 7, function),
            ('immutable', 58, 'deny_research_availability_band_mutation'),
        ):
            expected[prefix + '_' + suffix] = (table, 'O', bits, target, None, 0)
    bodies = dict(re.findall(r'CREATE FUNCTION mta\.(\w+)\(\).*?AS \$\$(.*?)\$\$;', FORWARD, re.S))
    with connection.cursor() as cursor:
        cursor.execute(
            'SELECT t.tgname,c.relname,t.tgenabled,t.tgtype,p.proname,t.tgqual::text,t.tgnargs '
            'FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid '
            'JOIN pg_namespace n ON n.oid=c.relnamespace JOIN pg_proc p ON p.oid=t.tgfoid '
            'JOIN pg_namespace pn ON pn.oid=p.pronamespace '
            "WHERE n.nspname='mta' AND pn.nspname='mta' AND t.tgname=ANY(%s)",
            [list(expected)],
        )
        if {name: tuple(row) for name, *row in cursor.fetchall()} != expected:
            raise ValueError('Research availability band trigger contract differs')
        cursor.execute(
            'SELECT p.proname,p.prosrc,p.prolang=l.oid,p.prosecdef FROM pg_proc p '
            "JOIN pg_namespace n ON n.oid=p.pronamespace JOIN pg_language l ON l.lanname='plpgsql' "
            "WHERE n.nspname='mta' AND p.proname=ANY(%s) AND p.pronargs=0",
            [list(bodies)],
        )
        from mta.runtime.daily_prepared_schema import installed_bodies
        bodies = installed_bodies(connection, bodies)
        if {name: tuple(row) for name, *row in cursor.fetchall()} != {
                name: (body, True, False) for name, body in bodies.items()}:
            raise ValueError('Research availability band function contract differs')
