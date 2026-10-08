"""Operational producer snapshots are live-transaction-only and append-only."""
from django.db import migrations


TABLES = ('operationalcalculationsource', 'operationalrequirementband', 'operationaladvancestock')
FORWARD = '''
CREATE FUNCTION mta.guard_operational_producer_insert() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE owner uuid;
BEGIN
 owner := COALESCE(to_jsonb(NEW)->>'run_id', to_jsonb(NEW)->>'source_id')::uuid;
 IF owner::text IS DISTINCT FROM current_setting('fresh.operational_capture_run', true)
    OR NOT EXISTS (SELECT 1 FROM mta.fresh_mta_calculationrun
                   WHERE id=owner AND status='RUNNING') THEN
   RAISE EXCEPTION 'Operational producer insert requires its live production owner';
 END IF;
 RETURN NEW;
END $$;
'''
for table in TABLES:
    FORWARD += f'''
CREATE TRIGGER op_producer_insert BEFORE INSERT ON mta.fresh_mta_{table}
 FOR EACH ROW EXECUTE FUNCTION mta.guard_operational_producer_insert();
CREATE TRIGGER op_producer_immutable BEFORE UPDATE OR DELETE OR TRUNCATE ON mta.fresh_mta_{table}
 FOR EACH STATEMENT EXECUTE FUNCTION mta.deny_daily_source_mutation();
'''
REVERSE = ''.join(f'''
DROP TRIGGER op_producer_immutable ON mta.fresh_mta_{table};
DROP TRIGGER op_producer_insert ON mta.fresh_mta_{table};
''' for table in reversed(TABLES)) + 'DROP FUNCTION mta.guard_operational_producer_insert();'


class Migration(migrations.Migration):
    dependencies = [('fresh_mta', '0084_operational_producer_sources')]
    operations = [migrations.RunSQL(FORWARD, REVERSE)]
