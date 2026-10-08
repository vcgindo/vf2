"""A completed calculation cannot acquire operational capture authorization."""
from django.db import migrations


FORWARD = '''
CREATE FUNCTION mta.guard_operational_authorization_insert() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
 IF NEW.run_id::text IS DISTINCT FROM current_setting('fresh.operational_capture_authorize', true)
    OR NEW.policy <> 'cohort2-operational-sources-v1'
    OR NOT EXISTS (SELECT 1 FROM mta.fresh_mta_calculationrun r WHERE r.id=NEW.run_id
        AND r.status='RUNNING' AND r.completed_at IS NULL
        AND r.output_digest='' AND r.production_digest='' AND r.input_digest=NEW.input_digest) THEN
   RAISE EXCEPTION 'Operational authorization requires its new uncalculated owner';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER op_capture_auth_insert BEFORE INSERT ON mta.fresh_mta_operationalcaptureauthorization
 FOR EACH ROW EXECUTE FUNCTION mta.guard_operational_authorization_insert();
CREATE TRIGGER op_capture_auth_immutable BEFORE UPDATE OR DELETE OR TRUNCATE
 ON mta.fresh_mta_operationalcaptureauthorization
 FOR EACH STATEMENT EXECUTE FUNCTION mta.deny_daily_source_mutation();
CREATE OR REPLACE FUNCTION mta.guard_operational_producer_insert() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE owner uuid;
BEGIN
 owner := COALESCE(to_jsonb(NEW)->>'run_id', to_jsonb(NEW)->>'source_id')::uuid;
 IF owner::text IS DISTINCT FROM current_setting('fresh.operational_capture_run', true)
    OR NOT EXISTS (SELECT 1 FROM mta.fresh_mta_calculationrun r
        JOIN mta.fresh_mta_operationalcaptureauthorization a ON a.run_id=r.id
        WHERE r.id=owner AND r.status='RUNNING' AND r.completed_at IS NULL
          AND a.input_digest=r.input_digest AND a.policy='cohort2-operational-sources-v1') THEN
   RAISE EXCEPTION 'Operational producer insert requires its authorized live production owner';
 END IF;
 RETURN NEW;
END $$;
'''

REVERSE = '''
DROP TRIGGER op_capture_auth_immutable ON mta.fresh_mta_operationalcaptureauthorization;
DROP TRIGGER op_capture_auth_insert ON mta.fresh_mta_operationalcaptureauthorization;
DROP FUNCTION mta.guard_operational_authorization_insert();
CREATE OR REPLACE FUNCTION mta.guard_operational_producer_insert() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE owner uuid;
BEGIN
 owner := COALESCE(to_jsonb(NEW)->>'run_id', to_jsonb(NEW)->>'source_id')::uuid;
 IF owner::text IS DISTINCT FROM current_setting('fresh.operational_capture_run', true)
    OR NOT EXISTS (SELECT 1 FROM mta.fresh_mta_calculationrun WHERE id=owner AND status='RUNNING') THEN
   RAISE EXCEPTION 'Operational producer insert requires its live production owner';
 END IF;
 RETURN NEW;
END $$;
'''


class Migration(migrations.Migration):
    dependencies = [('fresh_mta', '0086_operational_capture_authorization')]
    operations = [migrations.RunSQL(FORWARD, REVERSE)]
