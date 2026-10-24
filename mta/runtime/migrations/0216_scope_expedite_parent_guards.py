"""Retain parent Expedite ingredients under a sealed core and remark prefix."""
from importlib import import_module
from django.db import migrations

base=import_module('mta.runtime.migrations.0198_scope_report_guards')
GENERATION='fresh_mta_scopeexpediteparentgeneration'
TABLES={'base':'fresh_mta_scopeexpediteparentbase','match':'fresh_mta_scopeexpediteparentmatch'}
OLD=import_module('mta.runtime.migrations.0214_scope_expedite_guards').NEW
ADDED=base.ADDED.replace(base.GENERATION,GENERATION).replace(
    ','.join("'"+t+"'" for t in base.TABLES.values()),','.join("'"+t+"'" for t in TABLES.values()))
assert OLD.count(" IF kind='immutable' THEN")==1
NEW=OLD.replace(" IF kind='immutable' THEN",ADDED+" IF kind='immutable' THEN",1)
FUNCTIONS=('guard_scope_expedite_parent_generation','guard_scope_expedite_parent_rows',
    'require_scope_expedite_parent_complete','deny_scope_expedite_parent_truncate')
SQL=base.SQL.split('REVOKE ALL ON FUNCTION mta.guard_scope_report_generation()',1)[0]
SQL=SQL.replace(base.GENERATION,GENERATION).replace('scope_report','scope_expedite_parent')
SQL=SQL.replace("'reports'","'occurrences'").replace('fresh-bpr-report-generation-v1','fresh-bpr-expedite-parent-generation-v1')
SQL=SQL.replace('Scope report','Scope Expedite parent').replace('scope report','scope Expedite parent')
SQL=SQL.replace('item record; bag jsonb;','item record; bag jsonb; core mta.fresh_mta_scopeexpeditegeneration;')
needle=" IF TG_OP='INSERT' THEN"
assert SQL.count(needle)==1
SQL=SQL.replace(needle,r'''
 SELECT * INTO core FROM mta.fresh_mta_scopeexpeditegeneration WHERE id=NEW.core_generation_id;
 IF core.id IS NULL OR NOT core.sealed OR core.digest IS DISTINCT FROM NEW.core_generation_digest
  OR core.run_id IS DISTINCT FROM R.id OR core.phase_id IS DISTINCT FROM P.id
  OR core.action_revision IS DISTINCT FROM NEW.action_revision OR core.source_digest IS DISTINCT FROM NEW.source_digest
  OR core.configuration_digest IS DISTINCT FROM NEW.configuration_digest
  OR NEW.remark_highwater<NEW.remark_watermark OR NEW.remark_digest !~ '^[0-9a-f]{64}$'
  OR NOT EXISTS(SELECT 1 FROM mta.fresh_mta_remarkcapture C JOIN mta.fresh_mta_remarkowner O
    ON O.family=C.family WHERE C.id=NEW.remark_capture_id AND C.run_id=R.id AND C.family='BPRReport_RemarkDetails'
     AND C.provenance_digest=NEW.remark_provenance_digest AND O.provenance_digest=C.provenance_digest
     AND C.watermark=NEW.remark_watermark AND C.cutoff=NEW.remark_cutoff
     AND C.row_count=NEW.remark_row_count AND C.rows_digest=NEW.remark_rows_digest
     AND O.next_ordinal>=NEW.remark_highwater) THEN
  RAISE EXCEPTION 'Scope Expedite parent requires exact core and captured remark prefix'; END IF;
'''+needle,1)
start=SQL.index(" bag=NEW.metadata->'occurrences';")
end=SQL.index(' RETURN NEW;',start)
SQL=SQL[:start]+r'''
 bag=NEW.metadata->'occurrences';
 IF jsonb_typeof(bag) IS DISTINCT FROM 'object' OR (SELECT count(*) FROM jsonb_object_keys(bag))<>6
  OR NOT bag ?& ARRAY['schema','core_generation_id','core_generation_digest','remarks','remark_digest','images']
  OR bag->>'schema' IS DISTINCT FROM 'fresh-bpr-expedite-parent-occurrences-v1'
  OR bag->>'core_generation_id' IS DISTINCT FROM NEW.core_generation_id::text
  OR bag->>'core_generation_digest' IS DISTINCT FROM NEW.core_generation_digest
  OR bag->>'remark_digest' IS DISTINCT FROM NEW.remark_digest
  OR jsonb_typeof(bag->'images') IS DISTINCT FROM 'object'
  OR (SELECT count(*) FROM jsonb_object_keys(bag->'images'))<>2
  OR NOT (bag->'images') ?& ARRAY['base','match'] THEN
  RAISE EXCEPTION 'Scope Expedite parent finite dependency metadata differs'; END IF;
 bag=bag->'remarks';
 IF jsonb_typeof(bag) IS DISTINCT FROM 'object' OR (SELECT count(*) FROM jsonb_object_keys(bag))<>16
  OR NOT bag ?& ARRAY['schema','run_id','input_digest','input_manifest_digest','phase_id','phase_digest',
    'input_physical_owner_id','input_image','capture_id','provenance_digest','watermark','live_highwater',
    'cutoff','row_count','rows_digest','recipe_digest']
  OR bag->>'schema' IS DISTINCT FROM 'fresh-bpr-remark-read-v1'
  OR bag->>'run_id' IS DISTINCT FROM R.id::text OR bag->>'input_digest' IS DISTINCT FROM R.input_digest
  OR bag->>'input_manifest_digest' IS DISTINCT FROM R.input_manifest_digest
  OR bag->>'phase_id' IS DISTINCT FROM P.id::text OR bag->>'phase_digest' IS DISTINCT FROM P.digest
  OR bag->>'capture_id' IS DISTINCT FROM NEW.remark_capture_id::text
  OR bag->>'provenance_digest' IS DISTINCT FROM NEW.remark_provenance_digest
  OR bag->>'watermark' IS DISTINCT FROM NEW.remark_watermark::text
  OR bag->>'live_highwater' IS DISTINCT FROM NEW.remark_highwater::text
  OR (bag->>'cutoff')::timestamptz IS DISTINCT FROM NEW.remark_cutoff
  OR bag->>'row_count' IS DISTINCT FROM NEW.remark_row_count::text
  OR bag->>'rows_digest' IS DISTINCT FROM NEW.remark_rows_digest
  OR coalesce(bag->>'recipe_digest','') !~ '^[0-9a-f]{64}$'
  OR coalesce(bag->>'input_physical_owner_id','') !~ '^[0-9a-f-]{36}$'
  OR bag->'input_image'->>'table' IS DISTINCT FROM 'input/production_remark_bpr'
  OR bag->'input_image'->>'count' IS DISTINCT FROM NEW.remark_row_count::text
  OR bag->'input_image'->>'digest' IS DISTINCT FROM NEW.remark_rows_digest THEN
  RAISE EXCEPTION 'Scope Expedite parent remark provenance differs'; END IF;
 FOR item IN SELECT * FROM (VALUES ('base','fresh_mta_scopeexpediteparentbase'),
    ('match','fresh_mta_scopeexpediteparentmatch')) V(name,relation) LOOP
  bag=NEW.metadata->'occurrences'->'images'->item.name;
  IF jsonb_typeof(bag) IS DISTINCT FROM 'object' OR (SELECT count(*) FROM jsonb_object_keys(bag))<>2
   OR NOT bag ?& ARRAY['count','digest'] OR jsonb_typeof(bag->'count') IS DISTINCT FROM 'number'
   OR coalesce(bag->>'count','') !~ '^(0|[1-9][0-9]*)$'
   OR coalesce(bag->>'digest','') !~ '^[0-9a-f]{64}$' THEN
   RAISE EXCEPTION 'Scope Expedite parent bag metadata differs'; END IF;
  EXECUTE format('SELECT count(*),min(ordinal),max(ordinal) FROM mta.%I WHERE generation_id=$1',item.relation)
   INTO n,lo,hi USING NEW.id;
  IF n IS DISTINCT FROM (bag->>'count')::bigint OR (n>0 AND (lo IS DISTINCT FROM 0 OR hi IS DISTINCT FROM n-1)) THEN
   RAISE EXCEPTION 'Scope Expedite parent bag population/order differs'; END IF;
 END LOOP;
 IF EXISTS(SELECT 1 FROM mta.fresh_mta_scopeexpediteparentbase B WHERE B.generation_id=NEW.id AND
    (B.nms_ordinal>=(core.metadata->'occurrences'->'nms'->>'row_count')::bigint
     OR (B.remark_ordinal IS NOT NULL AND NOT EXISTS(
        SELECT 1 FROM mta.fresh_mta_bprcapturedremark C WHERE C.capture_id=NEW.remark_capture_id
          AND C.ordinal=B.remark_ordinal AND C.ordinal<NEW.remark_row_count
        UNION ALL SELECT 1 FROM mta.fresh_mta_bprliveremark L WHERE L.owner_id='BPRReport_RemarkDetails'
          AND L.ordinal>=NEW.remark_watermark AND L.ordinal<NEW.remark_highwater AND L."RemarkDate">NEW.remark_cutoff
          AND NEW.remark_row_count+L.ordinal-NEW.remark_watermark=B.remark_ordinal))))
  OR EXISTS(SELECT 1 FROM mta.fresh_mta_scopeexpediteparentmatch M
    LEFT JOIN mta.fresh_mta_scopeexpediteparentbase B ON B.generation_id=NEW.id AND B.ordinal=M.base_ordinal
    LEFT JOIN mta.fresh_mta_scopeexpeditegrid G ON G.generation_id=NEW.core_generation_id
      AND G.direction='parent' AND G.branch=M.branch AND G.ordinal=M.grid_ordinal
    LEFT JOIN mta.fresh_mta_scopepickreference K ON K.generation_id=core.pick_generation_id AND K.ordinal=M.pick_ordinal
    WHERE M.generation_id=NEW.id AND (B.id IS NULL OR B.remark_ordinal IS NULL OR G.id IS NULL
      OR M.branch NOT IN ('dispatch','availability') OR (M.pick_ordinal IS NOT NULL AND K.id IS NULL))) THEN
  RAISE EXCEPTION 'Scope Expedite parent source references differ'; END IF;
'''+SQL[end:]
for name in FUNCTIONS:SQL+='REVOKE ALL ON FUNCTION mta.'+name+'() FROM PUBLIC;\n'
SQL+='''CREATE TRIGGER scope_expedite_parent_generation_guard BEFORE INSERT OR UPDATE OR DELETE
 ON mta.fresh_mta_scopeexpediteparentgeneration FOR EACH ROW EXECUTE FUNCTION mta.guard_scope_expedite_parent_generation();
CREATE CONSTRAINT TRIGGER scope_expedite_parent_complete AFTER INSERT OR UPDATE
 ON mta.fresh_mta_scopeexpediteparentgeneration DEFERRABLE INITIALLY DEFERRED
 FOR EACH ROW EXECUTE FUNCTION mta.require_scope_expedite_parent_complete();
'''
for table in TABLES.values():
    for op,refs in (('INSERT','NEW TABLE AS new_rows'),('UPDATE','OLD TABLE AS old_rows NEW TABLE AS new_rows'),('DELETE','OLD TABLE AS old_rows')):
        SQL+=('CREATE TRIGGER scope_expedite_parent_rows_'+op.lower()+' AFTER '+op+' ON mta.'+table+
            ' REFERENCING '+refs+' FOR EACH STATEMENT EXECUTE FUNCTION mta.guard_scope_expedite_parent_rows();\n')
for table in (GENERATION,*TABLES.values()):
    SQL+=('CREATE TRIGGER scope_expedite_parent_no_truncate BEFORE TRUNCATE ON mta.'+table+
        ' FOR EACH STATEMENT EXECUTE FUNCTION mta.deny_scope_expedite_parent_truncate();\n')
    for op,refs in (('INSERT','NEW TABLE AS new_rows'),('UPDATE','OLD TABLE AS old_rows NEW TABLE AS new_rows'),('DELETE','OLD TABLE AS old_rows'),('TRUNCATE','')):
        SQL+=('CREATE TRIGGER ingestion_watch_'+op.lower()+' AFTER '+op+' ON mta.'+table+
            (' REFERENCING '+refs if refs else '')+" FOR EACH STATEMENT EXECUTE FUNCTION mta.ingestion_watch('operational');\n")
SQL+=base.transition(OLD,NEW)
REVERSE="""DO $pre$ BEGIN IF EXISTS(SELECT 1 FROM mta.fresh_mta_scopeexpediteparentgeneration) THEN
 RAISE EXCEPTION 'Accepted scoped Expedite parent requires a compatible forward release'; END IF; END $pre$;
"""+base.transition(NEW,OLD)
for table in (GENERATION,*TABLES.values()):
    for op in ('insert','update','delete','truncate'):REVERSE+='DROP TRIGGER ingestion_watch_'+op+' ON mta.'+table+';\n'
    REVERSE+='DROP TRIGGER scope_expedite_parent_no_truncate ON mta.'+table+';\n'
    if table!=GENERATION:
        for op in ('insert','update','delete'):REVERSE+='DROP TRIGGER scope_expedite_parent_rows_'+op+' ON mta.'+table+';\n'
REVERSE+='''DROP TRIGGER scope_expedite_parent_generation_guard ON mta.fresh_mta_scopeexpediteparentgeneration;
DROP TRIGGER scope_expedite_parent_complete ON mta.fresh_mta_scopeexpediteparentgeneration;
'''
for name in FUNCTIONS:REVERSE+='DROP FUNCTION mta.'+name+'();\n'


class Migration(migrations.Migration):
    dependencies=[('fresh_mta','0215_scope_expedite_parent_generation')]
    operations=[migrations.RunSQL(SQL,REVERSE)]
