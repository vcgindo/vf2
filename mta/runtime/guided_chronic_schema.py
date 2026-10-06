"""Reversible PostgreSQL seals for the fixture Chronic grid relation."""
FORWARD = """
CREATE FUNCTION mta.guard_guided_chronic_prepared_insert() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE owner_kind text; owner_status text;
BEGIN
  SELECT kind,status INTO owner_kind,owner_status FROM mta.fresh_mta_calculationrun
    WHERE id=NEW.run_id FOR UPDATE;
  IF owner_kind IS DISTINCT FROM 'LEGACY_UI_FIXTURE'
     OR owner_status IS DISTINCT FROM 'FIXTURE_BLOCKED' THEN
    RAISE EXCEPTION 'Guided Chronic prepared rows require the isolated fixture run';
  END IF;
  IF TG_TABLE_NAME = 'fresh_mta_guidedchronicpreparedrow' THEN
    IF EXISTS (SELECT 1 FROM mta.fresh_mta_guidedchronicpreparedprojection WHERE run_id=NEW.run_id) THEN
      RAISE EXCEPTION 'Sealed Guided Chronic prepared rows are immutable';
    END IF;
  ELSE
    IF NEW.row_count <> (SELECT count(*) FROM mta.fresh_mta_guidedchronicpreparedrow WHERE run_id=NEW.run_id) THEN
      RAISE EXCEPTION 'Guided Chronic prepared receipt count differs from its complete rows';
    END IF;
  END IF;
  RETURN NEW;
END $$;
CREATE FUNCTION mta.deny_guided_chronic_prepared_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  RAISE EXCEPTION 'Guided Chronic prepared rows and receipts are immutable';
END $$;
CREATE TRIGGER guided_chronic_prepared_row_insert BEFORE INSERT ON mta.fresh_mta_guidedchronicpreparedrow
FOR EACH ROW EXECUTE FUNCTION mta.guard_guided_chronic_prepared_insert();
CREATE TRIGGER guided_chronic_prepared_receipt_insert BEFORE INSERT ON mta.fresh_mta_guidedchronicpreparedprojection
FOR EACH ROW EXECUTE FUNCTION mta.guard_guided_chronic_prepared_insert();
CREATE TRIGGER guided_chronic_prepared_row_immutable BEFORE UPDATE OR DELETE ON mta.fresh_mta_guidedchronicpreparedrow
FOR EACH ROW EXECUTE FUNCTION mta.deny_guided_chronic_prepared_mutation();
CREATE TRIGGER guided_chronic_prepared_receipt_immutable BEFORE UPDATE OR DELETE ON mta.fresh_mta_guidedchronicpreparedprojection
FOR EACH ROW EXECUTE FUNCTION mta.deny_guided_chronic_prepared_mutation();
CREATE TRIGGER guided_chronic_prepared_row_no_truncate BEFORE TRUNCATE ON mta.fresh_mta_guidedchronicpreparedrow
FOR EACH STATEMENT EXECUTE FUNCTION mta.deny_guided_chronic_prepared_mutation();
CREATE TRIGGER guided_chronic_prepared_receipt_no_truncate BEFORE TRUNCATE ON mta.fresh_mta_guidedchronicpreparedprojection
FOR EACH STATEMENT EXECUTE FUNCTION mta.deny_guided_chronic_prepared_mutation();
"""

REVERSE = """
DROP TRIGGER guided_chronic_prepared_receipt_no_truncate ON mta.fresh_mta_guidedchronicpreparedprojection;
DROP TRIGGER guided_chronic_prepared_row_no_truncate ON mta.fresh_mta_guidedchronicpreparedrow;
DROP TRIGGER guided_chronic_prepared_receipt_immutable ON mta.fresh_mta_guidedchronicpreparedprojection;
DROP TRIGGER guided_chronic_prepared_row_immutable ON mta.fresh_mta_guidedchronicpreparedrow;
DROP TRIGGER guided_chronic_prepared_receipt_insert ON mta.fresh_mta_guidedchronicpreparedprojection;
DROP TRIGGER guided_chronic_prepared_row_insert ON mta.fresh_mta_guidedchronicpreparedrow;
DROP FUNCTION mta.deny_guided_chronic_prepared_mutation();
DROP FUNCTION mta.guard_guided_chronic_prepared_insert();
"""


def verify_guards(connection):
    import re
    expected = {}
    for table, prefix in (('fresh_mta_guidedchronicpreparedrow', 'guided_chronic_prepared_row'),
                          ('fresh_mta_guidedchronicpreparedprojection', 'guided_chronic_prepared_receipt')):
        expected[prefix + '_insert'] = (table, 'O', 7, 'guard_guided_chronic_prepared_insert', None, 0)
        expected[prefix + '_immutable'] = (table, 'O', 27, 'deny_guided_chronic_prepared_mutation', None, 0)
        expected[prefix + '_no_truncate'] = (table, 'O', 34, 'deny_guided_chronic_prepared_mutation', None, 0)
    with connection.cursor() as cursor:
        cursor.execute('SELECT t.tgname,c.relname,t.tgenabled,t.tgtype,p.proname,t.tgqual::text,t.tgnargs '
                       'FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid '
                       'JOIN pg_namespace n ON n.oid=c.relnamespace JOIN pg_proc p ON p.oid=t.tgfoid '
                       'JOIN pg_namespace pn ON pn.oid=p.pronamespace '
                       "WHERE n.nspname=%s AND pn.nspname='mta' AND t.tgname=ANY(%s)",
                       ['mta', list(expected)])
        actual = {name: tuple(values) for name, *values in cursor.fetchall()}
        if actual != expected:
            raise ValueError('Guided Chronic prepared immutable trigger contract differs')
        functions = dict(re.findall(r'CREATE FUNCTION mta\.(\w+)\(\).*?AS \$\$(.*?)\$\$;', FORWARD, flags=re.S))
        cursor.execute('SELECT p.proname,p.prosrc,p.prolang=l.oid,p.prosecdef FROM pg_proc p '
                       'JOIN pg_namespace n ON n.oid=p.pronamespace JOIN pg_language l ON l.lanname=\'plpgsql\' '
                       'WHERE n.nspname=%s AND p.proname=ANY(%s) AND p.pronargs=0',
                       ['mta', list(functions)])
        actual_functions = {name: (body, language, security)
                            for name, body, language, security in cursor.fetchall()}
        from mta.runtime.daily_prepared_schema import installed_bodies
        functions = installed_bodies(connection, functions)
        if actual_functions != {name: (body, True, False) for name, body in functions.items()}:
            raise ValueError('Guided Chronic prepared immutable function contract differs')
