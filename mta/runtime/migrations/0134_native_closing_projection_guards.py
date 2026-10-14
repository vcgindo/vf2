"""Bind location daily writes to one owned pending v2 projection receipt."""
from django.db import migrations

FORWARD = r'''
CREATE FUNCTION mta.location_transition_record(owner bigint) RETURNS jsonb
LANGUAGE plpgsql STABLE AS $$
DECLARE result jsonb;
BEGIN
 IF to_regclass('mta.native_location_transition') IS NULL THEN RETURN NULL; END IF;
 IF NOT EXISTS(SELECT 1 FROM pg_class T JOIN pg_roles R ON R.oid=T.relowner
  WHERE T.oid='mta.native_location_transition'::regclass AND R.rolname='fresh_namespace_registrar'
  AND NOT R.rolcanlogin AND NOT R.rolsuper AND NOT R.rolcreatedb AND NOT R.rolcreaterole)
  THEN RAISE EXCEPTION 'Location transition must be registrar owned'; END IF;
 EXECUTE 'SELECT record FROM mta.native_location_transition WHERE singleton IS TRUE' INTO STRICT result;
 IF (result->>'source_id')::bigint=owner THEN RETURN result; END IF;
 RETURN NULL;
END $$;

CREATE FUNCTION mta.valid_closing_projection(P mta.fresh_mta_mdmclosingprojectionreceipt) RETURNS boolean
LANGUAGE plpgsql STABLE AS $$
DECLARE C mta.fresh_mta_mdmdailyinputcapture; R mta.fresh_mta_calculationrun;
 S mta.fresh_mta_mdmsource; I mta.fresh_mta_mdmsourceintegration; T jsonb;
BEGIN
 SELECT * INTO STRICT C FROM mta.fresh_mta_mdmdailyinputcapture WHERE run_id=P.run_id;
 SELECT * INTO STRICT R FROM mta.fresh_mta_calculationrun WHERE id=P.run_id;
 SELECT * INTO STRICT S FROM mta.fresh_mta_mdmsource WHERE id=C.source_id;
 SELECT * INTO STRICT I FROM mta.fresh_mta_mdmsourceintegration WHERE source_id=C.source_id;
 IF S.receipt->>'schema'<>'fresh-production-mdm-source-v1' OR C.status<>'CONSUMED'
  OR R.kind<>'DAILY_CHAIN' OR R.status<>'RUNNING'
  OR P.run_id::text IS DISTINCT FROM current_setting('fresh.mdm_current_run',true)
  OR P.run_id::text IS DISTINCT FROM current_setting('fresh.mdm_consuming_run',true)
  OR P.version<>'native-closing-locations-v2' OR P.source_digest<>S.digest
  OR P.integration_digest<>I.digest OR length(P.capture_digest)<>64 THEN RETURN false; END IF;
 IF I.receipt->>'closing_projection_version'='native-closing-locations-v2' THEN
  RETURN P.transition_id IS NULL AND P.adapter_digest=I.receipt->>'adapter_digest'
   AND P.source_manifest_digest=I.receipt->>'source_manifest_digest'
   AND (R.predecessor_id IS NULL OR EXISTS(SELECT 1 FROM mta.fresh_mta_mdmclosingprojectionreceipt Q
    JOIN mta.fresh_mta_mdmdailyinputcapture D ON D.run_id=Q.run_id
    WHERE Q.run_id=R.predecessor_id AND Q.status='SEALED' AND D.source_id=C.source_id
     AND Q.transition_id IS NULL AND Q.version=P.version AND Q.integration_digest=P.integration_digest
     AND Q.adapter_digest=P.adapter_digest AND Q.source_manifest_digest=P.source_manifest_digest));
 END IF;
 IF I.receipt ? 'closing_projection_version' THEN RETURN false; END IF;
 T=mta.location_transition_record(C.source_id);
 IF T IS NULL THEN RETURN false; END IF;
 RETURN P.transition_id IS NOT NULL AND P.transition_id::text=T->>'transition_id'
  AND P.source_digest=T->>'source_digest' AND P.adapter_digest=T->>'new_adapter_digest'
  AND P.source_manifest_digest=T->>'new_source_manifest_digest'
  AND P.integration_digest=T->>'old_integration_digest'
  AND I.receipt->>'adapter_digest'=T->>'old_adapter_digest'
  AND R.business_date BETWEEN (T->>'first_day')::date AND (T->>'last_day')::date
  AND ((R.business_date=(T->>'first_day')::date AND R.predecessor_id::text=T->>'predecessor_id'
    AND EXISTS(SELECT 1 FROM mta.fresh_mta_calculationrun B WHERE B.id=R.predecessor_id
      AND B.status='SUCCEEDED' AND B.output_digest=T->>'predecessor_output_digest'))
   OR (R.business_date>(T->>'first_day')::date AND EXISTS(
    SELECT 1 FROM mta.fresh_mta_mdmclosingprojectionreceipt Q
    JOIN mta.fresh_mta_mdmdailyinputcapture D ON D.run_id=Q.run_id
    JOIN mta.fresh_mta_calculationrun B ON B.id=Q.run_id
    WHERE Q.run_id=R.predecessor_id AND Q.status='SEALED' AND B.status='SUCCEEDED'
      AND D.source_id=C.source_id AND Q.transition_id=P.transition_id AND Q.version=P.version
      AND Q.integration_digest=P.integration_digest AND Q.adapter_digest=P.adapter_digest
      AND Q.source_manifest_digest=P.source_manifest_digest)));
END $$;

CREATE FUNCTION mta.guard_closing_projection() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF TG_OP IN ('DELETE','TRUNCATE') THEN RAISE EXCEPTION 'Closing projection receipt is immutable'; END IF;
 IF NOT coalesce(mta.valid_closing_projection(NEW),false)
  THEN RAISE EXCEPTION 'Closing projection requires its exact owned native activation'; END IF;
 IF TG_OP='INSERT' THEN
  IF NEW.status<>'PENDING' OR NEW.metadata<>'{}'::jsonb OR NEW.digest<>''
   THEN RAISE EXCEPTION 'Closing projection must start pending'; END IF;
 ELSIF OLD.status<>'PENDING' OR NEW.status<>'SEALED'
  OR (to_jsonb(OLD)-ARRAY['status','metadata','digest'])<>(to_jsonb(NEW)-ARRAY['status','metadata','digest'])
  OR NEW.metadata->>'version' IS DISTINCT FROM NEW.version
  OR jsonb_typeof(NEW.metadata->'partitions') IS DISTINCT FROM 'array'
  OR jsonb_typeof(NEW.metadata->'sources') IS DISTINCT FROM 'array'
  OR length(NEW.digest)<>64
  THEN RAISE EXCEPTION 'Closing projection can seal exactly once';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER native_closing_projection BEFORE INSERT OR UPDATE OR DELETE
 ON mta.fresh_mta_mdmclosingprojectionreceipt FOR EACH ROW EXECUTE FUNCTION mta.guard_closing_projection();
CREATE TRIGGER native_closing_projection_truncate BEFORE TRUNCATE
 ON mta.fresh_mta_mdmclosingprojectionreceipt FOR EACH STATEMENT EXECUTE FUNCTION mta.guard_closing_projection();

CREATE FUNCTION mta.guard_location_projection_statement() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE current_id text; C mta.fresh_mta_mdmdailyinputcapture;
 P mta.fresh_mta_mdmclosingprojectionreceipt; corrected boolean;
BEGIN
 current_id=current_setting('fresh.mdm_current_run',true);
 IF coalesce(current_id,'')='' THEN
  -- Empty DELETE has no row trigger. In a v2 namespace it still requires an
  -- owned day. Synchronous Add is INSERT-only and remains independently backed.
  IF TG_OP='DELETE' AND (to_regclass('mta.native_location_transition') IS NOT NULL OR EXISTS(
   SELECT 1 FROM mta.fresh_mta_mdmsourceintegration
   WHERE receipt->>'closing_projection_version'='native-closing-locations-v2'))
   THEN RAISE EXCEPTION 'Location daily DELETE requires its owned projection'; END IF;
  RETURN NULL;
 END IF;
 SELECT * INTO STRICT C FROM mta.fresh_mta_mdmdailyinputcapture WHERE run_id=current_id::uuid;
 corrected=EXISTS(SELECT 1 FROM mta.fresh_mta_mdmsourceintegration WHERE source_id=C.source_id
  AND receipt->>'closing_projection_version'='native-closing-locations-v2')
  OR mta.location_transition_record(C.source_id) IS NOT NULL;
 IF corrected THEN
  SELECT * INTO P FROM mta.fresh_mta_mdmclosingprojectionreceipt WHERE run_id=C.run_id;
  IF NOT FOUND OR P.status<>'PENDING' OR NOT coalesce(mta.valid_closing_projection(P),false)
   THEN RAISE EXCEPTION 'Location daily publication requires its pending v2 receipt'; END IF;
 END IF;
 RETURN NULL;
END $$;
'''

for table in ('mdmlocationattributes','mdmlocationdescription'):
    FORWARD += f'''
CREATE TRIGGER native_location_projection_statement BEFORE INSERT OR DELETE
 ON mta.fresh_mta_{table} FOR EACH STATEMENT EXECUTE FUNCTION mta.guard_location_projection_statement();
'''

REVERSE = '''
DROP TRIGGER native_location_projection_statement ON mta.fresh_mta_mdmlocationattributes;
DROP TRIGGER native_location_projection_statement ON mta.fresh_mta_mdmlocationdescription;
DROP FUNCTION mta.guard_location_projection_statement();
DROP TRIGGER native_closing_projection ON mta.fresh_mta_mdmclosingprojectionreceipt;
DROP TRIGGER native_closing_projection_truncate ON mta.fresh_mta_mdmclosingprojectionreceipt;
DROP FUNCTION mta.guard_closing_projection();
DROP FUNCTION mta.valid_closing_projection(mta.fresh_mta_mdmclosingprojectionreceipt);
DROP FUNCTION mta.location_transition_record(bigint);
'''


class Migration(migrations.Migration):
    dependencies = [('fresh_mta','0133_mdmclosingprojectionreceipt')]
    operations = [migrations.RunSQL(FORWARD,REVERSE)]
