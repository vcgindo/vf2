"""Master13 generations and sealed typed images at the existing day boundary."""
from django.db import migrations

FORWARD = r'''
CREATE FUNCTION mta.force_consumption_owned(owner bigint) RETURNS boolean LANGUAGE sql AS $$
 SELECT EXISTS(SELECT 1 FROM mta.fresh_mta_mdmdailyinputcapture C
 JOIN mta.fresh_mta_calculationrun R ON R.id=C.run_id
 WHERE C.source_id=owner AND C.status='CAPTURED' AND R.status='RUNNING'
 AND C.run_id::text=current_setting('fresh.mdm_consuming_run',true))
$$;
CREATE FUNCTION mta.guard_force_queue() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE owner bigint; deciding boolean; consuming boolean;
BEGIN
 owner=CASE WHEN TG_OP='DELETE' THEN OLD.source_id ELSE NEW.source_id END;
 deciding=COALESCE(mta.supplier_decision_owned(owner),false);
 consuming=mta.force_consumption_owned(owner);
 IF TG_OP='DELETE' THEN
  IF NOT consuming THEN RAISE EXCEPTION 'Force deletion requires owned consumption'; END IF;
  RETURN OLD;
 END IF;
 IF TG_OP='INSERT' THEN
  IF NEW.revision<>0 OR NOT(deciding OR consuming)
   THEN RAISE EXCEPTION 'Force insert requires owned input writer'; END IF;
 ELSE
  IF NOT deciding OR NEW.revision<>OLD.revision+1
    OR (to_jsonb(NEW)-'NewNorm'-'revision')<>(to_jsonb(OLD)-'NewNorm'-'revision')
   THEN RAISE EXCEPTION 'Force update requires owned scalar revision'; END IF;
 END IF;
 IF deciding THEN UPDATE mta.fresh_mta_mdmforceowner SET generation=generation+1 WHERE source_id=owner; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER force_queue_owner BEFORE INSERT OR UPDATE OR DELETE
 ON mta.fresh_mta_mdmforcequeue FOR EACH ROW EXECUTE FUNCTION mta.guard_force_queue();
CREATE TRIGGER force_queue_truncate BEFORE TRUNCATE ON mta.fresh_mta_mdmforcequeue
 FOR EACH STATEMENT EXECUTE FUNCTION mta.deny_daily_source_mutation();
CREATE FUNCTION mta.guard_force_task_revision() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'Force task revision is retained'; END IF;
 IF NOT COALESCE(mta.supplier_decision_owned(NEW.source_id),false)
 THEN RAISE EXCEPTION 'Force task revision requires owned decision'; END IF;
 IF TG_OP='INSERT' THEN
  IF NEW.revision<>0 THEN RAISE EXCEPTION 'Force task revision must start at zero'; END IF;
 ELSE
  IF NEW.revision<>OLD.revision+1 OR (to_jsonb(NEW)-'revision')<>(to_jsonb(OLD)-'revision')
   THEN RAISE EXCEPTION 'Force task revision must advance once'; END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER force_task_revision_owner BEFORE INSERT OR UPDATE OR DELETE
 ON mta.fresh_mta_mdmforcetaskrevision FOR EACH ROW EXECUTE FUNCTION mta.guard_force_task_revision();
CREATE TRIGGER force_task_revision_truncate BEFORE TRUNCATE ON mta.fresh_mta_mdmforcetaskrevision
 FOR EACH STATEMENT EXECUTE FUNCTION mta.deny_daily_source_mutation();
CREATE FUNCTION mta.guard_force_owner() RETURNS trigger LANGUAGE plpgsql AS $$
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
CREATE TRIGGER force_owner_update BEFORE UPDATE OR DELETE ON mta.fresh_mta_mdmforceowner
 FOR EACH ROW EXECUTE FUNCTION mta.guard_force_owner();
CREATE TRIGGER force_owner_truncate BEFORE TRUNCATE ON mta.fresh_mta_mdmforceowner
 FOR EACH STATEMENT EXECUTE FUNCTION mta.deny_daily_source_mutation();
'''
TABLES = {
    'input_force_upload_log': 'id bigint, "SKUCode" text, "WHCode" text, "OldNorm" bigint, "NewNorm" bigint, "Approved" boolean, "RequestedBy" text, "ActionTimeStamp" timestamp, "ActionId" bigint',
    'input_force_queue': 'id bigint, revision bigint, "SKUCode" text, "WhCode" text, "NewNorm" bigint, "Approved" boolean, "RequestedBy" text',
    'input_force_task_revision': 'task_id text, revision bigint',
}
for table, columns in TABLES.items():
    FORWARD += f'''
CREATE TABLE mta_state.{table} (
 vf_run_id uuid NOT NULL REFERENCES mta.fresh_mta_calculationrun(id) ON DELETE RESTRICT,
 vf_image text NOT NULL, vf_ordinal bigint NOT NULL, {columns},
 PRIMARY KEY(vf_run_id,vf_image,vf_ordinal));
CREATE TRIGGER force_input_owner BEFORE INSERT OR UPDATE OR DELETE ON mta_state.{table}
 FOR EACH ROW EXECUTE FUNCTION mta.guard_supplier_input_image();
CREATE TRIGGER force_input_truncate BEFORE TRUNCATE ON mta_state.{table}
 FOR EACH STATEMENT EXECUTE FUNCTION mta.deny_daily_source_mutation();
'''
REVERSE = ''.join(f'DROP TABLE mta_state.{table};\n' for table in TABLES)
for table, triggers in (
    ('mdmforcequeue', ('force_queue_owner', 'force_queue_truncate')),
    ('mdmforcetaskrevision', ('force_task_revision_owner', 'force_task_revision_truncate')),
    ('mdmforceowner', ('force_owner_update', 'force_owner_truncate'))):
    REVERSE += ''.join(f'DROP TRIGGER {trigger} ON mta.fresh_mta_{table};\n' for trigger in triggers)
REVERSE += '''DROP FUNCTION mta.guard_force_owner(); DROP FUNCTION mta.guard_force_task_revision();
DROP FUNCTION mta.guard_force_queue(); DROP FUNCTION mta.force_consumption_owned(bigint);'''


class Migration(migrations.Migration):
    dependencies = [('fresh_mta', '0090_nms_force_norm_owners')]
    operations = [migrations.RunSQL(FORWARD, REVERSE)]
