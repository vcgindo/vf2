"""Exact stable memberships for retained Research and Buffer Trends readers."""
import inspect
import re

from mta.presentation import fixture
from mta.presentation.rrr_sql import equal, key
from mta.presentation.selective import image_query
from mta.runtime.relational_state import quote
from mta.serialization import digest


RUN_ID = 'bfd75b4b-a9df-4a08-82d3-852e3324b623'
SOURCES = {
    'R': 'reports/bpr/vf_RationedReqReport',
    'physical': 'closing/btr/BufferTrendPhysicalInv',
    'dispatch': 'closing/btr/BufferTrendDispatch',
    'sa': 'closing/btr/SkuAttributeData',
    'la': 'closing/btr/LocationAttributeData',
    'sla': 'closing/btr/SkuLocAttributeData',
    'dates': 'closing/btr/BufferTrendDates',
}


def source_signatures(run):
    if getattr(run, 'kind', None) == 'DAILY_CHAIN':
        from mta.presentation.daily_preparation import source_digest
        from mta.presentation.selective import image_metadata
        source_digest(run)
        return digest({path: image_metadata(run, path) for path in SOURCES.values()})
    return digest(fixture.image_metadata_batch(run, list(SOURCES.values())))


def _relations(run, names):
    ctes, params = [], []
    for alias in names:
        query, values = image_query(run, SOURCES[alias])
        ctes.append(alias + ' AS NOT MATERIALIZED (' + query + ')')
        params.extend(values)
    return ctes, params


def research_master_query(run):
    ctes, params = _relations(run, ('R',))
    fields = (('owner_sku_key', key('R."SKUCode"')),
              ('owner_location_key', key('R."WhCode"')),
              ('rationed_ordinal', 'R.vf_ordinal'))
    return ('WITH ' + ','.join(ctes) + ' SELECT ' +
            ','.join(value + ' AS ' + quote(name) for name, value in fields)
            + ' FROM R WHERE R."SKUCode" IS NOT NULL AND R."WhCode" IS NOT NULL'), params


def research_history_query(run):
    """Index direct/child history; selected master rows supply parent lookup keys."""
    parts, params = [], []
    for family in ('physical', 'dispatch'):
        ctes, values = _relations(run, (family,))
        params.extend(values)
        h = family
        direct = ('SELECT ' + key(h + '."SKUCode"') + ' AS owner_sku_key,'
                  + key(h + '."WhCode"') + ' AS owner_location_key,' + h + '.vf_ordinal AS history_ordinal FROM ' + h
                  + ' WHERE ' + h + '."SKUCode" IS NOT NULL AND ' + h + '."WhCode" IS NOT NULL')
        child = ('SELECT ' + key(h + '."SKUCode"') + ',' + key(h + '."ParentWhCode"') + ','
                 + h + '.vf_ordinal FROM ' + h + ' WHERE ' + h + '."SKUCode" IS NOT NULL AND '
                 + h + '."ParentWhCode" IS NOT NULL')
        parts.append('WITH ' + ','.join(ctes) + ' SELECT DISTINCT owner_sku_key,owner_location_key,'
                     + "'" + family + "' AS family,history_ordinal FROM ("
                     + direct + ' UNION ALL ' + child + ') owners')
    return ' UNION ALL '.join('(' + part + ')' for part in parts), params


def availability_query(run):
    ctes, params = _relations(run, ('physical', 'sa', 'la'))
    fields = (('history_ordinal', 'physical.vf_ordinal'), ('sku_ordinal', 'sa.vf_ordinal'),
              ('location_ordinal', 'la.vf_ordinal'), ('sku_key', key('physical."SKUCode"')),
              ('location_key', key('physical."WhCode"')))
    joins = (' FROM physical JOIN sa ON ' + equal('physical."SKUCode"', 'sa."SKUCode"')
             + ' JOIN la ON ' + equal('physical."WhCode"', 'la."WHCode"'))
    return ('WITH ' + ','.join(ctes) + ' SELECT '
            + ','.join(value + ' AS ' + quote(name) for name, value in fields) + joins), params


def graph_query(run):
    parts, params = [], []
    for family in ('physical', 'dispatch'):
        ctes, values = _relations(run, (family, 'sa', 'la', 'sla'))
        params.extend(values)
        fields = (('family', "'" + family + "'"), ('history_ordinal', family + '.vf_ordinal'),
                  ('sku_ordinal', 'sa.vf_ordinal'), ('location_ordinal', 'la.vf_ordinal'),
                  ('pair_ordinal', 'sla.vf_ordinal'), ('sku_key', key(family + '."SKUCode"')),
                  ('location_key', key(family + '."WhCode"')))
        joins = (' FROM ' + family + ' JOIN sa ON ' + equal(family + '."SKUCode"', 'sa."SKUCode"')
                 + ' JOIN la ON ' + equal(family + '."WhCode"', 'la."WHCode"')
                 + ' LEFT JOIN sla ON ' + equal(family + '."SKUCode"', 'sla."SKUCode"')
                 + ' AND ' + equal(family + '."WhCode"', 'sla."LocCode"'))
        parts.append('WITH ' + ','.join(ctes) + ' SELECT '
                     + ','.join(value + ' AS ' + quote(name) for name, value in fields) + joins)
    return ' UNION ALL '.join('(' + part + ')' for part in parts), params


def recipe_digest():
    return digest(dict(version=1, sources=SOURCES, queries={name: inspect.getsource(fn) for name, fn in (
        ('research_master', research_master_query), ('research_history', research_history_query),
        ('availability', availability_query), ('graph', graph_query))}))


FORWARD = r"""
CREATE FUNCTION mta.guard_history_prepared_build() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE owner uuid; k text; s text; d date;
BEGIN
  owner := nullif(current_setting('fresh.history_prepared_build',true),'')::uuid;
  IF owner IS NULL THEN RAISE EXCEPTION 'History report preparation required'; END IF;
  SELECT kind,status,business_date INTO k,s,d FROM mta.fresh_mta_calculationrun WHERE id=owner FOR UPDATE;
  IF owner IS DISTINCT FROM 'bfd75b4b-a9df-4a08-82d3-852e3324b623'::uuid
     OR k IS DISTINCT FROM 'LEGACY_UI_FIXTURE' OR s IS DISTINCT FROM 'FIXTURE_BLOCKED'
     OR d IS DISTINCT FROM DATE '2026-04-07' THEN
    RAISE EXCEPTION 'History preparation requires the retained April fixture';
  END IF;
  IF EXISTS(SELECT 1 FROM mta.fresh_mta_historypreparedprojection WHERE run_id=owner) THEN
    RAISE EXCEPTION 'History prepared receipt already sealed';
  END IF;
  RETURN NULL;
END $$;
CREATE FUNCTION mta.guard_history_prepared_row() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF current_setting('fresh.history_prepared_build',true) IS DISTINCT FROM NEW.run_id::text THEN
    RAISE EXCEPTION 'History prepared row owner mismatch';
  END IF;
  RETURN NEW;
END $$;
CREATE FUNCTION mta.guard_history_prepared_receipt() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF current_setting('fresh.history_prepared_build',true) IS DISTINCT FROM NEW.run_id::text
     OR NEW.status IS DISTINCT FROM 'READY' THEN
    RAISE EXCEPTION 'History prepared receipt must be ready and owner-bound';
  END IF;
  IF NEW.research_master_count IS DISTINCT FROM (SELECT count(*) FROM mta.fresh_mta_researchpreparedmasterreference WHERE run_id=NEW.run_id)
     OR NEW.research_history_count IS DISTINCT FROM (SELECT count(*) FROM mta.fresh_mta_researchpreparedhistoryreference WHERE run_id=NEW.run_id)
     OR NEW.availability_count IS DISTINCT FROM (SELECT count(*) FROM mta.fresh_mta_researchavailabilitymembership WHERE run_id=NEW.run_id)
     OR NEW.graph_count IS DISTINCT FROM (SELECT count(*) FROM mta.fresh_mta_buffergraphpreparedmembership WHERE run_id=NEW.run_id) THEN
    RAISE EXCEPTION 'History prepared receipt population differs';
  END IF;
  RETURN NEW;
END $$;
CREATE FUNCTION mta.deny_history_prepared_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'History prepared rows and receipt are immutable'; END $$;
"""

BINDINGS = (
    ('history_master_ref', 'fresh_mta_researchpreparedmasterreference', 'guard_history_prepared_row'),
    ('history_selected_ref', 'fresh_mta_researchpreparedhistoryreference', 'guard_history_prepared_row'),
    ('history_availability', 'fresh_mta_researchavailabilitymembership', 'guard_history_prepared_row'),
    ('history_graph', 'fresh_mta_buffergraphpreparedmembership', 'guard_history_prepared_row'),
    ('history_receipt', 'fresh_mta_historypreparedprojection', 'guard_history_prepared_receipt'),
)
for _prefix, _table, _function in BINDINGS:
    FORWARD += f'''\nCREATE TRIGGER {_prefix}_build BEFORE INSERT ON mta.{_table} FOR EACH STATEMENT EXECUTE FUNCTION mta.guard_history_prepared_build();
CREATE TRIGGER {_prefix}_insert BEFORE INSERT ON mta.{_table} FOR EACH ROW EXECUTE FUNCTION mta.{_function}();
CREATE TRIGGER {_prefix}_immutable BEFORE UPDATE OR DELETE OR TRUNCATE ON mta.{_table} FOR EACH STATEMENT EXECUTE FUNCTION mta.deny_history_prepared_mutation();\n'''

REVERSE = '\n'.join(f'DROP TRIGGER {_prefix}_{suffix} ON mta.{_table};'
                    for _prefix, _table, _ in BINDINGS for suffix in ('build','insert','immutable'))
REVERSE += '\n' + '\n'.join('DROP FUNCTION mta.' + name + '();' for name in (
    'guard_history_prepared_build', 'guard_history_prepared_row',
    'guard_history_prepared_receipt', 'deny_history_prepared_mutation'))


def verify_guards(connection):
    expected = {}
    for prefix, table, function in BINDINGS:
        for suffix, bits, target in (('build', 6, 'guard_history_prepared_build'),
                ('insert', 7, function), ('immutable', 58, 'deny_history_prepared_mutation')):
            expected[prefix + '_' + suffix] = (table, 'O', bits, target, None, 0)
    bodies = dict(re.findall(r'CREATE FUNCTION mta\.(\w+)\(\).*?AS \$\$(.*?)\$\$;', FORWARD, re.S))
    with connection.cursor() as cursor:
        cursor.execute('SELECT t.tgname,c.relname,t.tgenabled,t.tgtype,p.proname,t.tgqual::text,t.tgnargs '
                       'FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid '
                       'JOIN pg_namespace n ON n.oid=c.relnamespace JOIN pg_proc p ON p.oid=t.tgfoid '
                       'JOIN pg_namespace pn ON pn.oid=p.pronamespace '
                       "WHERE n.nspname='mta' AND pn.nspname='mta' AND t.tgname=ANY(%s)", [list(expected)])
        if {name: tuple(row) for name, *row in cursor.fetchall()} != expected:
            raise ValueError('History prepared trigger contract differs')
        cursor.execute('SELECT p.proname,p.prosrc,p.prolang=l.oid,p.prosecdef FROM pg_proc p '
                       "JOIN pg_namespace n ON n.oid=p.pronamespace JOIN pg_language l ON l.lanname='plpgsql' "
                       "WHERE n.nspname='mta' AND p.proname=ANY(%s) AND p.pronargs=0", [list(bodies)])
        from mta.runtime.daily_prepared_schema import installed_bodies
        bodies = installed_bodies(connection, bodies)
        if {name: tuple(row) for name, *row in cursor.fetchall()} != {
                name: (body, True, False) for name, body in bodies.items()}:
            raise ValueError('History prepared function contract differs')
