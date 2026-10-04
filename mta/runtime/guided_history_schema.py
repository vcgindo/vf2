"""Immutable seals for the two fixture Guided history occurrence grains."""
FORWARD = r"""
CREATE FUNCTION mta.guard_guided_history_row_insert() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE owner_kind text; owner_status text; family_name text;
BEGIN
  SELECT kind,status INTO owner_kind,owner_status FROM mta.fresh_mta_calculationrun
    WHERE id=NEW.run_id FOR UPDATE;
  IF owner_kind IS DISTINCT FROM 'LEGACY_UI_FIXTURE' OR owner_status IS DISTINCT FROM 'FIXTURE_BLOCKED' THEN
    RAISE EXCEPTION 'Guided history rows require the isolated fixture run';
  END IF;
  family_name := CASE TG_TABLE_NAME
    WHEN 'fresh_mta_guidedavailabilityhistoryrow' THEN 'availability'
    WHEN 'fresh_mta_guidedavailabilitysnapshotreference' THEN 'availability'
    ELSE 'excess' END;
  IF EXISTS (SELECT 1 FROM mta.fresh_mta_guidedhistorypreparedprojection
             WHERE run_id=NEW.run_id AND family=family_name) THEN
    RAISE EXCEPTION 'Sealed Guided history rows are immutable';
  END IF;
  IF current_setting('fresh.guided_history_build',true) IS DISTINCT FROM NEW.run_id::text THEN
    RAISE EXCEPTION 'Guided history rows require the preparation command';
  END IF;
  RETURN NEW;
END $$;
CREATE FUNCTION mta.guard_guided_history_receipt_insert() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE actual bigint;
BEGIN
  IF NEW.family='availability' THEN
    SELECT count(*) INTO actual FROM mta.fresh_mta_guidedavailabilityhistoryrow WHERE run_id=NEW.run_id;
    IF NEW.reference_count IS DISTINCT FROM
       (SELECT count(*) FROM mta.fresh_mta_guidedavailabilitysnapshotreference WHERE run_id=NEW.run_id) THEN
      RAISE EXCEPTION 'Guided history reference count differs';
    END IF;
  ELSIF NEW.family='excess' THEN
    SELECT count(*) INTO actual FROM mta.fresh_mta_guidedexcesshistoryrow WHERE run_id=NEW.run_id;
    IF NEW.reference_count IS DISTINCT FROM 0 THEN RAISE EXCEPTION 'Guided history excess references differ'; END IF;
  ELSE RAISE EXCEPTION 'Unknown Guided history family'; END IF;
  IF NEW.row_count IS DISTINCT FROM actual THEN RAISE EXCEPTION 'Guided history receipt count differs'; END IF;
  RETURN NEW;
END $$;
CREATE FUNCTION mta.deny_guided_history_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'Guided history rows and receipts are immutable'; END $$;
CREATE TRIGGER guided_availability_history_insert BEFORE INSERT ON mta.fresh_mta_guidedavailabilityhistoryrow FOR EACH ROW EXECUTE FUNCTION mta.guard_guided_history_row_insert();
CREATE TRIGGER guided_availability_snapshot_insert BEFORE INSERT ON mta.fresh_mta_guidedavailabilitysnapshotreference FOR EACH ROW EXECUTE FUNCTION mta.guard_guided_history_row_insert();
CREATE TRIGGER guided_excess_history_insert BEFORE INSERT ON mta.fresh_mta_guidedexcesshistoryrow FOR EACH ROW EXECUTE FUNCTION mta.guard_guided_history_row_insert();
CREATE TRIGGER guided_history_receipt_insert BEFORE INSERT ON mta.fresh_mta_guidedhistorypreparedprojection FOR EACH ROW EXECUTE FUNCTION mta.guard_guided_history_receipt_insert();
CREATE TRIGGER guided_availability_history_immutable BEFORE UPDATE OR DELETE OR TRUNCATE ON mta.fresh_mta_guidedavailabilityhistoryrow FOR EACH STATEMENT EXECUTE FUNCTION mta.deny_guided_history_mutation();
CREATE TRIGGER guided_availability_snapshot_immutable BEFORE UPDATE OR DELETE OR TRUNCATE ON mta.fresh_mta_guidedavailabilitysnapshotreference FOR EACH STATEMENT EXECUTE FUNCTION mta.deny_guided_history_mutation();
CREATE TRIGGER guided_excess_history_immutable BEFORE UPDATE OR DELETE OR TRUNCATE ON mta.fresh_mta_guidedexcesshistoryrow FOR EACH STATEMENT EXECUTE FUNCTION mta.deny_guided_history_mutation();
CREATE TRIGGER guided_history_receipt_immutable BEFORE UPDATE OR DELETE OR TRUNCATE ON mta.fresh_mta_guidedhistorypreparedprojection FOR EACH STATEMENT EXECUTE FUNCTION mta.deny_guided_history_mutation();
"""

REVERSE = r"""
DROP TRIGGER guided_history_receipt_immutable ON mta.fresh_mta_guidedhistorypreparedprojection;
DROP TRIGGER guided_excess_history_immutable ON mta.fresh_mta_guidedexcesshistoryrow;
DROP TRIGGER guided_availability_history_immutable ON mta.fresh_mta_guidedavailabilityhistoryrow;
DROP TRIGGER guided_availability_snapshot_immutable ON mta.fresh_mta_guidedavailabilitysnapshotreference;
DROP TRIGGER guided_history_receipt_insert ON mta.fresh_mta_guidedhistorypreparedprojection;
DROP TRIGGER guided_excess_history_insert ON mta.fresh_mta_guidedexcesshistoryrow;
DROP TRIGGER guided_availability_history_insert ON mta.fresh_mta_guidedavailabilityhistoryrow;
DROP TRIGGER guided_availability_snapshot_insert ON mta.fresh_mta_guidedavailabilitysnapshotreference;
DROP FUNCTION mta.deny_guided_history_mutation();
DROP FUNCTION mta.guard_guided_history_receipt_insert();
DROP FUNCTION mta.guard_guided_history_row_insert();
"""

# Freeze the 0023 function behavior.  The explicit 0024 correction replaces
# these functions after adding its verification columns.
LEGACY_FORWARD = FORWARD.replace(
    "  SELECT kind,status INTO owner_kind,owner_status FROM mta.fresh_mta_calculationrun\n",
    "  IF current_setting('fresh.guided_history_build',true)=NEW.run_id::text THEN RETURN NEW; END IF;\n"
    "  SELECT kind,status INTO owner_kind,owner_status FROM mta.fresh_mta_calculationrun\n").replace(
    "  IF current_setting('fresh.guided_history_build',true) IS DISTINCT FROM NEW.run_id::text THEN\n"
    "    RAISE EXCEPTION 'Guided history rows require the preparation command';\n"
    "  END IF;\n", "").replace(
    "    IF NEW.reference_count IS DISTINCT FROM\n"
    "       (SELECT count(*) FROM mta.fresh_mta_guidedavailabilitysnapshotreference WHERE run_id=NEW.run_id) THEN\n"
    "      RAISE EXCEPTION 'Guided history reference count differs';\n"
    "    END IF;\n", "").replace(
    "    IF NEW.reference_count IS DISTINCT FROM 0 THEN RAISE EXCEPTION 'Guided history excess references differ'; END IF;\n",
    "")

# 0024 reapplies the corrected functions to databases which already applied
# 0023 while preserving the additive tables and their trigger bindings.
CORRECTIVE = FORWARD.split('CREATE FUNCTION mta.deny_guided_history_mutation()', 1)[0]
CORRECTIVE = CORRECTIVE.replace('CREATE FUNCTION mta.guard_guided_history_row_insert()',
                                'CREATE OR REPLACE FUNCTION mta.guard_guided_history_row_insert()')
CORRECTIVE = CORRECTIVE.replace('CREATE FUNCTION mta.guard_guided_history_receipt_insert()',
                                'CREATE OR REPLACE FUNCTION mta.guard_guided_history_receipt_insert()')
FINAL_INSERT_GUARDS = r"""
CREATE OR REPLACE FUNCTION mta.guard_guided_history_row_insert() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF current_setting('fresh.guided_history_build',true) IS DISTINCT FROM NEW.run_id::text THEN
    RAISE EXCEPTION 'Guided history rows require the preparation command';
  END IF;
  RETURN NEW;
END $$;
CREATE FUNCTION mta.guard_guided_history_build_insert() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE build_run uuid; owner_kind text; owner_status text; family_name text;
BEGIN
  build_run := nullif(current_setting('fresh.guided_history_build',true),'')::uuid;
  SELECT kind,status INTO owner_kind,owner_status FROM mta.fresh_mta_calculationrun
    WHERE id=build_run FOR UPDATE;
  IF owner_kind IS DISTINCT FROM 'LEGACY_UI_FIXTURE' OR owner_status IS DISTINCT FROM 'FIXTURE_BLOCKED' THEN
    RAISE EXCEPTION 'Guided history rows require the isolated fixture run';
  END IF;
  family_name := CASE TG_TABLE_NAME
    WHEN 'fresh_mta_guidedavailabilityhistoryrow' THEN 'availability'
    WHEN 'fresh_mta_guidedavailabilitysnapshotreference' THEN 'availability'
    ELSE 'excess' END;
  IF EXISTS (SELECT 1 FROM mta.fresh_mta_guidedhistorypreparedprojection
             WHERE run_id=build_run AND family=family_name) THEN
    RAISE EXCEPTION 'Sealed Guided history rows are immutable';
  END IF;
  RETURN NULL;
END $$;
CREATE TRIGGER guided_availability_history_build BEFORE INSERT ON mta.fresh_mta_guidedavailabilityhistoryrow FOR EACH STATEMENT EXECUTE FUNCTION mta.guard_guided_history_build_insert();
CREATE TRIGGER guided_availability_snapshot_build BEFORE INSERT ON mta.fresh_mta_guidedavailabilitysnapshotreference FOR EACH STATEMENT EXECUTE FUNCTION mta.guard_guided_history_build_insert();
CREATE TRIGGER guided_excess_history_build BEFORE INSERT ON mta.fresh_mta_guidedexcesshistoryrow FOR EACH STATEMENT EXECUTE FUNCTION mta.guard_guided_history_build_insert();
"""
CORRECTIVE_REVERSE = LEGACY_FORWARD.split(
    'CREATE FUNCTION mta.deny_guided_history_mutation()', 1)[0].replace(
        'CREATE FUNCTION mta.guard_guided_history_row_insert()',
        'CREATE OR REPLACE FUNCTION mta.guard_guided_history_row_insert()').replace(
        'CREATE FUNCTION mta.guard_guided_history_receipt_insert()',
        'CREATE OR REPLACE FUNCTION mta.guard_guided_history_receipt_insert()')
BUILD_CORRECTIVE = FINAL_INSERT_GUARDS
BUILD_CORRECTIVE_REVERSE = r"""
DROP TRIGGER guided_excess_history_build ON mta.fresh_mta_guidedexcesshistoryrow;
DROP TRIGGER guided_availability_snapshot_build ON mta.fresh_mta_guidedavailabilitysnapshotreference;
DROP TRIGGER guided_availability_history_build ON mta.fresh_mta_guidedavailabilityhistoryrow;
DROP FUNCTION mta.guard_guided_history_build_insert();
"""
BUILD_CORRECTIVE_REVERSE += CORRECTIVE


def verify_guards(connection):
    import re
    bindings = (
        ('guided_availability_history', 'fresh_mta_guidedavailabilityhistoryrow',
         'guard_guided_history_row_insert'),
        ('guided_availability_snapshot', 'fresh_mta_guidedavailabilitysnapshotreference',
         'guard_guided_history_row_insert'),
        ('guided_excess_history', 'fresh_mta_guidedexcesshistoryrow',
         'guard_guided_history_row_insert'),
        ('guided_history_receipt', 'fresh_mta_guidedhistorypreparedprojection',
         'guard_guided_history_receipt_insert'))
    expected = {}
    for prefix, table, insert_function in bindings:
        expected[prefix+'_insert'] = (table, 'O', 7, insert_function, None, 0)
        expected[prefix+'_immutable'] = (table, 'O', 58, 'deny_guided_history_mutation', None, 0)
        if prefix != 'guided_history_receipt':
            expected[prefix+'_build'] = (table, 'O', 6, 'guard_guided_history_build_insert', None, 0)
    with connection.cursor() as cursor:
        cursor.execute('SELECT t.tgname,c.relname,t.tgenabled,t.tgtype,p.proname,t.tgqual::text,t.tgnargs '
                       'FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid '
                       'JOIN pg_namespace n ON n.oid=c.relnamespace JOIN pg_proc p ON p.oid=t.tgfoid '
                       'JOIN pg_namespace pn ON pn.oid=p.pronamespace '
                       "WHERE n.nspname=%s AND pn.nspname='mta' AND t.tgname=ANY(%s)",
                       ['mta', list(expected)])
        actual = {name:tuple(values) for name,*values in cursor.fetchall()}
        if actual != expected: raise ValueError('Guided history immutable trigger contract differs')
        functions = dict(re.findall(r'CREATE(?: OR REPLACE)? FUNCTION mta\.(\w+)\(\).*?AS \$\$(.*?)\$\$;',
                                    FORWARD + FINAL_INSERT_GUARDS, flags=re.S))
        cursor.execute('SELECT p.proname,p.prosrc,p.prolang=l.oid,p.prosecdef FROM pg_proc p '
                       "JOIN pg_namespace n ON n.oid=p.pronamespace JOIN pg_language l ON l.lanname='plpgsql' "
                       'WHERE n.nspname=%s AND p.proname=ANY(%s) AND p.pronargs=0',
                       ['mta', list(functions)])
        actual_functions = {name:(body,language,security)
                            for name,body,language,security in cursor.fetchall()}
        if actual_functions != {name:(body,True,False) for name,body in functions.items()}:
            raise ValueError('Guided history immutable function contract differs')
