"""Fenced calculation claims and one-transaction sealed phase acceptance."""
from importlib import import_module
from django.db import migrations

_storage = import_module('mta.runtime.migrations.0175_prepared_phase_rows')
SQL = r'''
CREATE FUNCTION mta.scope_head(target uuid) RETURNS TABLE(phase text,digest text)
 LANGUAGE sql STABLE SET search_path=pg_catalog,mta AS $body$
 SELECT coalesce(H.phase,'START'),coalesce(H.digest,'') FROM (SELECT 1) V
 LEFT JOIN LATERAL (SELECT P.phase,P.digest FROM mta.fresh_mta_runphaseacceptance P
 WHERE P.run_id=target AND P.state_sealed
 ORDER BY CASE P.phase WHEN 'DBM' THEN 3 WHEN 'BPR' THEN 2 ELSE 1 END DESC LIMIT 1) H ON true
$body$;
CREATE FUNCTION mta.guard_scope_attempt() RETURNS trigger LANGUAGE plpgsql
 SET search_path=pg_catalog,mta AS $guard$
DECLARE parent mta.fresh_mta_calculationrun; prior_attempt mta.fresh_mta_runscopeattempt;
 actual_phase text; actual_digest text;
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'Scoped attempts are retained'; END IF;
 SELECT * INTO parent FROM mta.fresh_mta_calculationrun WHERE id=NEW.run_id FOR UPDATE;
 IF NOT FOUND OR parent.kind<>'DAILY_CHAIN' THEN RAISE EXCEPTION 'Scoped daily owner absent'; END IF;
 IF TG_OP='UPDATE' THEN
  IF OLD.status<>'ACTIVE' OR NEW.status NOT IN ('FAILED','RELEASED')
   OR NEW.finished_at IS NULL
   OR (to_jsonb(OLD)-ARRAY['status','failure','finished_at']) IS DISTINCT FROM
      (to_jsonb(NEW)-ARRAY['status','failure','finished_at'])
   OR (current_setting('fresh.scope_worker',true) IS DISTINCT FROM OLD.worker_token::text
       AND NOT (NEW.status='FAILED' AND current_setting('fresh.scope_fence',true)=OLD.id::text))
   OR jsonb_typeof(NEW.failure)<>'object' OR octet_length(NEW.failure::text)>16384 THEN
   RAISE EXCEPTION 'Scoped attempt permits only its fenced terminal transition'; END IF;
  IF NEW.status='RELEASED' THEN
   SELECT H.phase,H.digest INTO actual_phase,actual_digest FROM mta.scope_head(NEW.run_id) H;
   IF NEW.failure<>'{}'::jsonb OR NOT (
    NEW.scope='UptoBPR' AND actual_phase='BPR' OR NEW.scope='UptoDBM' AND actual_phase='DBM'
    OR NEW.scope IN ('PostBPR','PostDBM') AND parent.status='SUCCEEDED') THEN
    RAISE EXCEPTION 'Worker release requires its calculation target'; END IF;
  ELSIF NEW.failure='{}'::jsonb THEN RAISE EXCEPTION 'Failed attempt requires retained diagnostic'; END IF;
  RETURN NEW;
 END IF;
 IF parent.status<>'RUNNING' OR parent.output_digest<>''
  OR NEW.input_digest<>parent.input_digest OR NEW.input_manifest_digest<>parent.input_manifest_digest
  OR NEW.input_digest !~ '^[0-9a-f]{64}$' OR NEW.input_manifest_digest !~ '^[0-9a-f]{64}$'
  OR NEW.compatibility_digest !~ '^[0-9a-f]{64}$' OR NEW.action_revision<>0
  OR NEW.scope NOT IN ('UptoBPR','UptoDBM','PostBPR','PostDBM')
  OR NEW.status<>'ACTIVE' OR NEW.failure<>'{}'::jsonb OR NEW.finished_at IS NOT NULL
  OR length(NEW.command_key)=0 OR length(NEW.worker_reference)=0 THEN
  RAISE EXCEPTION 'Scoped claim requires exact uncompleted captured input'; END IF;
 IF NOT EXISTS(SELECT 1 FROM mta.fresh_mta_mdmdailyinputcapture C
   WHERE C.run_id=NEW.run_id AND C.status='CAPTURED') THEN
  RAISE EXCEPTION 'Scoped claim requires its live captured day'; END IF;
 SELECT H.phase,H.digest INTO actual_phase,actual_digest FROM mta.scope_head(NEW.run_id) H;
 IF (NEW.expected_phase,NEW.expected_receipt_digest) IS DISTINCT FROM (actual_phase,actual_digest) THEN
  RAISE EXCEPTION 'Scoped expected accepted phase changed'; END IF;
 IF NEW.recovery_of_id IS NULL THEN
  IF NEW.attempt_no<>1 OR NOT (
    NEW.scope IN ('UptoBPR','UptoDBM') AND actual_phase='START'
    OR NEW.scope='PostBPR' AND actual_phase='BPR' OR NEW.scope='PostDBM' AND actual_phase='DBM') THEN
   RAISE EXCEPTION 'Scope does not start at its named boundary'; END IF;
 ELSE
  SELECT * INTO prior_attempt FROM mta.fresh_mta_runscopeattempt WHERE id=NEW.recovery_of_id FOR SHARE;
  IF NOT FOUND OR prior_attempt.status<>'FAILED' OR prior_attempt.run_id<>NEW.run_id
   OR NEW.attempt_no<>prior_attempt.attempt_no+1
   OR (NEW.command_key,NEW.scope,NEW.input_digest,NEW.input_manifest_digest,NEW.compatibility_digest,NEW.action_revision)
      IS DISTINCT FROM (prior_attempt.command_key,prior_attempt.scope,prior_attempt.input_digest,
                        prior_attempt.input_manifest_digest,prior_attempt.compatibility_digest,prior_attempt.action_revision)
   OR NOT (NEW.scope='UptoBPR' AND actual_phase IN ('START','PRE_BPR','BPR')
    OR NEW.scope='UptoDBM' AND actual_phase IN ('START','PRE_BPR','BPR','DBM')
    OR NEW.scope='PostBPR' AND actual_phase IN ('BPR','DBM') OR NEW.scope='PostDBM' AND actual_phase='DBM') THEN
   RAISE EXCEPTION 'Recovery must retain the failed command and accepted prefix'; END IF;
 END IF;
 RETURN NEW;
END
$guard$;
CREATE FUNCTION mta.guard_phase_acceptance() RETURNS trigger LANGUAGE plpgsql
 SET search_path=pg_catalog,mta AS $guard$
DECLARE claim mta.fresh_mta_runscopeattempt; parent mta.fresh_mta_calculationrun;
 captured mta.fresh_mta_mdmdailyinputcapture; image mta.fresh_mta_dailyphasesnapshot;
 actual_phase text; actual_digest text; previous_image bigint;
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'Accepted phase evidence is retained'; END IF;
 SELECT * INTO parent FROM mta.fresh_mta_calculationrun WHERE id=NEW.run_id FOR UPDATE;
 SELECT * INTO STRICT claim FROM mta.fresh_mta_runscopeattempt WHERE id=NEW.attempt_id FOR UPDATE;
 SELECT * INTO STRICT captured FROM mta.fresh_mta_mdmdailyinputcapture WHERE run_id=NEW.run_id FOR UPDATE;
 IF parent.status<>'RUNNING' OR parent.kind<>'DAILY_CHAIN' OR claim.status<>'ACTIVE'
  OR claim.run_id<>NEW.run_id OR claim.input_digest<>parent.input_digest
  OR claim.input_manifest_digest<>parent.input_manifest_digest
  OR captured.status<>'CAPTURED' OR captured.source_id<>NEW.source_id
  OR NEW.input_digest<>parent.input_digest OR NEW.capture_digest<>captured.revision_digest
  OR current_setting('fresh.scope_worker',true) IS DISTINCT FROM claim.worker_token::text
  OR current_setting('fresh.scope_phase',true) IS DISTINCT FROM NEW.id::text THEN
  RAISE EXCEPTION 'Phase acceptance requires its exact active worker/capture'; END IF;
 IF TG_OP='INSERT' THEN
  IF NEW.state_sealed OR NEW.snapshot_id IS NOT NULL OR NEW.metadata<>'{}'::jsonb
   OR NEW.digest<>'' OR NEW.accepted_at IS NOT NULL THEN
   RAISE EXCEPTION 'Phase acceptance must begin unsealed'; END IF;
  SELECT H.phase,H.digest INTO actual_phase,actual_digest FROM mta.scope_head(NEW.run_id) H;
  IF NOT (NEW.phase='PRE_BPR' AND actual_phase='START' AND claim.scope IN ('UptoBPR','UptoDBM')
   OR NEW.phase='BPR' AND actual_phase='PRE_BPR' AND claim.scope IN ('UptoBPR','UptoDBM')
   OR NEW.phase='DBM' AND actual_phase='BPR' AND claim.scope IN ('UptoDBM','PostBPR')) THEN
   RAISE EXCEPTION 'Business phases must follow the approved scope sequence'; END IF;
 ELSE
  IF OLD.state_sealed OR NOT NEW.state_sealed
   OR (to_jsonb(OLD)-ARRAY['snapshot_id','metadata','digest','state_sealed','accepted_at']) IS DISTINCT FROM
      (to_jsonb(NEW)-ARRAY['snapshot_id','metadata','digest','state_sealed','accepted_at']) THEN
   RAISE EXCEPTION 'Phase acceptance may seal exactly once'; END IF;
  SELECT * INTO STRICT image FROM mta.fresh_mta_dailyphasesnapshot WHERE id=NEW.snapshot_id;
  SELECT P.snapshot_id INTO previous_image FROM mta.fresh_mta_runphaseacceptance P
   WHERE P.run_id=NEW.run_id AND P.state_sealed ORDER BY
    CASE P.phase WHEN 'DBM' THEN 3 WHEN 'BPR' THEN 2 ELSE 1 END DESC LIMIT 1;
  IF image.run_id<>NEW.run_id OR image.phase<>NEW.phase OR image.acceptance_id IS DISTINCT FROM NEW.id
   OR image.input_digest<>NEW.input_digest OR image.parent_id IS DISTINCT FROM previous_image
   OR NEW.accepted_at IS NULL OR NEW.digest !~ '^[0-9a-f]{64}$'
   OR NEW.metadata->>'schema' IS DISTINCT FROM 'fresh-phase-acceptance-v1'
   OR NEW.metadata->>'snapshot_digest' IS DISTINCT FROM image.state_digest
   OR NEW.metadata->>'compatibility_digest' IS DISTINCT FROM claim.compatibility_digest
   OR coalesce(NEW.metadata->>'effect_digest','') !~ '^[0-9a-f]{64}$'
   OR jsonb_typeof(NEW.metadata->'partitions') IS DISTINCT FROM 'array'
   OR octet_length(NEW.metadata::text)>65536 THEN
   RAISE EXCEPTION 'Sealed phase requires exact typed state/effect evidence'; END IF;
 END IF;
 RETURN NEW;
END
$guard$;
CREATE FUNCTION mta.require_phase_acceptance_complete() RETURNS trigger LANGUAGE plpgsql
 SET search_path=pg_catalog,mta AS $guard$
BEGIN
 IF NOT EXISTS(SELECT 1 FROM mta.fresh_mta_runphaseacceptance P WHERE P.id=NEW.id
  AND P.state_sealed AND P.snapshot_id IS NOT NULL AND P.digest<>'' AND P.accepted_at IS NOT NULL) THEN
  RAISE EXCEPTION 'Phase state and effects must seal before commit'; END IF;
 RETURN NULL;
END
$guard$;
CREATE FUNCTION mta.guard_scoped_run_input() RETURNS trigger LANGUAGE plpgsql
 SET search_path=pg_catalog,mta AS $guard$
BEGIN
 IF EXISTS(SELECT 1 FROM mta.fresh_mta_runscopeattempt A WHERE A.run_id=OLD.id) THEN
  IF TG_OP='DELETE' OR (to_jsonb(OLD)-ARRAY['status','output_digest','production_digest','production_manifest',
     'output_roster','failure','completed_at']) IS DISTINCT FROM
    (to_jsonb(NEW)-ARRAY['status','output_digest','production_digest','production_manifest',
     'output_roster','failure','completed_at']) THEN
   RAISE EXCEPTION 'Scoped logical input and lineage are frozen'; END IF;
  IF NEW.status IS DISTINCT FROM OLD.status THEN
   RAISE EXCEPTION 'Scoped final completion requires its qualified final owner'; END IF;
  IF to_jsonb(OLD) IS DISTINCT FROM to_jsonb(NEW) AND NOT EXISTS(
    SELECT 1 FROM mta.fresh_mta_runscopeattempt A WHERE A.run_id=OLD.id AND A.status='ACTIVE'
     AND A.worker_token::text=current_setting('fresh.scope_worker',true)) THEN
   RAISE EXCEPTION 'Scoped run updates require its current worker'; END IF;
 END IF;
 RETURN NEW;
END
$guard$;
CREATE FUNCTION mta.guard_scoped_capture_status() RETURNS trigger LANGUAGE plpgsql
 SET search_path=pg_catalog,mta AS $guard$
BEGIN
 IF NEW.status IS DISTINCT FROM OLD.status AND EXISTS(
  SELECT 1 FROM mta.fresh_mta_runscopeattempt A WHERE A.run_id=OLD.run_id) THEN
  RAISE EXCEPTION 'Scoped capture consumption requires its qualified final owner'; END IF;
 RETURN NEW;
END
$guard$;
CREATE FUNCTION mta.deny_scope_truncate() RETURNS trigger LANGUAGE plpgsql
 SET search_path=pg_catalog,mta AS $guard$
BEGIN RAISE EXCEPTION 'Scoped execution evidence cannot be truncated'; END
$guard$;
CREATE TRIGGER scope_attempt_owner BEFORE INSERT OR UPDATE OR DELETE
 ON mta.fresh_mta_runscopeattempt FOR EACH ROW EXECUTE FUNCTION mta.guard_scope_attempt();
CREATE TRIGGER phase_acceptance_owner BEFORE INSERT OR UPDATE OR DELETE
 ON mta.fresh_mta_runphaseacceptance FOR EACH ROW EXECUTE FUNCTION mta.guard_phase_acceptance();
CREATE CONSTRAINT TRIGGER phase_acceptance_complete AFTER INSERT OR UPDATE
 ON mta.fresh_mta_runphaseacceptance DEFERRABLE INITIALLY DEFERRED
 FOR EACH ROW EXECUTE FUNCTION mta.require_phase_acceptance_complete();
CREATE TRIGGER scoped_run_input BEFORE UPDATE OR DELETE ON mta.fresh_mta_calculationrun
 FOR EACH ROW EXECUTE FUNCTION mta.guard_scoped_run_input();
CREATE TRIGGER scoped_capture_status BEFORE UPDATE ON mta.fresh_mta_mdmdailyinputcapture
 FOR EACH ROW EXECUTE FUNCTION mta.guard_scoped_capture_status();
'''

_snapshot = _storage._prepared_snapshot.replace(
    " IF NOT FOUND OR parent.kind<>'DAILY_CHAIN'", """ IF EXISTS(SELECT 1 FROM mta.fresh_mta_runscopeattempt A WHERE A.run_id=NEW.run_id)
  OR NEW.acceptance_id IS NOT NULL THEN
  PERFORM 1 FROM mta.fresh_mta_runphaseacceptance P JOIN mta.fresh_mta_runscopeattempt A ON A.id=P.attempt_id
   WHERE P.id=NEW.acceptance_id AND P.run_id=NEW.run_id AND P.phase=NEW.phase AND NOT P.state_sealed
    AND A.status='ACTIVE' AND P.id::text=current_setting('fresh.scope_phase',true)
    AND A.worker_token::text=current_setting('fresh.scope_worker',true);
  IF NOT FOUND THEN RAISE EXCEPTION 'Scoped snapshot requires its pending acceptance unit'; END IF;
 END IF;
 IF parent.id IS NULL OR parent.kind<>'DAILY_CHAIN'""")
_rows = _storage._prepared_rows.replace(
    '    CONTINUE;', """    IF EXISTS(SELECT 1 FROM mta.fresh_mta_runscopeattempt A
       JOIN mta.fresh_mta_calculationrun R ON R.id=A.run_id
       WHERE A.run_id=item.owner AND R.status='RUNNING')
       AND item.image NOT LIKE 'input/%' AND item.image NOT LIKE 'batch/%' THEN
     RAISE EXCEPTION 'Scoped terminal writing requires its qualified final owner'; END IF;
    CONTINUE;""", 1).replace(
    "   IF NOT FOUND OR EXISTS(SELECT 1 FROM mta.fresh_mta_dailyphasesnapshot S", """   IF NOT FOUND THEN RAISE EXCEPTION 'Phase rows require their running day'; END IF;
   IF EXISTS(SELECT 1 FROM mta.fresh_mta_runscopeattempt A WHERE A.run_id=owner) THEN
    PERFORM 1 FROM mta.fresh_mta_runphaseacceptance P JOIN mta.fresh_mta_runscopeattempt A ON A.id=P.attempt_id
     WHERE P.run_id=owner AND P.phase=target_phase AND NOT P.state_sealed AND A.status='ACTIVE'
      AND P.id::text=current_setting('fresh.scope_phase',true)
      AND A.worker_token::text=current_setting('fresh.scope_worker',true);
    IF NOT FOUND THEN RAISE EXCEPTION 'Scoped rows require their fenced phase acceptance'; END IF;
   END IF;
   IF EXISTS(SELECT 1 FROM mta.fresh_mta_dailyphasesnapshot S""")
SQL += 'CREATE OR REPLACE FUNCTION mta.guard_phase_snapshot()'+_snapshot+'$guard$;\n'+_rows
for name in ('scope_head(uuid)', 'guard_scope_attempt()', 'guard_phase_acceptance()',
             'require_phase_acceptance_complete()', 'guard_scoped_run_input()',
             'guard_scoped_capture_status()', 'deny_scope_truncate()'):
    SQL += 'REVOKE ALL ON FUNCTION mta.'+name+' FROM PUBLIC;\n'
for table in ('fresh_mta_runscopeattempt', 'fresh_mta_runphaseacceptance'):
    SQL += ('CREATE TRIGGER scope_no_truncate BEFORE TRUNCATE ON mta.'+table+
            ' FOR EACH STATEMENT EXECUTE FUNCTION mta.deny_scope_truncate();\n')
    for operation, references in (('INSERT', 'NEW TABLE AS new_rows'),
            ('UPDATE', 'OLD TABLE AS old_rows NEW TABLE AS new_rows'),
            ('DELETE', 'OLD TABLE AS old_rows'), ('TRUNCATE', '')):
        SQL += ('CREATE TRIGGER ingestion_watch_'+operation.lower()+' AFTER '+operation+
            ' ON mta.'+table+(' REFERENCING '+references if references else '')+
            " FOR EACH STATEMENT EXECUTE FUNCTION mta.ingestion_watch('operational');\n")

REVERSE = """DO $pre$ BEGIN
 IF EXISTS(SELECT 1 FROM mta.fresh_mta_runscopeattempt) OR EXISTS(SELECT 1 FROM mta.fresh_mta_runphaseacceptance)
 THEN RAISE EXCEPTION 'Scoped evidence requires a compatible forward release'; END IF;
END $pre$;
DROP TRIGGER scoped_run_input ON mta.fresh_mta_calculationrun;
DROP TRIGGER scoped_capture_status ON mta.fresh_mta_mdmdailyinputcapture;
DROP TRIGGER scope_attempt_owner ON mta.fresh_mta_runscopeattempt;
DROP TRIGGER phase_acceptance_owner ON mta.fresh_mta_runphaseacceptance;
DROP TRIGGER phase_acceptance_complete ON mta.fresh_mta_runphaseacceptance;
"""
for table in ('fresh_mta_runscopeattempt', 'fresh_mta_runphaseacceptance'):
    REVERSE += 'DROP TRIGGER scope_no_truncate ON mta.'+table+';\n'
    for operation in ('insert', 'update', 'delete', 'truncate'):
        REVERSE += 'DROP TRIGGER ingestion_watch_'+operation+' ON mta.'+table+';\n'
for name in ('guard_phase_acceptance()', 'require_phase_acceptance_complete()', 'guard_scope_attempt()',
             'scope_head(uuid)', 'guard_scoped_run_input()', 'guard_scoped_capture_status()', 'deny_scope_truncate()'):
    REVERSE += 'DROP FUNCTION mta.'+name+';\n'
REVERSE += 'CREATE OR REPLACE FUNCTION mta.guard_phase_snapshot()'+_storage._prepared_snapshot+'$guard$;\n'+_storage._prepared_rows


class Migration(migrations.Migration):
    dependencies = [('fresh_mta', '0176_scoped_phase_acceptance')]
    operations = [migrations.RunSQL(SQL, REVERSE)]
