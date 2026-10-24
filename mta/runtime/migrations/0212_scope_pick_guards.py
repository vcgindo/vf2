"""Seal independent raw Pick and RRR display reference bags."""
from importlib import import_module
from django.db import migrations

base=import_module('mta.runtime.migrations.0198_scope_report_guards')
GENERATION='fresh_mta_scopepickgeneration'
TABLES={'raw':'fresh_mta_scopepickreference','rrr':'fresh_mta_scoperrrreference'}
PATHS=('sources/calculation/PickBands','reports/bpr/vf_RationedReqReport',
       'closing/dbm/SKULocStandardAttributes','closing/importer/SkuLocAttributeData',
       'closing/importer/SkuAttributeData','closing/importer/LocationAttributeData')
OLD=import_module('mta.runtime.migrations.0210_scope_git_guards').NEW
ADDED=base.ADDED.replace(base.GENERATION,GENERATION).replace(
    ','.join("'"+t+"'" for t in base.TABLES.values()),','.join("'"+t+"'" for t in TABLES.values()))
assert OLD.count(" IF kind='immutable' THEN")==1
NEW=OLD.replace(" IF kind='immutable' THEN",ADDED+" IF kind='immutable' THEN",1)
FUNCTIONS=('guard_scope_pick_view_generation','guard_scope_pick_view_rows',
           'require_scope_pick_view_complete','deny_scope_pick_view_truncate')
SQL=base.SQL.split('REVOKE ALL ON FUNCTION mta.guard_scope_report_generation()',1)[0]
SQL=SQL.replace(base.GENERATION,GENERATION).replace('scope_report','scope_pick_view')
SQL=SQL.replace("'reports'","'pick'").replace('fresh-bpr-report-generation-v1','fresh-bpr-pick-generation-v1')
SQL=SQL.replace('Scope report','Scope Pick').replace('scope report','scope Pick')
start=SQL.index(" bag=NEW.metadata->'pick';")
end=SQL.index(' RETURN NEW;',start)
SQL=SQL[:start]+r'''
 bag=NEW.metadata->'pick';
 IF jsonb_typeof(bag) IS DISTINCT FROM 'object'
  OR (SELECT count(*) FROM jsonb_object_keys(bag))<>3
  OR NOT bag ?& ARRAY['schema','inputs','images']
  OR bag->>'schema' IS DISTINCT FROM 'fresh-bpr-pick-references-v1'
  OR jsonb_typeof(bag->'inputs') IS DISTINCT FROM 'object'
  OR (SELECT count(*) FROM jsonb_object_keys(bag->'inputs'))<>6
  OR NOT (bag->'inputs') ?& ARRAY['schema','recipe_digest','run_id','source_digest','action_revision','images']
  OR bag->'inputs'->>'schema' IS DISTINCT FROM 'fresh-bpr-pick-query-sources-v1'
  OR coalesce(bag->'inputs'->>'recipe_digest','') !~ '^[0-9a-f]{64}$'
  OR bag->'inputs'->>'run_id' IS DISTINCT FROM R.id::text
  OR bag->'inputs'->>'source_digest' IS DISTINCT FROM NEW.source_digest
  OR bag->'inputs'->>'action_revision' IS DISTINCT FROM NEW.action_revision::text
  OR jsonb_typeof(bag->'inputs'->'images') IS DISTINCT FROM 'object'
  OR (SELECT count(*) FROM jsonb_object_keys(bag->'inputs'->'images'))<>6
  OR NOT (bag->'inputs'->'images') ?& ARRAY['sources/calculation/PickBands',
     'reports/bpr/vf_RationedReqReport','closing/dbm/SKULocStandardAttributes',
     'closing/importer/SkuLocAttributeData','closing/importer/SkuAttributeData',
     'closing/importer/LocationAttributeData']
  OR jsonb_typeof(bag->'images') IS DISTINCT FROM 'object'
  OR (SELECT count(*) FROM jsonb_object_keys(bag->'images'))<>2
  OR NOT (bag->'images') ?& ARRAY['raw','rrr'] THEN
  RAISE EXCEPTION 'Scope Pick finite source metadata differs'; END IF;
 FOR item IN SELECT V.path,V.node,V.binding,I.value FROM (VALUES
  ('sources/calculation/PickBands',ARRAY['consumers','pick_bands','image'],'phase/PickBand'),
  ('reports/bpr/vf_RationedReqReport',ARRAY['state','late','vf_RationedReqReport','image'],'BPR/vf_RationedReqReport'),
  ('closing/dbm/SKULocStandardAttributes',ARRAY['state','standard_attributes','image'],'Importer/SKULocStandardAttributes'),
  ('closing/importer/SkuLocAttributeData',ARRAY['state','importer','SkuLocAttributeData','image'],'Importer/SkuLocAttributeData'),
  ('closing/importer/SkuAttributeData',ARRAY['state','importer','SkuAttributeData','image'],'Importer/SkuAttributeData'),
  ('closing/importer/LocationAttributeData',ARRAY['state','importer','LocationAttributeData','image'],'Importer/LocationAttributeData')
 ) V(path,node,binding) JOIN jsonb_each(bag->'inputs'->'images') I ON I.key=V.path LOOP
  IF jsonb_typeof(item.value) IS DISTINCT FROM 'object'
   OR (SELECT count(*) FROM jsonb_object_keys(item.value))<>11
   OR NOT item.value ?& ARRAY['owner','run_id','acceptance_id','acceptance_digest',
     'snapshot_digest','action_revision','accepted_business_date','physical_image','table','rows_digest','row_count']
   OR item.value->>'owner' IS DISTINCT FROM 'accepted_BPR'
   OR item.value->>'run_id' IS DISTINCT FROM R.id::text
   OR item.value->>'acceptance_id' IS DISTINCT FROM P.id::text
   OR item.value->>'acceptance_digest' IS DISTINCT FROM P.digest
   OR item.value->>'snapshot_digest' IS DISTINCT FROM S.state_digest
   OR item.value->>'action_revision' IS DISTINCT FROM NEW.action_revision::text
   OR item.value->>'accepted_business_date' IS DISTINCT FROM R.business_date::text
   OR jsonb_typeof(item.value->'row_count') IS DISTINCT FROM 'number'
   OR coalesce(item.value->>'row_count','') !~ '^(0|[1-9][0-9]*)$'
   OR coalesce(item.value->>'rows_digest','') !~ '^[0-9a-f]{64}$'
   OR item.value->>'table' IS DISTINCT FROM item.binding
   OR item.value->>'physical_image' IS DISTINCT FROM (S.manifest->'images'->(S.manifest #>> item.node)->>'image')
   OR item.value->>'table' IS DISTINCT FROM (S.manifest->'images'->(S.manifest #>> item.node)->>'table')
   OR item.value->>'rows_digest' IS DISTINCT FROM (S.manifest->'images'->(S.manifest #>> item.node)->>'digest')
   OR item.value->'row_count' IS DISTINCT FROM (S.manifest->'images'->(S.manifest #>> item.node)->'count') THEN
   RAISE EXCEPTION 'Scope Pick accepted image provenance differs'; END IF;
 END LOOP;
 FOR item IN SELECT * FROM (VALUES ('raw','fresh_mta_scopepickreference'),
   ('rrr','fresh_mta_scoperrrreference')) V(name,relation) LOOP
  bag=NEW.metadata->'pick'->'images'->item.name;
  IF jsonb_typeof(bag) IS DISTINCT FROM 'object' OR (SELECT count(*) FROM jsonb_object_keys(bag))<>2
   OR NOT bag ?& ARRAY['count','digest'] OR jsonb_typeof(bag->'count') IS DISTINCT FROM 'number'
   OR coalesce(bag->>'count','') !~ '^(0|[1-9][0-9]*)$'
   OR coalesce(bag->>'digest','') !~ '^[0-9a-f]{64}$' THEN
   RAISE EXCEPTION 'Scope Pick reference metadata differs'; END IF;
  EXECUTE format('SELECT count(*),min(ordinal),max(ordinal) FROM mta.%I WHERE generation_id=$1',item.relation)
   INTO n,lo,hi USING NEW.id;
  IF n IS DISTINCT FROM (bag->>'count')::bigint
   OR (n>0 AND (lo IS DISTINCT FROM 0 OR hi IS DISTINCT FROM n-1)) THEN
   RAISE EXCEPTION 'Scope Pick reference population/order differs'; END IF;
 END LOOP;
 SELECT count(*) INTO n FROM mta.fresh_mta_scopepickreference WHERE generation_id=NEW.id;
 IF n IS DISTINCT FROM (NEW.metadata->'pick'->'inputs'->'images'->'sources/calculation/PickBands'->>'row_count')::bigint
  OR EXISTS(SELECT 1 FROM mta.fresh_mta_scopepickreference WHERE generation_id=NEW.id AND band_ordinal<>ordinal)
  OR EXISTS(SELECT 1 FROM mta.fresh_mta_scoperrrreference D
    LEFT JOIN mta.fresh_mta_scopepickreference A ON A.generation_id=D.generation_id AND A.ordinal=D.band_ordinal
    WHERE D.generation_id=NEW.id AND (A.id IS NULL OR A.rationed_ordinal IS DISTINCT FROM D.rationed_ordinal
     OR A.virtual IS DISTINCT FROM D.virtual)) THEN
  RAISE EXCEPTION 'Scope Pick raw source or RRR references differ'; END IF;
'''+SQL[end:]
for name in FUNCTIONS:SQL+='REVOKE ALL ON FUNCTION mta.'+name+'() FROM PUBLIC;\n'
SQL+='''CREATE TRIGGER scope_pick_view_generation_guard BEFORE INSERT OR UPDATE OR DELETE
 ON mta.fresh_mta_scopepickgeneration FOR EACH ROW EXECUTE FUNCTION mta.guard_scope_pick_view_generation();
CREATE CONSTRAINT TRIGGER scope_pick_view_complete AFTER INSERT OR UPDATE
 ON mta.fresh_mta_scopepickgeneration DEFERRABLE INITIALLY DEFERRED
 FOR EACH ROW EXECUTE FUNCTION mta.require_scope_pick_view_complete();
'''
for table in TABLES.values():
    for op,refs in (('INSERT','NEW TABLE AS new_rows'),('UPDATE','OLD TABLE AS old_rows NEW TABLE AS new_rows'),('DELETE','OLD TABLE AS old_rows')):
        SQL+=('CREATE TRIGGER scope_pick_view_rows_'+op.lower()+' AFTER '+op+' ON mta.'+table+
            ' REFERENCING '+refs+' FOR EACH STATEMENT EXECUTE FUNCTION mta.guard_scope_pick_view_rows();\n')
for table in (GENERATION,*TABLES.values()):
    SQL+=('CREATE TRIGGER scope_pick_view_no_truncate BEFORE TRUNCATE ON mta.'+table+
        ' FOR EACH STATEMENT EXECUTE FUNCTION mta.deny_scope_pick_view_truncate();\n')
    for op,refs in (('INSERT','NEW TABLE AS new_rows'),('UPDATE','OLD TABLE AS old_rows NEW TABLE AS new_rows'),
            ('DELETE','OLD TABLE AS old_rows'),('TRUNCATE','')):
        SQL+=('CREATE TRIGGER ingestion_watch_'+op.lower()+' AFTER '+op+' ON mta.'+table+
            (' REFERENCING '+refs if refs else '')+" FOR EACH STATEMENT EXECUTE FUNCTION mta.ingestion_watch('operational');\n")
SQL+=base.transition(OLD,NEW)
REVERSE="""DO $pre$ BEGIN IF EXISTS(SELECT 1 FROM mta.fresh_mta_scopepickgeneration) THEN
 RAISE EXCEPTION 'Accepted scoped Pick requires a compatible forward release'; END IF; END $pre$;
"""+base.transition(NEW,OLD)
for table in (GENERATION,*TABLES.values()):
    for op in ('insert','update','delete','truncate'):REVERSE+='DROP TRIGGER ingestion_watch_'+op+' ON mta.'+table+';\n'
    REVERSE+='DROP TRIGGER scope_pick_view_no_truncate ON mta.'+table+';\n'
    if table!=GENERATION:
        for op in ('insert','update','delete'):REVERSE+='DROP TRIGGER scope_pick_view_rows_'+op+' ON mta.'+table+';\n'
REVERSE+='''DROP TRIGGER scope_pick_view_generation_guard ON mta.fresh_mta_scopepickgeneration;
DROP TRIGGER scope_pick_view_complete ON mta.fresh_mta_scopepickgeneration;
'''
for name in FUNCTIONS:REVERSE+='DROP FUNCTION mta.'+name+'();\n'


class Migration(migrations.Migration):
    dependencies=[('fresh_mta','0211_scope_pick_generation')]
    operations=[migrations.RunSQL(SQL,REVERSE)]
