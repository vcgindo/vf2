"""Insert-only references to existing, exactly matched BPR read dependencies."""
from importlib import import_module
from django.db import migrations

base=import_module('mta.runtime.migrations.0198_scope_report_guards')
TABLE='fresh_mta_scopereadreference'
OLD=import_module('mta.runtime.migrations.0216_scope_expedite_parent_guards').NEW
ADDED=("\n IF TG_TABLE_SCHEMA='mta' AND TG_TABLE_NAME='"+TABLE+"' AND TG_OP='INSERT' THEN\n"
    ' IF NOT EXISTS(SELECT 1 FROM new_rows G LEFT JOIN mta.fresh_mta_scopereportgeneration H '
    'ON H.id=G.report_generation_id '+base.JOINS.replace('G.','H.')+
    ' WHERE H.id IS NULL OR '+base.VALID.replace('G.','H.')+') THEN RETURN NULL; END IF;\n END IF;\n')
assert OLD.count(" IF kind='immutable' THEN")==1
NEW=OLD.replace(" IF kind='immutable' THEN",ADDED+" IF kind='immutable' THEN",1)
KEYS=('schema','run_id','phase_id','phase_digest','snapshot_digest','input_digest','input_manifest_digest',
    'action_revision','source_digest','configuration_digest','recipe_digest','scope_request_digest',
    'runtime_reports','bpr','planning','git','pick','expedite','pick_files')
SQL=r'''
CREATE FUNCTION mta.guard_scope_read_reference() RETURNS trigger LANGUAGE plpgsql
 SET search_path=pg_catalog,mta AS $guard$
DECLARE H mta.fresh_mta_scopereportgeneration; R mta.fresh_mta_calculationrun;
 P mta.fresh_mta_runphaseacceptance; S mta.fresh_mta_dailyphasesnapshot;
 G mta.fresh_mta_scopegitgeneration; E mta.fresh_mta_scopeexpediteparentgeneration;
 C mta.fresh_mta_scopeexpeditegeneration; Q mta.fresh_mta_scopepickgeneration;
 B mta.fresh_mta_scopesourceprojection; L mta.fresh_mta_scopeplanningprojection;
 F mta.fresh_mta_scopepickfiles; node jsonb; request_node jsonb; runtime_node jsonb;
 config_node jsonb; frozen jsonb; item text;
BEGIN
 IF TG_OP<>'INSERT' THEN RAISE EXCEPTION 'Scope read references are immutable and retained'; END IF;
 SELECT * INTO H FROM mta.fresh_mta_scopereportgeneration WHERE id=NEW.report_generation_id;
 SELECT * INTO R FROM mta.fresh_mta_calculationrun WHERE id=H.run_id FOR UPDATE;
 SELECT * INTO P FROM mta.fresh_mta_runphaseacceptance WHERE id=H.phase_id;
 SELECT * INTO S FROM mta.fresh_mta_dailyphasesnapshot WHERE id=P.snapshot_id;
 SELECT * INTO G FROM mta.fresh_mta_scopegitgeneration WHERE id=NEW.git_generation_id;
 SELECT * INTO E FROM mta.fresh_mta_scopeexpediteparentgeneration WHERE id=NEW.expedite_parent_generation_id;
 SELECT * INTO C FROM mta.fresh_mta_scopeexpeditegeneration WHERE id=E.core_generation_id;
 SELECT * INTO Q FROM mta.fresh_mta_scopepickgeneration WHERE id=C.pick_generation_id;
 SELECT * INTO B FROM mta.fresh_mta_scopesourceprojection WHERE generation_id=H.id;
 SELECT * INTO L FROM mta.fresh_mta_scopeplanningprojection WHERE generation_id=H.id;
 SELECT * INTO F FROM mta.fresh_mta_scopepickfiles WHERE phase_id=NEW.pick_files_id;
 IF H.id IS NULL OR NOT H.sealed OR R.id IS NULL OR R.kind<>'DAILY_CHAIN'
  OR R.status NOT IN ('RUNNING','SUCCEEDED') OR P.id IS NULL OR P.run_id IS DISTINCT FROM R.id
  OR P.phase<>'BPR' OR NOT P.state_sealed OR P.input_digest IS DISTINCT FROM R.input_digest
  OR S.id IS NULL OR S.acceptance_id IS DISTINCT FROM P.id OR S.run_id IS DISTINCT FROM R.id
  OR H.configuration_digest IS DISTINCT FROM S.manifest->'references'->>'profile'
  OR H.action_revision IS DISTINCT FROM mta.scope_action_revision(R.id)
  OR G.id IS NULL OR NOT G.sealed OR G.report_generation_id IS DISTINCT FROM H.id
  OR E.id IS NULL OR NOT E.sealed OR C.id IS NULL OR NOT C.sealed OR Q.id IS NULL OR NOT Q.sealed
  OR C.report_generation_id IS DISTINCT FROM H.id OR E.core_generation_digest IS DISTINCT FROM C.digest
  OR B.generation_id IS NULL OR NOT B.sealed OR L.generation_id IS NULL OR NOT L.sealed
  OR G.report_generation_digest IS DISTINCT FROM H.digest OR C.report_generation_digest IS DISTINCT FROM H.digest
  OR B.report_generation_digest IS DISTINCT FROM H.digest OR L.report_generation_digest IS DISTINCT FROM H.digest
  OR G.source_projection_digest IS DISTINCT FROM B.digest OR C.source_projection_digest IS DISTINCT FROM B.digest
  OR L.source_projection_digest IS DISTINCT FROM B.digest
  OR F.phase_id IS DISTINCT FROM P.id OR F.source_digest IS DISTINCT FROM P.digest
  OR NEW.id::text IS DISTINCT FROM current_setting('fresh.scope_read_reference',true)
  OR NEW.digest !~ '^[0-9a-f]{64}$' OR NEW.recipe_digest !~ '^[0-9a-f]{64}$'
  OR NEW.runtime_reports_digest !~ '^[0-9a-f]{64}$'
  OR NOT EXISTS(SELECT 1 FROM mta.fresh_mta_mdmdailyinputcapture D WHERE D.run_id=R.id
    AND D.source_id=P.source_id AND D.revision_digest=P.capture_digest AND D.status IN ('CAPTURED','CONSUMED'))
  THEN RAISE EXCEPTION 'Scope read reference requires exact accepted prepared owners'; END IF;
 IF EXISTS(SELECT 1 FROM (VALUES
    (G.run_id,G.phase_id,G.action_revision,G.source_digest,G.configuration_digest),
    (E.run_id,E.phase_id,E.action_revision,E.source_digest,E.configuration_digest),
    (C.run_id,C.phase_id,C.action_revision,C.source_digest,C.configuration_digest),
    (Q.run_id,Q.phase_id,Q.action_revision,Q.source_digest,Q.configuration_digest))
    V(run_id,phase_id,action_revision,source_digest,configuration_digest)
    WHERE (V.run_id,V.phase_id,V.action_revision,V.source_digest,V.configuration_digest)
      IS DISTINCT FROM (R.id,P.id,H.action_revision,H.source_digest,H.configuration_digest)) THEN
  RAISE EXCEPTION 'Scope read reference component owners differ'; END IF;
 IF jsonb_typeof(NEW.metadata) IS DISTINCT FROM 'object' OR octet_length(NEW.metadata::text)>32768
  OR (SELECT count(*) FROM jsonb_object_keys(NEW.metadata))<>19
  OR NOT NEW.metadata ?& ARRAY[__KEYS__]
  OR NEW.metadata->>'schema' IS DISTINCT FROM 'fresh-bpr-read-reference-v1'
  OR NEW.metadata->>'run_id' IS DISTINCT FROM R.id::text
  OR NEW.metadata->>'phase_id' IS DISTINCT FROM P.id::text
  OR NEW.metadata->>'phase_digest' IS DISTINCT FROM P.digest
  OR NEW.metadata->>'snapshot_digest' IS DISTINCT FROM S.state_digest
  OR NEW.metadata->>'input_digest' IS DISTINCT FROM R.input_digest
  OR NEW.metadata->>'input_manifest_digest' IS DISTINCT FROM R.input_manifest_digest
  OR NEW.metadata->>'action_revision' IS DISTINCT FROM H.action_revision::text
  OR NEW.metadata->>'source_digest' IS DISTINCT FROM H.source_digest
  OR NEW.metadata->>'configuration_digest' IS DISTINCT FROM H.configuration_digest
  OR NEW.metadata->>'recipe_digest' IS DISTINCT FROM NEW.recipe_digest
  OR coalesce(NEW.metadata->>'scope_request_digest','') !~ '^[0-9a-f]{64}$'
  OR NEW.metadata->'git'->>'generation_id' IS DISTINCT FROM G.id::text
  OR NEW.metadata->'git'->>'digest' IS DISTINCT FROM G.digest
  OR NEW.metadata->'planning'->>'planning_digest' IS DISTINCT FROM L.digest
  OR NEW.metadata->'bpr'->>'generation_id' IS DISTINCT FROM H.id::text
  OR NEW.metadata->'bpr'->>'projection_digest' IS DISTINCT FROM B.digest
  OR NEW.metadata->'bpr'->>'report_digest' IS DISTINCT FROM H.digest
  OR NEW.metadata->'pick'->>'generation_id' IS DISTINCT FROM Q.id::text
  OR NEW.metadata->'pick'->>'digest' IS DISTINCT FROM Q.digest
  OR NEW.metadata->'expedite'->>'parent_generation_id' IS DISTINCT FROM E.id::text
  OR NEW.metadata->'expedite'->>'parent_digest' IS DISTINCT FROM E.digest
  OR NEW.metadata->'expedite'->>'core_generation_id' IS DISTINCT FROM C.id::text
  OR NEW.metadata->'expedite'->>'core_digest' IS DISTINCT FROM C.digest
  OR NEW.metadata->'expedite'->>'transit_generation_id' IS DISTINCT FROM G.transit_generation_id::text
  OR NEW.metadata->'expedite'->>'transit_digest' IS DISTINCT FROM G.transit_generation_digest
  OR NEW.metadata->'pick_files'->>'digest' IS DISTINCT FROM F.digest
  OR NEW.metadata->'pick_files'->>'directory' IS DISTINCT FROM F.directory::text
  OR NEW.metadata->'pick_files'->'files' IS DISTINCT FROM F.files THEN
  RAISE EXCEPTION 'Scope read reference dependency metadata differs'; END IF;
 -- The new native entry uses its physical V2/V3 scope request. Unsupported
 -- capture wrappers deny until their own SQL provenance is qualified.
 IF R.input_payload->>'schema' NOT IN ('fresh-daily-input-manifest-v2','fresh-daily-input-manifest-v3')
  OR left(current_database(),13)<>'VFTEST_Fresh_' THEN
  RAISE EXCEPTION 'Scope read reference requires applicable owned test configuration'; END IF;
 node=R.input_payload->'tree';
 FOREACH item IN ARRAY ARRAY['scope_request','runtime_reports'] LOOP
  SELECT value->1 INTO node FROM jsonb_array_elements(node->'object') WHERE value->>0=item;
  IF node IS NULL THEN RAISE EXCEPTION 'Scope read configuration is missing'; END IF;
  IF item='scope_request' THEN request_node=node; END IF;
 END LOOP;
 runtime_node=node;
 SELECT value->1 INTO config_node FROM jsonb_array_elements(runtime_node->'object') WHERE value->>0='configuration';
 SELECT value->1 INTO node FROM jsonb_array_elements(config_node->'object') WHERE value->>0='RuntimeReports';
 IF node IS DISTINCT FROM '{"empty":true}'::jsonb THEN
  RAISE EXCEPTION 'Explicit empty RuntimeReports configuration required'; END IF;
 SELECT jsonb_object_agg(value->>0,value->1->'scalar') INTO frozen
  FROM jsonb_array_elements(config_node->'object') WHERE value->>0<>'RuntimeReports';
 frozen=frozen||'{"RuntimeReports":[]}'::jsonb;
 SELECT jsonb_build_object('schema',max(value->1->>'scalar') FILTER(WHERE value->>0='schema'),
    'sha256',max(value->1->>'scalar') FILTER(WHERE value->>0='sha256'),
    'configuration_digest',max(value->1->>'scalar') FILTER(WHERE value->>0='configuration_digest'),
    'configuration',frozen) INTO frozen FROM jsonb_array_elements(runtime_node->'object');
 IF NEW.metadata->'runtime_reports' IS DISTINCT FROM frozen
  OR frozen->>'schema' IS DISTINCT FROM 'fresh-scoped-runtime-reports-reference-v1'
  OR frozen->'configuration'->>'schema' IS DISTINCT FROM 'fresh-scoped-test-runtime-reports-v1'
  OR frozen->'configuration'->>'purpose' IS DISTINCT FROM 'owned-scoped-test'
  OR frozen->>'configuration_digest' IS DISTINCT FROM NEW.runtime_reports_digest
  OR NOT EXISTS(SELECT 1 FROM jsonb_array_elements(request_node->'object')
    WHERE value->>0='schema' AND value->1->>'scalar'='fresh-native-scope-request-v2')
  OR NOT EXISTS(SELECT 1 FROM jsonb_array_elements(request_node->'object')
    WHERE value->>0='scope' AND value->1->>'scalar'='UptoBPR') THEN
  RAISE EXCEPTION 'Scope read captured configuration differs'; END IF;
 RETURN NEW;
END $guard$;
CREATE FUNCTION mta.deny_scope_read_truncate() RETURNS trigger LANGUAGE plpgsql
 SET search_path=pg_catalog,mta AS $guard$
BEGIN RAISE EXCEPTION 'Scope read references cannot be truncated'; END $guard$;
CREATE TRIGGER scope_read_reference_guard BEFORE INSERT OR UPDATE OR DELETE
 ON mta.fresh_mta_scopereadreference FOR EACH ROW EXECUTE FUNCTION mta.guard_scope_read_reference();
CREATE TRIGGER scope_read_no_truncate BEFORE TRUNCATE
 ON mta.fresh_mta_scopereadreference FOR EACH STATEMENT EXECUTE FUNCTION mta.deny_scope_read_truncate();
REVOKE ALL ON FUNCTION mta.guard_scope_read_reference() FROM PUBLIC;
REVOKE ALL ON FUNCTION mta.deny_scope_read_truncate() FROM PUBLIC;
'''.replace('__KEYS__',','.join("'"+key+"'" for key in KEYS))
for op,refs in (('INSERT','NEW TABLE AS new_rows'),('UPDATE','OLD TABLE AS old_rows NEW TABLE AS new_rows'),('DELETE','OLD TABLE AS old_rows'),('TRUNCATE','')):
    SQL+=('CREATE TRIGGER ingestion_watch_'+op.lower()+' AFTER '+op+' ON mta.'+TABLE+
        (' REFERENCING '+refs if refs else '')+" FOR EACH STATEMENT EXECUTE FUNCTION mta.ingestion_watch('operational');\n")
SQL+=base.transition(OLD,NEW)
REVERSE=("DO $pre$ BEGIN IF EXISTS(SELECT 1 FROM mta."+TABLE+
    ") THEN RAISE EXCEPTION 'Retained scope read references require a compatible forward release'; END IF; END $pre$;\n")
REVERSE+=base.transition(NEW,OLD)
for op in ('insert','update','delete','truncate'):REVERSE+='DROP TRIGGER ingestion_watch_'+op+' ON mta.'+TABLE+';\n'
REVERSE+='DROP TRIGGER scope_read_reference_guard ON mta.'+TABLE+';\nDROP TRIGGER scope_read_no_truncate ON mta.'+TABLE+';\n'
for name in ('guard_scope_read_reference','deny_scope_read_truncate'):REVERSE+='DROP FUNCTION mta.'+name+'();\n'


class Migration(migrations.Migration):
    dependencies=[('fresh_mta','0217_scope_read_reference')]
    operations=[migrations.RunSQL(SQL,REVERSE)]
