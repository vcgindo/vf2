"""One guarded stopped-sixth continuation; original attempts remain immutable."""
from django.db import migrations,models
import django.db.models.deletion

SQL=r'''
CREATE FUNCTION mta.finite_capture_prefix_digest(leaf uuid) RETURNS text LANGUAGE plpgsql STABLE
SET search_path=pg_catalog,mta SET TimeZone='UTC' SET DateStyle='ISO, YMD' AS $$
DECLARE payload jsonb; row_count integer; distinct_runs integer; terminal boolean;
BEGIN
 WITH RECURSIVE prefix(run_id,depth) AS (
  SELECT leaf,0
  UNION ALL SELECT C.origin_id,P.depth+1 FROM prefix P
    JOIN mta.fresh_mta_mdmdailyinputcapture C ON C.run_id=P.run_id
    WHERE P.depth<6 AND C.origin_id IS NOT NULL),
 records AS (
  SELECT P.depth,R.id,C.origin_id,jsonb_build_object('run',to_jsonb(R),
    'capture',to_jsonb(C),'attempt',to_jsonb(A)) AS body
  FROM prefix P JOIN mta.fresh_mta_calculationrun R ON R.id=P.run_id
  JOIN mta.fresh_mta_mdmdailyinputcapture C ON C.run_id=R.id
  JOIN mta.fresh_mta_dailyfeedattempt A ON A.run_id=R.id)
 SELECT jsonb_agg(body ORDER BY depth),count(*),count(DISTINCT id),
   bool_or(depth=6 AND origin_id IS NULL)
 INTO payload,row_count,distinct_runs,terminal FROM records;
 IF row_count<>7 OR distinct_runs<>7 OR terminal IS DISTINCT FROM true THEN
  RAISE EXCEPTION 'Finite digest requires seven complete canonical metadata records';
 END IF;
 RETURN encode(sha256(convert_to(payload::text,'UTF8')),'hex');
END $$;
REVOKE ALL ON FUNCTION mta.finite_capture_prefix_digest(uuid) FROM PUBLIC;
CREATE FUNCTION mta.finite_capture_attempt_guard() RETURNS trigger LANGUAGE plpgsql
SET search_path=pg_catalog,mta AS $$
DECLARE parent mta.fresh_mta_dailyfeedattempt; child mta.fresh_mta_calculationrun;
 ancestor mta.fresh_mta_calculationrun; cap mta.fresh_mta_mdmdailyinputcapture;
 priorcap mta.fresh_mta_mdmdailyinputcapture; owner mta.fresh_mta_dailyfeedattempt;
 seen uuid[]:=ARRAY[]::uuid[]; at_run uuid; expected_schema text; expected_manifest text;
 i integer; target regclass; populated boolean;
BEGIN
 IF TG_OP='DELETE' THEN
  IF OLD.recovery_origin_id IS NOT NULL THEN RAISE EXCEPTION 'Finite attempt is retained'; END IF;
  RETURN OLD;
 END IF;
 IF TG_OP='UPDATE' THEN
  IF NEW.recovery_origin_id IS DISTINCT FROM OLD.recovery_origin_id THEN
   RAISE EXCEPTION 'Finite origin cannot be rebound'; END IF;
  IF OLD.recovery_origin_id IS NOT NULL AND
    (to_jsonb(NEW)-ARRAY['status','phase','error','updated_at','prior_selection_digest','candidate_selection_digest'])
     IS DISTINCT FROM
    (to_jsonb(OLD)-ARRAY['status','phase','error','updated_at','prior_selection_digest','candidate_selection_digest']) THEN
   RAISE EXCEPTION 'Finite attempt identity is immutable'; END IF;
  IF OLD.recovery_origin_id IS NOT NULL THEN
   SELECT * INTO STRICT child FROM mta.fresh_mta_calculationrun WHERE id=NEW.run_id;
   IF (OLD.status='FAILED' AND NEW.status<>'FAILED')
      OR (OLD.status='PUBLISHED' AND NEW.status<>'PUBLISHED')
      OR NEW.status NOT IN ('RUNNING','FAILED','COMMITTED','PREPARED','PUBLISHED')
      OR (NEW.status='RUNNING' AND (OLD.status<>'RUNNING' OR child.status<>'RUNNING' OR NEW.phase<>'CALCULATE'))
      OR (NEW.status='FAILED' AND child.status<>'FAILED')
      OR (NEW.status IN ('COMMITTED','PREPARED','PUBLISHED') AND child.status<>'SUCCEEDED') THEN
    RAISE EXCEPTION 'Finite attempt lifecycle differs from its own run'; END IF;
  END IF;
  RETURN NEW;
 END IF;
 IF NEW.recovery_origin_id IS NULL THEN RETURN NEW; END IF;
 SELECT * INTO STRICT parent FROM mta.fresh_mta_dailyfeedattempt WHERE id=NEW.recovery_origin_id FOR UPDATE;
 SELECT * INTO STRICT child FROM mta.fresh_mta_calculationrun WHERE id=NEW.run_id FOR UPDATE;
 IF parent.id=NEW.id OR parent.recovery_origin_id IS NOT NULL OR parent.run_id=NEW.run_id
    OR parent.status<>'RUNNING' OR parent.phase<>'CALCULATE' OR parent.accepted_facts<>'{}'::jsonb
    OR NEW.status<>'RUNNING' OR NEW.phase<>'CALCULATE' OR NEW.accepted_facts<>'{}'::jsonb
    OR ROW(NEW.initialization_id,NEW.business_date,NEW.predecessor_id,NEW.predecessor_output_digest,
           NEW.batch_id,NEW.batch_digest,NEW.binding_digest,NEW.input_sha256,NEW.certification_id,NEW.master_revision_id)
       IS DISTINCT FROM
       ROW(parent.initialization_id,parent.business_date,parent.predecessor_id,parent.predecessor_output_digest,
           parent.batch_id,parent.batch_digest,parent.binding_digest,parent.input_sha256,parent.certification_id,parent.master_revision_id)
    OR NEW.archive_path=parent.archive_path OR NEW.request_key=parent.request_key
    OR child.status<>'RUNNING' OR child.kind<>'DAILY_CHAIN' OR child.evidence_mode<>'production'
    OR child.business_date IS DISTINCT FROM parent.business_date
    OR child.predecessor_id IS DISTINCT FROM parent.predecessor_id
    OR child.input_payload->>'schema' IS DISTINCT FROM 'fresh-captured-input-reference-v3'
    OR child.input_payload->>'origin_run_id' IS DISTINCT FROM parent.run_id::text
    OR child.input_payload->>'origin_attempt_id' IS DISTINCT FROM parent.attempt_id::text
    OR child.input_payload->>'execution_revision' IS DISTINCT FROM child.execution_revision
    OR NOT COALESCE(child.input_payload->>'packaged_source' ~ '^[0-9a-f]{40}$',false)
    OR NOT COALESCE(child.input_payload->>'prefix_digest' ~ '^[0-9a-f]{64}$',false)
    OR child.execution_revision IS DISTINCT FROM 'native-finite-'||(child.input_payload->>'packaged_source')
    OR child.input_payload->'images' IS DISTINCT FROM '{}'::jsonb THEN
   RAISE EXCEPTION 'Finite attempt requires exact stopped parent and packaged reference';
 END IF;
 IF NOT EXISTS(SELECT 1 FROM fresh_control.ingestion_release_authority A
    JOIN mta.fresh_mta_initializationcertification C ON C.initialization_id=A.initialization_id
    WHERE A.initialization_id=NEW.initialization_id AND C.id=NEW.certification_id
      AND A.body->>'target_commit'=child.input_payload->>'packaged_source'
      AND A.body->>'certification_digest'=C.receipt_digest
      AND (A.target_release=C.release_digest OR EXISTS(
        SELECT 1 FROM mta.fresh_mta_ingestionreleasecompatibility K
        WHERE K.initialization_id=A.initialization_id AND K.target_release=A.target_release
          AND K.target_commit=A.body->>'target_commit' AND K.certification_digest=C.receipt_digest))) THEN
  RAISE EXCEPTION 'Finite attempt requires registrar-bound packaged schema admission';
 END IF;
 SELECT * INTO STRICT priorcap FROM mta.fresh_mta_mdmdailyinputcapture WHERE run_id=NEW.run_id;
 IF priorcap.origin_id IS DISTINCT FROM parent.run_id OR priorcap.status<>'CAPTURED' THEN
  RAISE EXCEPTION 'Finite attempt requires its canonical retry capture'; END IF;
 at_run=parent.run_id; expected_manifest=child.input_payload->>'origin_manifest_digest';
 FOR i IN 0..6 LOOP
  IF at_run IS NULL OR at_run=ANY(seen) THEN RAISE EXCEPTION 'Finite prefix depth/cycle differs'; END IF;
  seen=array_append(seen,at_run);
  SELECT * INTO STRICT ancestor FROM mta.fresh_mta_calculationrun WHERE id=at_run FOR UPDATE;
  SELECT * INTO STRICT cap FROM mta.fresh_mta_mdmdailyinputcapture WHERE run_id=at_run FOR UPDATE;
  SELECT * INTO STRICT owner FROM mta.fresh_mta_dailyfeedattempt WHERE run_id=at_run FOR UPDATE;
  expected_schema=CASE WHEN i<5 THEN 'fresh-captured-input-reference-v2'
      WHEN i=5 THEN 'fresh-captured-input-reference-v1' ELSE 'fresh-daily-input-manifest-v3' END;
  IF ancestor.status IS DISTINCT FROM (CASE WHEN i=0 THEN 'RUNNING' ELSE 'FAILED' END)
    OR owner.status IS DISTINCT FROM (CASE WHEN i=0 THEN 'RUNNING' ELSE 'FAILED' END)
    OR owner.recovery_origin_id IS NOT NULL OR cap.status<>'CAPTURED'
    OR ancestor.kind<>'DAILY_CHAIN' OR ancestor.evidence_mode<>'production'
    OR ancestor.input_payload->>'schema' IS DISTINCT FROM expected_schema
    OR ancestor.business_date IS DISTINCT FROM child.business_date
    OR ancestor.predecessor_id IS DISTINCT FROM child.predecessor_id
    OR ancestor.input_digest IS DISTINCT FROM child.input_digest
    OR ancestor.input_manifest_digest IS DISTINCT FROM expected_manifest
    OR owner.initialization_id IS DISTINCT FROM NEW.initialization_id
    OR owner.input_sha256 IS DISTINCT FROM NEW.input_sha256 OR owner.batch_digest IS DISTINCT FROM NEW.batch_digest
    OR ancestor.output_digest<>'' OR ancestor.production_digest<>'' OR ancestor.output_roster<>'[]'::jsonb
    OR cap.source_id IS DISTINCT FROM priorcap.source_id
    OR cap.request_digest IS DISTINCT FROM priorcap.request_digest
    OR cap.revision_digest IS DISTINCT FROM priorcap.revision_digest
    OR (SELECT count(*) FROM mta.fresh_mta_mdmdailyinputcapture WHERE origin_id=cap.run_id)<>1 THEN
   RAISE EXCEPTION 'Finite exact six-wrapper prefix differs'; END IF;
  IF EXISTS(SELECT 1 FROM mta.fresh_mta_checkpoint WHERE run_id=at_run)
     OR EXISTS(SELECT 1 FROM mta.fresh_mta_runcommand WHERE run_id=at_run)
     OR EXISTS(SELECT 1 FROM mta.fresh_mta_calculationrun WHERE predecessor_id=at_run) THEN
   RAISE EXCEPTION 'Finite prefix has downstream state'; END IF;
  IF i=0 THEN
   FOR target IN SELECT C.oid::regclass FROM pg_class C JOIN pg_namespace N ON N.oid=C.relnamespace
      JOIN pg_attribute A ON A.attrelid=C.oid AND A.attname='vf_run_id' AND NOT A.attisdropped
      WHERE N.nspname='mta_state' AND C.relkind IN ('r','p') LOOP
    EXECUTE format('SELECT EXISTS(SELECT 1 FROM %s WHERE vf_run_id=$1)',target) INTO populated USING at_run;
    IF populated THEN RAISE EXCEPTION 'Finite stopped leaf contains typed result rows'; END IF;
   END LOOP;
   FOR target IN SELECT C.oid::regclass FROM pg_class C JOIN pg_namespace N ON N.oid=C.relnamespace
     WHERE N.nspname='mta' AND C.relname=ANY(ARRAY['fresh_mta_pickprojection','fresh_mta_excessprojection',
       'fresh_mta_fulfillmentprojection','fresh_mta_expediteprojection','fresh_mta_pickpostprojection',
       'fresh_mta_dailysourcereceipt','fresh_mta_offlinerrrcoloursource',
       'fresh_mta_dailyreportgeneration','fresh_mta_dailyreportorderroutesource','fresh_mta_dailyuipublication']) LOOP
    EXECUTE format('SELECT EXISTS(SELECT 1 FROM %s WHERE run_id=$1)',target) INTO populated USING at_run;
    IF populated THEN RAISE EXCEPTION 'Finite stopped leaf contains output receipts'; END IF;
   END LOOP;
  END IF;
  IF i=0 AND child.input_payload->>'origin_manifest_digest' IS DISTINCT FROM ancestor.input_manifest_digest THEN
   RAISE EXCEPTION 'Finite terminal manifest differs'; END IF;
  IF i=6 THEN
   IF cap.origin_id IS NOT NULL OR NOT (owner.accepted_facts<>'{}'::jsonb)
      OR child.input_payload->>'physical_origin_run_id' IS DISTINCT FROM ancestor.id::text
      OR child.input_payload->>'physical_origin_manifest_digest' IS DISTINCT FROM ancestor.input_manifest_digest THEN
    RAISE EXCEPTION 'Finite physical origin differs'; END IF;
  ELSE
   IF ancestor.input_payload->>'origin_run_id' IS DISTINCT FROM cap.origin_id::text THEN
    RAISE EXCEPTION 'Finite reference/capture edge differs'; END IF;
  END IF;
  priorcap=cap; at_run=cap.origin_id; expected_manifest=ancestor.input_payload->>'origin_manifest_digest';
 END LOOP;
 IF child.input_payload->>'prefix_digest' IS DISTINCT FROM mta.finite_capture_prefix_digest(parent.run_id) THEN
  RAISE EXCEPTION 'Finite captured complete metadata digest differs';
 END IF;
 RETURN NEW;
END $$;
REVOKE ALL ON FUNCTION mta.finite_capture_attempt_guard() FROM PUBLIC;
CREATE TRIGGER finite_capture_attempt BEFORE INSERT OR UPDATE OR DELETE ON mta.fresh_mta_dailyfeedattempt
 FOR EACH ROW EXECUTE FUNCTION mta.finite_capture_attempt_guard();

CREATE FUNCTION mta.finite_capture_preserved_guard() RETURNS trigger LANGUAGE plpgsql
SET search_path=pg_catalog,mta AS $$
DECLARE run_key uuid;
BEGIN
 run_key=CASE WHEN TG_TABLE_NAME='fresh_mta_calculationrun' THEN (to_jsonb(OLD)->>'id')::uuid
              ELSE (to_jsonb(OLD)->>'run_id')::uuid END;
 IF EXISTS(WITH RECURSIVE prefix(run_id,depth) AS (
    SELECT P.run_id,0 FROM mta.fresh_mta_dailyfeedattempt C
      JOIN mta.fresh_mta_dailyfeedattempt P ON P.id=C.recovery_origin_id
    UNION ALL SELECT M.origin_id,P.depth+1 FROM prefix P
      JOIN mta.fresh_mta_mdmdailyinputcapture M ON M.run_id=P.run_id
      WHERE P.depth<6 AND M.origin_id IS NOT NULL)
    SELECT 1 FROM prefix WHERE run_id=run_key) THEN
  RAISE EXCEPTION 'Finite captured original metadata is immutable';
 END IF;
 IF TG_OP='DELETE' THEN RETURN OLD; END IF;
 RETURN NEW;
END $$;
REVOKE ALL ON FUNCTION mta.finite_capture_preserved_guard() FROM PUBLIC;
'''
for table in ('calculationrun','mdmdailyinputcapture','dailyfeedattempt'):
    SQL+='CREATE TRIGGER finite_capture_preserved BEFORE UPDATE OR DELETE ON mta.fresh_mta_'+table+' FOR EACH ROW EXECUTE FUNCTION mta.finite_capture_preserved_guard();\n'

REVERSE="DO $$ BEGIN IF EXISTS(SELECT 1 FROM mta.fresh_mta_dailyfeedattempt WHERE recovery_origin_id IS NOT NULL) THEN RAISE EXCEPTION 'Finite admission cannot be downgraded after an attempt'; END IF; END $$;\n"
for table in ('calculationrun','mdmdailyinputcapture','dailyfeedattempt'):
    REVERSE+='DROP TRIGGER finite_capture_preserved ON mta.fresh_mta_'+table+';\n'
REVERSE+='DROP TRIGGER finite_capture_attempt ON mta.fresh_mta_dailyfeedattempt; DROP FUNCTION mta.finite_capture_preserved_guard(); DROP FUNCTION mta.finite_capture_attempt_guard();'
REVERSE+='DROP FUNCTION mta.finite_capture_prefix_digest(uuid);'


class Migration(migrations.Migration):
    dependencies=[('fresh_mta','0162_derived_trend_ownership')]
    operations=[
        migrations.AddField(model_name='dailyfeedattempt',name='recovery_origin',
            field=models.ForeignKey(blank=True,null=True,on_delete=django.db.models.deletion.PROTECT,
                related_name='finite_recoveries',to='fresh_mta.dailyfeedattempt')),
        migrations.RemoveConstraint(model_name='dailyfeedattempt',name='csv_one_live_initialized_date'),
        migrations.AddConstraint(model_name='dailyfeedattempt',constraint=models.UniqueConstraint(
            fields=('initialization','business_date'),condition=models.Q(status__in=('RUNNING','COMMITTED','PREPARED','PUBLISHED'),recovery_origin__isnull=True),name='csv_one_live_initialized_date')),
        migrations.AddConstraint(model_name='dailyfeedattempt',constraint=models.UniqueConstraint(
            fields=('recovery_origin',),condition=models.Q(recovery_origin__isnull=False),name='csv_one_finite_origin')),
        migrations.AddConstraint(model_name='dailyfeedattempt',constraint=models.UniqueConstraint(
            fields=('initialization','business_date'),condition=models.Q(recovery_origin__isnull=False),name='csv_one_finite_initialized_date')),
        migrations.RunSQL(SQL,REVERSE),
    ]
