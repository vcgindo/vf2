"""Append-only access activation cannot mutate the original publication seal."""
from django.db import migrations

FORWARD = '''
CREATE FUNCTION mta.guard_daily_ui_activation() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF current_setting('fresh.daily_activation',true) IS DISTINCT FROM NEW.publication_id::text THEN
  RAISE EXCEPTION 'Explicit daily activation owner required'; END IF;
 PERFORM 1 FROM mta.fresh_mta_dailyuipublication P
 JOIN mta.fresh_mta_calculationrun R ON R.id=P.run_id
 WHERE P.run_id=NEW.publication_id AND P.status='READY'
 AND P.seal_digest=NEW.publication_seal AND P.seal_digest<>''
 AND R.kind='DAILY_CHAIN' AND R.status='SUCCEEDED'
 AND P.output_digest=R.output_digest
 AND R.parity_summary->>'status' IN ('PASS','PASS_WITH_LEGACY_FLAWS')
 FOR UPDATE OF P;
 IF NOT FOUND THEN RAISE EXCEPTION 'Accepted sealed daily publication required'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER daily_activation_insert BEFORE INSERT ON mta.fresh_mta_dailyuiactivation
 FOR EACH ROW EXECUTE FUNCTION mta.guard_daily_ui_activation();
CREATE TRIGGER daily_activation_immutable BEFORE UPDATE OR DELETE OR TRUNCATE ON mta.fresh_mta_dailyuiactivation
 FOR EACH STATEMENT EXECUTE FUNCTION mta.deny_daily_source_mutation();
'''
REVERSE = '''
DROP TRIGGER daily_activation_immutable ON mta.fresh_mta_dailyuiactivation;
DROP TRIGGER daily_activation_insert ON mta.fresh_mta_dailyuiactivation;
DROP FUNCTION mta.guard_daily_ui_activation();
'''


class Migration(migrations.Migration):
    dependencies = [('fresh_mta', '0068_daily_ui_activation')]
    operations = [migrations.RunSQL(FORWARD, REVERSE)]
