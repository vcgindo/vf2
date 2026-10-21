"""Migration registration is append-only authority metadata, not a business edit.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
from django.db import migrations

BODY="""
DECLARE owner_name text;
BEGIN
 IF TG_TABLE_SCHEMA<>'mta' OR TG_TABLE_NAME<>'django_migrations' OR TG_OP<>'INSERT'
 THEN RAISE EXCEPTION 'Migration history is append-only authority'; END IF;
 SELECT pg_get_userbyid(relowner) INTO owner_name FROM pg_class WHERE oid=TG_RELID;
 IF current_user<>owner_name AND NOT EXISTS(SELECT 1 FROM pg_roles WHERE rolname=current_user AND rolsuper)
 THEN RAISE EXCEPTION 'Migration history requires its trusted owner'; END IF;
 RETURN NEW;
END
"""
FORWARD='CREATE OR REPLACE FUNCTION mta.guard_migration_history() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog,mta AS $$'+BODY+'$$;\n'
FORWARD+='REVOKE ALL ON FUNCTION mta.guard_migration_history() FROM PUBLIC;\n'
for op in ('insert','update','delete','truncate'):
    FORWARD+='DROP TRIGGER IF EXISTS ingestion_watch_'+op+' ON mta.django_migrations;\n'
FORWARD+='DROP TRIGGER IF EXISTS migration_history_append ON mta.django_migrations;\n'
FORWARD+='DROP TRIGGER IF EXISTS migration_history_immutable ON mta.django_migrations;\n'
FORWARD+='CREATE TRIGGER migration_history_append BEFORE INSERT ON mta.django_migrations FOR EACH ROW EXECUTE FUNCTION mta.guard_migration_history();\n'
FORWARD+='CREATE TRIGGER migration_history_immutable BEFORE UPDATE OR DELETE OR TRUNCATE ON mta.django_migrations FOR EACH STATEMENT EXECUTE FUNCTION mta.guard_migration_history();\n'
REVERSE='DROP TRIGGER migration_history_append ON mta.django_migrations; DROP TRIGGER migration_history_immutable ON mta.django_migrations; DROP FUNCTION mta.guard_migration_history();\n'
for op,ref in (('INSERT','NEW TABLE AS new_rows'),('UPDATE','OLD TABLE AS old_rows NEW TABLE AS new_rows'),('DELETE','OLD TABLE AS old_rows'),('TRUNCATE','')):
    REVERSE+='CREATE TRIGGER ingestion_watch_'+op.lower()+' AFTER '+op+' ON mta.django_migrations'+(' REFERENCING '+ref if ref else '')+" FOR EACH STATEMENT EXECUTE FUNCTION mta.ingestion_watch('operational');\n"


class Migration(migrations.Migration):
    dependencies=[('fresh_mta','0163_finite_capture_admission')]
    operations=[migrations.RunSQL(FORWARD,REVERSE)]
