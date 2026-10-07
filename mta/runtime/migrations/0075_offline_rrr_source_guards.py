"""Additive guards only; the accepted smoke RRR objects remain untouched."""
from django.db import migrations

FORWARD = r'''
CREATE FUNCTION mta.guard_offline_rrr_insert() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE owner uuid;
BEGIN
 owner := CASE WHEN TG_TABLE_NAME='fresh_mta_offlinerrrcoloursource'
   THEN (to_jsonb(NEW)->>'run_id')::uuid ELSE (to_jsonb(NEW)->>'receipt_id')::uuid END;
 IF current_database()<>'daily_3006' OR
    current_setting('fresh.offline_rrr_write',true) IS DISTINCT FROM owner::text THEN
   RAISE EXCEPTION 'Explicit owned offline RRR transaction required'; END IF;
 PERFORM 1 FROM mta.fresh_mta_calculationrun R
 JOIN mta.fresh_mta_mdmdailyinputcapture C ON C.run_id=R.id
 JOIN mta.fresh_mta_mdmsource S ON S.id=C.source_id
 WHERE R.id=owner AND R.kind='DAILY_CHAIN' AND R.status='RUNNING'
 AND S.receipt->>'scenario_sha256'='120ca4c8b6363627e339519fa2816883e81e46b768071ee6266232645d6ad52a'
 AND S.receipt->>'artifact_sha256' IN
 ('ee707e71eb134f8ade084bef95d4ff915d8ba94a50776e0c1621e5a3bd0b0f56',
  'a7e12b4a0ea39c4e0122076df8f6a6268e749dca73a51387278878511281993f')
 AND S.receipt ? 'offline_owner';
 IF NOT FOUND THEN RAISE EXCEPTION 'Registered running offline source owner required'; END IF;
 IF TG_TABLE_NAME='fresh_mta_offlinerrrcoloursource' THEN
   PERFORM 1 FROM mta.fresh_mta_calculationrun R
   JOIN mta.fresh_mta_mdmdailyinputcapture C ON C.run_id=R.id
   JOIN mta.fresh_mta_mdmsource S ON S.id=C.source_id
   WHERE R.id=owner AND R.input_digest=NEW.input_digest
   AND S.receipt->>'artifact_sha256'=NEW.artifact_sha256
   AND S.receipt->>'scenario_sha256'=NEW.scenario_sha256;
   IF NOT FOUND THEN RAISE EXCEPTION 'Offline source input identity differs'; END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE FUNCTION mta.check_offline_rrr_population() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE owner uuid; expected bigint; actual bigint; lowest bigint; highest bigint;
BEGIN
 owner := CASE WHEN TG_TABLE_NAME='fresh_mta_offlinerrrcoloursource'
   THEN (to_jsonb(NEW)->>'run_id')::uuid ELSE (to_jsonb(NEW)->>'receipt_id')::uuid END;
 SELECT row_count INTO expected FROM mta.fresh_mta_offlinerrrcoloursource WHERE run_id=owner;
 SELECT count(*),min(ordinal),max(ordinal) INTO actual,lowest,highest
 FROM mta.fresh_mta_offlinerrrcolourrow WHERE receipt_id=owner;
 IF expected IS NULL OR actual<>expected OR (actual>0 AND (lowest<>0 OR highest<>actual-1)) THEN
   RAISE EXCEPTION 'Complete offline RRR ordinal population required'; END IF;
 RETURN NULL;
END $$;
CREATE TRIGGER offline_rrr_source_insert BEFORE INSERT ON mta.fresh_mta_offlinerrrcoloursource
 FOR EACH ROW EXECUTE FUNCTION mta.guard_offline_rrr_insert();
CREATE TRIGGER offline_rrr_row_insert BEFORE INSERT ON mta.fresh_mta_offlinerrrcolourrow
 FOR EACH ROW EXECUTE FUNCTION mta.guard_offline_rrr_insert();
CREATE TRIGGER offline_rrr_source_immutable BEFORE UPDATE OR DELETE OR TRUNCATE ON mta.fresh_mta_offlinerrrcoloursource
 FOR EACH STATEMENT EXECUTE FUNCTION mta.deny_daily_source_mutation();
CREATE TRIGGER offline_rrr_row_immutable BEFORE UPDATE OR DELETE OR TRUNCATE ON mta.fresh_mta_offlinerrrcolourrow
 FOR EACH STATEMENT EXECUTE FUNCTION mta.deny_daily_source_mutation();
CREATE CONSTRAINT TRIGGER offline_rrr_source_population AFTER INSERT ON mta.fresh_mta_offlinerrrcoloursource
 DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION mta.check_offline_rrr_population();
CREATE CONSTRAINT TRIGGER offline_rrr_row_population AFTER INSERT ON mta.fresh_mta_offlinerrrcolourrow
 DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION mta.check_offline_rrr_population();
'''
REVERSE = r'''
DROP TRIGGER offline_rrr_row_population ON mta.fresh_mta_offlinerrrcolourrow;
DROP TRIGGER offline_rrr_source_population ON mta.fresh_mta_offlinerrrcoloursource;
DROP TRIGGER offline_rrr_row_immutable ON mta.fresh_mta_offlinerrrcolourrow;
DROP TRIGGER offline_rrr_source_immutable ON mta.fresh_mta_offlinerrrcoloursource;
DROP TRIGGER offline_rrr_row_insert ON mta.fresh_mta_offlinerrrcolourrow;
DROP TRIGGER offline_rrr_source_insert ON mta.fresh_mta_offlinerrrcoloursource;
DROP FUNCTION mta.check_offline_rrr_population();
DROP FUNCTION mta.guard_offline_rrr_insert();
'''


class Migration(migrations.Migration):
    dependencies = [('fresh_mta','0074_offline_rrr_sources')]
    operations = [migrations.RunSQL(FORWARD,REVERSE)]
