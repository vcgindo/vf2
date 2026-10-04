"""Reversible PostgreSQL seals for the single fixture BPR prepared relation."""
FORWARD = """
CREATE FUNCTION mta.guard_bpr_prepared_insert() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE owner_kind text; owner_status text;
BEGIN
  SELECT kind,status INTO owner_kind,owner_status FROM mta.fresh_mta_calculationrun
    WHERE id=NEW.run_id FOR UPDATE;
  IF owner_kind IS DISTINCT FROM 'LEGACY_UI_FIXTURE'
     OR owner_status IS DISTINCT FROM 'FIXTURE_BLOCKED' THEN
    RAISE EXCEPTION 'BPR prepared rows require the isolated fixture run';
  END IF;
  IF TG_TABLE_NAME = 'fresh_mta_bprpreparedrow' THEN
    IF EXISTS (SELECT 1 FROM mta.fresh_mta_bprpreparedprojection WHERE run_id=NEW.run_id) THEN
      RAISE EXCEPTION 'Sealed BPR prepared rows are immutable';
    END IF;
  ELSE
    IF NEW.row_count <> (SELECT count(*) FROM mta.fresh_mta_bprpreparedrow WHERE run_id=NEW.run_id) THEN
      RAISE EXCEPTION 'BPR prepared receipt count differs from its complete rows';
    END IF;
  END IF;
  RETURN NEW;
END $$;
CREATE FUNCTION mta.deny_bpr_prepared_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  RAISE EXCEPTION 'BPR prepared rows and receipts are immutable';
END $$;
CREATE TRIGGER bpr_prepared_row_insert BEFORE INSERT
ON mta.fresh_mta_bprpreparedrow FOR EACH ROW
EXECUTE FUNCTION mta.guard_bpr_prepared_insert();
CREATE TRIGGER bpr_prepared_receipt_insert BEFORE INSERT
ON mta.fresh_mta_bprpreparedprojection FOR EACH ROW
EXECUTE FUNCTION mta.guard_bpr_prepared_insert();
CREATE TRIGGER bpr_prepared_row_immutable BEFORE UPDATE OR DELETE
ON mta.fresh_mta_bprpreparedrow FOR EACH ROW
EXECUTE FUNCTION mta.deny_bpr_prepared_mutation();
CREATE TRIGGER bpr_prepared_receipt_immutable BEFORE UPDATE OR DELETE
ON mta.fresh_mta_bprpreparedprojection FOR EACH ROW
EXECUTE FUNCTION mta.deny_bpr_prepared_mutation();
CREATE TRIGGER bpr_prepared_row_no_truncate BEFORE TRUNCATE
ON mta.fresh_mta_bprpreparedrow FOR EACH STATEMENT
EXECUTE FUNCTION mta.deny_bpr_prepared_mutation();
CREATE TRIGGER bpr_prepared_receipt_no_truncate BEFORE TRUNCATE
ON mta.fresh_mta_bprpreparedprojection FOR EACH STATEMENT
EXECUTE FUNCTION mta.deny_bpr_prepared_mutation();
"""

REVERSE = """
DROP TRIGGER bpr_prepared_receipt_no_truncate ON mta.fresh_mta_bprpreparedprojection;
DROP TRIGGER bpr_prepared_row_no_truncate ON mta.fresh_mta_bprpreparedrow;
DROP TRIGGER bpr_prepared_receipt_immutable ON mta.fresh_mta_bprpreparedprojection;
DROP TRIGGER bpr_prepared_row_immutable ON mta.fresh_mta_bprpreparedrow;
DROP TRIGGER bpr_prepared_receipt_insert ON mta.fresh_mta_bprpreparedprojection;
DROP TRIGGER bpr_prepared_row_insert ON mta.fresh_mta_bprpreparedrow;
DROP FUNCTION mta.deny_bpr_prepared_mutation();
DROP FUNCTION mta.guard_bpr_prepared_insert();
"""


def verify_guards(connection):
    """Admit only the installed, enabled guards with their exact owned bodies."""
    import re
    expected = {}
    for table, prefix in (('fresh_mta_bprpreparedrow', 'bpr_prepared_row'),
                          ('fresh_mta_bprpreparedprojection', 'bpr_prepared_receipt')):
        expected[prefix + '_insert'] = (table, 'O', 7, 'guard_bpr_prepared_insert', None, 0)
        expected[prefix + '_immutable'] = (table, 'O', 27, 'deny_bpr_prepared_mutation', None, 0)
        expected[prefix + '_no_truncate'] = (table, 'O', 34, 'deny_bpr_prepared_mutation', None, 0)
    with connection.cursor() as cursor:
        cursor.execute('SELECT t.tgname,c.relname,t.tgenabled,t.tgtype,p.proname,'
                       't.tgqual::text,t.tgnargs FROM pg_trigger t '
                       'JOIN pg_class c ON c.oid=t.tgrelid '
                       'JOIN pg_namespace n ON n.oid=c.relnamespace '
                       'JOIN pg_proc p ON p.oid=t.tgfoid '
                       'JOIN pg_namespace pn ON pn.oid=p.pronamespace '
                       "WHERE n.nspname=%s AND pn.nspname='mta' AND t.tgname=ANY(%s)",
                       ['mta', list(expected)])
        actual = {name: tuple(values) for name, *values in cursor.fetchall()}
        if actual != expected:
            raise ValueError('BPR prepared immutable trigger contract differs')
        functions = dict(re.findall(r'CREATE FUNCTION mta\.(\w+)\(\).*?AS \$\$(.*?)\$\$;',
                                    FORWARD, flags=re.S))
        cursor.execute('SELECT p.proname,p.prosrc,p.prolang=l.oid,p.prosecdef '
                       'FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace '
                       "JOIN pg_language l ON l.lanname='plpgsql' "
                       'WHERE n.nspname=%s AND p.proname=ANY(%s) AND p.pronargs=0',
                       ['mta', list(functions)])
        actual_functions = {name: (body, language, security) for name, body, language, security in cursor.fetchall()}
        if actual_functions != {name: (body, True, False) for name, body in functions.items()}:
            raise ValueError('BPR prepared immutable function contract differs')
