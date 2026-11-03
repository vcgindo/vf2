"""Fail-closed cut ownership and exact qualified metadata before activation.

0250 was applied to the isolated schema database; retain it unchanged. Fresh
anchors begin under the existing pending initialization owner and must seal in
that same transaction. No transaction-ID assumptions, new session capability,
business backfill, or writer activation. Required on fresh and upgraded DBs.
"""
from django.db import migrations

SQL = r'''

-- Only scalar metadata is decoded. No typed population or profile scan.
CREATE FUNCTION mta.state_input_scalars(node jsonb) RETURNS jsonb
LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog AS $$
DECLARE item jsonb; result jsonb='{}'; key text;
BEGIN
 IF jsonb_typeof(node) IS DISTINCT FROM 'object' OR
    (SELECT count(*) FROM jsonb_object_keys(node))<>1 OR
    jsonb_typeof(node->'object') IS DISTINCT FROM 'array'
 THEN RAISE EXCEPTION 'Frozen scalar object shape differs'; END IF;
 FOR item IN SELECT value FROM jsonb_array_elements(node->'object') LOOP
  IF jsonb_typeof(item) IS DISTINCT FROM 'array' OR jsonb_array_length(item)<>2 OR
     jsonb_typeof(item->0) IS DISTINCT FROM 'string' OR
     jsonb_typeof(item->1) IS DISTINCT FROM 'object' OR
     (SELECT count(*) FROM jsonb_object_keys(item->1))<>1 OR NOT (item->1 ? 'scalar') OR
     jsonb_typeof(item->1->'scalar') IN ('object','array')
  THEN RAISE EXCEPTION 'Frozen scalar member shape differs'; END IF;
  key=item->>0;
  IF result ? key THEN RAISE EXCEPTION 'Duplicate frozen scalar member'; END IF;
  result=result||jsonb_build_object(key,item->1->'scalar');
 END LOOP;
 RETURN result;
END $$;
REVOKE ALL ON FUNCTION mta.state_input_scalars(jsonb) FROM PUBLIC;

CREATE FUNCTION mta.state_cut_settings(owner uuid,identity uuid) RETURNS text
LANGUAGE plpgsql STABLE SET search_path=pg_catalog,mta AS $$
DECLARE i mta.fresh_mta_productioninitialization; r mta.fresh_mta_calculationrun;
 origin mta.fresh_mta_calculationrun; v mta.fresh_mta_executionsettingsversion;
 payload jsonb; binding jsonb; ref jsonb; nodes jsonb; n bigint;
BEGIN
 SELECT * INTO STRICT i FROM mta.fresh_mta_productioninitialization WHERE id=owner;
 SELECT * INTO STRICT r FROM mta.fresh_mta_calculationrun WHERE id=identity;
 payload=r.input_payload;
 IF payload->>'schema' IN ('fresh-captured-input-reference-v1','fresh-captured-input-reference-v2',
   'fresh-captured-input-reference-v3','fresh-captured-input-reference-v4',
   'fresh-captured-input-reference-v5','fresh-captured-input-reference-v6') THEN
  SELECT * INTO STRICT origin FROM mta.fresh_mta_calculationrun WHERE id=
   (CASE WHEN payload->>'schema'='fresh-captured-input-reference-v1' THEN payload->>'origin_run_id'
         ELSE payload->>'physical_origin_run_id' END)::uuid;
  IF origin.input_manifest_digest IS DISTINCT FROM
    (CASE WHEN payload->>'schema'='fresh-captured-input-reference-v1' THEN payload->>'origin_manifest_digest'
          ELSE payload->>'physical_origin_manifest_digest' END) OR
    origin.input_digest IS DISTINCT FROM r.input_digest OR origin.input_manifest_digest=''
  THEN RAISE EXCEPTION 'Frozen settings physical capture differs'; END IF;
  payload=origin.input_payload;
 END IF;
 IF payload->>'schema' NOT IN ('fresh-daily-input-manifest-v2','fresh-daily-input-manifest-v3') OR
    payload->>'schema' IS NULL OR jsonb_typeof(payload->'tree'->'object') IS DISTINCT FROM 'array' OR
    payload->>'content_digest' IS DISTINCT FROM r.input_digest
 THEN RAISE EXCEPTION 'Operational settings require typed frozen inputs'; END IF;
 nodes=payload->'tree'->'object';
 SELECT count(*) INTO n FROM jsonb_array_elements(nodes) X WHERE X->>0='initialization_binding';
 IF n<>1 THEN RAISE EXCEPTION 'Frozen settings initialization owner missing or repeated'; END IF;
 SELECT mta.state_input_scalars(X->1) INTO binding FROM jsonb_array_elements(nodes) X
  WHERE X->>0='initialization_binding';
 IF binding->>'id' IS DISTINCT FROM i.id::text OR
    binding->>'configuration_digest' IS DISTINCT FROM i.configuration_digest OR
    NOT EXISTS(SELECT 1 FROM mta.fresh_mta_mdmdailyinputcapture C
      WHERE C.run_id=r.id AND C.source_id=i.source_id)
 THEN RAISE EXCEPTION 'Frozen settings initialization/capture differs'; END IF;
 SELECT count(*) INTO n FROM jsonb_array_elements(nodes) X WHERE X->>0='execution_settings';
 IF n=0 THEN RETURN i.configuration_digest; END IF;
 IF n<>1 THEN RAISE EXCEPTION 'Frozen settings reference repeated'; END IF;
 SELECT mta.state_input_scalars(X->1) INTO ref FROM jsonb_array_elements(nodes) X
  WHERE X->>0='execution_settings';
 SELECT * INTO STRICT v FROM mta.fresh_mta_executionsettingsversion
  WHERE id=(ref->>'id')::uuid AND initialization_id=i.id AND status='COMMITTED';
 IF v.effective_date>r.business_date OR ref IS DISTINCT FROM jsonb_build_object(
    'contract','vectorflow-execution-settings-v1','id',v.id::text,'initialization_id',i.id::text,
    'revision',v.revision,'effective_date',v.effective_date::text,
    'values_digest',v.values_digest,'profile_digest',v.profile_digest)
 THEN RAISE EXCEPTION 'Frozen settings version/date/reference differs'; END IF;
 RETURN v.profile_digest;
END $$;
REVOKE ALL ON FUNCTION mta.state_cut_settings(uuid,uuid) FROM PUBLIC;

CREATE FUNCTION mta.rationing_fields_valid(fields jsonb,population bigint) RETURNS boolean
LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog AS $$
DECLARE descriptor jsonb; expected jsonb; ordinal integer=0;
 roster constant jsonb='[["SKUCode",["str"]],["SKUName",["str"]],["WhCode",["str"]],["WhName",["str"]],["WhType",["str"]],["ParentWhType",["str"]],["Norm",["str","int"]],["VirtualNorm",["str","int"]],["VirtualNodeNorm",["str","int"]],["SpikeThreshold",["str","int","float"]],["PSOThreshold",["str","int","float"]],["Stock",["str","int"]],["GIT",["str","int"]],["Receipts",["str","int"]],["Consumption",["str","int"]],["Dispatch",["str","int"]],["StockForRationing",["str","int"]],["StockForReqCalc",["str","int"]],["TechPen",["str","int","float"]],["TechColor",["str"]],["EcoPen",["str","int","float"]],["EcoColor",["str"]],["DispatchPen",["str","int","float"]],["DispatchColor",["str"]],["DispatchColorSequence",["str","int"]],["PhysicalInventoryPen",["str","int","float"]],["PhysicalInventoryColor",["str"]],["PhysicalInventoryColorSequence",["str","int"]],["ParentWhCode",["str"]],["ParentWhName",["str"]],["ParentNorm",["str","int"]],["TechPenParent",["str","int","float"]],["TechColorParent",["str"]],["EcoPenParent",["str","int","float"]],["EcoColorParent",["str"]],["Req",["str","int"]],["AllocatedForVirtualNormReq",["str","int"]],["AllocatedForNormReq",["str","int"]],["AllocatedForSnPReq",["str","int"]],["AllocatedForDirectOrders",["str","int"]],["RationedReq",["str","int"]],["SupplierDispatchReq",["str","int"]],["PackSize",["str","int"]],["RationedCasePacks",["str","int"]],["LeftoverParentStock",["str","int"]],["LeftoverStock",["str","int"]],["ParentPackSize",["str","int"]],["IsNormed",["str","bool","int"]],["DirectSpikeOverdue",["str","int"]],["SpikeOverdueAtParent",["str","int"]],["PSO",["str","int"]],["RelPSOAndCNR",["str","int"]],["ResidualChildrenSnP",["str","int"]],["SnPToNetOff",["str","int"]],["SnPNettedOff",["str","int"]],["ResidualSnP",["str","int"]],["EcoStockForNormReq",["str","int"]],["NormReq",["str","int"]],["BlueReq",["str","int"]],["AvgSiblingsNorm",["str","int"]],["AvgChildrenNorm",["str","int"]],["ParentStockForNormRationing",["str","int"]],["ParentStockForSnPRationing",["str","int"]],["ParentStockForRationing",["str","int"]],["StockPercentageForRationing",["str","int"]],["NormPercentReservation",["str","int"]],["ParentStockPercentageForRationing",["str","int"]],["ParentNormPercentReservation",["str","int"]],["ReportDate",["str"]]]';
BEGIN
 IF population IS NULL OR population<0 OR jsonb_typeof(fields) IS DISTINCT FROM 'array'
 THEN RETURN false; END IF;
 IF fields='[]'::jsonb THEN RETURN population=0; END IF;
 IF jsonb_array_length(fields)<>69 THEN RETURN false; END IF;
 FOR descriptor IN SELECT value FROM jsonb_array_elements(fields) LOOP
  expected=roster->ordinal;
  IF jsonb_typeof(descriptor) IS DISTINCT FROM 'array' OR jsonb_array_length(descriptor)<>3 OR
    descriptor->0 IS DISTINCT FROM expected->0 OR descriptor->1 IS DISTINCT FROM expected->0 OR
    jsonb_typeof(descriptor->2) IS DISTINCT FROM 'string' OR
    NOT (expected->1 ? (descriptor->>2)) THEN RETURN false; END IF;
  ordinal=ordinal+1;
 END LOOP;
 RETURN true;
END $$;
REVOKE ALL ON FUNCTION mta.rationing_fields_valid(jsonb,bigint) FROM PUBLIC;

CREATE OR REPLACE FUNCTION mta.state_cut_owner() RETURNS trigger LANGUAGE plpgsql
SET search_path=pg_catalog,mta AS $$
DECLARE p mta.fresh_mta_operationalstatecut; r mta.fresh_mta_calculationrun;
 i mta.fresh_mta_productioninitialization; table_owner name;
BEGIN
 SELECT pg_get_userbyid(relowner) INTO table_owner FROM pg_class WHERE oid=TG_RELID;
 IF current_user<>table_owner AND NOT EXISTS(SELECT 1 FROM pg_roles WHERE rolname=current_user AND rolsuper)
 THEN RAISE EXCEPTION 'Operational cut requires its trusted writer'; END IF;
 IF TG_OP='UPDATE' THEN
  PERFORM mta.require_pending_state_cut(OLD.id);
  IF NEW.root_digest='' OR NEW.root_body='' OR
    (to_jsonb(OLD)-ARRAY['root_body','root_digest']) IS DISTINCT FROM
    (to_jsonb(NEW)-ARRAY['root_body','root_digest'])
  THEN RAISE EXCEPTION 'Only the pending operational commitment may seal'; END IF;
  RETURN NEW;
 END IF;
 IF NEW.root_body<>'' OR NEW.root_digest<>'' THEN RAISE EXCEPTION 'Operational cut must start pending'; END IF;
 SELECT * INTO STRICT i FROM mta.fresh_mta_productioninitialization
  WHERE id=NEW.initialization_id FOR UPDATE;
 IF (NEW.position>0 OR NEW.run_id IS NOT NULL) AND i.receipt_digest=''
 THEN RAISE EXCEPTION 'Operational cut initialization is unsealed'; END IF;
 IF NEW.position=0 THEN
  IF NOT EXISTS(SELECT 1 FROM pg_roles WHERE rolname=current_user AND rolsuper) AND
    (NEW.run_id IS NOT NULL OR mta.native_initialization_pending(i.id) IS NOT TRUE)
  THEN RAISE EXCEPTION 'Existing-state anchor requires normal trusted adoption'; END IF;
  IF NEW.run_id IS NULL THEN
   IF NEW.input_digest<>i.input_digest OR NEW.settings_digest<>i.configuration_digest OR
    EXISTS(SELECT 1 FROM mta.fresh_mta_mdmdailyinputcapture C
      JOIN mta.fresh_mta_calculationrun R ON R.id=C.run_id
      WHERE C.source_id=i.source_id AND R.status IN ('RUNNING','SUCCEEDED'))
   THEN RAISE EXCEPTION 'Initial anchor differs from its unused opening'; END IF;
  ELSE
   SELECT * INTO STRICT r FROM mta.fresh_mta_calculationrun WHERE id=NEW.run_id FOR SHARE;
   IF r.status<>'SUCCEEDED' OR NEW.input_digest<>r.input_digest OR
     NOT EXISTS(SELECT 1 FROM mta.fresh_mta_mdmdailyinputcapture
       WHERE run_id=r.id AND source_id=i.source_id AND status='CONSUMED') OR
     EXISTS(SELECT 1 FROM mta.fresh_mta_calculationrun
       WHERE predecessor_id=r.id AND status IN ('RUNNING','SUCCEEDED'))
   THEN RAISE EXCEPTION 'Accepted anchor is not the exact current owned predecessor'; END IF;
  END IF;
 ELSE
  SELECT * INTO STRICT r FROM mta.fresh_mta_calculationrun WHERE id=NEW.run_id FOR UPDATE;
  SELECT * INTO STRICT p FROM mta.fresh_mta_operationalstatecut WHERE id=NEW.parent_id FOR SHARE;
  IF r.status<>'RUNNING' OR NEW.input_digest<>r.input_digest OR
    p.initialization_id<>NEW.initialization_id OR p.family<>NEW.family OR p.root_digest='' OR
    NEW.position<>p.position+1 OR r.predecessor_id IS DISTINCT FROM p.run_id OR
    NOT EXISTS(SELECT 1 FROM mta.fresh_mta_mdmdailyinputcapture
      WHERE run_id=r.id AND source_id=i.source_id AND status IN ('CAPTURED','CONSUMED')) OR
    (p.run_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM mta.fresh_mta_calculationrun
      WHERE id=p.run_id AND status='SUCCEEDED'))
  THEN RAISE EXCEPTION 'Operational cut owner or accepted parent differs'; END IF;
 END IF;
 IF NEW.run_id IS NOT NULL AND
    NEW.settings_digest IS DISTINCT FROM mta.state_cut_settings(i.id,NEW.run_id)
 THEN RAISE EXCEPTION 'Operational cut frozen settings differ'; END IF;
 RETURN NEW;
END $$;
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
    dependencies = [('fresh_mta', '0250_rationing_occurrence_storage')]
    operations = [migrations.RunSQL(SQL)]
