"""Disambiguate the captured-run alias from the PL/pgSQL run variable."""
from django.db import migrations

SQL = r'''
CREATE OR REPLACE FUNCTION mta.state_cut_owner() RETURNS trigger LANGUAGE plpgsql
SET search_path=pg_catalog,mta AS $$
DECLARE p mta.fresh_mta_operationalstatecut; r mta.fresh_mta_calculationrun;
 i mta.fresh_mta_productioninitialization; table_owner name;
BEGIN
 SELECT pg_get_userbyid(relowner) INTO table_owner FROM pg_class WHERE oid=TG_RELID;
 IF current_user<>table_owner AND NOT EXISTS(SELECT 1 FROM pg_roles WHERE rolname=current_user AND rolsuper)
 THEN RAISE EXCEPTION 'Operational cut requires its trusted writer'; END IF;
 IF TG_OP='UPDATE' THEN
  PERFORM mta.require_pending_state_cut(OLD.id);
  IF NEW.root_digest='' OR NEW.root_body='' OR
    (to_jsonb(OLD)-ARRAY['root_body','root_digest']) IS DISTINCT FROM
    (to_jsonb(NEW)-ARRAY['root_body','root_digest'])
  THEN RAISE EXCEPTION 'Only the pending operational commitment may seal'; END IF;
  RETURN NEW;
 END IF;
 IF NEW.root_body<>'' OR NEW.root_digest<>'' THEN RAISE EXCEPTION 'Operational cut must start pending'; END IF;
 SELECT * INTO STRICT i FROM mta.fresh_mta_productioninitialization
  WHERE id=NEW.initialization_id FOR UPDATE;
 IF (NEW.position>0 OR NEW.run_id IS NOT NULL) AND i.receipt_digest=''
 THEN RAISE EXCEPTION 'Operational cut initialization is unsealed'; END IF;
 IF NEW.position=0 THEN
  IF NOT EXISTS(SELECT 1 FROM pg_roles WHERE rolname=current_user AND rolsuper) AND
    (NEW.run_id IS NOT NULL OR mta.native_initialization_pending(i.id) IS NOT TRUE)
  THEN RAISE EXCEPTION 'Existing-state anchor requires normal trusted adoption'; END IF;
  IF NEW.run_id IS NULL THEN
   IF NEW.input_digest<>i.input_digest OR NEW.settings_digest<>i.configuration_digest OR
    EXISTS(SELECT 1 FROM mta.fresh_mta_mdmdailyinputcapture C
      JOIN mta.fresh_mta_calculationrun captured_run ON captured_run.id=C.run_id
      WHERE C.source_id=i.source_id AND captured_run.status IN ('RUNNING','SUCCEEDED'))
   THEN RAISE EXCEPTION 'Initial anchor differs from its unused opening'; END IF;
  ELSE
   SELECT * INTO STRICT r FROM mta.fresh_mta_calculationrun WHERE id=NEW.run_id FOR SHARE;
   IF r.status<>'SUCCEEDED' OR NEW.input_digest<>r.input_digest OR
     NOT EXISTS(SELECT 1 FROM mta.fresh_mta_mdmdailyinputcapture
       WHERE run_id=r.id AND source_id=i.source_id AND status='CONSUMED') OR
     EXISTS(SELECT 1 FROM mta.fresh_mta_calculationrun
       WHERE predecessor_id=r.id AND status IN ('RUNNING','SUCCEEDED'))
   THEN RAISE EXCEPTION 'Accepted anchor is not the exact current owned predecessor'; END IF;
  END IF;
 ELSE
  SELECT * INTO STRICT r FROM mta.fresh_mta_calculationrun WHERE id=NEW.run_id FOR UPDATE;
  SELECT * INTO STRICT p FROM mta.fresh_mta_operationalstatecut WHERE id=NEW.parent_id FOR SHARE;
  IF r.status<>'RUNNING' OR NEW.input_digest<>r.input_digest OR
    p.initialization_id<>NEW.initialization_id OR p.family<>NEW.family OR p.root_digest='' OR
    NEW.position<>p.position+1 OR r.predecessor_id IS DISTINCT FROM p.run_id OR
    NOT EXISTS(SELECT 1 FROM mta.fresh_mta_mdmdailyinputcapture
      WHERE run_id=r.id AND source_id=i.source_id AND status IN ('CAPTURED','CONSUMED')) OR
    (p.run_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM mta.fresh_mta_calculationrun
      WHERE id=p.run_id AND status='SUCCEEDED'))
  THEN RAISE EXCEPTION 'Operational cut owner or accepted parent differs'; END IF;
 END IF;
 IF NEW.run_id IS NOT NULL AND
    NEW.settings_digest IS DISTINCT FROM mta.state_cut_settings(i.id,NEW.run_id)
 THEN RAISE EXCEPTION 'Operational cut frozen settings differ'; END IF;
 RETURN NEW;
END $$;
'''

class Migration(migrations.Migration):
    dependencies = [('fresh_mta', '0251_operational_cut_qualification')]
    operations = [migrations.RunSQL(SQL)]
