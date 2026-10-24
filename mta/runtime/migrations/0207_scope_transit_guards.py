"""Seal three derived transit bags without changing terminal state authority."""
from importlib import import_module
from django.db import migrations

base=import_module('mta.runtime.migrations.0198_scope_report_guards')
TABLES={'InTransitData':'fresh_mta_scopetransitrow',
    'GoodsInTransitTransporterMaster':'fresh_mta_scopetransporterrow',
    'TransitRejectedMaster':'fresh_mta_scopetransitdiagnostic'}
GENERATION='fresh_mta_scopetransitgeneration'
OLD=import_module('mta.runtime.migrations.0204_scoped_bpr_consumer_ownership').NEW
ADDED=base.ADDED.replace(base.GENERATION,GENERATION).replace(
    ','.join("'"+table+"'" for table in base.TABLES.values()),
    ','.join("'"+table+"'" for table in TABLES.values()))
assert OLD.count(" IF kind='immutable' THEN")==1
NEW=OLD.replace(" IF kind='immutable' THEN",ADDED+" IF kind='immutable' THEN",1)

# Reuse the immutable generation/row/completeness protocol, with a distinct
# finite roster and functions. No old SQL function or migration is rewritten.
FUNCTIONS=('guard_scope_transit_generation','guard_scope_transit_rows',
    'require_scope_transit_complete','deny_scope_transit_truncate')
SQL=base.SQL.split('REVOKE ALL ON FUNCTION mta.guard_scope_report_generation()',1)[0]
SQL=SQL.replace(base.GENERATION,GENERATION).replace('scope_report','scope_transit')
SQL=SQL.replace("'reports'","'transit'").replace('fresh-bpr-report-generation-v1','fresh-bpr-transit-generation-v1')
SQL=SQL.replace('Scope report','Scope transit').replace('scope report','scope transit').replace('>16384','>65536')
start=SQL.index(" bag=NEW.metadata->'transit';")
end=SQL.index(' FOR item IN SELECT * FROM (VALUES',start)
SQL=SQL[:start]+r'''
 bag=NEW.metadata->'transit';
 IF jsonb_typeof(bag) IS DISTINCT FROM 'object'
  OR (SELECT count(*) FROM jsonb_object_keys(bag))<>17
  OR NOT bag ?& ARRAY['schema','run_id','input_digest','input_manifest_digest','source_digest',
   'phase_id','phase_digest','snapshot_digest','action_revision','display_date','recipe_digest',
   'producers','captured_sources','settings_owner','super_delay_factor','run_timestamp','images']
  OR bag->>'schema' IS DISTINCT FROM 'fresh-bpr-transit-rows-v1'
  OR bag->>'run_id' IS DISTINCT FROM R.id::text
  OR bag->>'input_digest' IS DISTINCT FROM R.input_digest
  OR bag->>'input_manifest_digest' IS DISTINCT FROM R.input_manifest_digest
  OR bag->>'source_digest' IS DISTINCT FROM NEW.source_digest
  OR bag->>'phase_id' IS DISTINCT FROM P.id::text OR bag->>'phase_digest' IS DISTINCT FROM P.digest
  OR bag->>'snapshot_digest' IS DISTINCT FROM S.state_digest
  OR bag->>'action_revision' IS DISTINCT FROM NEW.action_revision::text
  OR bag->>'display_date' IS DISTINCT FROM R.business_date::text
  OR coalesce(bag->>'recipe_digest','') !~ '^[0-9a-f]{64}$'
  OR jsonb_typeof(bag->'images') IS DISTINCT FROM 'object'
  OR (SELECT count(*) FROM jsonb_object_keys(bag->'images'))<>4
  OR NOT (bag->'images') ?& ARRAY['InTransitDataRaw','InTransitData',
      'GoodsInTransitTransporterMaster','TransitRejectedMaster']
  OR jsonb_typeof(bag->'producers') IS DISTINCT FROM 'object'
  OR (SELECT count(*) FROM jsonb_object_keys(bag->'producers'))<>2
  OR NOT (bag->'producers') ?& ARRAY['validate','transporter']
  OR coalesce(bag->'producers'->>'validate','') !~ '^[0-9a-f]{64}$'
  OR coalesce(bag->'producers'->>'transporter','') !~ '^[0-9a-f]{64}$'
  OR jsonb_typeof(bag->'captured_sources') IS DISTINCT FROM 'object'
  OR (SELECT count(*) FROM jsonb_object_keys(bag->'captured_sources'))<>2
  OR NOT (bag->'captured_sources') ?& ARRAY['shipments','transporters']
  OR jsonb_typeof(bag->'settings_owner') IS DISTINCT FROM 'object'
  OR bag->'settings_owner'->>'path' IS DISTINCT FROM
     'input/profile/delivery/btr_history/importer_vf_settings'
  OR bag->'settings_owner'->'image'->>'table' IS DISTINCT FROM 'Importer/VFSettings'
  OR coalesce(bag->'settings_owner'->>'input_manifest_digest','') !~ '^[0-9a-f]{64}$'
  OR coalesce(bag->'settings_owner'->'image'->>'digest','') !~ '^[0-9a-f]{64}$' THEN
  RAISE EXCEPTION 'Scope transit finite consumer metadata differs'; END IF;
 FOR item IN SELECT value FROM jsonb_each(bag->'captured_sources') LOOP
  IF jsonb_typeof(item.value) IS DISTINCT FROM 'object'
   OR NOT item.value ?& ARRAY['digest','provenance']
   OR coalesce(item.value->>'digest','') !~ '^[0-9a-f]{64}$'
   OR jsonb_typeof(item.value->'provenance') IS DISTINCT FROM 'object' THEN
   RAISE EXCEPTION 'Scope transit captured provenance differs'; END IF;
 END LOOP;
 FOR item IN SELECT value FROM jsonb_each(bag->'images') LOOP
  IF jsonb_typeof(item.value) IS DISTINCT FROM 'object'
   OR (SELECT count(*) FROM jsonb_object_keys(item.value))<>2
   OR NOT item.value ?& ARRAY['count','digest']
   OR jsonb_typeof(item.value->'count') IS DISTINCT FROM 'number'
   OR coalesce(item.value->>'count','') !~ '^(0|[1-9][0-9]*)$'
   OR coalesce(item.value->>'digest','') !~ '^[0-9a-f]{64}$' THEN
   RAISE EXCEPTION 'Scope transit image metadata differs'; END IF;
 END LOOP;
'''+SQL[end:]
start=SQL.index(' FOR item IN SELECT * FROM (VALUES')
end=SQL.index("  bag=NEW.metadata->'transit'->'images'->item.name;",start)
SQL=SQL[:start]+(' FOR item IN SELECT * FROM (VALUES\n  '+
    ',\n  '.join("('"+name+"','"+table+"')" for name,table in TABLES.items())+
    ') V(name,relation) LOOP\n')+SQL[end:]
for name in FUNCTIONS:SQL+='REVOKE ALL ON FUNCTION mta.'+name+'() FROM PUBLIC;\n'
SQL+='''CREATE TRIGGER scope_transit_generation_guard BEFORE INSERT OR UPDATE OR DELETE
 ON mta.fresh_mta_scopetransitgeneration FOR EACH ROW EXECUTE FUNCTION mta.guard_scope_transit_generation();
CREATE CONSTRAINT TRIGGER scope_transit_complete AFTER INSERT OR UPDATE
 ON mta.fresh_mta_scopetransitgeneration DEFERRABLE INITIALLY DEFERRED
 FOR EACH ROW EXECUTE FUNCTION mta.require_scope_transit_complete();
'''
for table in TABLES.values():
    for op,refs in (('INSERT','NEW TABLE AS new_rows'),
            ('UPDATE','OLD TABLE AS old_rows NEW TABLE AS new_rows'),('DELETE','OLD TABLE AS old_rows')):
        SQL+=('CREATE TRIGGER scope_transit_rows_'+op.lower()+' AFTER '+op+' ON mta.'+table+
            ' REFERENCING '+refs+' FOR EACH STATEMENT EXECUTE FUNCTION mta.guard_scope_transit_rows();\n')
for table in (GENERATION,*TABLES.values()):
    SQL+=('CREATE TRIGGER scope_transit_no_truncate BEFORE TRUNCATE ON mta.'+table+
        ' FOR EACH STATEMENT EXECUTE FUNCTION mta.deny_scope_transit_truncate();\n')
    for op,refs in (('INSERT','NEW TABLE AS new_rows'),('UPDATE','OLD TABLE AS old_rows NEW TABLE AS new_rows'),
            ('DELETE','OLD TABLE AS old_rows'),('TRUNCATE','')):
        SQL+=('CREATE TRIGGER ingestion_watch_'+op.lower()+' AFTER '+op+' ON mta.'+table+
            (' REFERENCING '+refs if refs else '')+
            " FOR EACH STATEMENT EXECUTE FUNCTION mta.ingestion_watch('operational');\n")
SQL+=base.transition(OLD,NEW)
REVERSE="""DO $pre$ BEGIN IF EXISTS(SELECT 1 FROM mta.fresh_mta_scopetransitgeneration) THEN
 RAISE EXCEPTION 'Accepted scope transit requires a compatible forward release'; END IF; END $pre$;
"""+base.transition(NEW,OLD)
for table in (GENERATION,*TABLES.values()):
    for op in ('insert','update','delete','truncate'):
        REVERSE+='DROP TRIGGER ingestion_watch_'+op+' ON mta.'+table+';\n'
    REVERSE+='DROP TRIGGER scope_transit_no_truncate ON mta.'+table+';\n'
    if table!=GENERATION:
        for op in ('insert','update','delete'):
            REVERSE+='DROP TRIGGER scope_transit_rows_'+op+' ON mta.'+table+';\n'
REVERSE+='''DROP TRIGGER scope_transit_generation_guard ON mta.fresh_mta_scopetransitgeneration;
DROP TRIGGER scope_transit_complete ON mta.fresh_mta_scopetransitgeneration;
'''
for name in FUNCTIONS:REVERSE+='DROP FUNCTION mta.'+name+'();\n'


class Migration(migrations.Migration):
    dependencies=[('fresh_mta','0206_scope_transit_generation')]
    operations=[migrations.RunSQL(SQL,REVERSE)]
