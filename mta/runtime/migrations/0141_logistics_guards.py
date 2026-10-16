"""Operational history/current owners; frozen daily tables remain untouched."""
from django.db import migrations

FORWARD = r'''
CREATE FUNCTION mta.guard_logistics_owner() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF TG_OP='UPDATE' THEN
  IF NEW.name IS DISTINCT FROM OLD.name OR NEW.provenance IS DISTINCT FROM OLD.provenance
   OR NEW.provenance_digest IS DISTINCT FROM OLD.provenance_digest
   OR NEW.next_ordinal<OLD.next_ordinal OR NEW.revision<OLD.revision
  THEN RAISE EXCEPTION 'Immutable logistics owner identity'; END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER logistics_owner_update BEFORE UPDATE ON mta.fresh_mta_logisticshistoryowner
 FOR EACH ROW EXECUTE FUNCTION mta.guard_logistics_owner();
CREATE TRIGGER logistics_owner_immutable BEFORE DELETE OR TRUNCATE ON mta.fresh_mta_logisticshistoryowner
 FOR EACH STATEMENT EXECUTE FUNCTION mta.deny_daily_source_mutation();

CREATE FUNCTION mta.guard_transit_generation() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF TG_OP='UPDATE' AND (NEW.run_id IS DISTINCT FROM OLD.run_id
   OR NEW.source_digest IS DISTINCT FROM OLD.source_digest OR NEW.revision<OLD.revision)
 THEN RAISE EXCEPTION 'Immutable shipment generation binding'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER transit_generation_update BEFORE UPDATE ON mta.fresh_mta_transitlivegeneration
 FOR EACH ROW EXECUTE FUNCTION mta.guard_transit_generation();
CREATE TRIGGER transit_generation_immutable BEFORE DELETE OR TRUNCATE ON mta.fresh_mta_transitlivegeneration
 FOR EACH STATEMENT EXECUTE FUNCTION mta.deny_daily_source_mutation();

CREATE FUNCTION mta.guard_transit_annotation() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF current_setting('fresh.logistics_command',true) IS DISTINCT FROM 'LogisticsWorkflow'
 THEN RAISE EXCEPTION 'Logistics command transaction required'; END IF;
 IF TG_OP='UPDATE' AND (NEW.generation_id IS DISTINCT FROM OLD.generation_id
    OR NEW.source_ordinal IS DISTINCT FROM OLD.source_ordinal)
 THEN RAISE EXCEPTION 'Immutable shipment occurrence binding'; END IF;
 PERFORM 1 FROM mta.fresh_mta_transitlivegeneration WHERE run_id=NEW.generation_id FOR UPDATE;
 IF NOT FOUND OR NOT EXISTS(SELECT 1 FROM mta.fresh_mta_dailytransitrow
   WHERE run_id=NEW.generation_id AND ordinal=NEW.source_ordinal)
 THEN RAISE EXCEPTION 'Native shipment occurrence required'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER transit_annotation_write BEFORE INSERT OR UPDATE ON mta.fresh_mta_transitannotation
 FOR EACH ROW EXECUTE FUNCTION mta.guard_transit_annotation();
CREATE TRIGGER transit_annotation_immutable BEFORE DELETE OR TRUNCATE ON mta.fresh_mta_transitannotation
 FOR EACH STATEMENT EXECUTE FUNCTION mta.deny_daily_source_mutation();

CREATE FUNCTION mta.guard_logistics_history() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE cutoff timestamp with time zone; stamp timestamp with time zone;
BEGIN
 IF TG_OP='DELETE' THEN
  cutoff:=nullif(current_setting('fresh.logistics_retention_cutoff',true),'')::timestamptz;
  stamp:=CASE WHEN TG_TABLE_NAME='fresh_mta_transitremarkhistory' THEN
    (to_jsonb(OLD)->>'RemarksDate')::timestamptz ELSE (to_jsonb(OLD)->>'RemarkDate')::timestamptz END;
  IF cutoff IS NULL OR stamp IS NULL OR stamp>cutoff
  THEN RAISE EXCEPTION 'Native logistics retention cutoff required'; END IF;
  RETURN OLD;
 END IF;
 IF TG_OP='UPDATE' OR current_setting('fresh.logistics_command',true) IS DISTINCT FROM 'LogisticsWorkflow'
 THEN RAISE EXCEPTION 'Append-only logistics command history'; END IF;
 PERFORM 1 FROM mta.fresh_mta_logisticshistoryowner WHERE name=NEW.owner_id FOR UPDATE;
 IF NOT FOUND THEN RAISE EXCEPTION 'Logistics history owner required'; END IF;
 RETURN NEW;
END $$;
'''
REVERSE = ''
for table in ('fresh_mta_transitremarkhistory', 'fresh_mta_expediteremarkhistory'):
    FORWARD += f'''
CREATE TRIGGER logistics_history_write BEFORE INSERT OR UPDATE OR DELETE ON mta.{table}
 FOR EACH ROW EXECUTE FUNCTION mta.guard_logistics_history();
CREATE TRIGGER logistics_history_truncate BEFORE TRUNCATE ON mta.{table}
 FOR EACH STATEMENT EXECUTE FUNCTION mta.deny_daily_source_mutation();
'''
    REVERSE += f'DROP TRIGGER logistics_history_write ON mta.{table}; DROP TRIGGER logistics_history_truncate ON mta.{table};\n'
REVERSE += '''
DROP FUNCTION mta.guard_logistics_history();
DROP TRIGGER transit_annotation_write ON mta.fresh_mta_transitannotation;
DROP TRIGGER transit_annotation_immutable ON mta.fresh_mta_transitannotation;
DROP FUNCTION mta.guard_transit_annotation();
DROP TRIGGER transit_generation_update ON mta.fresh_mta_transitlivegeneration;
DROP TRIGGER transit_generation_immutable ON mta.fresh_mta_transitlivegeneration;
DROP FUNCTION mta.guard_transit_generation();
DROP TRIGGER logistics_owner_update ON mta.fresh_mta_logisticshistoryowner;
DROP TRIGGER logistics_owner_immutable ON mta.fresh_mta_logisticshistoryowner;
DROP FUNCTION mta.guard_logistics_owner();
'''


class Migration(migrations.Migration):
    dependencies = [('fresh_mta', '0140_logistics_live')]
    operations = [migrations.RunSQL(FORWARD, REVERSE)]
