"""Seal core Expedite occurrences under report/source/raw-Pick ownership."""
from importlib import import_module
from django.db import migrations

base=import_module('mta.runtime.migrations.0198_scope_report_guards')
GENERATION='fresh_mta_scopeexpeditegeneration'
TABLES={'grid':'fresh_mta_scopeexpeditegrid','custom':'fresh_mta_scopeexpeditecustom',
    'chart':'fresh_mta_scopeexpeditechartmember','prepost':'fresh_mta_scopeexpediteprepostmember'}
OLD=import_module('mta.runtime.migrations.0212_scope_pick_guards').NEW
ADDED=base.ADDED.replace(base.GENERATION,GENERATION).replace(
    ','.join("'"+t+"'" for t in base.TABLES.values()),','.join("'"+t+"'" for t in TABLES.values()))
assert OLD.count(" IF kind='immutable' THEN")==1
NEW=OLD.replace(" IF kind='immutable' THEN",ADDED+" IF kind='immutable' THEN",1)
FUNCTIONS=('guard_scope_expedite_generation','guard_scope_expedite_rows',
    'require_scope_expedite_complete','deny_scope_expedite_truncate')
SQL=base.SQL.split('REVOKE ALL ON FUNCTION mta.guard_scope_report_generation()',1)[0]
SQL=SQL.replace(base.GENERATION,GENERATION).replace('scope_report','scope_expedite')
SQL=SQL.replace("'reports'","'occurrences'").replace('fresh-bpr-report-generation-v1','fresh-bpr-expedite-generation-v1')
SQL=SQL.replace('Scope report','Scope Expedite').replace('scope report','scope Expedite')
assert SQL.count('item record; bag jsonb;')==1
SQL=SQL.replace('item record; bag jsonb;','item record; bag jsonb; image jsonb; bad boolean;')
needle=" IF TG_OP='INSERT' THEN"
assert SQL.count(needle)==1
SQL=SQL.replace(needle,r'''
 IF NOT EXISTS(SELECT 1 FROM mta.fresh_mta_scopereportgeneration G
   JOIN mta.fresh_mta_scopesourceprojection X ON X.generation_id=G.id
   JOIN mta.fresh_mta_scopepickgeneration K ON K.id=NEW.pick_generation_id
   WHERE G.id=NEW.report_generation_id AND G.sealed AND X.sealed AND K.sealed
    AND G.digest=NEW.report_generation_digest AND X.digest=NEW.source_projection_digest
    AND X.report_generation_digest=G.digest AND K.digest=NEW.pick_generation_digest
    AND G.run_id=R.id AND K.run_id=R.id AND G.phase_id=P.id AND K.phase_id=P.id
    AND G.action_revision=NEW.action_revision AND K.action_revision=NEW.action_revision
    AND G.source_digest=NEW.source_digest AND K.source_digest=NEW.source_digest
    AND G.configuration_digest=NEW.configuration_digest AND K.configuration_digest=NEW.configuration_digest) THEN
  RAISE EXCEPTION 'Scope Expedite requires exact sealed report/source/Pick generations'; END IF;
'''+needle,1)
start=SQL.index(" bag=NEW.metadata->'occurrences';")
end=SQL.index(' RETURN NEW;',start)
SQL=SQL[:start]+r'''
 bag=NEW.metadata->'occurrences';
 IF jsonb_typeof(bag) IS DISTINCT FROM 'object' OR (SELECT count(*) FROM jsonb_object_keys(bag))<>8
  OR NOT bag ?& ARRAY['schema','report_generation_id','report_generation_digest','source_projection_digest',
     'pick_generation_id','pick_generation_digest','nms','images']
  OR bag->>'schema' IS DISTINCT FROM 'fresh-bpr-expedite-occurrences-v1'
  OR bag->>'report_generation_id' IS DISTINCT FROM NEW.report_generation_id::text
  OR bag->>'report_generation_digest' IS DISTINCT FROM NEW.report_generation_digest
  OR bag->>'source_projection_digest' IS DISTINCT FROM NEW.source_projection_digest
  OR bag->>'pick_generation_id' IS DISTINCT FROM NEW.pick_generation_id::text
  OR bag->>'pick_generation_digest' IS DISTINCT FROM NEW.pick_generation_digest
  OR jsonb_typeof(bag->'images') IS DISTINCT FROM 'object'
  OR (SELECT count(*) FROM jsonb_object_keys(bag->'images'))<>4
  OR NOT (bag->'images') ?& ARRAY['grid','custom','chart','prepost'] THEN
  RAISE EXCEPTION 'Scope Expedite finite dependency metadata differs'; END IF;
 bag=bag->'nms';
 image=S.manifest->'images'->(S.manifest #>> ARRAY['state','nms','NMSAllItems','image']);
 IF jsonb_typeof(bag) IS DISTINCT FROM 'object' OR (SELECT count(*) FROM jsonb_object_keys(bag))<>11
  OR NOT bag ?& ARRAY['owner','run_id','acceptance_id','acceptance_digest','snapshot_digest',
     'action_revision','accepted_business_date','physical_image','table','rows_digest','row_count']
  OR bag->>'owner' IS DISTINCT FROM 'accepted_BPR' OR bag->>'run_id' IS DISTINCT FROM R.id::text
  OR bag->>'acceptance_id' IS DISTINCT FROM P.id::text OR bag->>'acceptance_digest' IS DISTINCT FROM P.digest
  OR bag->>'snapshot_digest' IS DISTINCT FROM S.state_digest
  OR bag->>'action_revision' IS DISTINCT FROM NEW.action_revision::text
  OR bag->>'accepted_business_date' IS DISTINCT FROM R.business_date::text
  OR bag->>'table' IS DISTINCT FROM 'Importer/NMSAllItems'
  OR bag->>'physical_image' IS DISTINCT FROM image->>'image'
  OR bag->>'table' IS DISTINCT FROM image->>'table'
  OR bag->>'rows_digest' IS DISTINCT FROM image->>'digest'
  OR bag->'row_count' IS DISTINCT FROM image->'count'
  OR jsonb_typeof(bag->'row_count') IS DISTINCT FROM 'number'
  OR coalesce(bag->>'row_count','') !~ '^(0|[1-9][0-9]*)$'
  OR coalesce(bag->>'rows_digest','') !~ '^[0-9a-f]{64}$' THEN
  RAISE EXCEPTION 'Scope Expedite accepted NMS image provenance differs'; END IF;
 FOR item IN SELECT * FROM (VALUES
  ('grid','fresh_mta_scopeexpeditegrid',false),('custom','fresh_mta_scopeexpeditecustom',true),
  ('chart','fresh_mta_scopeexpeditechartmember',false),('prepost','fresh_mta_scopeexpediteprepostmember',true)) V(name,relation,dense) LOOP
  bag=NEW.metadata->'occurrences'->'images'->item.name;
  IF jsonb_typeof(bag) IS DISTINCT FROM 'object' OR (SELECT count(*) FROM jsonb_object_keys(bag))<>2
   OR NOT bag ?& ARRAY['count','digest'] OR jsonb_typeof(bag->'count') IS DISTINCT FROM 'number'
   OR coalesce(bag->>'count','') !~ '^(0|[1-9][0-9]*)$'
   OR coalesce(bag->>'digest','') !~ '^[0-9a-f]{64}$' THEN
   RAISE EXCEPTION 'Scope Expedite bag metadata differs'; END IF;
  EXECUTE format('SELECT count(*),min(ordinal),max(ordinal) FROM mta.%I WHERE generation_id=$1',item.relation)
   INTO n,lo,hi USING NEW.id;
  IF n IS DISTINCT FROM (bag->>'count')::bigint OR
   (item.dense AND n>0 AND (lo IS DISTINCT FROM 0 OR hi IS DISTINCT FROM n-1)) THEN
   RAISE EXCEPTION 'Scope Expedite bag population/order differs'; END IF;
 END LOOP;
 IF EXISTS(SELECT 1 FROM mta.fresh_mta_scopeexpeditegrid WHERE generation_id=NEW.id AND
    (direction NOT IN ('parent','child') OR branch NOT IN ('dispatch','availability')))
  OR EXISTS(SELECT 1 FROM mta.fresh_mta_scopeexpeditechartmember WHERE generation_id=NEW.id AND NOT
    ((direction='parent' AND family IN ('critical','receiving','nil_stock','chronic'))
     OR (direction='child' AND family IN ('critical','receiving')))) THEN
  RAISE EXCEPTION 'Unknown scoped Expedite occurrence grain'; END IF;
 FOR item IN SELECT * FROM (VALUES ('fresh_mta_scopeexpeditegrid','direction,branch'),
    ('fresh_mta_scopeexpeditechartmember','direction,family')) V(relation,grouping) LOOP
  EXECUTE format('SELECT EXISTS(SELECT 1 FROM mta.%I WHERE generation_id=$1 GROUP BY %s
    HAVING min(ordinal)<>0 OR max(ordinal)<>count(*)-1)',item.relation,item.grouping) INTO bad USING NEW.id;
  IF bad THEN RAISE EXCEPTION 'Scoped Expedite source-grain order differs'; END IF;
 END LOOP;
 IF EXISTS(SELECT 1 FROM mta.fresh_mta_scopeexpeditegrid H LEFT JOIN mta.fresh_mta_scopeexpediterow A
    ON A.generation_id=NEW.report_generation_id AND A.ordinal=H.fact_ordinal
    LEFT JOIN mta.fresh_mta_scopeplanningbprrow M
    ON M.generation_id=NEW.report_generation_id AND M.source_ordinal=H.master_ordinal
    WHERE H.generation_id=NEW.id AND (A.id IS NULL OR (H.master_ordinal IS NOT NULL AND M.id IS NULL)
     OR (H.direction='parent' AND H.branch='availability') IS DISTINCT FROM (H.master_ordinal IS NOT NULL)))
  OR EXISTS(SELECT 1 FROM mta.fresh_mta_scopeexpeditecustom H LEFT JOIN mta.fresh_mta_scopeexpediterow A
    ON A.generation_id=NEW.report_generation_id AND A.ordinal=H.fact_ordinal
    WHERE H.generation_id=NEW.id AND (A.id IS NULL OR H.nms_ordinal>=
      (NEW.metadata->'occurrences'->'nms'->>'row_count')::bigint))
  OR EXISTS(SELECT 1 FROM mta.fresh_mta_scopeexpeditechartmember H
    LEFT JOIN mta.fresh_mta_scopeexpediterow A ON A.generation_id=NEW.report_generation_id AND A.ordinal=H.fact_ordinal
    LEFT JOIN mta.fresh_mta_scopeexpediterow B ON B.generation_id=NEW.report_generation_id AND B.ordinal=H.scope_ordinal
    WHERE H.generation_id=NEW.id AND (A.id IS NULL OR B.id IS NULL))
  OR EXISTS(SELECT 1 FROM mta.fresh_mta_scopeexpediteprepostmember H
    LEFT JOIN mta.fresh_mta_scopepickreference A ON A.generation_id=NEW.pick_generation_id AND A.ordinal=H.fact_ordinal
    LEFT JOIN mta.fresh_mta_scopepickreference B ON B.generation_id=NEW.pick_generation_id AND B.ordinal=H.scope_ordinal
    WHERE H.generation_id=NEW.id AND (A.id IS NULL OR B.id IS NULL OR H.multiplicity<=0)) THEN
  RAISE EXCEPTION 'Scope Expedite source references differ'; END IF;
'''+SQL[end:]
for name in FUNCTIONS:SQL+='REVOKE ALL ON FUNCTION mta.'+name+'() FROM PUBLIC;\n'
SQL+='''CREATE TRIGGER scope_expedite_generation_guard BEFORE INSERT OR UPDATE OR DELETE
 ON mta.fresh_mta_scopeexpeditegeneration FOR EACH ROW EXECUTE FUNCTION mta.guard_scope_expedite_generation();
CREATE CONSTRAINT TRIGGER scope_expedite_complete AFTER INSERT OR UPDATE
 ON mta.fresh_mta_scopeexpeditegeneration DEFERRABLE INITIALLY DEFERRED
 FOR EACH ROW EXECUTE FUNCTION mta.require_scope_expedite_complete();
'''
for table in TABLES.values():
    for op,refs in (('INSERT','NEW TABLE AS new_rows'),('UPDATE','OLD TABLE AS old_rows NEW TABLE AS new_rows'),('DELETE','OLD TABLE AS old_rows')):
        SQL+=('CREATE TRIGGER scope_expedite_rows_'+op.lower()+' AFTER '+op+' ON mta.'+table+
            ' REFERENCING '+refs+' FOR EACH STATEMENT EXECUTE FUNCTION mta.guard_scope_expedite_rows();\n')
for table in (GENERATION,*TABLES.values()):
    SQL+=('CREATE TRIGGER scope_expedite_no_truncate BEFORE TRUNCATE ON mta.'+table+
        ' FOR EACH STATEMENT EXECUTE FUNCTION mta.deny_scope_expedite_truncate();\n')
    for op,refs in (('INSERT','NEW TABLE AS new_rows'),('UPDATE','OLD TABLE AS old_rows NEW TABLE AS new_rows'),('DELETE','OLD TABLE AS old_rows'),('TRUNCATE','')):
        SQL+=('CREATE TRIGGER ingestion_watch_'+op.lower()+' AFTER '+op+' ON mta.'+table+
            (' REFERENCING '+refs if refs else '')+" FOR EACH STATEMENT EXECUTE FUNCTION mta.ingestion_watch('operational');\n")
SQL+=base.transition(OLD,NEW)
REVERSE="""DO $pre$ BEGIN IF EXISTS(SELECT 1 FROM mta.fresh_mta_scopeexpeditegeneration) THEN
 RAISE EXCEPTION 'Accepted scoped Expedite requires a compatible forward release'; END IF; END $pre$;
"""+base.transition(NEW,OLD)
for table in (GENERATION,*TABLES.values()):
    for op in ('insert','update','delete','truncate'):REVERSE+='DROP TRIGGER ingestion_watch_'+op+' ON mta.'+table+';\n'
    REVERSE+='DROP TRIGGER scope_expedite_no_truncate ON mta.'+table+';\n'
    if table!=GENERATION:
        for op in ('insert','update','delete'):REVERSE+='DROP TRIGGER scope_expedite_rows_'+op+' ON mta.'+table+';\n'
REVERSE+='''DROP TRIGGER scope_expedite_generation_guard ON mta.fresh_mta_scopeexpeditegeneration;
DROP TRIGGER scope_expedite_complete ON mta.fresh_mta_scopeexpeditegeneration;
'''
for name in FUNCTIONS:REVERSE+='DROP FUNCTION mta.'+name+'();\n'


class Migration(migrations.Migration):
    dependencies=[('fresh_mta','0213_scope_expedite_generation')]
    operations=[migrations.RunSQL(SQL,REVERSE)]
