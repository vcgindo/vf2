"""Internal revisions and immutable frozen supplier input images."""
from django.db import migrations

QUEUES = ('mdmsobapproved', 'mdmmoqwithdestinationapproved', 'mdmmoqwithoutdestinationapproved')
IMAGES = ('input_supplier_sob', 'input_supplier_moq_with_destination', 'input_supplier_moq_without_destination')
FORWARD = r'''
CREATE FUNCTION mta.supplier_decision_owned(owner bigint) RETURNS boolean LANGUAGE sql AS $$
 SELECT current_setting('fresh.supplier_deciding_source',true)=owner::text
 AND EXISTS(SELECT 1 FROM pg_locks WHERE pid=pg_backend_pid() AND locktype='advisory'
 AND granted AND objsubid=1
 AND classid::bigint=((hashtextextended('fresh-mdm-supplier:'||owner::text,0)>>32)&4294967295)
 AND objid::bigint=(hashtextextended('fresh-mdm-supplier:'||owner::text,0)&4294967295))
$$;
CREATE FUNCTION mta.guard_supplier_revision() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE scalar text;
BEGIN
 IF TG_OP='INSERT' THEN
  IF NEW.revision<>0 THEN RAISE EXCEPTION 'Supplier revision must start at zero'; END IF;
  RETURN NEW;
 END IF;
 IF TG_OP='DELETE' THEN
  PERFORM 1 FROM mta.fresh_mta_mdmdailyinputcapture C
   JOIN mta.fresh_mta_calculationrun R ON R.id=C.run_id
   WHERE C.source_id=OLD.source_id AND C.status='CAPTURED' AND R.status='RUNNING'
   AND C.run_id::text=current_setting('fresh.mdm_consuming_run',true);
  IF NOT FOUND THEN RAISE EXCEPTION 'Supplier queue deletion requires owned consumption'; END IF;
  RETURN OLD;
 END IF;
 scalar=CASE WHEN TG_TABLE_NAME='fresh_mta_mdmsobapproved' THEN 'SOB' ELSE 'MOQ' END;
 IF NOT COALESCE(mta.supplier_decision_owned(OLD.source_id),false)
  OR NEW.revision<>OLD.revision+1
  OR (to_jsonb(NEW)-scalar-'revision')<>(to_jsonb(OLD)-scalar-'revision')
 THEN RAISE EXCEPTION 'Supplier queue revision requires its owned scalar decision'; END IF;
 RETURN NEW;
END $$;
CREATE FUNCTION mta.guard_supplier_task_revision() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'Supplier task revision is retained'; END IF;
 IF NOT COALESCE(mta.supplier_decision_owned(NEW.source_id),false)
  OR NEW.master_id NOT IN (4,5)
 THEN RAISE EXCEPTION 'Supplier task revision requires an owned decision'; END IF;
 IF TG_OP='INSERT' THEN
  IF NEW.revision<>0 THEN RAISE EXCEPTION 'Supplier task revision must start at zero'; END IF;
 ELSE
  IF NEW.revision<>OLD.revision+1 OR (to_jsonb(NEW)-'revision')<>(to_jsonb(OLD)-'revision')
   THEN RAISE EXCEPTION 'Supplier task revision must advance once'; END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER supplier_task_revision_owner BEFORE INSERT OR UPDATE OR DELETE
 ON mta.fresh_mta_mdmsuppliertaskrevision FOR EACH ROW EXECUTE FUNCTION mta.guard_supplier_task_revision();
CREATE TRIGGER supplier_task_revision_truncate BEFORE TRUNCATE
 ON mta.fresh_mta_mdmsuppliertaskrevision FOR EACH STATEMENT EXECUTE FUNCTION mta.deny_daily_source_mutation();
CREATE TABLE mta_state.input_supplier_task_revision (
 vf_run_id uuid NOT NULL REFERENCES mta.fresh_mta_calculationrun(id) ON DELETE RESTRICT,
 vf_image text NOT NULL, vf_ordinal bigint NOT NULL,
 master_id bigint, task_id text, revision bigint,
 PRIMARY KEY(vf_run_id,vf_image,vf_ordinal));
CREATE FUNCTION mta.guard_supplier_input_image() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF TG_OP<>'INSERT' THEN RAISE EXCEPTION 'Supplier captured image is immutable'; END IF;
 PERFORM 1 FROM mta.fresh_mta_calculationrun WHERE id=NEW.vf_run_id
  AND status='RUNNING' AND input_manifest_digest='' FOR UPDATE;
 IF NOT FOUND THEN RAISE EXCEPTION 'Supplier image requires an unsealed running input'; END IF;
 RETURN NEW;
END $$;
'''
for table in QUEUES:
    FORWARD += f'''CREATE TRIGGER supplier_revision BEFORE INSERT OR UPDATE OR DELETE ON mta.fresh_mta_{table}
 FOR EACH ROW EXECUTE FUNCTION mta.guard_supplier_revision();
 CREATE TRIGGER supplier_revision_truncate BEFORE TRUNCATE ON mta.fresh_mta_{table}
 FOR EACH STATEMENT EXECUTE FUNCTION mta.deny_daily_source_mutation();
'''
for table in IMAGES:
    FORWARD += f'ALTER TABLE mta_state.{table} ADD COLUMN revision bigint;\n'
for table in (*IMAGES, 'input_supplier_task_revision'):
    FORWARD += f'''CREATE TRIGGER supplier_input_owner BEFORE INSERT OR UPDATE OR DELETE ON mta_state.{table}
 FOR EACH ROW EXECUTE FUNCTION mta.guard_supplier_input_image();
 CREATE TRIGGER supplier_input_truncate BEFORE TRUNCATE ON mta_state.{table}
 FOR EACH STATEMENT EXECUTE FUNCTION mta.deny_daily_source_mutation();
'''
REVERSE = ''
for table in (*IMAGES, 'input_supplier_task_revision'):
    REVERSE += f'DROP TRIGGER supplier_input_owner ON mta_state.{table}; DROP TRIGGER supplier_input_truncate ON mta_state.{table};\n'
REVERSE += 'DROP FUNCTION mta.guard_supplier_input_image(); DROP TABLE mta_state.input_supplier_task_revision;\n'
for table in IMAGES:
    REVERSE += f'ALTER TABLE mta_state.{table} DROP COLUMN revision;\n'
for table in QUEUES:
    REVERSE += f'DROP TRIGGER supplier_revision ON mta.fresh_mta_{table}; DROP TRIGGER supplier_revision_truncate ON mta.fresh_mta_{table};\n'
REVERSE += '''DROP TRIGGER supplier_task_revision_owner ON mta.fresh_mta_mdmsuppliertaskrevision;
DROP TRIGGER supplier_task_revision_truncate ON mta.fresh_mta_mdmsuppliertaskrevision;
DROP FUNCTION mta.guard_supplier_task_revision(); DROP FUNCTION mta.guard_supplier_revision();
DROP FUNCTION mta.supplier_decision_owned(bigint);'''


class Migration(migrations.Migration):
    dependencies = [('fresh_mta', '0087_nms_supplier_revisions')]
    operations = [migrations.RunSQL(FORWARD, REVERSE)]
