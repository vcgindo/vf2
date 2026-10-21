"""Guard report-source capture and post-commit generation sealing.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
from django.db import migrations


SQL = r"""
CREATE FUNCTION mta.guard_report_route_source() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF NEW.run_id::text IS DISTINCT FROM current_setting('fresh.report_route_source',true)
 OR NOT EXISTS(SELECT 1 FROM mta.fresh_mta_calculationrun WHERE id=NEW.run_id
    AND kind='DAILY_CHAIN' AND status='RUNNING') THEN
  RAISE EXCEPTION 'Report route facts require the live owning day'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER report_route_insert BEFORE INSERT ON mta.fresh_mta_dailyreportorderroutesource
 FOR EACH ROW EXECUTE FUNCTION mta.guard_report_route_source();
CREATE TRIGGER report_route_immutable BEFORE UPDATE OR DELETE OR TRUNCATE ON mta.fresh_mta_dailyreportorderroutesource
 FOR EACH STATEMENT EXECUTE FUNCTION mta.deny_daily_source_mutation();
CREATE FUNCTION mta.guard_report_generation() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE source text;
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'Report generation identity is retained'; END IF;
 SELECT production_digest INTO source FROM mta.fresh_mta_calculationrun
 WHERE id=NEW.run_id AND kind='DAILY_CHAIN' AND status='SUCCEEDED'
   AND production_manifest->>'version'='3' FOR UPDATE;
 IF NOT FOUND OR NEW.source_digest IS DISTINCT FROM source OR NEW.version<>1
   OR NEW.recipe_digest !~ '^[0-9a-f]{64}$' THEN
  RAISE EXCEPTION 'Report generation requires its completed version-three source'; END IF;
 IF TG_OP='INSERT' AND (NEW.status<>'INCOMPLETE' OR NEW.metadata<>'{}'::jsonb
     OR NEW.digest<>'' OR NEW.sealed_at IS NOT NULL) THEN
  RAISE EXCEPTION 'New report generation must start unsealed'; END IF;
 IF TG_OP='UPDATE' THEN
  IF OLD.status='READY' OR NEW.run_id IS DISTINCT FROM OLD.run_id
    OR NEW.source_digest IS DISTINCT FROM OLD.source_digest
    OR NEW.recipe_digest IS DISTINCT FROM OLD.recipe_digest
    OR NEW.version IS DISTINCT FROM OLD.version THEN
   RAISE EXCEPTION 'Sealed report generation identity is immutable'; END IF;
  IF NEW.status<>'READY' OR NEW.digest !~ '^[0-9a-f]{64}$' OR NEW.sealed_at IS NULL
    OR NEW.run_id::text IS DISTINCT FROM current_setting('fresh.report_generation',true)
    OR octet_length(NEW.metadata::text)>1048576 THEN
   RAISE EXCEPTION 'Report seal requires bounded verified owning generation'; END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER report_generation_guard BEFORE INSERT OR UPDATE OR DELETE ON mta.fresh_mta_dailyreportgeneration
 FOR EACH ROW EXECUTE FUNCTION mta.guard_report_generation();
CREATE TRIGGER report_generation_no_truncate BEFORE TRUNCATE ON mta.fresh_mta_dailyreportgeneration
 FOR EACH STATEMENT EXECUTE FUNCTION mta.deny_daily_source_mutation();
"""
REVERSE = """
DROP TRIGGER report_generation_no_truncate ON mta.fresh_mta_dailyreportgeneration;
DROP TRIGGER report_generation_guard ON mta.fresh_mta_dailyreportgeneration;
DROP FUNCTION mta.guard_report_generation();
DROP TRIGGER report_route_immutable ON mta.fresh_mta_dailyreportorderroutesource;
DROP TRIGGER report_route_insert ON mta.fresh_mta_dailyreportorderroutesource;
DROP FUNCTION mta.guard_report_route_source();
"""
for table in ('fresh_mta_dailyreportgeneration','fresh_mta_dailyreportorderroutesource'):
    for op,ref in (('INSERT','NEW TABLE AS new_rows'),
        ('UPDATE','OLD TABLE AS old_rows NEW TABLE AS new_rows'),
        ('DELETE','OLD TABLE AS old_rows'),('TRUNCATE','')):
        SQL += ('CREATE TRIGGER ingestion_watch_'+op.lower()+' AFTER '+op+' ON mta.'+table+
            (' REFERENCING '+ref if ref else '')+
            " FOR EACH STATEMENT EXECUTE FUNCTION mta.ingestion_watch('operational');\n")
        REVERSE = 'DROP TRIGGER ingestion_watch_'+op.lower()+' ON mta.'+table+';\n'+REVERSE


class Migration(migrations.Migration):
    dependencies=[('fresh_mta','0155_daily_report_route_source')]
    operations=[migrations.RunSQL(SQL,REVERSE)]
