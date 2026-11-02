"""Append-only settings, existing configuration watches and a readable view.

No old guard, applied migration, producer identity or business table is changed.
The table owner is the existing trusted management capability; serving has SELECT.
"""
from django.db import migrations

SQL = r'''
CREATE FUNCTION mta.execution_settings_guard() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog,mta AS $$
DECLARE table_owner name;
BEGIN
 IF TG_OP IN ('DELETE','TRUNCATE') THEN
  RAISE EXCEPTION 'Execution settings history is retained';
 END IF;
 SELECT pg_get_userbyid(relowner) INTO table_owner FROM pg_class WHERE oid=TG_RELID;
 IF current_user<>table_owner AND NOT EXISTS(SELECT 1 FROM pg_roles WHERE rolname=current_user AND rolsuper) THEN
  RAISE EXCEPTION 'Execution settings require their trusted management owner';
 END IF;
 IF TG_TABLE_NAME='fresh_mta_executionsettingsversion' THEN
  IF TG_OP='INSERT' THEN
   IF NEW.status<>'PREPARING' THEN RAISE EXCEPTION 'Settings version must be prepared atomically'; END IF;
   IF (NEW.revision=1) IS DISTINCT FROM (NEW.parent_id IS NULL) THEN
    RAISE EXCEPTION 'Settings revision requires its own predecessor';
   END IF;
   IF NEW.parent_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM mta.fresh_mta_executionsettingsversion P
     WHERE P.id=NEW.parent_id AND P.initialization_id=NEW.initialization_id
       AND P.status='COMMITTED' AND P.revision=NEW.revision-1) THEN
    RAISE EXCEPTION 'Settings parent/installation differs';
   END IF;
  ELSIF NOT (OLD.status='PREPARING' AND NEW.status='COMMITTED'
     AND (to_jsonb(OLD)-'status')=(to_jsonb(NEW)-'status')) THEN
   RAISE EXCEPTION 'Committed settings are immutable';
  END IF;
 ELSE
  IF TG_OP<>'INSERT' OR NOT EXISTS(SELECT 1 FROM mta.fresh_mta_executionsettingsversion V
     WHERE V.id=NEW.version_id AND V.status='PREPARING' AND V.xmin=pg_current_xact_id()::text::xid) THEN
   RAISE EXCEPTION 'Settings values belong to their creating transaction';
  END IF;
 END IF;
 RETURN NEW;
END $$;
REVOKE ALL ON FUNCTION mta.execution_settings_guard() FROM PUBLIC;
'''

for table in ('fresh_mta_executionsettingsversion','fresh_mta_executionsetting'):
    SQL += ('CREATE TRIGGER execution_settings_owner BEFORE INSERT OR UPDATE OR DELETE ON mta.'+table+
        ' FOR EACH ROW EXECUTE FUNCTION mta.execution_settings_guard();\n'
        'CREATE TRIGGER execution_settings_retained BEFORE TRUNCATE ON mta.'+table+
        ' FOR EACH STATEMENT EXECUTE FUNCTION mta.execution_settings_guard();\n')
    for suffix,op,ref in (
            ('insert','INSERT','NEW TABLE AS new_rows'),
            ('update','UPDATE','OLD TABLE AS old_rows NEW TABLE AS new_rows'),
            ('delete','DELETE','OLD TABLE AS old_rows'),('truncate','TRUNCATE','')):
        SQL += ('CREATE TRIGGER ingestion_watch_'+suffix+' AFTER '+op+' ON mta.'+table+
            (' REFERENCING '+ref if ref else '')+
            " FOR EACH STATEMENT EXECUTE FUNCTION mta.ingestion_watch('configuration');\n")

SQL += '''
CREATE VIEW mta.execution_settings_current AS
SELECT V.initialization_id,V.revision,V.effective_date,V.values_digest,
 R.position,R.path,R.module,R.parameter,R.ordinal,R.value_state,R.value_kind,R.value_text
FROM mta.fresh_mta_executionsettingsversion V
JOIN mta.fresh_mta_executionsetting R ON R.version_id=V.id
WHERE V.status='COMMITTED' AND NOT EXISTS(
 SELECT 1 FROM mta.fresh_mta_executionsettingsversion N
 WHERE N.initialization_id=V.initialization_id AND N.status='COMMITTED' AND N.revision>V.revision);
'''


class Migration(migrations.Migration):
    dependencies = [('fresh_mta','0247_execution_settings_versions')]
    # No destructive reversal of committed configuration history.
    operations = [migrations.RunSQL(SQL)]
