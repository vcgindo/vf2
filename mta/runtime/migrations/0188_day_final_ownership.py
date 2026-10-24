"""DAY_FINAL references the common writer's real typed root, not a second snapshot."""
from importlib import import_module
from django.db import migrations

_base=import_module('mta.runtime.migrations.0177_scope_acceptance_guards')
_cuts=import_module('mta.runtime.migrations.0182_scoped_revision_ownership')
SQL=r'''
CREATE FUNCTION mta.pending_day_final(target uuid) RETURNS boolean
 LANGUAGE sql STABLE SET search_path=pg_catalog,mta AS $body$
 SELECT EXISTS(SELECT 1 FROM mta.fresh_mta_runphaseacceptance P
 JOIN mta.fresh_mta_runscopeattempt A ON A.id=P.attempt_id
 JOIN mta.fresh_mta_calculationrun R ON R.id=P.run_id
 JOIN mta.fresh_mta_mdmdailyinputcapture C ON C.run_id=R.id
 JOIN mta.fresh_mta_runphaseacceptance B ON B.run_id=R.id AND B.phase='DBM' AND B.state_sealed
 WHERE R.id=target AND R.kind='DAILY_CHAIN' AND R.status IN ('RUNNING','SUCCEEDED')
  AND P.phase='DAY_FINAL' AND NOT P.state_sealed AND A.run_id=R.id AND A.status='ACTIVE'
  AND A.scope IN ('PostBPR','PostDBM') AND A.input_digest=R.input_digest
  AND A.input_manifest_digest=R.input_manifest_digest AND P.input_digest=R.input_digest
  AND P.source_id=C.source_id AND P.capture_digest=C.revision_digest
  AND C.status IN ('CAPTURED','CONSUMED')
  AND P.id::text=current_setting('fresh.scope_phase',true)
  AND A.worker_token::text=current_setting('fresh.scope_worker',true))
$body$;
REVOKE ALL ON FUNCTION mta.pending_day_final(uuid) FROM PUBLIC;
'''
_head=_base.SQL.split('CREATE FUNCTION mta.scope_head(target uuid)',1)[1].split('$body$;',1)[0]
_head=_head.replace("CASE P.phase WHEN 'DBM'", "CASE P.phase WHEN 'DAY_FINAL' THEN 4 WHEN 'DBM'")
SQL+='CREATE OR REPLACE FUNCTION mta.scope_head(target uuid)'+_head+'$body$;\n'

_phase=_cuts._phase.replace("IF parent.status<>'RUNNING' OR parent.kind", """IF (CASE WHEN NEW.phase='DAY_FINAL' AND TG_OP='UPDATE'
       THEN parent.status<>'SUCCEEDED' ELSE parent.status<>'RUNNING' END) OR parent.kind""").replace(
    "OR captured.status<>'CAPTURED' OR captured.source_id", """OR (CASE WHEN NEW.phase='DAY_FINAL' AND TG_OP='UPDATE'
       THEN captured.status<>'CONSUMED' ELSE captured.status<>'CAPTURED' END) OR captured.source_id""")
_anchor="OR NEW.phase='DBM' AND actual_phase='BPR' AND claim.scope IN ('UptoDBM','PostBPR')"
assert _phase.count(_anchor)==1
_phase=_phase.replace(_anchor,_anchor+"\n   OR NEW.phase='DAY_FINAL' AND actual_phase='DBM' AND claim.scope IN ('PostBPR','PostDBM')")
_start=_phase.index('  SELECT * INTO STRICT image')
_stop=_phase.index('\n END IF;\n RETURN NEW;',_start)
_terminal=r'''
  IF NEW.phase='DAY_FINAL' THEN
   SELECT H.phase,H.digest INTO actual_phase,actual_digest FROM mta.scope_head(NEW.run_id) H;
   IF NOT mta.pending_day_final(NEW.run_id) OR actual_phase<>'DBM' OR NEW.snapshot_id IS NOT NULL
    OR NEW.accepted_at IS NULL OR NEW.digest !~ '^[0-9a-f]{64}$'
    OR parent.output_digest !~ '^[0-9a-f]{64}$' OR parent.production_digest !~ '^[0-9a-f]{64}$'
    OR parent.completed_at IS NULL OR parent.production_manifest->>'version' IS DISTINCT FROM '3'
    OR NEW.metadata->>'schema' IS DISTINCT FROM 'fresh-day-final-acceptance-v1'
    OR NEW.metadata->>'parent_acceptance_digest' IS DISTINCT FROM actual_digest
    OR NEW.metadata->>'output_digest' IS DISTINCT FROM parent.output_digest
    OR NEW.metadata->>'production_digest' IS DISTINCT FROM parent.production_digest
    OR NEW.metadata->>'input_manifest_digest' IS DISTINCT FROM parent.input_manifest_digest
    OR NEW.metadata->>'compatibility_digest' IS DISTINCT FROM claim.compatibility_digest
    OR octet_length(NEW.metadata::text)>65536 THEN
    RAISE EXCEPTION 'DAY_FINAL requires the completed common typed output root'; END IF;
  ELSE
'''
_phase=_phase[:_start]+_terminal+_phase[_start:_stop]+'\n  END IF;'+_phase[_stop:]
SQL+='CREATE OR REPLACE FUNCTION mta.guard_phase_acceptance()'+_phase+'$guard$;\n'

SQL+=r'''
CREATE OR REPLACE FUNCTION mta.require_phase_acceptance_complete() RETURNS trigger LANGUAGE plpgsql
 SET search_path=pg_catalog,mta AS $guard$
BEGIN
 IF NOT EXISTS(SELECT 1 FROM mta.fresh_mta_runphaseacceptance P
  JOIN mta.fresh_mta_calculationrun R ON R.id=P.run_id
  JOIN mta.fresh_mta_mdmdailyinputcapture C ON C.run_id=R.id
  WHERE P.id=NEW.id AND P.state_sealed AND P.digest<>'' AND P.accepted_at IS NOT NULL
   AND (P.phase<>'DAY_FINAL' AND P.snapshot_id IS NOT NULL OR P.phase='DAY_FINAL'
    AND P.snapshot_id IS NULL AND R.status='SUCCEEDED' AND C.status='CONSUMED'
    AND P.metadata->>'output_digest'=R.output_digest
    AND P.metadata->>'production_digest'=R.production_digest)) THEN
  RAISE EXCEPTION 'Phase state and effects must seal before commit'; END IF;
 RETURN NULL;
END
$guard$;
'''
_run=_cuts._run.replace("  IF NEW.status IS DISTINCT FROM OLD.status THEN", """  IF OLD.status='SUCCEEDED' AND to_jsonb(OLD) IS DISTINCT FROM to_jsonb(NEW) THEN
   RAISE EXCEPTION 'Scoped completed output root is immutable'; END IF;
  IF NEW.status IS DISTINCT FROM OLD.status AND NOT (
    OLD.status='RUNNING' AND NEW.status='SUCCEEDED' AND mta.pending_day_final(NEW.id)
    AND NEW.output_digest ~ '^[0-9a-f]{64}$' AND NEW.production_digest ~ '^[0-9a-f]{64}$'
    AND NEW.completed_at IS NOT NULL AND NEW.production_manifest->>'version'='3'
    AND EXISTS(SELECT 1 FROM mta.fresh_mta_mdmdailyinputcapture C WHERE C.run_id=NEW.id
      AND C.status='CONSUMED')) THEN""")
SQL+='CREATE OR REPLACE FUNCTION mta.guard_scoped_run_input()'+_run+'$guard$;\n'
_capture=_base.SQL.split('CREATE FUNCTION mta.guard_scoped_capture_status()',1)[1].split('$guard$;',1)[0]
_capture=_capture.replace("WHERE A.run_id=OLD.run_id) THEN", """WHERE A.run_id=OLD.run_id) AND NOT (
   OLD.status='CAPTURED' AND NEW.status='CONSUMED' AND NEW.consumed_at IS NOT NULL
   AND mta.pending_day_final(NEW.run_id)) THEN""")
SQL+='CREATE OR REPLACE FUNCTION mta.guard_scoped_capture_status()'+_capture+'$guard$;\n'

_rows=_base._rows.replace("AND item.image NOT LIKE 'input/%' AND item.image NOT LIKE 'batch/%' THEN",
    "AND item.image NOT LIKE 'input/%' AND item.image NOT LIKE 'batch/%'\n"
    '       AND NOT mta.pending_day_final(item.owner) THEN')
assert _rows!=_base._rows
SQL+=_rows
REVERSE="""DO $pre$ BEGIN
 IF EXISTS(SELECT 1 FROM mta.fresh_mta_runphaseacceptance WHERE phase='DAY_FINAL') THEN
 RAISE EXCEPTION 'DAY_FINAL evidence requires a compatible forward release'; END IF;
END $pre$;
"""
for name,body,end in (
    ('scope_head(target uuid)',_base.SQL.split('CREATE FUNCTION mta.scope_head(target uuid)',1)[1].split('$body$;',1)[0],'$body$;'),
    ('guard_phase_acceptance()',_cuts._phase,'$guard$;'),
    ('require_phase_acceptance_complete()',_base.SQL.split('CREATE FUNCTION mta.require_phase_acceptance_complete()',1)[1].split('$guard$;',1)[0],'$guard$;'),
    ('guard_scoped_run_input()',_cuts._run,'$guard$;'),
    ('guard_scoped_capture_status()',_base.SQL.split('CREATE FUNCTION mta.guard_scoped_capture_status()',1)[1].split('$guard$;',1)[0],'$guard$;')):
    REVERSE+='CREATE OR REPLACE FUNCTION mta.'+name+body+end+'\n'
REVERSE+=_base._rows+'\nDROP FUNCTION mta.pending_day_final(uuid);'


class Migration(migrations.Migration):
    dependencies=[('fresh_mta','0187_day_final_acceptance')]
    operations=[migrations.RunSQL(SQL,REVERSE)]
