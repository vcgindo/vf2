"""Freeze the capture header/input and prevent truncating scoped evidence."""
from importlib import import_module
from django.db import migrations

_prior=import_module('mta.runtime.migrations.0179_prepared_effect_ownership')
SQL = r'''
CREATE OR REPLACE FUNCTION mta.guard_scoped_capture_status() RETURNS trigger LANGUAGE plpgsql
 SET search_path=pg_catalog,mta AS $guard$
BEGIN
 IF to_jsonb(NEW) IS DISTINCT FROM to_jsonb(OLD) AND EXISTS(
  SELECT 1 FROM mta.fresh_mta_runscopeattempt A WHERE A.run_id=OLD.run_id) THEN
  RAISE EXCEPTION 'Scoped capture header is frozen until its qualified final owner'; END IF;
 RETURN NEW;
END
$guard$;
CREATE FUNCTION mta.guard_scoped_exclusion_input() RETURNS trigger LANGUAGE plpgsql
 SET search_path=pg_catalog,mta AS $guard$
DECLARE captured_id uuid;
BEGIN
 captured_id=CASE WHEN TG_OP='DELETE' THEN OLD.capture_id ELSE NEW.capture_id END;
 IF EXISTS(SELECT 1 FROM mta.fresh_mta_runscopeattempt A WHERE A.run_id=captured_id)
  OR TG_OP='UPDATE' AND EXISTS(SELECT 1 FROM mta.fresh_mta_runscopeattempt A WHERE A.run_id=OLD.capture_id) THEN
  RAISE EXCEPTION 'Scoped captured pair-exclusion input is immutable'; END IF;
 IF TG_OP='DELETE' THEN RETURN OLD; ELSE RETURN NEW; END IF;
END
$guard$;
CREATE FUNCTION mta.guard_scoped_effect_truncate() RETURNS trigger LANGUAGE plpgsql
 SET search_path=pg_catalog,mta AS $guard$
BEGIN
 IF EXISTS(SELECT 1 FROM mta.fresh_mta_runscopeattempt) THEN
  RAISE EXCEPTION 'Scoped MDM effect and capture evidence cannot be truncated'; END IF;
 RETURN NULL;
END
$guard$;
REVOKE ALL ON FUNCTION mta.guard_scoped_exclusion_input() FROM PUBLIC;
REVOKE ALL ON FUNCTION mta.guard_scoped_effect_truncate() FROM PUBLIC;
CREATE TRIGGER scoped_exclusion_input BEFORE INSERT OR UPDATE OR DELETE
 ON mta.fresh_mta_mdmdailypairexclusion FOR EACH ROW EXECUTE FUNCTION mta.guard_scoped_exclusion_input();
'''
for table in (*_prior.SOURCE_TABLES,*_prior.CAPTURE_TABLES,*_prior.CURRENT_TABLES,
              'mdmdailypairexclusion','mdmdailyinputcapture'):
    SQL += ('CREATE TRIGGER scoped_effect_no_truncate BEFORE TRUNCATE ON mta.fresh_mta_'+table+
            ' FOR EACH STATEMENT EXECUTE FUNCTION mta.guard_scoped_effect_truncate();\n')

REVERSE = """DO $pre$ BEGIN
 IF EXISTS(SELECT 1 FROM mta.fresh_mta_runscopeattempt) THEN
 RAISE EXCEPTION 'Scoped evidence requires a compatible forward release'; END IF;
END $pre$;
DROP TRIGGER scoped_exclusion_input ON mta.fresh_mta_mdmdailypairexclusion;
DROP FUNCTION mta.guard_scoped_exclusion_input();
"""
for table in (*_prior.SOURCE_TABLES,*_prior.CAPTURE_TABLES,*_prior.CURRENT_TABLES,
              'mdmdailypairexclusion','mdmdailyinputcapture'):
    REVERSE += 'DROP TRIGGER scoped_effect_no_truncate ON mta.fresh_mta_'+table+';\n'
REVERSE += 'DROP FUNCTION mta.guard_scoped_effect_truncate();\n'
_old=import_module('mta.runtime.migrations.0177_scope_acceptance_guards').SQL
REVERSE += 'CREATE OR REPLACE FUNCTION mta.guard_scoped_capture_status()'+_old.split(
    'CREATE FUNCTION mta.guard_scoped_capture_status()',1)[1].split('$guard$;',1)[0]+'$guard$;'


class Migration(migrations.Migration):
    dependencies=[('fresh_mta','0179_prepared_effect_ownership')]
    operations=[migrations.RunSQL(SQL,REVERSE)]
