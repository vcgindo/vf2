"""Bind the pending anchor to final sealed initialization scalar ownership."""
from django.db import migrations

SQL = r'''
CREATE OR REPLACE FUNCTION mta.require_state_cut_seal() RETURNS trigger LANGUAGE plpgsql
SET search_path=pg_catalog,mta AS $$
DECLARE c mta.fresh_mta_operationalstatecut; p mta.fresh_mta_operationalstatecut;
 b jsonb; image jsonb; anchor jsonb; original_digest text;
 facts bigint; revisions bigint; expired bigint; retained bigint;
BEGIN
 SELECT * INTO STRICT c FROM mta.fresh_mta_operationalstatecut WHERE id=NEW.id;
 IF c.root_digest='' THEN RAISE EXCEPTION 'Unsealed operational cut cannot commit'; END IF;
 IF NOT EXISTS(SELECT 1 FROM mta.fresh_mta_productioninitialization
   WHERE id=c.initialization_id AND receipt_digest<>'' AND input_manifest_digest<>'')
 THEN RAISE EXCEPTION 'Operational cut initialization must seal before commit'; END IF;
 b=c.root_body::jsonb;
 IF jsonb_typeof(b) IS DISTINCT FROM 'object' OR
    (SELECT count(*) FROM jsonb_object_keys(b))<>19 OR NOT (b ?& ARRAY['format','cut','initialization','family','position',
     'run','parent','parent_root','input_digest','settings_digest','fields','count',
     'inserted','revised','expired','facts_digest','revisions_digest','expiry_digest','anchor']) OR
    b->>'format' IS DISTINCT FROM 'rationing-occurrences-v1' OR b->>'cut' IS DISTINCT FROM c.id::text OR
    b->>'initialization' IS DISTINCT FROM c.initialization_id::text OR b->>'family' IS DISTINCT FROM c.family OR
    (b->>'position')::bigint IS DISTINCT FROM c.position OR b->>'run' IS DISTINCT FROM c.run_id::text OR
    b->>'parent' IS DISTINCT FROM c.parent_id::text OR b->>'input_digest' IS DISTINCT FROM c.input_digest OR
    b->>'settings_digest' IS DISTINCT FROM c.settings_digest OR jsonb_typeof(b->'fields') IS DISTINCT FROM 'array' OR
    mta.rationing_fields_valid(b->'fields',(b->>'count')::bigint) IS NOT TRUE OR
    COALESCE(b->>'facts_digest','') !~ '^[0-9a-f]{64}$' OR
    COALESCE(b->>'revisions_digest','') !~ '^[0-9a-f]{64}$' OR
    COALESCE(b->>'expiry_digest','') !~ '^[0-9a-f]{64}$'
 THEN RAISE EXCEPTION 'Operational commitment context differs'; END IF;
 SELECT count(*) INTO facts FROM mta_state.rationing_fact WHERE cut_id=c.id;
 SELECT count(*) INTO revisions FROM mta_state.rationing_dispatch WHERE cut_id=c.id;
 SELECT count(*) INTO expired FROM mta_state.rationing_expiry WHERE cut_id=c.id;
 IF (b->>'inserted')::bigint IS DISTINCT FROM facts OR (b->>'revised')::bigint IS DISTINCT FROM revisions OR
   (b->>'expired')::bigint IS DISTINCT FROM expired OR
   EXISTS(SELECT 1 FROM mta_state.rationing_fact F LEFT JOIN mta_state.rationing_lifetime L
    ON L.fact_cut_id=F.cut_id AND L.original_ordinal=F.vf_ordinal WHERE F.cut_id=c.id AND L.fact_cut_id IS NULL) OR
   EXISTS(SELECT 1 FROM mta_state.rationing_expiry E LEFT JOIN mta_state.rationing_lifetime L
    ON L.fact_cut_id=E.original_cut_id AND L.original_ordinal=E.original_ordinal
    WHERE E.cut_id=c.id AND (L.closing_cut_id IS DISTINCT FROM c.id OR L.end_position IS DISTINCT FROM c.position))
 THEN RAISE EXCEPTION 'Operational deltas or lifetime index are incomplete'; END IF;
 IF c.position=0 THEN
  IF b->>'parent_root' IS DISTINCT FROM repeat('0',64) OR revisions<>0 OR expired<>0 OR
     jsonb_typeof(b->'anchor') IS DISTINCT FROM 'object'
  THEN RAISE EXCEPTION 'Anchor commitment differs'; END IF;
  anchor=b->'anchor';
  IF (SELECT count(*) FROM jsonb_object_keys(anchor))<>6 OR
     NOT (anchor ?& ARRAY['owner_kind','owner_id','manifest_digest','image','digest','count'])
  THEN RAISE EXCEPTION 'Anchor provenance fields differ'; END IF;
  IF c.run_id IS NULL THEN
   IF NOT EXISTS(SELECT 1 FROM mta.fresh_mta_productioninitialization
     WHERE id=c.initialization_id AND input_digest=c.input_digest
       AND configuration_digest=c.settings_digest)
   THEN RAISE EXCEPTION 'Anchor final initialization ownership differs'; END IF;
   SELECT input_manifest_digest,input_payload->'images'->'input/opening/state/btr/RationingHistory/values'
    INTO original_digest,image FROM mta.fresh_mta_productioninitialization WHERE id=c.initialization_id;
   IF anchor->>'owner_kind' IS DISTINCT FROM 'INITIALIZATION' OR
      anchor->>'owner_id' IS DISTINCT FROM c.initialization_id::text OR
      anchor->>'image' IS DISTINCT FROM 'input/opening/state/btr/RationingHistory/values'
   THEN RAISE EXCEPTION 'Anchor must name its exact initialized opening'; END IF;
  ELSE
   SELECT production_digest,production_manifest->'images'->'closing/btr/RationingHistory'
    INTO original_digest,image FROM mta.fresh_mta_calculationrun WHERE id=c.run_id AND status='SUCCEEDED';
   IF anchor->>'owner_kind' IS DISTINCT FROM 'RUN' OR anchor->>'owner_id' IS DISTINCT FROM c.run_id::text OR
      anchor->>'image' IS DISTINCT FROM 'closing/btr/RationingHistory'
   THEN RAISE EXCEPTION 'Anchor must name its exact accepted predecessor'; END IF;
  END IF;
  IF image IS NULL OR image ? 'storage_format' OR
    anchor->>'manifest_digest' IS DISTINCT FROM original_digest OR anchor->'digest' IS DISTINCT FROM image->'digest' OR
    anchor->'count' IS DISTINCT FROM image->'count' OR b->'count' IS DISTINCT FROM image->'count' OR
    b->'fields' IS DISTINCT FROM image->'fields'
  THEN RAISE EXCEPTION 'Anchor accepted representation differs'; END IF;
  retained=0;
 ELSE
  SELECT * INTO STRICT p FROM mta.fresh_mta_operationalstatecut WHERE id=c.parent_id;
  retained=(p.root_body::jsonb->>'count')::bigint-expired;
  IF b->>'parent_root' IS DISTINCT FROM p.root_digest OR b->'anchor' IS DISTINCT FROM 'null'::jsonb
  THEN RAISE EXCEPTION 'Operational parent commitment differs'; END IF;
  SELECT production_manifest->'images'->'closing/btr/RationingHistory' INTO image
   FROM mta.fresh_mta_calculationrun WHERE id=c.run_id AND status='SUCCEEDED';
  IF image IS NULL OR image->>'storage_format' IS DISTINCT FROM 'rationing-occurrences-v1' OR
     image->>'cut_id' IS DISTINCT FROM c.id::text OR image->>'digest' IS DISTINCT FROM c.root_digest OR
     image->'fields' IS DISTINCT FROM b->'fields' OR image->'count' IS DISTINCT FROM b->'count'
  THEN RAISE EXCEPTION 'Accepted run must bind its exact sealed operational cut'; END IF;
 END IF;
 IF retained<0 OR (b->>'count')::bigint IS DISTINCT FROM retained+facts THEN
  RAISE EXCEPTION 'Operational logical membership count differs';
 END IF;
 RETURN NULL;
END $$;
'''

class Migration(migrations.Migration):
    dependencies = [('fresh_mta', '0252_state_cut_owner_alias')]
    operations = [migrations.RunSQL(SQL)]
