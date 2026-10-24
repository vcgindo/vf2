"""Immutable generation-owned BPR candidates and two Planning masters."""
from importlib import import_module
from django.db import migrations

prior=import_module('mta.runtime.migrations.0198_scope_report_guards')
TABLES={
    'bpr_candidates':('fresh_mta_scopebprcandidaterow','ordinal',True),
    'bpr_master':('fresh_mta_scopeplanningbprrow','source_ordinal',True),
    'git_master':('fresh_mta_scopeplanninggitrow','rationed_ordinal',False),
}
PROJECTION='fresh_mta_scopesourceprojection'
OLD=prior.NEW
ADDED=(r"""
 IF TG_TABLE_SCHEMA='mta' AND TG_TABLE_NAME='fresh_mta_scopesourceprojection'
  AND TG_OP IN ('INSERT','UPDATE') THEN
  IF NOT EXISTS(SELECT 1 FROM new_rows N
   LEFT JOIN mta.fresh_mta_scopereportgeneration G ON G.id=N.generation_id """+prior.JOINS+
   ' WHERE G.id IS NULL OR NOT G.sealed OR N.report_generation_digest IS DISTINCT FROM G.digest OR '+prior.VALID+
   r""") THEN RETURN NULL; END IF;
 END IF;
 IF TG_TABLE_SCHEMA='mta' AND TG_TABLE_NAME=ANY(ARRAY["""+
   ','.join("'"+table+"'" for table,_ordinal,_dense in TABLES.values())+r"""]) AND TG_OP='INSERT' THEN
  IF NOT EXISTS(SELECT 1 FROM (SELECT DISTINCT generation_id FROM new_rows) K
   LEFT JOIN mta.fresh_mta_scopereportgeneration G ON G.id=K.generation_id
   LEFT JOIN mta.fresh_mta_scopesourceprojection X ON X.generation_id=G.id """+prior.JOINS+
   ' WHERE G.id IS NULL OR NOT G.sealed OR X.generation_id IS NULL OR X.sealed OR '+prior.VALID+
   r""") THEN RETURN NULL; END IF;
 END IF;
""")
assert OLD.count(" IF kind='immutable' THEN")==1
NEW=OLD.replace(" IF kind='immutable' THEN",ADDED+" IF kind='immutable' THEN",1)

SQL=r'''
CREATE FUNCTION mta.guard_scope_source_projection() RETURNS trigger LANGUAGE plpgsql
 SET search_path=pg_catalog,mta AS $guard$
DECLARE G mta.fresh_mta_scopereportgeneration; R mta.fresh_mta_calculationrun;
 P mta.fresh_mta_runphaseacceptance; item record; bag jsonb; n bigint; lo bigint; hi bigint;
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'Scope source projections are retained'; END IF;
 SELECT * INTO G FROM mta.fresh_mta_scopereportgeneration WHERE id=NEW.generation_id;
 SELECT * INTO R FROM mta.fresh_mta_calculationrun WHERE id=G.run_id FOR UPDATE;
 SELECT * INTO P FROM mta.fresh_mta_runphaseacceptance WHERE id=G.phase_id;
 IF G.id IS NULL OR NOT G.sealed OR R.id IS NULL OR R.kind<>'DAILY_CHAIN'
  OR R.status NOT IN ('RUNNING','SUCCEEDED') OR P.id IS NULL OR NOT P.state_sealed
  OR P.phase IS DISTINCT FROM 'BPR' OR P.run_id IS DISTINCT FROM R.id
  OR G.action_revision IS DISTINCT FROM mta.scope_action_revision(R.id)
  OR NEW.report_generation_digest IS DISTINCT FROM G.digest
  OR NEW.recipe_digest !~ '^[0-9a-f]{64}$'
  OR NEW.generation_id::text IS DISTINCT FROM current_setting('fresh.scope_source_generation',true) THEN
  RAISE EXCEPTION 'Scope source projection requires its exact sealed BPR report generation'; END IF;
 IF TG_OP='INSERT' THEN
  IF NEW.sealed OR NEW.metadata<>'{}'::jsonb OR NEW.digest<>'' OR NEW.sealed_at IS NOT NULL THEN
   RAISE EXCEPTION 'Scope source projection starts transaction-local and unsealed'; END IF;
  RETURN NEW;
 END IF;
 IF OLD.sealed OR NOT NEW.sealed OR NEW.sealed_at IS NULL OR NEW.digest !~ '^[0-9a-f]{64}$'
  OR (to_jsonb(NEW)-ARRAY['metadata','digest','sealed','sealed_at']) IS DISTINCT FROM
     (to_jsonb(OLD)-ARRAY['metadata','digest','sealed','sealed_at']) THEN
  RAISE EXCEPTION 'Scope source projection identity is immutable'; END IF;
 IF jsonb_typeof(NEW.metadata) IS DISTINCT FROM 'object' OR octet_length(NEW.metadata::text)>8192
  OR (SELECT count(*) FROM jsonb_object_keys(NEW.metadata))<>9
  OR NOT NEW.metadata ?& ARRAY['schema','generation_id','report_generation_digest','phase_id',
      'phase_digest','source_digest','action_revision','recipe_digest','images']
  OR NEW.metadata->>'schema' IS DISTINCT FROM 'fresh-bpr-source-projection-v1'
  OR NEW.metadata->>'generation_id' IS DISTINCT FROM G.id::text
  OR NEW.metadata->>'report_generation_digest' IS DISTINCT FROM G.digest
  OR NEW.metadata->>'phase_id' IS DISTINCT FROM P.id::text
  OR NEW.metadata->>'phase_digest' IS DISTINCT FROM P.digest
  OR NEW.metadata->>'source_digest' IS DISTINCT FROM G.source_digest
  OR NEW.metadata->>'action_revision' IS DISTINCT FROM G.action_revision::text
  OR NEW.metadata->>'recipe_digest' IS DISTINCT FROM NEW.recipe_digest
  OR jsonb_typeof(NEW.metadata->'images') IS DISTINCT FROM 'object'
  OR (SELECT count(*) FROM jsonb_object_keys(NEW.metadata->'images'))<>3
  OR NOT (NEW.metadata->'images') ?& ARRAY['bpr_candidates','bpr_master','git_master'] THEN
  RAISE EXCEPTION 'Scope source projection finite metadata differs'; END IF;
 FOR item IN SELECT * FROM (VALUES
  ('bpr_candidates','fresh_mta_scopebprcandidaterow','ordinal',true),
  ('bpr_master','fresh_mta_scopeplanningbprrow','source_ordinal',true),
  ('git_master','fresh_mta_scopeplanninggitrow','rationed_ordinal',false)) V(name,relation,ordinal,dense) LOOP
  bag=NEW.metadata->'images'->item.name;
  IF jsonb_typeof(bag) IS DISTINCT FROM 'object' OR (SELECT count(*) FROM jsonb_object_keys(bag))<>2
   OR NOT bag ?& ARRAY['count','digest'] OR jsonb_typeof(bag->'count') IS DISTINCT FROM 'number'
   OR coalesce(bag->>'count','') !~ '^(0|[1-9][0-9]*)$'
   OR coalesce(bag->>'digest','') !~ '^[0-9a-f]{64}$' THEN
   RAISE EXCEPTION 'Scope prepared bag metadata differs'; END IF;
  EXECUTE format('SELECT count(*),min(%I),max(%I) FROM mta.%I WHERE generation_id=$1',
    item.ordinal,item.ordinal,item.relation) INTO n,lo,hi USING G.id;
  IF n IS DISTINCT FROM (bag->>'count')::bigint OR (n>0 AND (lo<0 OR
       (item.dense AND (lo IS DISTINCT FROM 0 OR hi IS DISTINCT FROM n-1)))) THEN
   RAISE EXCEPTION 'Scope prepared bag population/order differs'; END IF;
 END LOOP;
 IF EXISTS(SELECT 1 FROM mta.fresh_mta_scopeplanninggitrow
   WHERE generation_id=G.id AND standard_ordinal<0) THEN
  RAISE EXCEPTION 'Scope GIT source ordinal differs'; END IF;
 RETURN NEW;
END $guard$;
CREATE FUNCTION mta.guard_scope_source_rows() RETURNS trigger LANGUAGE plpgsql
 SET search_path=pg_catalog,mta AS $guard$
DECLARE owner record;
BEGIN
 IF TG_OP<>'INSERT' THEN RAISE EXCEPTION 'Scope prepared source rows are immutable'; END IF;
 FOR owner IN SELECT DISTINCT generation_id FROM new_rows LOOP
  PERFORM 1 FROM mta.fresh_mta_scopesourceprojection X
   JOIN mta.fresh_mta_scopereportgeneration G ON G.id=X.generation_id
   JOIN mta.fresh_mta_calculationrun R ON R.id=G.run_id
   WHERE X.generation_id=owner.generation_id AND NOT X.sealed AND G.sealed
     AND X.report_generation_digest=G.digest AND R.kind='DAILY_CHAIN'
     AND R.status IN ('RUNNING','SUCCEEDED')
     AND G.action_revision=mta.scope_action_revision(R.id)
     AND G.id::text=current_setting('fresh.scope_source_generation',true) FOR SHARE OF X,R;
  IF NOT FOUND THEN RAISE EXCEPTION 'Scope source row requires its unsealed projection'; END IF;
 END LOOP;
 RETURN NULL;
END $guard$;
CREATE FUNCTION mta.require_scope_source_complete() RETURNS trigger LANGUAGE plpgsql
 SET search_path=pg_catalog,mta AS $guard$
BEGIN
 IF NOT EXISTS(SELECT 1 FROM mta.fresh_mta_scopesourceprojection
   WHERE generation_id=NEW.generation_id AND sealed) THEN
  RAISE EXCEPTION 'Unsealed scope source projection cannot commit'; END IF;
 RETURN NULL;
END $guard$;
CREATE FUNCTION mta.deny_scope_source_truncate() RETURNS trigger LANGUAGE plpgsql
 SET search_path=pg_catalog,mta AS $guard$
BEGIN RAISE EXCEPTION 'Scope source projections and rows cannot be truncated'; END $guard$;
'''
FUNCTIONS=('guard_scope_source_projection','guard_scope_source_rows',
           'require_scope_source_complete','deny_scope_source_truncate')
for name in FUNCTIONS:SQL+='REVOKE ALL ON FUNCTION mta.'+name+'() FROM PUBLIC;\n'
SQL+='''CREATE TRIGGER scope_source_projection_guard BEFORE INSERT OR UPDATE OR DELETE
 ON mta.fresh_mta_scopesourceprojection FOR EACH ROW EXECUTE FUNCTION mta.guard_scope_source_projection();
CREATE CONSTRAINT TRIGGER scope_source_complete AFTER INSERT OR UPDATE
 ON mta.fresh_mta_scopesourceprojection DEFERRABLE INITIALLY DEFERRED
 FOR EACH ROW EXECUTE FUNCTION mta.require_scope_source_complete();
'''
for table,_ordinal,_dense in TABLES.values():
    for op,refs in (('INSERT','NEW TABLE AS new_rows'),
            ('UPDATE','OLD TABLE AS old_rows NEW TABLE AS new_rows'),('DELETE','OLD TABLE AS old_rows')):
        SQL+=('CREATE TRIGGER scope_source_rows_'+op.lower()+' AFTER '+op+' ON mta.'+table+
              ' REFERENCING '+refs+' FOR EACH STATEMENT EXECUTE FUNCTION mta.guard_scope_source_rows();\n')
for table in (PROJECTION,*(item[0] for item in TABLES.values())):
    SQL+=('CREATE TRIGGER scope_source_no_truncate BEFORE TRUNCATE ON mta.'+table+
          ' FOR EACH STATEMENT EXECUTE FUNCTION mta.deny_scope_source_truncate();\n')
    for op,refs in (('INSERT','NEW TABLE AS new_rows'),
            ('UPDATE','OLD TABLE AS old_rows NEW TABLE AS new_rows'),('DELETE','OLD TABLE AS old_rows'),('TRUNCATE','')):
        SQL+=('CREATE TRIGGER ingestion_watch_'+op.lower()+' AFTER '+op+' ON mta.'+table+
              (' REFERENCING '+refs if refs else '')+
              " FOR EACH STATEMENT EXECUTE FUNCTION mta.ingestion_watch('operational');\n")
transition=import_module('mta.runtime.migrations.0195_scope_pick_revision_ownership').transition
SQL+=transition(OLD,NEW)
REVERSE="""DO $pre$ BEGIN IF EXISTS(SELECT 1 FROM mta.fresh_mta_scopesourceprojection) THEN
 RAISE EXCEPTION 'Accepted scope sources require a compatible forward release'; END IF; END $pre$;
"""+transition(NEW,OLD)
for table in (PROJECTION,*(item[0] for item in TABLES.values())):
    for op in ('insert','update','delete','truncate'):
        REVERSE+='DROP TRIGGER ingestion_watch_'+op+' ON mta.'+table+';\n'
    REVERSE+='DROP TRIGGER scope_source_no_truncate ON mta.'+table+';\n'
    if table!=PROJECTION:
        for op in ('insert','update','delete'):
            REVERSE+='DROP TRIGGER scope_source_rows_'+op+' ON mta.'+table+';\n'
REVERSE+='''DROP TRIGGER scope_source_projection_guard ON mta.fresh_mta_scopesourceprojection;
DROP TRIGGER scope_source_complete ON mta.fresh_mta_scopesourceprojection;
'''
for name in FUNCTIONS:REVERSE+='DROP FUNCTION mta.'+name+'();\n'


class Migration(migrations.Migration):
    dependencies=[('fresh_mta','0199_scope_source_projection')]
    operations=[migrations.RunSQL(SQL,REVERSE)]
