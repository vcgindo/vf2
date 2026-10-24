"""Seal GIT occurrences under exact report/source/transit owners."""
from importlib import import_module
from django.db import migrations

base=import_module('mta.runtime.migrations.0198_scope_report_guards')
previous=import_module('mta.runtime.migrations.0207_scope_transit_guards')
GENERATION='fresh_mta_scopegitgeneration'
TABLES={'occurrences':'fresh_mta_scopegitoccurrence'}
OLD=previous.NEW
ADDED=base.ADDED.replace(base.GENERATION,GENERATION).replace(
    ','.join("'"+table+"'" for table in base.TABLES.values()),
    ','.join("'"+table+"'" for table in TABLES.values()))
assert OLD.count(" IF kind='immutable' THEN")==1
NEW=OLD.replace(" IF kind='immutable' THEN",ADDED+" IF kind='immutable' THEN",1)
FUNCTIONS=('guard_scope_git_generation','guard_scope_git_rows',
           'require_scope_git_complete','deny_scope_git_truncate')

SQL=base.SQL.split('REVOKE ALL ON FUNCTION mta.guard_scope_report_generation()',1)[0]
SQL=SQL.replace(base.GENERATION,GENERATION).replace('scope_report','scope_git')
SQL=SQL.replace("'reports'","'occurrences'").replace('fresh-bpr-report-generation-v1','fresh-bpr-git-generation-v1')
SQL=SQL.replace('Scope report','Scope GIT').replace('scope report','scope GIT')
# Dependencies are immutable typed rows. Their exact identities must agree even
# before an unsealed generation can be inserted; a GUC never waives this check.
needle=" IF TG_OP='INSERT' THEN"
dependency=r'''
 IF NOT EXISTS(SELECT 1 FROM mta.fresh_mta_scopereportgeneration G
   JOIN mta.fresh_mta_scopesourceprojection X ON X.generation_id=G.id
   JOIN mta.fresh_mta_scopetransitgeneration T ON T.id=NEW.transit_generation_id
   WHERE G.id=NEW.report_generation_id AND G.sealed AND X.sealed AND T.sealed
    AND G.digest=NEW.report_generation_digest AND X.digest=NEW.source_projection_digest
    AND X.report_generation_digest=G.digest AND T.digest=NEW.transit_generation_digest
    AND G.run_id=R.id AND T.run_id=R.id AND G.phase_id=P.id AND T.phase_id=P.id
    AND G.action_revision=NEW.action_revision AND T.action_revision=NEW.action_revision
    AND G.source_digest=NEW.source_digest AND T.source_digest=NEW.source_digest
    AND G.configuration_digest=NEW.configuration_digest
    AND T.configuration_digest=NEW.configuration_digest) THEN
  RAISE EXCEPTION 'Scope GIT requires exact sealed source and transit generations'; END IF;
'''
assert SQL.count(needle)==1
SQL=SQL.replace(needle,dependency+needle,1)
start=SQL.index(" bag=NEW.metadata->'occurrences';")
end=SQL.index(' RETURN NEW;',start)
SQL=SQL[:start]+r'''
 bag=NEW.metadata->'occurrences';
 IF jsonb_typeof(bag) IS DISTINCT FROM 'object'
  OR (SELECT count(*) FROM jsonb_object_keys(bag))<>7
  OR NOT bag ?& ARRAY['schema','report_generation_id','report_generation_digest',
     'source_projection_digest','transit_generation_id','transit_generation_digest','image']
  OR bag->>'schema' IS DISTINCT FROM 'fresh-bpr-git-occurrences-v1'
  OR bag->>'report_generation_id' IS DISTINCT FROM NEW.report_generation_id::text
  OR bag->>'report_generation_digest' IS DISTINCT FROM NEW.report_generation_digest
  OR bag->>'source_projection_digest' IS DISTINCT FROM NEW.source_projection_digest
  OR bag->>'transit_generation_id' IS DISTINCT FROM NEW.transit_generation_id::text
  OR bag->>'transit_generation_digest' IS DISTINCT FROM NEW.transit_generation_digest THEN
  RAISE EXCEPTION 'Scope GIT dependency metadata differs'; END IF;
 bag=bag->'image';
 IF jsonb_typeof(bag) IS DISTINCT FROM 'object'
  OR (SELECT count(*) FROM jsonb_object_keys(bag))<>2
  OR NOT bag ?& ARRAY['count','digest'] OR jsonb_typeof(bag->'count') IS DISTINCT FROM 'number'
  OR coalesce(bag->>'count','') !~ '^(0|[1-9][0-9]*)$'
  OR coalesce(bag->>'digest','') !~ '^[0-9a-f]{64}$' THEN
  RAISE EXCEPTION 'Scope GIT occurrence metadata differs'; END IF;
 SELECT count(*),min(ordinal),max(ordinal) INTO n,lo,hi
  FROM mta.fresh_mta_scopegitoccurrence WHERE generation_id=NEW.id;
 IF n IS DISTINCT FROM (bag->>'count')::bigint
  OR (n>0 AND (lo IS DISTINCT FROM 0 OR hi IS DISTINCT FROM n-1)) THEN
  RAISE EXCEPTION 'Scope GIT occurrence population/order differs'; END IF;
'''+SQL[end:]
for name in FUNCTIONS:SQL+='REVOKE ALL ON FUNCTION mta.'+name+'() FROM PUBLIC;\n'
SQL+='''CREATE TRIGGER scope_git_generation_guard BEFORE INSERT OR UPDATE OR DELETE
 ON mta.fresh_mta_scopegitgeneration FOR EACH ROW EXECUTE FUNCTION mta.guard_scope_git_generation();
CREATE CONSTRAINT TRIGGER scope_git_complete AFTER INSERT OR UPDATE
 ON mta.fresh_mta_scopegitgeneration DEFERRABLE INITIALLY DEFERRED
 FOR EACH ROW EXECUTE FUNCTION mta.require_scope_git_complete();
'''
for table in TABLES.values():
    for op,refs in (('INSERT','NEW TABLE AS new_rows'),
            ('UPDATE','OLD TABLE AS old_rows NEW TABLE AS new_rows'),('DELETE','OLD TABLE AS old_rows')):
        SQL+=('CREATE TRIGGER scope_git_rows_'+op.lower()+' AFTER '+op+' ON mta.'+table+
            ' REFERENCING '+refs+' FOR EACH STATEMENT EXECUTE FUNCTION mta.guard_scope_git_rows();\n')
for table in (GENERATION,*TABLES.values()):
    SQL+=('CREATE TRIGGER scope_git_no_truncate BEFORE TRUNCATE ON mta.'+table+
        ' FOR EACH STATEMENT EXECUTE FUNCTION mta.deny_scope_git_truncate();\n')
    for op,refs in (('INSERT','NEW TABLE AS new_rows'),('UPDATE','OLD TABLE AS old_rows NEW TABLE AS new_rows'),
            ('DELETE','OLD TABLE AS old_rows'),('TRUNCATE','')):
        SQL+=('CREATE TRIGGER ingestion_watch_'+op.lower()+' AFTER '+op+' ON mta.'+table+
            (' REFERENCING '+refs if refs else '')+
            " FOR EACH STATEMENT EXECUTE FUNCTION mta.ingestion_watch('operational');\n")
SQL+=base.transition(OLD,NEW)
REVERSE="""DO $pre$ BEGIN IF EXISTS(SELECT 1 FROM mta.fresh_mta_scopegitgeneration) THEN
 RAISE EXCEPTION 'Accepted scoped GIT requires a compatible forward release'; END IF; END $pre$;
"""+base.transition(NEW,OLD)
for table in (GENERATION,*TABLES.values()):
    for op in ('insert','update','delete','truncate'):
        REVERSE+='DROP TRIGGER ingestion_watch_'+op+' ON mta.'+table+';\n'
    REVERSE+='DROP TRIGGER scope_git_no_truncate ON mta.'+table+';\n'
    if table!=GENERATION:
        for op in ('insert','update','delete'):
            REVERSE+='DROP TRIGGER scope_git_rows_'+op+' ON mta.'+table+';\n'
REVERSE+='''DROP TRIGGER scope_git_generation_guard ON mta.fresh_mta_scopegitgeneration;
DROP TRIGGER scope_git_complete ON mta.fresh_mta_scopegitgeneration;
'''
for name in FUNCTIONS:REVERSE+='DROP FUNCTION mta.'+name+'();\n'


class Migration(migrations.Migration):
    dependencies=[('fresh_mta','0209_scope_git_generation')]
    operations=[migrations.RunSQL(SQL,REVERSE)]
