"""Seasonality source ownership, generations, and sealed typed capture images."""
from django.db import migrations

FORWARD = r'''
CREATE FUNCTION mta.guard_season_queue() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE owner bigint; deciding boolean; consuming boolean;
BEGIN
 owner=CASE WHEN TG_OP='DELETE' THEN OLD.source_id ELSE NEW.source_id END;
 deciding=COALESCE(mta.supplier_decision_owned(owner),false);
 consuming=mta.force_consumption_owned(owner);
 IF TG_OP='DELETE' THEN
  IF NOT consuming THEN RAISE EXCEPTION 'Seasonality deletion requires owned consumption'; END IF;
  RETURN OLD;
 END IF;
 IF TG_OP='INSERT' THEN
  IF NEW.revision<>0 OR NOT deciding THEN RAISE EXCEPTION 'Seasonality input requires owned decision'; END IF;
 ELSE
  IF NOT deciding OR NEW.revision<>OLD.revision+1
   OR (to_jsonb(NEW)-ARRAY['revision','StartDate','EndDate','TargetNorm','DeltaNormPercentage','UpperLowerCap','BuildupDuration'])
     <>(to_jsonb(OLD)-ARRAY['revision','StartDate','EndDate','TargetNorm','DeltaNormPercentage','UpperLowerCap','BuildupDuration'])
  THEN RAISE EXCEPTION 'Seasonality update requires native input-field revision'; END IF;
 END IF;
 UPDATE mta.fresh_mta_mdmseasonowner SET generation=generation+1 WHERE source_id=owner;
 RETURN NEW;
END $$;
CREATE FUNCTION mta.guard_season_current() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE owner bigint; deciding boolean; consuming boolean;
BEGIN
 owner=CASE WHEN TG_OP='DELETE' THEN OLD.source_id ELSE NEW.source_id END;
 deciding=COALESCE(mta.supplier_decision_owned(owner),false);
 consuming=mta.force_consumption_owned(owner);
 IF TG_OP='DELETE' THEN
  IF NOT consuming THEN RAISE EXCEPTION 'Seasonality replacement requires owned consumption'; END IF;
  RETURN OLD;
 END IF;
 IF TG_OP='INSERT' THEN
  IF NOT consuming OR NEW.revision<>0 THEN RAISE EXCEPTION 'Seasonality current requires produced closing'; END IF;
 ELSE
  IF NOT deciding OR NEW.revision<>OLD.revision+1
    OR (to_jsonb(NEW)-ARRAY['revision','Status','Comment'])<>(to_jsonb(OLD)-ARRAY['revision','Status','Comment'])
   THEN RAISE EXCEPTION 'Seasonality decision may change only status/comment'; END IF;
  UPDATE mta.fresh_mta_mdmseasonowner SET generation=generation+1 WHERE source_id=owner;
 END IF;
 RETURN NEW;
END $$;
CREATE FUNCTION mta.guard_season_owner() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'Seasonality source ownership is retained'; END IF;
 IF (to_jsonb(NEW)-ARRAY['generation','last_run_id','closing_queue_digest','closing_current_digest'])
   <>(to_jsonb(OLD)-ARRAY['generation','last_run_id','closing_queue_digest','closing_current_digest'])
 THEN RAISE EXCEPTION 'Seasonality installation identity is immutable'; END IF;
 IF NEW.generation<>OLD.generation THEN
  IF NOT COALESCE(mta.supplier_decision_owned(OLD.source_id),false)
   OR NEW.generation<>OLD.generation+1 OR NEW.last_run_id IS DISTINCT FROM OLD.last_run_id
   OR NEW.closing_queue_digest<>OLD.closing_queue_digest OR NEW.closing_current_digest<>OLD.closing_current_digest
  THEN RAISE EXCEPTION 'Seasonality generation requires owned decision'; END IF;
 ELSE
  IF NOT mta.force_consumption_owned(OLD.source_id)
   OR NEW.last_run_id::text<>current_setting('fresh.mdm_consuming_run',true)
  THEN RAISE EXCEPTION 'Seasonality closing requires owned consumption'; END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE FUNCTION mta.guard_season_task_revision() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'Seasonality task revision is retained'; END IF;
 IF NOT COALESCE(mta.supplier_decision_owned(NEW.source_id),false)
 THEN RAISE EXCEPTION 'Seasonality task revision requires owned decision'; END IF;
 IF TG_OP='INSERT' THEN
  IF NEW.revision<>0 THEN RAISE EXCEPTION 'Seasonality task revision starts at zero'; END IF;
 ELSIF NEW.revision<>OLD.revision+1 OR (to_jsonb(NEW)-'revision')<>(to_jsonb(OLD)-'revision') THEN
  RAISE EXCEPTION 'Seasonality task revision must advance once';
 END IF;
 RETURN NEW;
END $$;
'''

TABLES = {'input_season_queue': '"id" bigint,"revision" bigint,"SKUCode" text,"WhCode" text,"StartDate" date,"EndDate" date,"TargetNorm" bigint,"DeltaNormPercentage" bigint,"UpperLowerCap" bigint,"BuildupDuration" bigint,"ActivateDBM" boolean,"Approved" boolean', 'input_season_current': '"id" bigint,"revision" bigint,"ordinal" bigint,"SKUCode" text,"WhCode" text,"StartDate" date,"EndDate" date,"TargetNorm" bigint,"DeltaNormPercentage" bigint,"UpperLowerCap" bigint,"BuildupDuration" bigint,"ActivateDBM" boolean,"OrigNorm" bigint,"NewNorm" bigint,"Type" bigint,"Status" bigint,"Comment" text,"LastProcessedOn" date', 'input_season_task_revision': '"master_id" bigint,"task_id" text,"revision" bigint'}
REVERSE = ""

for model, function, events in (
    ('mdmseasonqueue', 'guard_season_queue', 'INSERT OR UPDATE OR DELETE'),
    ('mdmseasoncurrent', 'guard_season_current', 'INSERT OR UPDATE OR DELETE'),
    ('mdmseasonowner', 'guard_season_owner', 'UPDATE OR DELETE'),
    ('mdmseasontaskrevision', 'guard_season_task_revision', 'INSERT OR UPDATE OR DELETE'),
    ('mdmseasonconsumed', 'guard_force_consumed', 'INSERT OR UPDATE OR DELETE'),
    ('mdmseasoneligibility', 'deny_daily_source_mutation', 'UPDATE OR DELETE')):
    FORWARD += f"CREATE TRIGGER season_owner BEFORE {events} ON mta.fresh_mta_{model} FOR EACH ROW EXECUTE FUNCTION mta.{function}();\n"
    FORWARD += f"CREATE TRIGGER season_truncate BEFORE TRUNCATE ON mta.fresh_mta_{model} FOR EACH STATEMENT EXECUTE FUNCTION mta.deny_daily_source_mutation();\n"
    REVERSE += f"DROP TRIGGER season_owner ON mta.fresh_mta_{model}; DROP TRIGGER season_truncate ON mta.fresh_mta_{model};\n"
for table, columns in TABLES.items():
    FORWARD += f'''
CREATE TABLE mta_state.{table} (
 vf_run_id uuid NOT NULL REFERENCES mta.fresh_mta_calculationrun(id) ON DELETE RESTRICT,
 vf_image text NOT NULL, vf_ordinal bigint NOT NULL, {columns},
 PRIMARY KEY(vf_run_id,vf_image,vf_ordinal));
CREATE TRIGGER season_input_owner BEFORE INSERT OR UPDATE OR DELETE ON mta_state.{table}
 FOR EACH ROW EXECUTE FUNCTION mta.guard_supplier_input_image();
CREATE TRIGGER season_input_truncate BEFORE TRUNCATE ON mta_state.{table}
 FOR EACH STATEMENT EXECUTE FUNCTION mta.deny_daily_source_mutation();
'''
    REVERSE += f'DROP TABLE mta_state.{table};\n'
REVERSE += 'DROP FUNCTION mta.guard_season_task_revision(); DROP FUNCTION mta.guard_season_owner(); DROP FUNCTION mta.guard_season_current(); DROP FUNCTION mta.guard_season_queue();'


class Migration(migrations.Migration):
    dependencies = [('fresh_mta', '0096_nms_seasonality_owners')]
    operations = [migrations.RunSQL(FORWARD, REVERSE)]
