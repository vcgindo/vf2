"""Seal Force upload/consumption rows and bind complete terminal ownership."""
from django.db import migrations


FORWARD = r'''
CREATE OR REPLACE FUNCTION mta.guard_force_owner() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'Force source ownership is retained'; END IF;
 IF (to_jsonb(NEW)-'generation'-'last_run_id'-'closing_digest'-'closing_log_digest')<>
    (to_jsonb(OLD)-'generation'-'last_run_id'-'closing_digest'-'closing_log_digest')
 THEN RAISE EXCEPTION 'Force installation identity is immutable'; END IF;
 IF NEW.generation<>OLD.generation THEN
  IF NOT COALESCE(mta.supplier_decision_owned(OLD.source_id),false)
    OR NEW.generation<>OLD.generation+1 OR NEW.last_run_id IS DISTINCT FROM OLD.last_run_id
    OR NEW.closing_digest<>OLD.closing_digest
    OR NEW.closing_log_digest<>OLD.closing_log_digest
   THEN RAISE EXCEPTION 'Force generation requires owned decision'; END IF;
 ELSE
  IF NOT mta.force_consumption_owned(OLD.source_id)
    OR NEW.last_run_id::text<>current_setting('fresh.mdm_consuming_run',true)
   THEN RAISE EXCEPTION 'Force closing receipt requires owned consumption'; END IF;
 END IF;
 RETURN NEW;
END $$;

CREATE FUNCTION mta.guard_force_upload_log() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE owner bigint;
BEGIN
 owner=CASE WHEN TG_OP='DELETE' THEN OLD.source_id ELSE NEW.source_id END;
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'Force upload log is retained'; END IF;
 IF TG_OP='INSERT' THEN
  IF NOT COALESCE(mta.supplier_decision_owned(owner),false)
   THEN RAISE EXCEPTION 'Force upload log insert requires owned decision'; END IF;
 ELSE
  IF NOT mta.force_consumption_owned(owner)
    OR NEW.source_id<>OLD.source_id
    OR (to_jsonb(NEW)-'OldNorm')<>(to_jsonb(OLD)-'OldNorm')
   THEN RAISE EXCEPTION 'Force upload log update requires owned OldNorm consumption'; END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER force_upload_log_owner BEFORE INSERT OR UPDATE OR DELETE
 ON mta.fresh_mta_mdmforceuploadlog FOR EACH ROW EXECUTE FUNCTION mta.guard_force_upload_log();
CREATE TRIGGER force_upload_log_truncate BEFORE TRUNCATE
 ON mta.fresh_mta_mdmforceuploadlog FOR EACH STATEMENT EXECUTE FUNCTION mta.deny_daily_source_mutation();

CREATE FUNCTION mta.guard_force_consumed() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF TG_OP<>'INSERT' THEN RAISE EXCEPTION 'Force consumption receipt is immutable'; END IF;
 IF NEW.run_id::text<>current_setting('fresh.mdm_consuming_run',true)
   OR NOT mta.force_consumption_owned(NEW.source_id)
  THEN RAISE EXCEPTION 'Force consumption receipt requires owned consumption'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER force_consumed_owner BEFORE INSERT OR UPDATE OR DELETE
 ON mta.fresh_mta_mdmforceconsumed FOR EACH ROW EXECUTE FUNCTION mta.guard_force_consumed();
CREATE TRIGGER force_consumed_truncate BEFORE TRUNCATE
 ON mta.fresh_mta_mdmforceconsumed FOR EACH STATEMENT EXECUTE FUNCTION mta.deny_daily_source_mutation();
'''

REVERSE = r'''
DROP TRIGGER force_consumed_truncate ON mta.fresh_mta_mdmforceconsumed;
DROP TRIGGER force_consumed_owner ON mta.fresh_mta_mdmforceconsumed;
DROP FUNCTION mta.guard_force_consumed();
DROP TRIGGER force_upload_log_truncate ON mta.fresh_mta_mdmforceuploadlog;
DROP TRIGGER force_upload_log_owner ON mta.fresh_mta_mdmforceuploadlog;
DROP FUNCTION mta.guard_force_upload_log();
CREATE OR REPLACE FUNCTION mta.guard_force_owner() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'Force source ownership is retained'; END IF;
 IF (to_jsonb(NEW)-'generation'-'last_run_id'-'closing_digest')<>
    (to_jsonb(OLD)-'generation'-'last_run_id'-'closing_digest')
 THEN RAISE EXCEPTION 'Force installation identity is immutable'; END IF;
 IF NEW.generation<>OLD.generation THEN
  IF NOT COALESCE(mta.supplier_decision_owned(OLD.source_id),false)
    OR NEW.generation<>OLD.generation+1 OR NEW.last_run_id IS DISTINCT FROM OLD.last_run_id
    OR NEW.closing_digest<>OLD.closing_digest
   THEN RAISE EXCEPTION 'Force generation requires owned decision'; END IF;
 ELSE
  IF NOT mta.force_consumption_owned(OLD.source_id)
    OR NEW.last_run_id::text<>current_setting('fresh.mdm_consuming_run',true)
   THEN RAISE EXCEPTION 'Force closing receipt requires owned consumption'; END IF;
 END IF;
 RETURN NEW;
END $$;
'''


class Migration(migrations.Migration):
    dependencies = [('fresh_mta', '0092_nms_force_owner_digests')]
    operations = [migrations.RunSQL(FORWARD, REVERSE)]
