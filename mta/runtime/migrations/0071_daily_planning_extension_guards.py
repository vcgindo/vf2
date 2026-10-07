"""An extension cannot replace a seal or an access activation."""
from django.db import migrations

FORWARD = '''
CREATE FUNCTION mta.guard_daily_planning_extension() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF current_database()<>'daily_3006' OR
 current_setting('fresh.daily_planning_extension',true) IS DISTINCT FROM NEW.publication_id::text THEN
  RAISE EXCEPTION 'Owned explicit Planning extension required'; END IF;
 PERFORM 1 FROM mta.fresh_mta_dailyuipublication P
 JOIN mta.fresh_mta_dailyuiactivation A ON A.publication_id=P.run_id
 WHERE P.run_id=NEW.publication_id AND P.status='READY'
 AND P.seal_digest=NEW.publication_seal AND P.source_digest=NEW.source_digest
 AND A.publication_seal=P.seal_digest AND A.activation_digest=NEW.activation_digest
 FOR UPDATE OF P;
 IF NOT FOUND THEN RAISE EXCEPTION 'Unchanged sealed activated publication required'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER daily_planning_extension_insert BEFORE INSERT ON mta.fresh_mta_dailyplanningextension
 FOR EACH ROW EXECUTE FUNCTION mta.guard_daily_planning_extension();
CREATE TRIGGER daily_planning_extension_immutable BEFORE UPDATE OR DELETE OR TRUNCATE ON mta.fresh_mta_dailyplanningextension
 FOR EACH STATEMENT EXECUTE FUNCTION mta.deny_daily_source_mutation();
'''
REVERSE = '''
DROP TRIGGER daily_planning_extension_immutable ON mta.fresh_mta_dailyplanningextension;
DROP TRIGGER daily_planning_extension_insert ON mta.fresh_mta_dailyplanningextension;
DROP FUNCTION mta.guard_daily_planning_extension();
'''


class Migration(migrations.Migration):
    dependencies = [('fresh_mta', '0070_daily_planning_extension')]
    operations = [migrations.RunSQL(FORWARD, REVERSE)]
