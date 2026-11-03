"""Seal a missing successor cut from its already accepted transition."""
from importlib import import_module

from django.db import migrations


prior = import_module('mta.runtime.migrations.0281_producer_history_storage')
base = import_module('mta.runtime.migrations.0250_rationing_occurrence_storage')
owner = import_module('mta.runtime.migrations.0252_state_cut_owner_alias')
source = r"""
CREATE FUNCTION mta.history_transition_adoption(c mta.fresh_mta_operationalstatecut)
RETURNS jsonb LANGUAGE sql STABLE SET search_path=pg_catalog,mta AS $$
 SELECT jsonb_build_object('owner_kind','RUN','owner_id',r.id::text,
    'manifest_digest',r.production_digest,'image',c.family,
    'digest',image.item->'digest','count',image.item->'count')
 FROM mta.fresh_mta_calculationrun r
 JOIN mta.fresh_mta_productioninitialization i ON i.id=c.initialization_id
 JOIN mta.fresh_mta_mdmdailyinputcapture capture
   ON capture.run_id=r.id AND capture.source_id=i.source_id AND capture.status='CONSUMED'
 JOIN mta.fresh_mta_operationalstatecut p ON p.id=c.parent_id
 JOIN mta.fresh_mta_dailyphasesnapshot phase ON phase.run_id=r.id AND phase.phase='DBM'
 CROSS JOIN LATERAL (SELECT r.production_manifest->'images'->c.family,
    phase.manifest->'images'->('phase/DBM/'||substr(c.family,9))) image(item,transition)
 WHERE c.family IN (FAMILIES) AND c.position=p.position+1
   AND p.initialization_id=c.initialization_id AND p.family=c.family AND p.root_digest<>''
   AND r.id=c.run_id AND r.status='SUCCEEDED' AND r.input_digest=c.input_digest
   AND r.predecessor_id=p.run_id AND phase.input_digest=r.input_digest
   AND NOT EXISTS(SELECT FROM mta.fresh_mta_calculationrun next
     WHERE next.predecessor_id=r.id AND next.status IN ('RUNNING','SUCCEEDED'))
   AND image.item->>'image'=c.family AND NOT image.item ? 'storage_format'
   AND image.transition->>'storage_format'='phase-history-transition-v1'
   AND image.transition->>'family'=c.family AND image.transition->>'run_id'=r.id::text
   AND image.transition->>'cut_id'=p.id::text AND image.transition->>'cut_digest'=p.root_digest
   AND image.transition->'count'=image.item->'count'
   AND image.transition->'digest'=image.item->'digest'
   AND image.transition->'fields'=image.item->'fields'
   AND image.transition->'table'=image.item->'table'
$$;
REVOKE ALL ON FUNCTION mta.history_transition_adoption(mta.fresh_mta_operationalstatecut) FROM PUBLIC;
""".replace('FAMILIES', prior.families)

allowed = """EXISTS(SELECT FROM pg_roles WHERE rolname=current_user AND rolsuper)
    AND mta.history_transition_adoption(CUT) IS NOT NULL"""
start = base.SQL.index('CREATE FUNCTION mta.require_pending_state_cut(')
end = base.SQL.index('REVOKE ALL ON FUNCTION mta.require_pending_state_cut(', start)
pending = base.SQL[start:end].replace('CREATE FUNCTION', 'CREATE OR REPLACE FUNCTION', 1)
pending = prior.replace(pending, "WHERE id=c.run_id AND status='RUNNING')",
    "WHERE id=c.run_id AND status='RUNNING') AND NOT ("+allowed.replace('CUT','c')+")")
owner_sql = prior.replace(owner.SQL, "IF r.status<>'RUNNING' OR NEW.input_digest",
    "IF (r.status<>'RUNNING' AND NOT ("+allowed.replace('CUT','NEW')+")) OR NEW.input_digest")
seal = prior.replace(prior.seal, "OR b->'anchor' IS DISTINCT FROM 'null'::jsonb",
    """OR (b->'anchor' IS DISTINCT FROM 'null'::jsonb
        AND b->'anchor' IS DISTINCT FROM mta.history_transition_adoption(c))""")
seal = prior.replace(seal, "  IF image IS NULL OR image->>'storage_format'",
    """  IF b->'anchor' IS DISTINCT FROM 'null'::jsonb THEN
   IF b->'count' IS DISTINCT FROM b->'anchor'->'count'
     OR b->'fields' IS DISTINCT FROM image->'fields'
   THEN RAISE EXCEPTION 'Adopted history closing representation differs'; END IF;
  ELSIF image IS NULL OR image->>'storage_format'""")


class Migration(migrations.Migration):
    dependencies = [('fresh_mta', '0283_dbm_phase_history_carries')]
    operations = [migrations.RunSQL(source+pending+owner_sql+seal)]
