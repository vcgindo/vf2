"""Bind native scoped operations to existing certified revision counters."""
from importlib import import_module
from django.db import migrations

SQL = r'''
CREATE FUNCTION mta.valid_scope_cut(value jsonb) RETURNS boolean LANGUAGE sql IMMUTABLE
 SET search_path=pg_catalog AS $body$
 SELECT CASE WHEN jsonb_typeof(value)='array' THEN
  CASE WHEN jsonb_array_length(value)=5 THEN
   NOT EXISTS(SELECT 1 FROM jsonb_array_elements(value) V(x) WHERE
    CASE WHEN jsonb_typeof(x)='number' AND x::text ~ '^[0-9]+$'
      THEN x::text::numeric>9223372036854775807 ELSE true END)
  ELSE false END ELSE false END
$body$;
CREATE FUNCTION mta.scope_cut_next(value jsonb) RETURNS jsonb LANGUAGE plpgsql
 SET search_path=pg_catalog,mta AS $body$
BEGIN
 IF NOT coalesce(mta.valid_scope_cut(value),false) THEN
  RAISE EXCEPTION 'Scoped revision cut requires five nonnegative integer counters'; END IF;
 RETURN jsonb_set(value,'{3}',to_jsonb((value->>3)::bigint+1));
END
$body$;
CREATE FUNCTION mta.scope_native_cut(target uuid) RETURNS jsonb LANGUAGE plpgsql
 SET search_path=pg_catalog,mta AS $body$
DECLARE binding jsonb; observed jsonb;
BEGIN
 SELECT R.production_manifest->'ingestion_preparation' INTO binding
  FROM mta.fresh_mta_calculationrun R WHERE R.id=target;
 IF binding IS NULL THEN RETURN NULL; END IF;
 SELECT jsonb_build_array(S.master_epoch,S.configuration_epoch,S.fact_epoch,S.operational_epoch,S.action_epoch)
  INTO observed FROM mta.fresh_mta_ingestionrevisionstate S
  JOIN mta.fresh_mta_initializationcertification C ON C.initialization_id=S.initialization_id
  JOIN mta.fresh_mta_productioninitialization I ON I.id=S.initialization_id
  JOIN mta.fresh_mta_mdmdailyinputcapture D ON D.source_id=I.source_id
  JOIN mta.fresh_mta_mdmsource O ON O.id=D.source_id
  JOIN mta.fresh_mta_masterinputrevision M ON M.initialization_id=I.id
  WHERE I.id::text=binding->>'initialization_id' AND D.run_id=target
   AND C.status='CERTIFIED' AND C.receipt_digest=binding->>'certification_digest'
   AND O.digest=binding->>'source_digest' AND M.id::text=binding->>'base_revision_id'
   AND M.status='ACCEPTED' FOR UPDATE OF S;
 IF observed IS NULL THEN RAISE EXCEPTION 'Scoped certified revision owner is unavailable'; END IF;
 RETURN observed;
END
$body$;
CREATE FUNCTION mta.scope_expected_cut(target uuid) RETURNS jsonb LANGUAGE plpgsql
 SET search_path=pg_catalog,mta AS $body$
DECLARE binding jsonb; expected jsonb; candidate jsonb;
BEGIN
 SELECT R.production_manifest->'ingestion_preparation' INTO binding
  FROM mta.fresh_mta_calculationrun R WHERE R.id=target;
 IF binding IS NULL THEN RETURN NULL; END IF;
 expected=binding->'capture_cut';
 IF NOT coalesce(mta.valid_scope_cut(expected),false) THEN RAISE EXCEPTION 'Captured revision cut is invalid'; END IF;
 IF EXISTS(SELECT 1 FROM mta.fresh_mta_runscopeattempt A WHERE A.run_id=target
  AND (A.revision_before IS NULL OR A.revision_after IS NULL))
  OR EXISTS(SELECT 1 FROM mta.fresh_mta_runphaseacceptance P WHERE P.run_id=target AND P.state_sealed
   AND (P.revision_before IS NULL OR P.metadata->'revision_after' IS NULL)) THEN
  RAISE EXCEPTION 'Existing native scoped evidence has no qualified revision cut'; END IF;
 FOR candidate IN
  SELECT A.revision_after FROM mta.fresh_mta_runscopeattempt A WHERE A.run_id=target
  UNION ALL SELECT A.revision_closed FROM mta.fresh_mta_runscopeattempt A
    WHERE A.run_id=target AND A.revision_closed IS NOT NULL
  UNION ALL SELECT P.metadata->'revision_after' FROM mta.fresh_mta_runphaseacceptance P
    WHERE P.run_id=target AND P.state_sealed LOOP
  IF NOT coalesce(mta.valid_scope_cut(candidate),false) THEN RAISE EXCEPTION 'Scoped revision evidence is invalid'; END IF;
  IF (candidate->>3)::bigint>(expected->>3)::bigint THEN expected=candidate;
  ELSIF (candidate->>3)::bigint=(expected->>3)::bigint AND candidate IS DISTINCT FROM expected THEN
   RAISE EXCEPTION 'Scoped revision evidence branches at the same counter'; END IF;
 END LOOP;
 RETURN expected;
END
$body$;
'''

_old_attempt=import_module('mta.runtime.migrations.0178_scope_fence_null_denial')._fixed
_attempt=_old_attempt.replace('actual_phase text; actual_digest text;',
    'actual_phase text; actual_digest text; observed jsonb; expected jsonb;')
_anchor=" IF TG_OP='UPDATE' THEN"
assert _attempt.count(_anchor)==1
_attempt=_attempt.replace(_anchor,r'''
 observed=mta.scope_native_cut(NEW.run_id); expected=mta.scope_expected_cut(NEW.run_id);
 IF TG_OP='INSERT' THEN
  IF observed IS NULL THEN
   IF NEW.revision_before IS NOT NULL OR NEW.revision_after IS NOT NULL OR NEW.revision_closed IS NOT NULL
    THEN RAISE EXCEPTION 'Uncertified scope cannot invent native revision cuts'; END IF;
  ELSIF observed IS DISTINCT FROM expected OR NEW.revision_before IS DISTINCT FROM observed
   OR NEW.revision_after IS DISTINCT FROM mta.scope_cut_next(observed) OR NEW.revision_closed IS NOT NULL THEN
   RAISE EXCEPTION 'Scoped claim requires its exact certified revision cut';
  END IF;
 ELSE
  IF observed IS NULL THEN
   IF NEW.revision_closed IS NOT NULL THEN RAISE EXCEPTION 'Uncertified attempt has no native closing cut'; END IF;
  ELSIF NEW.revision_closed IS DISTINCT FROM mta.scope_cut_next(expected) THEN
   RAISE EXCEPTION 'Scoped terminal revision cut cannot adopt unowned changes';
  ELSIF observed IS DISTINCT FROM expected THEN
   IF NEW.status<>'FAILED' OR NEW.failure->'revision_conflict' IS DISTINCT FROM
      jsonb_build_object('expected',expected,'observed',observed) THEN
    RAISE EXCEPTION 'Conflicted worker may only retain its exact revision failure'; END IF;
  ELSIF NEW.failure ? 'revision_conflict' THEN
   RAISE EXCEPTION 'Revision-conflict diagnostic does not match its counters';
  END IF;
 END IF;
''' + _anchor).replace("ARRAY['status','failure','finished_at']",
                       "ARRAY['status','failure','finished_at','revision_closed']")
SQL+='CREATE OR REPLACE FUNCTION mta.guard_scope_attempt()'+_attempt+'$guard$;\n'

_old_phase=import_module('mta.runtime.migrations.0177_scope_acceptance_guards').SQL.split(
    'CREATE FUNCTION mta.guard_phase_acceptance()',1)[1].split('$guard$;',1)[0]
_phase=_old_phase.replace('actual_phase text; actual_digest text; previous_image bigint;',
    'actual_phase text; actual_digest text; previous_image bigint; observed jsonb; expected jsonb;')
_anchor=" IF TG_OP='INSERT' THEN"
assert _phase.count(_anchor)==1
_phase=_phase.replace(_anchor,r'''
 observed=mta.scope_native_cut(NEW.run_id);
 IF observed IS NULL THEN
  IF NEW.revision_before IS NOT NULL OR NEW.metadata ? 'revision_after' THEN
   RAISE EXCEPTION 'Uncertified phase cannot invent native revision cuts'; END IF;
 ELSIF TG_OP='INSERT' THEN
  expected=mta.scope_expected_cut(NEW.run_id);
  IF observed IS DISTINCT FROM expected OR NEW.revision_before IS DISTINCT FROM observed THEN
   RAISE EXCEPTION 'Phase requires its exact accepted native revision prefix'; END IF;
 ELSE
  IF NEW.metadata->'revision_after' IS DISTINCT FROM mta.scope_cut_next(observed) THEN
   RAISE EXCEPTION 'Phase seal requires its exact owned native revision cut'; END IF;
 END IF;
''' + _anchor)
SQL+='CREATE OR REPLACE FUNCTION mta.guard_phase_acceptance()'+_phase+'$guard$;\n'

_old_run=import_module('mta.runtime.migrations.0177_scope_acceptance_guards').SQL.split(
    'CREATE FUNCTION mta.guard_scoped_run_input()',1)[1].split('$guard$;',1)[0]
_run=_old_run.replace("  IF TG_OP='DELETE' OR", """  IF OLD.production_manifest->'ingestion_preparation' IS DISTINCT FROM
     NEW.production_manifest->'ingestion_preparation' THEN
   RAISE EXCEPTION 'Scoped original capture preparation is immutable'; END IF;
  IF TG_OP='DELETE' OR""")
assert _run!=_old_run
SQL+='CREATE OR REPLACE FUNCTION mta.guard_scoped_run_input()'+_run+'$guard$;\n'
for function in ('valid_scope_cut(jsonb)','scope_cut_next(jsonb)','scope_native_cut(uuid)','scope_expected_cut(uuid)'):
    SQL+='REVOKE ALL ON FUNCTION mta.'+function+' FROM PUBLIC;\n'

REVERSE="""DO $pre$ BEGIN
 IF EXISTS(SELECT 1 FROM mta.fresh_mta_runscopeattempt WHERE revision_before IS NOT NULL) THEN
 RAISE EXCEPTION 'Native scoped revision evidence requires a compatible forward release'; END IF;
END $pre$;
"""
for name,body in (('guard_scope_attempt',_old_attempt),('guard_phase_acceptance',_old_phase),('guard_scoped_run_input',_old_run)):
    REVERSE+='CREATE OR REPLACE FUNCTION mta.'+name+'()'+body+'$guard$;\n'
for function in ('scope_expected_cut(uuid)','scope_native_cut(uuid)','scope_cut_next(jsonb)','valid_scope_cut(jsonb)'):
    REVERSE+='DROP FUNCTION mta.'+function+';\n'


class Migration(migrations.Migration):
    dependencies=[('fresh_mta','0181_scoped_revision_cuts')]
    operations=[migrations.RunSQL(SQL,REVERSE)]
