"""Typed phase images and immutable snapshot ownership, not scope acceptance."""
from importlib import import_module
from django.db import migrations

NEW_TABLES = ('phase_pickband', 'phase_advancestock')
TYPED_TABLES = import_module('mta.runtime.migrations.0169_accepted_state_ownership').TYPED_TABLES
SQL = r'''
CREATE TABLE mta_state.phase_pickband (
 vf_run_id uuid NOT NULL REFERENCES mta.fresh_mta_calculationrun(id) ON DELETE RESTRICT,
 vf_image text NOT NULL, vf_ordinal bigint NOT NULL,
 sku_code text, location_code text, parent_location_code text,
 to_black text, to_red text, to_yellow text, to_green text, to_blue text,
 PRIMARY KEY(vf_run_id,vf_image,vf_ordinal));
CREATE TABLE mta_state.phase_advancestock (
 vf_run_id uuid NOT NULL REFERENCES mta.fresh_mta_calculationrun(id) ON DELETE RESTRICT,
 vf_image text NOT NULL, vf_ordinal bigint NOT NULL,
 sku_code text, source_location_code text, allocated_quantity bigint,
 PRIMARY KEY(vf_run_id,vf_image,vf_ordinal));
CREATE FUNCTION mta.guard_phase_snapshot() RETURNS trigger LANGUAGE plpgsql
 SET search_path=pg_catalog,mta AS $guard$
DECLARE parent mta.fresh_mta_calculationrun; predecessor mta.fresh_mta_dailyphasesnapshot;
BEGIN
 IF TG_OP<>'INSERT' THEN RAISE EXCEPTION 'Sealed phase snapshots are immutable'; END IF;
 SELECT * INTO parent FROM mta.fresh_mta_calculationrun WHERE id=NEW.run_id FOR UPDATE;
 IF NOT FOUND OR parent.kind<>'DAILY_CHAIN' OR parent.status<>'RUNNING'
  OR parent.input_digest<>NEW.input_digest OR parent.output_digest<>''
  OR NEW.phase NOT IN ('BPR','DBM')
  OR NEW.manifest->>'schema' IS DISTINCT FROM 'fresh-native-phase-state-v1'
  OR NEW.manifest->>'phase' IS DISTINCT FROM NEW.phase
  OR NEW.manifest->'metadata'->>'identity' IS DISTINCT FROM NEW.run_id::text
  OR NEW.recipe_digest !~ '^[0-9a-f]{64}$' OR NEW.state_digest !~ '^[0-9a-f]{64}$'
  OR octet_length(NEW.manifest::text)>2097152 THEN
  RAISE EXCEPTION 'Phase snapshot requires its exact uncompleted daily owner'; END IF;
 IF NEW.phase='BPR' AND NEW.parent_id IS NOT NULL THEN
  RAISE EXCEPTION 'BPR snapshot has no earlier calculation snapshot'; END IF;
 IF NEW.phase='DBM' THEN
  SELECT * INTO predecessor FROM mta.fresh_mta_dailyphasesnapshot WHERE id=NEW.parent_id;
  IF NOT FOUND OR predecessor.run_id<>NEW.run_id OR predecessor.phase<>'BPR'
   OR predecessor.input_digest<>NEW.input_digest OR predecessor.recipe_digest<>NEW.recipe_digest THEN
   RAISE EXCEPTION 'DBM snapshot requires its own BPR parent'; END IF;
 END IF;
 RETURN NEW;
END
$guard$;
CREATE FUNCTION mta.guard_phase_rows() RETURNS trigger LANGUAGE plpgsql
 SET search_path=pg_catalog,mta AS $guard$
DECLARE changes text; item record; owner uuid; phase text;
BEGIN
 FOR changes IN SELECT CASE WHEN TG_OP='DELETE' THEN 'old_rows' ELSE 'new_rows' END
  UNION ALL SELECT 'old_rows' WHERE TG_OP='UPDATE' LOOP
  FOR item IN EXECUTE format('SELECT DISTINCT vf_run_id AS owner,vf_image AS image FROM %I ORDER BY 1,2',changes) LOOP
   IF item.image NOT LIKE 'phase/%' THEN
    IF TG_TABLE_NAME IN ('phase_pickband','phase_advancestock') THEN
     RAISE EXCEPTION 'Phase consumer row requires its phase namespace'; END IF;
    CONTINUE;
   END IF;
   IF item.image !~ '^phase/(BPR|DBM)/.+$' THEN RAISE EXCEPTION 'Unknown phase row namespace'; END IF;
   owner=item.owner; phase=split_part(item.image,'/',2);
   PERFORM 1 FROM mta.fresh_mta_calculationrun WHERE id=owner
    AND kind='DAILY_CHAIN' AND status='RUNNING' FOR SHARE;
   IF NOT FOUND OR EXISTS(SELECT 1 FROM mta.fresh_mta_dailyphasesnapshot S
       WHERE S.run_id=owner AND S.phase=phase) THEN
    RAISE EXCEPTION 'Sealed phase rows are immutable'; END IF;
  END LOOP;
 END LOOP;
 RETURN NULL;
END
$guard$;
CREATE FUNCTION mta.deny_phase_truncate() RETURNS trigger LANGUAGE plpgsql
 SET search_path=pg_catalog,mta AS $guard$
BEGIN RAISE EXCEPTION 'Phase state cannot be truncated'; END
$guard$;
REVOKE ALL ON FUNCTION mta.guard_phase_snapshot() FROM PUBLIC;
REVOKE ALL ON FUNCTION mta.guard_phase_rows() FROM PUBLIC;
REVOKE ALL ON FUNCTION mta.deny_phase_truncate() FROM PUBLIC;
CREATE TRIGGER phase_snapshot_immutable BEFORE INSERT OR UPDATE OR DELETE
 ON mta.fresh_mta_dailyphasesnapshot FOR EACH ROW EXECUTE FUNCTION mta.guard_phase_snapshot();
CREATE TRIGGER phase_snapshot_no_truncate BEFORE TRUNCATE
 ON mta.fresh_mta_dailyphasesnapshot FOR EACH STATEMENT EXECUTE FUNCTION mta.deny_phase_truncate();
'''


def install(apps, editor):
    if editor.connection.vendor != 'postgresql':raise RuntimeError('Phase state requires PostgreSQL')
    q = editor.quote_name
    with editor.connection.cursor() as cursor:
        cursor.execute(SQL)
        for table in (*TYPED_TABLES, *NEW_TABLES):
            for operation, references in (('INSERT', 'NEW TABLE AS new_rows'),
                    ('UPDATE', 'OLD TABLE AS old_rows NEW TABLE AS new_rows'),
                    ('DELETE', 'OLD TABLE AS old_rows')):
                cursor.execute('CREATE TRIGGER phase_rows_'+operation.lower()+' AFTER '+operation+
                    ' ON mta_state.'+q(table)+' REFERENCING '+references+
                    ' FOR EACH STATEMENT EXECUTE FUNCTION mta.guard_phase_rows()')
        for schema, table in [('mta_state', name) for name in NEW_TABLES]+[
                ('mta', 'fresh_mta_dailyphasesnapshot')]:
            target = q(schema)+'.'+q(table)
            for operation, references in (('INSERT', 'NEW TABLE AS new_rows'),
                    ('UPDATE', 'OLD TABLE AS old_rows NEW TABLE AS new_rows'),
                    ('DELETE', 'OLD TABLE AS old_rows'), ('TRUNCATE', '')):
                cursor.execute('CREATE TRIGGER ingestion_watch_'+operation.lower()+' AFTER '+operation+
                    ' ON '+target+(' REFERENCING '+references if references else '')+
                    " FOR EACH STATEMENT EXECUTE FUNCTION mta.ingestion_watch('operational')")
            if schema == 'mta_state':
                cursor.execute('CREATE TRIGGER phase_no_truncate BEFORE TRUNCATE ON '+target+
                    ' FOR EACH STATEMENT EXECUTE FUNCTION mta.deny_phase_truncate()')


def uninstall(apps, editor):
    q = editor.quote_name
    with editor.connection.cursor() as cursor:
        for table in TYPED_TABLES:
            for operation in ('insert', 'update', 'delete'):
                cursor.execute('DROP TRIGGER phase_rows_'+operation+' ON mta_state.'+q(table))
        for table in NEW_TABLES:cursor.execute('DROP TABLE mta_state.'+q(table))
        for operation in ('insert', 'update', 'delete', 'truncate'):
            cursor.execute('DROP TRIGGER ingestion_watch_'+operation+' ON mta.fresh_mta_dailyphasesnapshot')
        cursor.execute('DROP TRIGGER phase_snapshot_immutable ON mta.fresh_mta_dailyphasesnapshot; '
            'DROP TRIGGER phase_snapshot_no_truncate ON mta.fresh_mta_dailyphasesnapshot; '
            'DROP FUNCTION mta.guard_phase_snapshot(); DROP FUNCTION mta.guard_phase_rows(); '
            'DROP FUNCTION mta.deny_phase_truncate();')


class Migration(migrations.Migration):
    dependencies = [('fresh_mta', '0171_daily_phase_snapshots')]
    operations = [migrations.RunPython(install, uninstall)]
