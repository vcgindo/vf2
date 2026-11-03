"""Typed immutable history payloads with one-time visibility closure.

Required for fresh and upgraded schemas; this does not activate a writer or
convert accepted images. Only the seven qualified terminal DBM families enter.
Existing rationing guards retain their exact checks and their own trigger.
"""
from importlib import import_module
import json

from django.db import migrations


# Frozen names; do not import a mutable runtime family registry into migrations.
FAMILIES = {
    'DailyConsumption': 'ReportDate', 'OrderData': 'ImportDate',
    'OrderDataSummary': 'ImportDate', 'SuggestionsLog': 'SuggestionDate',
    'DiscardedSuggestions': 'SuggestionDate', 'SpikeReport': 'SuspendFromDate',
    'SuspendHistory': 'ReportDate',
}

SQL = r'''
CREATE FUNCTION mta.dated_history_table(family text) RETURNS text
LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog AS $$
BEGIN
 IF family NOT IN ('closing/dbm/DailyConsumption','closing/dbm/OrderData',
   'closing/dbm/OrderDataSummary','closing/dbm/SuggestionsLog',
   'closing/dbm/DiscardedSuggestions','closing/dbm/SpikeReport','closing/dbm/SuspendHistory')
   OR family IS NULL THEN RAISE EXCEPTION 'Unqualified dated history family'; END IF;
 RETURN 'history_dbm_'||lower(split_part(family,'/',3));
END $$;
REVOKE ALL ON FUNCTION mta.dated_history_table(text) FROM PUBLIC;

CREATE FUNCTION mta.dated_history_insert() RETURNS trigger LANGUAGE plpgsql
SET search_path=pg_catalog,mta AS $$
DECLARE identity uuid; owners bigint; c mta.fresh_mta_operationalstatecut;
BEGIN
 SELECT min(cut_id::text)::uuid,count(DISTINCT cut_id) INTO identity,owners FROM new_rows;
 IF owners=0 THEN RETURN NULL; END IF;
 IF owners<>1 THEN RAISE EXCEPTION 'History insertion requires one producing cut'; END IF;
 c=mta.require_pending_state_cut(identity);
 IF TG_TABLE_NAME<>mta.dated_history_table(c.family) OR EXISTS(
   SELECT FROM new_rows WHERE initialization_id<>c.initialization_id OR born_position<>c.position
     OR end_position IS NOT NULL OR closing_cut_id IS NOT NULL)
 THEN RAISE EXCEPTION 'History insertion owner differs'; END IF;
 IF c.position>0 AND EXISTS(SELECT FROM new_rows N JOIN mta.fresh_mta_calculationrun R ON R.id=c.run_id
     WHERE (to_jsonb(N)->>TG_ARGV[0])::date IS DISTINCT FROM R.business_date)
 THEN RAISE EXCEPTION 'New history facts require the current producer date'; END IF;
 RETURN NULL;
END $$;
REVOKE ALL ON FUNCTION mta.dated_history_insert() FROM PUBLIC;

CREATE FUNCTION mta.dated_history_close() RETURNS trigger LANGUAGE plpgsql
SET search_path=pg_catalog,mta AS $$
DECLARE identity uuid; owners bigint; c mta.fresh_mta_operationalstatecut;
BEGIN
 IF NOT EXISTS(SELECT FROM new_rows) THEN RETURN NULL; END IF;
 SELECT min(closing_cut_id::text)::uuid,count(DISTINCT closing_cut_id) INTO identity,owners FROM new_rows;
 IF owners<>1 THEN RAISE EXCEPTION 'History closure requires one producing cut'; END IF;
 c=mta.require_pending_state_cut(identity);
 IF c.position=0 OR TG_TABLE_NAME<>mta.dated_history_table(c.family) OR EXISTS(
   SELECT FROM old_rows O FULL JOIN new_rows N ON N.cut_id=O.cut_id AND N.vf_ordinal=O.vf_ordinal
   WHERE O.cut_id IS NULL OR N.cut_id IS NULL OR O.end_position IS NOT NULL OR O.closing_cut_id IS NOT NULL
     OR N.end_position IS DISTINCT FROM c.position OR N.closing_cut_id IS DISTINCT FROM c.id
     OR N.initialization_id<>c.initialization_id OR N.born_position>=c.position
     OR (to_jsonb(O)-ARRAY['end_position','closing_cut_id']) IS DISTINCT FROM
        (to_jsonb(N)-ARRAY['end_position','closing_cut_id']))
 THEN RAISE EXCEPTION 'History payload is immutable; visible membership may close once'; END IF;
 RETURN NULL;
END $$;
REVOKE ALL ON FUNCTION mta.dated_history_close() FROM PUBLIC;

CREATE FUNCTION mta.dated_history_fields_valid(family text,fields jsonb,population bigint)
RETURNS boolean LANGUAGE plpgsql STABLE SET search_path=pg_catalog,mta AS $$
DECLARE names text[]; supplied text[]; descriptor jsonb;
BEGIN
 IF population IS NULL OR population<0 OR jsonb_typeof(fields) IS DISTINCT FROM 'array'
 THEN RETURN false; END IF;
 IF fields='[]'::jsonb THEN RETURN population=0; END IF;
 SELECT array_agg(attname::text ORDER BY attname) INTO names FROM pg_attribute
 WHERE attrelid=('mta_state.'||mta.dated_history_table(family))::regclass AND attnum>0 AND NOT attisdropped
 AND attname NOT IN ('cut_id','vf_ordinal','initialization_id','born_position','end_position','closing_cut_id');
 FOR descriptor IN SELECT value FROM jsonb_array_elements(fields) LOOP
  IF jsonb_typeof(descriptor) IS DISTINCT FROM 'array' OR jsonb_array_length(descriptor)<>3
    OR jsonb_typeof(descriptor->0) IS DISTINCT FROM 'string' OR descriptor->0 IS DISTINCT FROM descriptor->1
    OR coalesce(descriptor->>2,'') NOT IN ('str','int','float','bool') THEN RETURN false; END IF;
 END LOOP;
 SELECT array_agg(D->>0 ORDER BY D->>0) INTO supplied FROM jsonb_array_elements(fields) D;
 RETURN names=supplied;
END $$;
REVOKE ALL ON FUNCTION mta.dated_history_fields_valid(text,jsonb,bigint) FROM PUBLIC;

CREATE FUNCTION mta.require_dated_history_seal() RETURNS trigger LANGUAGE plpgsql
SET search_path=pg_catalog,mta AS $$
DECLARE c mta.fresh_mta_operationalstatecut; p mta.fresh_mta_operationalstatecut;
 b jsonb; image jsonb; anchor jsonb; original_digest text; original_image text;
 facts bigint; removed bigint; last_ordinal bigint; retained bigint; relation text;
BEGIN
 SELECT * INTO STRICT c FROM mta.fresh_mta_operationalstatecut WHERE id=NEW.id;
 IF c.root_digest='' THEN RAISE EXCEPTION 'Unsealed history cut cannot commit'; END IF;
 IF NOT EXISTS(SELECT FROM mta.fresh_mta_productioninitialization
   WHERE id=c.initialization_id AND receipt_digest<>'' AND input_manifest_digest<>'')
 THEN RAISE EXCEPTION 'History initialization must seal before commit'; END IF;
 b=c.root_body::jsonb;
 IF jsonb_typeof(b) IS DISTINCT FROM 'object' OR (SELECT count(*) FROM jsonb_object_keys(b))<>17
   OR NOT (b ?& ARRAY['format','cut','initialization','family','position','run','parent','parent_root',
       'input_digest','settings_digest','fields','count','inserted','removed','facts_digest','removals_digest','anchor'])
   OR b->>'format' IS DISTINCT FROM 'dated-history-occurrences-v1'
   OR b->>'cut' IS DISTINCT FROM c.id::text OR b->>'initialization' IS DISTINCT FROM c.initialization_id::text
   OR b->>'family' IS DISTINCT FROM c.family OR b->'position' IS DISTINCT FROM to_jsonb(c.position)
   OR b->>'run' IS DISTINCT FROM c.run_id::text OR b->>'parent' IS DISTINCT FROM c.parent_id::text
   OR b->>'input_digest' IS DISTINCT FROM c.input_digest OR b->>'settings_digest' IS DISTINCT FROM c.settings_digest
   OR mta.dated_history_fields_valid(c.family,b->'fields',(b->>'count')::bigint) IS NOT TRUE
   OR coalesce(b->>'facts_digest','') !~ '^[0-9a-f]{64}$'
   OR coalesce(b->>'removals_digest','') !~ '^[0-9a-f]{64}$'
 THEN RAISE EXCEPTION 'History commitment context differs'; END IF;
 relation=mta.dated_history_table(c.family);
 EXECUTE format('SELECT count(*),max(vf_ordinal) FROM mta_state.%I WHERE cut_id=$1',relation)
   INTO facts,last_ordinal USING c.id;
 EXECUTE format('SELECT count(*) FROM mta_state.%I WHERE closing_cut_id=$1',relation)
   INTO removed USING c.id;
 IF b->'inserted' IS DISTINCT FROM to_jsonb(facts) OR b->'removed' IS DISTINCT FROM to_jsonb(removed)
    OR coalesce(last_ordinal,-1)<>facts-1
 THEN RAISE EXCEPTION 'History delta count or dense producer ordinal differs'; END IF;
 IF c.position=0 THEN
  IF b->>'parent_root' IS DISTINCT FROM repeat('0',64) OR removed<>0
    OR jsonb_typeof(b->'anchor') IS DISTINCT FROM 'object'
  THEN RAISE EXCEPTION 'History anchor commitment differs'; END IF;
  anchor=b->'anchor';
  IF (SELECT count(*) FROM jsonb_object_keys(anchor))<>6
    OR NOT (anchor ?& ARRAY['owner_kind','owner_id','manifest_digest','image','digest','count'])
  THEN RAISE EXCEPTION 'History anchor provenance fields differ'; END IF;
  IF c.run_id IS NULL THEN
   original_image='input/opening/state/dbm/'||split_part(c.family,'/',3)||'/values';
   SELECT input_manifest_digest,input_payload->'images'->original_image INTO original_digest,image
    FROM mta.fresh_mta_productioninitialization WHERE id=c.initialization_id
      AND input_digest=c.input_digest AND configuration_digest=c.settings_digest;
   IF anchor->>'owner_kind' IS DISTINCT FROM 'INITIALIZATION'
      OR anchor->>'owner_id' IS DISTINCT FROM c.initialization_id::text
   THEN RAISE EXCEPTION 'History anchor initialized owner differs'; END IF;
  ELSE
   original_image=c.family;
   SELECT production_digest,production_manifest->'images'->original_image INTO original_digest,image
    FROM mta.fresh_mta_calculationrun WHERE id=c.run_id AND status='SUCCEEDED';
   IF anchor->>'owner_kind' IS DISTINCT FROM 'RUN' OR anchor->>'owner_id' IS DISTINCT FROM c.run_id::text
   THEN RAISE EXCEPTION 'History anchor accepted owner differs'; END IF;
  END IF;
  IF image IS NULL OR image ? 'storage_format' OR anchor->>'image' IS DISTINCT FROM original_image
    OR anchor->>'manifest_digest' IS DISTINCT FROM original_digest
    OR anchor->'digest' IS DISTINCT FROM image->'digest' OR anchor->'count' IS DISTINCT FROM image->'count'
    OR b->'count' IS DISTINCT FROM image->'count' OR b->'fields' IS DISTINCT FROM image->'fields'
  THEN RAISE EXCEPTION 'History anchor accepted representation differs'; END IF;
  retained=0;
 ELSE
  SELECT * INTO STRICT p FROM mta.fresh_mta_operationalstatecut WHERE id=c.parent_id;
  retained=(p.root_body::jsonb->>'count')::bigint-removed;
  IF b->>'parent_root' IS DISTINCT FROM p.root_digest OR b->'anchor' IS DISTINCT FROM 'null'::jsonb
  THEN RAISE EXCEPTION 'History parent commitment differs'; END IF;
  SELECT production_manifest->'images'->c.family INTO image FROM mta.fresh_mta_calculationrun
   WHERE id=c.run_id AND status='SUCCEEDED';
  IF image IS NULL OR image->>'storage_format' IS DISTINCT FROM 'dated-history-occurrences-v1'
    OR image->>'cut_id' IS DISTINCT FROM c.id::text OR image->>'digest' IS DISTINCT FROM c.root_digest
    OR image->>'image' IS DISTINCT FROM c.family OR image->>'table' IS DISTINCT FROM ('DBM/'||split_part(c.family,'/',3))
    OR image->'fields' IS DISTINCT FROM b->'fields' OR image->'count' IS DISTINCT FROM b->'count'
  THEN RAISE EXCEPTION 'Accepted run must bind its exact sealed history cut'; END IF;
 END IF;
 IF retained<0 OR b->'count' IS DISTINCT FROM to_jsonb(retained+facts)
 THEN RAISE EXCEPTION 'History logical membership count differs'; END IF;
 RETURN NULL;
END $$;
REVOKE ALL ON FUNCTION mta.require_dated_history_seal() FROM PUBLIC;

DROP TRIGGER state_cut_complete ON mta.fresh_mta_operationalstatecut;
CREATE CONSTRAINT TRIGGER state_cut_complete AFTER INSERT OR UPDATE ON mta.fresh_mta_operationalstatecut
 DEFERRABLE INITIALLY DEFERRED FOR EACH ROW WHEN (NEW.family='rationing_history')
 EXECUTE FUNCTION mta.require_state_cut_seal();
CREATE CONSTRAINT TRIGGER history_cut_complete AFTER INSERT OR UPDATE ON mta.fresh_mta_operationalstatecut
 DEFERRABLE INITIALLY DEFERRED FOR EACH ROW WHEN (NEW.family<>'rationing_history')
 EXECUTE FUNCTION mta.require_dated_history_seal();
'''

for name, date_field in FAMILIES.items():
    table = 'history_dbm_' + name.lower()
    SQL += f'''
CREATE TABLE mta_state.{table} (LIKE mta_state.dbm_{name.lower()} INCLUDING CONSTRAINTS);
ALTER TABLE mta_state.{table} DROP COLUMN vf_run_id, DROP COLUMN vf_image,
 ADD COLUMN cut_id uuid NOT NULL REFERENCES mta.fresh_mta_operationalstatecut(id) ON DELETE RESTRICT,
 ADD COLUMN initialization_id uuid NOT NULL REFERENCES mta.fresh_mta_productioninitialization(id) ON DELETE RESTRICT,
 ADD COLUMN born_position bigint NOT NULL CHECK(born_position>=0),
 ADD COLUMN end_position bigint,
 ADD COLUMN closing_cut_id uuid REFERENCES mta.fresh_mta_operationalstatecut(id) ON DELETE RESTRICT,
 ADD PRIMARY KEY(cut_id,vf_ordinal), ADD CHECK(vf_ordinal>=0),
 ADD CHECK((end_position IS NULL AND closing_cut_id IS NULL) OR
   (end_position IS NOT NULL AND closing_cut_id IS NOT NULL AND end_position>born_position));
CREATE INDEX {table}_visible ON mta_state.{table} USING gist(int8range(born_position,end_position,'[)'));
CREATE INDEX {table}_owner ON mta_state.{table}(initialization_id,born_position,vf_ordinal);
CREATE INDEX {table}_closed ON mta_state.{table}(closing_cut_id,born_position,vf_ordinal)
 WHERE closing_cut_id IS NOT NULL;
CREATE INDEX {table}_date ON mta_state.{table}(initialization_id,"{date_field}");
CREATE TRIGGER history_insert AFTER INSERT ON mta_state.{table}
 REFERENCING NEW TABLE AS new_rows FOR EACH STATEMENT EXECUTE FUNCTION mta.dated_history_insert('{date_field}');
CREATE TRIGGER history_close AFTER UPDATE ON mta_state.{table}
 REFERENCING OLD TABLE AS old_rows NEW TABLE AS new_rows FOR EACH STATEMENT EXECUTE FUNCTION mta.dated_history_close();
CREATE TRIGGER history_retained BEFORE DELETE OR TRUNCATE ON mta_state.{table}
 FOR EACH STATEMENT EXECUTE FUNCTION mta.state_storage_retained();
'''
    for suffix, operation, reference in (
        ('insert', 'INSERT', 'NEW TABLE AS new_rows'),
        ('update', 'UPDATE', 'OLD TABLE AS old_rows NEW TABLE AS new_rows'),
        ('delete', 'DELETE', 'OLD TABLE AS old_rows'), ('truncate', 'TRUNCATE', ''),
    ):
        SQL += (f'CREATE TRIGGER ingestion_watch_{suffix} AFTER {operation} ON mta_state.{table} '
                + (f'REFERENCING {reference} ' if reference else '')
                + "FOR EACH STATEMENT EXECUTE FUNCTION mta.ingestion_watch('operational');\n")

# New cut families must not enable rationing payload writes under another seal.
prior = import_module('mta.runtime.migrations.0250_rationing_occurrence_storage')
start = prior.SQL.index('CREATE FUNCTION mta.rationing_delta_owner()')
body = prior.SQL[start:prior.SQL.index('REVOKE ALL ON FUNCTION mta.rationing_delta_owner()',start)]
body = body.replace('CREATE FUNCTION', 'CREATE OR REPLACE FUNCTION', 1).replace(
    ' c=mta.require_pending_state_cut(identity);',
    " c=mta.require_pending_state_cut(identity);\n IF c.family<>'rationing_history' THEN RAISE EXCEPTION 'Rationing family differs'; END IF;")
SQL += body


class Migration(migrations.Migration):
    dependencies = [('fresh_mta', '0265_dated_history_families')]
    # Accepted immutable history cannot be discarded by a schema downgrade.
    operations = [migrations.RunSQL(SQL)]
