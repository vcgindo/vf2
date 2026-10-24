"""Current copies are owned by their actual PRE_BPR/BPR/DBM phase."""
from importlib import import_module
from django.db import migrations

_prior=import_module('mta.runtime.migrations.0179_prepared_effect_ownership')
SQL=r'''
CREATE FUNCTION mta.pending_scoped_current(owner bigint) RETURNS text
 LANGUAGE sql STABLE SET search_path=pg_catalog,mta AS $body$
 SELECT P.phase FROM mta.fresh_mta_runphaseacceptance P
 JOIN mta.fresh_mta_runscopeattempt A ON A.id=P.attempt_id
 JOIN mta.fresh_mta_mdmdailyinputcapture C ON C.run_id=P.run_id
 JOIN mta.fresh_mta_calculationrun R ON R.id=P.run_id
 WHERE P.phase IN ('PRE_BPR','BPR','DBM') AND NOT P.state_sealed
  AND P.source_id=owner AND C.source_id=owner AND A.run_id=R.id AND A.status='ACTIVE'
  AND R.status='RUNNING' AND R.kind='DAILY_CHAIN' AND C.status='CAPTURED'
  AND P.input_digest=R.input_digest AND A.input_digest=R.input_digest
  AND A.input_manifest_digest=R.input_manifest_digest AND P.capture_digest=C.revision_digest
  AND R.id::text=current_setting('fresh.mdm_current_run',true)
  AND P.id::text=current_setting('fresh.scope_phase',true)
  AND A.worker_token::text=current_setting('fresh.scope_worker',true)
  AND (P.phase='PRE_BPR' AND R.id::text=current_setting('fresh.mdm_consuming_run',true)
    OR P.phase IN ('BPR','DBM') AND coalesce(current_setting('fresh.mdm_consuming_run',true),'')='')
$body$;
REVOKE ALL ON FUNCTION mta.pending_scoped_current(bigint) FROM PUBLIC;
CREATE FUNCTION mta.guard_scoped_current_copy() RETURNS trigger LANGUAGE plpgsql
 SET search_path=pg_catalog,mta AS $guard$
DECLARE current_id uuid; row_value jsonb; accepted_phase text; expected_owner text;
BEGIN
 current_id=nullif(current_setting('fresh.mdm_current_run',true),'')::uuid;
 IF current_id IS NULL OR NOT EXISTS(SELECT 1 FROM mta.fresh_mta_runscopeattempt A WHERE A.run_id=current_id) THEN
  IF TG_OP='DELETE' THEN RETURN OLD; ELSE RETURN NEW; END IF;
 END IF;
 row_value=CASE WHEN TG_OP='DELETE' THEN to_jsonb(OLD) ELSE to_jsonb(NEW) END;
 accepted_phase=mta.pending_scoped_current((row_value->>'source_id')::bigint);
 expected_owner=CASE accepted_phase WHEN 'PRE_BPR' THEN 'Importer' ELSE accepted_phase END;
 IF accepted_phase IS NULL OR
   (row_value ? 'owner' AND row_value->>'owner' IS DISTINCT FROM expected_owner) OR
   (accepted_phase IN ('BPR','DBM') AND TG_TABLE_NAME NOT IN ('fresh_mta_mdmskuattributes',
      'fresh_mta_mdmskudescription','fresh_mta_mdmlocationattributes','fresh_mta_mdmlocationdescription')) OR
   (TG_TABLE_NAME='fresh_mta_mdmlocationuse' AND row_value->>'use_kind' NOT IN ('direct','parent')) THEN
  RAISE EXCEPTION 'Scoped current copies require their exact producing phase and partition'; END IF;
 IF TG_OP='UPDATE' AND (NEW.id IS DISTINCT FROM OLD.id OR NEW.source_id IS DISTINCT FROM OLD.source_id
    OR NEW.ordinal IS DISTINCT FROM OLD.ordinal
    OR to_jsonb(NEW)->'owner' IS DISTINCT FROM to_jsonb(OLD)->'owner'
    OR to_jsonb(NEW)->'use_kind' IS DISTINCT FROM to_jsonb(OLD)->'use_kind') THEN
  RAISE EXCEPTION 'Scoped current copies cannot move an occurrence'; END IF;
 IF TG_OP='DELETE' THEN RETURN OLD; ELSE RETURN NEW; END IF;
END
$guard$;
REVOKE ALL ON FUNCTION mta.guard_scoped_current_copy() FROM PUBLIC;
'''

_anchor=' IF coalesce(mta.pending_prepared_effects(owner),false) THEN'
_end=" END IF;\n IF TG_OP='INSERT' AND current_setting('fresh.mdm_current_bootstrap',true)=owner::text"
_start=_prior._new_current.index(_anchor)
_stop=_prior._new_current.index(_end,_start)+len(' END IF;')
_current=(_prior._new_current[:_start]+r'''
 IF mta.pending_scoped_current(owner) IS NOT NULL THEN
  -- The separate scoped-current row guard validates the exact phase partition,
  -- even for sources outside this original protected-source predicate.
  IF TG_OP='DELETE' THEN RETURN OLD; ELSE RETURN NEW; END IF;
 END IF;'''+_prior._new_current[_stop:])
SQL+='CREATE OR REPLACE FUNCTION mta.guard_active_mdm_current()'+_current+'\n'
_anchor=r'''
 IF coalesce(mta.pending_prepared_effects(C.source_id),false)
  AND C.run_id::text=current_setting('fresh.mdm_consuming_run',true) THEN RETURN NULL; END IF;
'''
assert _prior._new_projection.count(_anchor)==1
_projection=_prior._new_projection.replace(_anchor,
    '\n IF mta.pending_scoped_current(C.source_id) IS NOT NULL THEN RETURN NULL; END IF;\n')
SQL+='CREATE OR REPLACE FUNCTION mta.guard_location_projection_statement()'+_projection+'\n'
for table in _prior.CURRENT_TABLES:
    SQL+=('CREATE TRIGGER scope_current_phase BEFORE INSERT OR UPDATE OR DELETE ON mta.fresh_mta_'+table+
          ' FOR EACH ROW EXECUTE FUNCTION mta.guard_scoped_current_copy();\n')

REVERSE="""DO $pre$ BEGIN
 IF EXISTS(SELECT 1 FROM mta.fresh_mta_runphaseacceptance WHERE phase IN ('BPR','DBM')) THEN
 RAISE EXCEPTION 'Accepted current copies require a compatible forward release'; END IF;
END $pre$;
"""
for table in _prior.CURRENT_TABLES:
    REVERSE+='DROP TRIGGER scope_current_phase ON mta.fresh_mta_'+table+';\n'
REVERSE+=('CREATE OR REPLACE FUNCTION mta.guard_active_mdm_current()'+_prior._new_current+'\n'
    +'CREATE OR REPLACE FUNCTION mta.guard_location_projection_statement()'+_prior._new_projection+'\n'
    +'DROP FUNCTION mta.guard_scoped_current_copy(); DROP FUNCTION mta.pending_scoped_current(bigint);')


class Migration(migrations.Migration):
    dependencies=[('fresh_mta','0185_scope_cut_scalar_types')]
    operations=[migrations.RunSQL(SQL,REVERSE)]
