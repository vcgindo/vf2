"""Atomic immutable BPR report facts, separate from terminal Full ownership."""
from importlib import import_module
from django.db import migrations

TABLES={
    'ExcessInventoryDetails':'fresh_mta_scopeexcessrow',
    'OrderFulfillmentSummary':'fresh_mta_scopefulfillmentsummaryrow',
    'OrderFulfillmentDetails':'fresh_mta_scopefulfillmentdetailrow',
    'ExpediteDispatches':'fresh_mta_scopeexpediterow',
    'PickPost':'fresh_mta_scopepickpostrow',
}
GENERATION='fresh_mta_scopereportgeneration'

# The predicates classify only these new, separately guarded derived tables.
# No current_setting controls ingestion invalidation and no Full case changes.
VALID=r"""P.id IS NULL OR P.phase IS DISTINCT FROM 'BPR' OR NOT P.state_sealed
 OR P.snapshot_id IS NULL OR P.run_id IS DISTINCT FROM R.id
 OR R.kind IS DISTINCT FROM 'DAILY_CHAIN' OR R.status NOT IN ('RUNNING','SUCCEEDED')
 OR C.run_id IS NULL OR C.status NOT IN ('CAPTURED','CONSUMED')
 OR P.source_id IS DISTINCT FROM C.source_id OR P.capture_digest IS DISTINCT FROM C.revision_digest
 OR P.input_digest IS DISTINCT FROM R.input_digest OR S.acceptance_id IS DISTINCT FROM P.id
 OR S.run_id IS DISTINCT FROM R.id OR S.phase IS DISTINCT FROM 'BPR'
 OR G.configuration_digest IS DISTINCT FROM S.manifest->'references'->>'profile'
 OR G.action_revision IS DISTINCT FROM mta.scope_action_revision(R.id)"""
JOINS=r"""LEFT JOIN mta.fresh_mta_runphaseacceptance P ON P.id=G.phase_id
 LEFT JOIN mta.fresh_mta_calculationrun R ON R.id=G.run_id
 LEFT JOIN mta.fresh_mta_mdmdailyinputcapture C ON C.run_id=R.id
 LEFT JOIN mta.fresh_mta_dailyphasesnapshot S ON S.id=P.snapshot_id"""
OLD=import_module('mta.runtime.migrations.0196_scope_pick_capture_key').NEW
ADDED=(r"""
 IF TG_TABLE_SCHEMA='mta' AND TG_TABLE_NAME='fresh_mta_scopereportgeneration'
  AND TG_OP IN ('INSERT','UPDATE') THEN
  IF NOT EXISTS(SELECT 1 FROM new_rows G """+JOINS+' WHERE '+VALID+r""") THEN RETURN NULL; END IF;
 END IF;
 IF TG_TABLE_SCHEMA='mta' AND TG_TABLE_NAME=ANY(ARRAY["""+
    ','.join("'"+table+"'" for table in TABLES.values())+r"""]) AND TG_OP='INSERT' THEN
  IF NOT EXISTS(SELECT 1 FROM (SELECT DISTINCT generation_id FROM new_rows) K
   LEFT JOIN mta.fresh_mta_scopereportgeneration G ON G.id=K.generation_id """+JOINS+
    ' WHERE G.id IS NULL OR '+VALID+r""") THEN RETURN NULL; END IF;
 END IF;
""")
assert OLD.count(" IF kind='immutable' THEN")==1
NEW=OLD.replace(" IF kind='immutable' THEN",ADDED+" IF kind='immutable' THEN",1)

SQL=r'''
CREATE FUNCTION mta.guard_scope_report_generation() RETURNS trigger LANGUAGE plpgsql
 SET search_path=pg_catalog,mta AS $guard$
DECLARE P mta.fresh_mta_runphaseacceptance; R mta.fresh_mta_calculationrun;
 S mta.fresh_mta_dailyphasesnapshot; item record; bag jsonb; n bigint; lo bigint; hi bigint;
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'Scope report generations are retained'; END IF;
 SELECT * INTO R FROM mta.fresh_mta_calculationrun WHERE id=NEW.run_id FOR UPDATE;
 SELECT * INTO P FROM mta.fresh_mta_runphaseacceptance WHERE id=NEW.phase_id;
 SELECT * INTO S FROM mta.fresh_mta_dailyphasesnapshot WHERE id=P.snapshot_id;
 IF R.id IS NULL OR R.kind<>'DAILY_CHAIN' OR R.status NOT IN ('RUNNING','SUCCEEDED')
  OR P.id IS NULL OR P.run_id IS DISTINCT FROM R.id OR P.phase<>'BPR' OR NOT P.state_sealed
  OR S.id IS NULL OR S.acceptance_id IS DISTINCT FROM P.id OR S.run_id IS DISTINCT FROM R.id
  OR S.phase IS DISTINCT FROM 'BPR' OR P.input_digest IS DISTINCT FROM R.input_digest
  OR NEW.configuration_digest IS DISTINCT FROM S.manifest->'references'->>'profile'
  OR NEW.action_revision IS DISTINCT FROM mta.scope_action_revision(R.id)
  OR NEW.id::text IS DISTINCT FROM current_setting('fresh.scope_report_generation',true)
  OR NEW.source_digest !~ '^[0-9a-f]{64}$' OR NEW.recipe_digest !~ '^[0-9a-f]{64}$'
  OR NEW.configuration_digest !~ '^[0-9a-f]{64}$'
  OR NOT EXISTS(SELECT 1 FROM mta.fresh_mta_mdmdailyinputcapture C WHERE C.run_id=R.id
    AND C.source_id=P.source_id AND C.revision_digest=P.capture_digest
    AND C.status IN ('CAPTURED','CONSUMED')) THEN
  RAISE EXCEPTION 'Scope reports require their exact accepted BPR owner'; END IF;
 IF TG_OP='INSERT' THEN
  IF NEW.sealed OR NEW.metadata<>'{}'::jsonb OR NEW.digest<>'' OR NEW.sealed_at IS NOT NULL THEN
   RAISE EXCEPTION 'Scope report generation must start transaction-local and unsealed'; END IF;
  RETURN NEW;
 END IF;
 IF OLD.sealed OR NOT NEW.sealed OR NEW.sealed_at IS NULL OR NEW.digest !~ '^[0-9a-f]{64}$'
  OR (to_jsonb(NEW)-ARRAY['metadata','digest','sealed','sealed_at']) IS DISTINCT FROM
     (to_jsonb(OLD)-ARRAY['metadata','digest','sealed','sealed_at']) THEN
  RAISE EXCEPTION 'Scope report generation identity is immutable'; END IF;
 IF jsonb_typeof(NEW.metadata)<>'object' OR octet_length(NEW.metadata::text)>16384
  OR (SELECT count(*) FROM jsonb_object_keys(NEW.metadata))<>13
  OR NOT NEW.metadata ?& ARRAY['schema','run_id','phase_id','phase_digest','snapshot_digest',
     'input_digest','input_manifest_digest','action_revision','source_digest',
     'configuration_digest','recipe_digest','reports','generation_id']
  OR NEW.metadata->>'schema' IS DISTINCT FROM 'fresh-bpr-report-generation-v1'
  OR NEW.metadata->>'generation_id' IS DISTINCT FROM NEW.id::text
  OR NEW.metadata->>'run_id' IS DISTINCT FROM R.id::text
  OR NEW.metadata->>'phase_id' IS DISTINCT FROM P.id::text
  OR NEW.metadata->>'phase_digest' IS DISTINCT FROM P.digest
  OR NEW.metadata->>'snapshot_digest' IS DISTINCT FROM S.state_digest
  OR NEW.metadata->>'input_digest' IS DISTINCT FROM R.input_digest
  OR NEW.metadata->>'input_manifest_digest' IS DISTINCT FROM R.input_manifest_digest
  OR NEW.metadata->>'action_revision' IS DISTINCT FROM NEW.action_revision::text
  OR NEW.metadata->>'source_digest' IS DISTINCT FROM NEW.source_digest
  OR NEW.metadata->>'configuration_digest' IS DISTINCT FROM NEW.configuration_digest
  OR NEW.metadata->>'recipe_digest' IS DISTINCT FROM NEW.recipe_digest THEN
  RAISE EXCEPTION 'Scope report generation seal identity differs'; END IF;
 bag=NEW.metadata->'reports';
 IF jsonb_typeof(bag)<>'object' OR (SELECT count(*) FROM jsonb_object_keys(bag))<>9
  OR NOT bag ?& ARRAY['schema','source_digest','recipe_digest','phase_id','phase_digest',
      'action_revision','display_date','producers','images']
  OR bag->>'schema' IS DISTINCT FROM 'fresh-bpr-report-rows-v1'
  OR bag->>'source_digest' IS DISTINCT FROM NEW.source_digest
  OR bag->>'phase_id' IS DISTINCT FROM P.id::text OR bag->>'phase_digest' IS DISTINCT FROM P.digest
  OR bag->>'action_revision' IS DISTINCT FROM NEW.action_revision::text
  OR bag->>'display_date' IS DISTINCT FROM R.business_date::text
  OR coalesce(bag->>'recipe_digest','') !~ '^[0-9a-f]{64}$'
  OR jsonb_typeof(bag->'images') IS DISTINCT FROM 'object'
  OR jsonb_typeof(bag->'producers') IS DISTINCT FROM 'object'
  OR (SELECT count(*) FROM jsonb_object_keys(bag->'images'))<>5
  OR NOT (bag->'images') ?& ARRAY['ExcessInventoryDetails','OrderFulfillmentSummary',
      'OrderFulfillmentDetails','ExpediteDispatches','PickPost']
  OR (SELECT count(*) FROM jsonb_object_keys(bag->'producers'))<>4
  OR NOT (bag->'producers') ?& ARRAY['excess','fulfillment','expedite','pick_post']
  OR coalesce(bag->'producers'->>'excess','') !~ '^[0-9a-f]{64}$'
  OR coalesce(bag->'producers'->>'fulfillment','') !~ '^[0-9a-f]{64}$'
  OR coalesce(bag->'producers'->>'expedite','') !~ '^[0-9a-f]{64}$'
  OR jsonb_typeof(bag->'producers'->'pick_post') IS DISTINCT FROM 'object'
  OR (SELECT count(*) FROM jsonb_object_keys(bag->'producers'->'pick_post'))<>3
  OR NOT (bag->'producers'->'pick_post') ?& ARRAY['PostRationEcoAvailability.sql',
      'CalculatePenetrationAndColor.sql','UpdatePostRationPipelineInventoryPen.sql'] THEN
  RAISE EXCEPTION 'Scope report finite consumer metadata differs'; END IF;
 FOR item IN SELECT value FROM jsonb_each_text(bag->'producers'->'pick_post') LOOP
  IF item.value !~ '^[0-9a-f]{64}$' THEN RAISE EXCEPTION 'Scope report producer identity differs'; END IF;
 END LOOP;
 FOR item IN SELECT * FROM (VALUES
  ('ExcessInventoryDetails','fresh_mta_scopeexcessrow'),
  ('OrderFulfillmentSummary','fresh_mta_scopefulfillmentsummaryrow'),
  ('OrderFulfillmentDetails','fresh_mta_scopefulfillmentdetailrow'),
  ('ExpediteDispatches','fresh_mta_scopeexpediterow'),
  ('PickPost','fresh_mta_scopepickpostrow')) V(name,relation) LOOP
  bag=NEW.metadata->'reports'->'images'->item.name;
  IF jsonb_typeof(bag) IS DISTINCT FROM 'object' OR (SELECT count(*) FROM jsonb_object_keys(bag))<>2
   OR NOT bag ?& ARRAY['count','digest'] OR jsonb_typeof(bag->'count') IS DISTINCT FROM 'number'
   OR coalesce(bag->>'count','') !~ '^(0|[1-9][0-9]*)$'
   OR coalesce(bag->>'digest','') !~ '^[0-9a-f]{64}$' THEN
   RAISE EXCEPTION 'Scope report bag metadata differs'; END IF;
  EXECUTE format('SELECT count(*),min(ordinal),max(ordinal) FROM mta.%I WHERE generation_id=$1',item.relation)
   INTO n,lo,hi USING NEW.id;
  IF n IS DISTINCT FROM (bag->>'count')::bigint
   OR (n>0 AND (lo IS DISTINCT FROM 0 OR hi IS DISTINCT FROM n-1)) THEN
   RAISE EXCEPTION 'Scope report bag population/order differs'; END IF;
 END LOOP;
 RETURN NEW;
END $guard$;
CREATE FUNCTION mta.guard_scope_report_rows() RETURNS trigger LANGUAGE plpgsql
 SET search_path=pg_catalog,mta AS $guard$
DECLARE owner record;
BEGIN
 IF TG_OP<>'INSERT' THEN RAISE EXCEPTION 'Scope report rows are immutable'; END IF;
 FOR owner IN SELECT DISTINCT generation_id FROM new_rows LOOP
  PERFORM 1 FROM mta.fresh_mta_scopereportgeneration G
   JOIN mta.fresh_mta_runphaseacceptance P ON P.id=G.phase_id
   JOIN mta.fresh_mta_calculationrun R ON R.id=G.run_id
   WHERE G.id=owner.generation_id AND NOT G.sealed AND G.run_id=P.run_id
     AND P.phase='BPR' AND P.state_sealed AND R.kind='DAILY_CHAIN'
     AND R.status IN ('RUNNING','SUCCEEDED')
     AND G.id::text=current_setting('fresh.scope_report_generation',true)
     AND G.action_revision=mta.scope_action_revision(R.id) FOR SHARE OF G,R;
  IF NOT FOUND THEN RAISE EXCEPTION 'Scope report row requires its unsealed generation'; END IF;
 END LOOP;
 RETURN NULL;
END $guard$;
CREATE FUNCTION mta.require_scope_report_complete() RETURNS trigger LANGUAGE plpgsql
 SET search_path=pg_catalog,mta AS $guard$
BEGIN
 IF NOT EXISTS(SELECT 1 FROM mta.fresh_mta_scopereportgeneration G WHERE G.id=NEW.id AND G.sealed) THEN
  RAISE EXCEPTION 'Unsealed scope report generation cannot commit'; END IF;
 RETURN NULL;
END $guard$;
CREATE FUNCTION mta.deny_scope_report_truncate() RETURNS trigger LANGUAGE plpgsql
 SET search_path=pg_catalog,mta AS $guard$
BEGIN RAISE EXCEPTION 'Scope report generations and rows cannot be truncated'; END $guard$;
'''
for name in ('guard_scope_report_generation','guard_scope_report_rows',
             'require_scope_report_complete','deny_scope_report_truncate'):
    SQL+='REVOKE ALL ON FUNCTION mta.'+name+'() FROM PUBLIC;\n'
SQL+='''CREATE TRIGGER scope_report_generation_guard BEFORE INSERT OR UPDATE OR DELETE
 ON mta.fresh_mta_scopereportgeneration FOR EACH ROW EXECUTE FUNCTION mta.guard_scope_report_generation();
CREATE CONSTRAINT TRIGGER scope_report_complete AFTER INSERT OR UPDATE
 ON mta.fresh_mta_scopereportgeneration DEFERRABLE INITIALLY DEFERRED
 FOR EACH ROW EXECUTE FUNCTION mta.require_scope_report_complete();
'''
for table in TABLES.values():
    for op,refs in (('INSERT','NEW TABLE AS new_rows'),
            ('UPDATE','OLD TABLE AS old_rows NEW TABLE AS new_rows'),('DELETE','OLD TABLE AS old_rows')):
        SQL+=('CREATE TRIGGER scope_report_rows_'+op.lower()+' AFTER '+op+' ON mta.'+table+
              ' REFERENCING '+refs+' FOR EACH STATEMENT EXECUTE FUNCTION mta.guard_scope_report_rows();\n')
for table in (GENERATION,*TABLES.values()):
    SQL+=('CREATE TRIGGER scope_report_no_truncate BEFORE TRUNCATE ON mta.'+table+
          ' FOR EACH STATEMENT EXECUTE FUNCTION mta.deny_scope_report_truncate();\n')
    for op,refs in (('INSERT','NEW TABLE AS new_rows'),
            ('UPDATE','OLD TABLE AS old_rows NEW TABLE AS new_rows'),
            ('DELETE','OLD TABLE AS old_rows'),('TRUNCATE','')):
        SQL+=('CREATE TRIGGER ingestion_watch_'+op.lower()+' AFTER '+op+' ON mta.'+table+
              (' REFERENCING '+refs if refs else '')+
              " FOR EACH STATEMENT EXECUTE FUNCTION mta.ingestion_watch('operational');\n")
transition=import_module('mta.runtime.migrations.0195_scope_pick_revision_ownership').transition
SQL+=transition(OLD,NEW)
REVERSE="""DO $pre$ BEGIN IF EXISTS(SELECT 1 FROM mta.fresh_mta_scopereportgeneration) THEN
 RAISE EXCEPTION 'Accepted scope reports require a compatible forward release'; END IF; END $pre$;
"""+transition(NEW,OLD)
for table in (GENERATION,*TABLES.values()):
    for op in ('insert','update','delete','truncate'):
        REVERSE+='DROP TRIGGER ingestion_watch_'+op+' ON mta.'+table+';\n'
    REVERSE+='DROP TRIGGER scope_report_no_truncate ON mta.'+table+';\n'
    if table!=GENERATION:
        for op in ('insert','update','delete'):
            REVERSE+='DROP TRIGGER scope_report_rows_'+op+' ON mta.'+table+';\n'
REVERSE+='''DROP TRIGGER scope_report_generation_guard ON mta.fresh_mta_scopereportgeneration;
DROP TRIGGER scope_report_complete ON mta.fresh_mta_scopereportgeneration;
DROP FUNCTION mta.guard_scope_report_generation(); DROP FUNCTION mta.guard_scope_report_rows();
DROP FUNCTION mta.require_scope_report_complete(); DROP FUNCTION mta.deny_scope_report_truncate();
'''


class Migration(migrations.Migration):
    dependencies=[('fresh_mta','0197_scope_report_generation')]
    operations=[migrations.RunSQL(SQL,REVERSE)]
