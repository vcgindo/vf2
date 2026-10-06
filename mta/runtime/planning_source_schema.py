"""Narrow immutable build/seal guards for the two Planning source masters."""
FORWARD = r"""
CREATE FUNCTION mta.guard_planning_source_build() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE owner uuid; k text; s text; d date;
BEGIN
  owner := nullif(current_setting('fresh.planning_source_build',true),'')::uuid;
  IF owner IS NULL THEN RAISE EXCEPTION 'Planning source preparation required'; END IF;
  SELECT kind,status,business_date INTO k,s,d FROM mta.fresh_mta_calculationrun WHERE id=owner FOR UPDATE;
  IF k IS DISTINCT FROM 'LEGACY_UI_FIXTURE' OR s IS DISTINCT FROM 'FIXTURE_BLOCKED'
     OR d IS DISTINCT FROM DATE '2026-04-07' THEN
    RAISE EXCEPTION 'Planning sources require the retained April fixture';
  END IF;
  IF EXISTS(SELECT 1 FROM mta.fresh_mta_planningsourceprojection WHERE run_id=owner) THEN
    RAISE EXCEPTION 'Planning source receipt already sealed';
  END IF;
  RETURN NULL;
END $$;
CREATE FUNCTION mta.guard_planning_source_row() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF current_setting('fresh.planning_source_build',true) IS DISTINCT FROM NEW.run_id::text THEN
    RAISE EXCEPTION 'Planning source row owner mismatch';
  END IF;
  RETURN NEW;
END $$;
CREATE FUNCTION mta.guard_planning_source_receipt() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF current_setting('fresh.planning_source_build',true) IS DISTINCT FROM NEW.run_id::text THEN
    RAISE EXCEPTION 'Planning source receipt owner mismatch';
  END IF;
  IF NEW.bpr_count IS DISTINCT FROM (SELECT count(*) FROM mta.fresh_mta_planningbprmasterrow WHERE run_id=NEW.run_id)
     OR NEW.git_count IS DISTINCT FROM (SELECT count(*) FROM mta.fresh_mta_planninggitmasterrow WHERE run_id=NEW.run_id) THEN
    RAISE EXCEPTION 'Planning source receipt population differs';
  END IF;
  RETURN NEW;
END $$;
CREATE FUNCTION mta.deny_planning_source_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'Planning source rows and receipts are immutable'; END $$;
"""

BINDINGS = (
    ('planning_bpr_source', 'fresh_mta_planningbprmasterrow', 'guard_planning_source_row'),
    ('planning_git_source', 'fresh_mta_planninggitmasterrow', 'guard_planning_source_row'),
    ('planning_source_receipt', 'fresh_mta_planningsourceprojection', 'guard_planning_source_receipt'),
)
for prefix, table, function in BINDINGS:
    FORWARD += f'''
CREATE TRIGGER {prefix}_build BEFORE INSERT ON mta.{table} FOR EACH STATEMENT EXECUTE FUNCTION mta.guard_planning_source_build();
CREATE TRIGGER {prefix}_insert BEFORE INSERT ON mta.{table} FOR EACH ROW EXECUTE FUNCTION mta.{function}();
CREATE TRIGGER {prefix}_immutable BEFORE UPDATE OR DELETE OR TRUNCATE ON mta.{table} FOR EACH STATEMENT EXECUTE FUNCTION mta.deny_planning_source_mutation();
'''
REVERSE = '\n'.join(f'DROP TRIGGER {prefix}_{suffix} ON mta.{table};'
                    for prefix, table, _ in BINDINGS for suffix in ('build', 'insert', 'immutable'))
REVERSE += '\n' + '\n'.join('DROP FUNCTION mta.' + name + '();' for name in (
    'guard_planning_source_build', 'guard_planning_source_row',
    'guard_planning_source_receipt', 'deny_planning_source_mutation'))


def verify_guards(connection):
    """Check exact trigger bindings and function bodies, as other prepared readers do."""
    import re
    expected = {}
    for prefix, table, function in BINDINGS:
        for suffix, bits, target in (
                ('build', 6, 'guard_planning_source_build'),
                ('insert', 7, function), ('immutable', 58, 'deny_planning_source_mutation')):
            expected[prefix + '_' + suffix] = (table, 'O', bits, target, None, 0)
    bodies = dict(re.findall(r'CREATE FUNCTION mta\.(\w+)\(\).*?AS \$\$(.*?)\$\$;', FORWARD, re.S))
    with connection.cursor() as c:
        c.execute('SELECT t.tgname,c.relname,t.tgenabled,t.tgtype,p.proname,t.tgqual::text,t.tgnargs '
                  'FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid '
                  'JOIN pg_namespace n ON n.oid=c.relnamespace JOIN pg_proc p ON p.oid=t.tgfoid '
                  'JOIN pg_namespace pn ON pn.oid=p.pronamespace '
                  "WHERE n.nspname='mta' AND pn.nspname='mta' AND t.tgname=ANY(%s)", [list(expected)])
        if {name: tuple(row) for name, *row in c.fetchall()} != expected:
            raise ValueError('Planning source trigger contract differs')
        c.execute('SELECT p.proname,p.prosrc,p.prolang=l.oid,p.prosecdef FROM pg_proc p '
                  "JOIN pg_namespace n ON n.oid=p.pronamespace JOIN pg_language l ON l.lanname='plpgsql' "
                  "WHERE n.nspname='mta' AND p.proname=ANY(%s) AND p.pronargs=0", [list(bodies)])
        from mta.runtime.daily_prepared_schema import installed_bodies
        bodies = installed_bodies(connection, bodies)
        if {name: tuple(row) for name, *row in c.fetchall()} != {
                name: (body, True, False) for name, body in bodies.items()}:
            raise ValueError('Planning source function contract differs')
