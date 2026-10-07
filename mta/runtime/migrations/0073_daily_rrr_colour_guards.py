"""Own only the additive, immutable two-run RRR colour source tables."""
from django.db import migrations

FORWARD = '''
CREATE FUNCTION mta.guard_daily_rrr_colour_insert() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE owner uuid;
BEGIN
 owner := CASE WHEN TG_TABLE_NAME='fresh_mta_dailyrrrcolourreceipt'
   THEN (to_jsonb(NEW)->>'run_id')::uuid ELSE (to_jsonb(NEW)->>'receipt_id')::uuid END;
 IF current_database()<>'daily_3006' OR
    current_setting('fresh.daily_rrr_colour_install',true) IS DISTINCT FROM owner::text OR
    owner NOT IN ('63c71fa7-944d-4547-a80f-2316a580d3c7'::uuid,
                  '17f0eb84-7b6d-40e9-a288-9441a4d7a860'::uuid) THEN
   RAISE EXCEPTION 'Owned explicit two-run RRR colour installation required'; END IF;
 IF TG_TABLE_NAME='fresh_mta_dailyrrrcolourreceipt' THEN
   PERFORM 1 FROM mta.fresh_mta_calculationrun R
    JOIN mta.fresh_mta_dailyuipublication P ON P.run_id=R.id
    JOIN mta.fresh_mta_dailyuiactivation A ON A.publication_id=R.id
    WHERE R.id=owner AND R.kind='DAILY_CHAIN' AND R.status='SUCCEEDED'
    AND R.output_digest=NEW.output_digest AND P.output_digest=NEW.output_digest
    AND P.status='READY' AND P.seal_digest=NEW.publication_seal
    AND P.source_digest=NEW.publication_source_digest
    AND A.publication_seal=P.seal_digest AND A.activation_digest=NEW.activation_digest
    AND R.output_digest=CASE WHEN owner='63c71fa7-944d-4547-a80f-2316a580d3c7'::uuid
      THEN 'f14806c1397661e2380ae59282db86bd1b5ca629351a61e73a3b09a407a2388b'
      ELSE 'e9777b060d27a77584fcc20734e5f1daba7fab38f8e1eaf99bec907cc278233f' END
    FOR UPDATE OF P;
   IF NOT FOUND THEN RAISE EXCEPTION 'RRR colour original publication identity differs'; END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE FUNCTION mta.check_daily_rrr_colour_population() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE owner uuid; expected bigint; actual bigint; lowest bigint; highest bigint;
BEGIN
 owner := CASE WHEN TG_TABLE_NAME='fresh_mta_dailyrrrcolourreceipt'
   THEN (to_jsonb(NEW)->>'run_id')::uuid ELSE (to_jsonb(NEW)->>'receipt_id')::uuid END;
 SELECT row_count INTO expected FROM mta.fresh_mta_dailyrrrcolourreceipt WHERE run_id=owner;
 SELECT count(*),min(ordinal),max(ordinal) INTO actual,lowest,highest
   FROM mta.fresh_mta_dailyrrrcolourrow WHERE receipt_id=owner;
 IF expected IS NULL OR actual<>expected OR
   (actual>0 AND (lowest<>0 OR highest<>actual-1)) THEN
   RAISE EXCEPTION 'RRR colour complete ordinal population required'; END IF;
 RETURN NULL;
END $$;
CREATE TRIGGER daily_rrr_receipt_insert BEFORE INSERT ON mta.fresh_mta_dailyrrrcolourreceipt
 FOR EACH ROW EXECUTE FUNCTION mta.guard_daily_rrr_colour_insert();
CREATE TRIGGER daily_rrr_row_insert BEFORE INSERT ON mta.fresh_mta_dailyrrrcolourrow
 FOR EACH ROW EXECUTE FUNCTION mta.guard_daily_rrr_colour_insert();
CREATE TRIGGER daily_rrr_receipt_immutable BEFORE UPDATE OR DELETE OR TRUNCATE ON mta.fresh_mta_dailyrrrcolourreceipt
 FOR EACH STATEMENT EXECUTE FUNCTION mta.deny_daily_source_mutation();
CREATE TRIGGER daily_rrr_row_immutable BEFORE UPDATE OR DELETE OR TRUNCATE ON mta.fresh_mta_dailyrrrcolourrow
 FOR EACH STATEMENT EXECUTE FUNCTION mta.deny_daily_source_mutation();
CREATE CONSTRAINT TRIGGER daily_rrr_receipt_population AFTER INSERT ON mta.fresh_mta_dailyrrrcolourreceipt
 DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION mta.check_daily_rrr_colour_population();
CREATE CONSTRAINT TRIGGER daily_rrr_row_population AFTER INSERT ON mta.fresh_mta_dailyrrrcolourrow
 DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION mta.check_daily_rrr_colour_population();
'''

REVERSE = '''
DROP TRIGGER daily_rrr_row_population ON mta.fresh_mta_dailyrrrcolourrow;
DROP TRIGGER daily_rrr_receipt_population ON mta.fresh_mta_dailyrrrcolourreceipt;
DROP TRIGGER daily_rrr_row_immutable ON mta.fresh_mta_dailyrrrcolourrow;
DROP TRIGGER daily_rrr_receipt_immutable ON mta.fresh_mta_dailyrrrcolourreceipt;
DROP TRIGGER daily_rrr_row_insert ON mta.fresh_mta_dailyrrrcolourrow;
DROP TRIGGER daily_rrr_receipt_insert ON mta.fresh_mta_dailyrrrcolourreceipt;
DROP FUNCTION mta.check_daily_rrr_colour_population();
DROP FUNCTION mta.guard_daily_rrr_colour_insert();
'''


class Migration(migrations.Migration):
    dependencies = [('fresh_mta', '0072_daily_rrr_colour')]
    operations = [migrations.RunSQL(FORWARD, REVERSE)]
