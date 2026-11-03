"""Typed occurrences and indexed lifetimes; old accepted payloads stay intact.

Required on fresh databases and upgrades. No business backfill or activation is
performed by this schema migration. Anchor certification has its normal owner.
"""
from django.db import migrations


SQL = r'''
CREATE TABLE mta_state.rationing_fact
 (LIKE mta_state.btr_rationinghistory INCLUDING CONSTRAINTS);
ALTER TABLE mta_state.rationing_fact DROP COLUMN vf_run_id, DROP COLUMN vf_image,
 ADD COLUMN cut_id uuid NOT NULL REFERENCES mta.fresh_mta_operationalstatecut(id) ON DELETE RESTRICT,
 ADD PRIMARY KEY(cut_id,vf_ordinal), ADD CHECK(vf_ordinal>=0);
CREATE INDEX rationing_fact_date ON mta_state.rationing_fact("ReportDate",cut_id,vf_ordinal);

CREATE TABLE mta_state.rationing_dispatch (
 cut_id uuid NOT NULL REFERENCES mta.fresh_mta_operationalstatecut(id) ON DELETE RESTRICT,
 position bigint NOT NULL CHECK(position>0), original_cut_id uuid NOT NULL,
 original_ordinal bigint NOT NULL, dispatch integer,
 PRIMARY KEY(cut_id,original_cut_id,original_ordinal),
 FOREIGN KEY(original_cut_id,original_ordinal)
  REFERENCES mta_state.rationing_fact(cut_id,vf_ordinal) ON DELETE RESTRICT);
CREATE INDEX rationing_dispatch_at_cut ON mta_state.rationing_dispatch
 (original_cut_id,original_ordinal,position DESC) INCLUDE(dispatch,cut_id);

CREATE TABLE mta_state.rationing_expiry (
 cut_id uuid NOT NULL REFERENCES mta.fresh_mta_operationalstatecut(id) ON DELETE RESTRICT,
 position bigint NOT NULL CHECK(position>0), original_cut_id uuid NOT NULL,
 original_ordinal bigint NOT NULL,
 PRIMARY KEY(cut_id,original_cut_id,original_ordinal),
 UNIQUE(original_cut_id,original_ordinal),
 FOREIGN KEY(original_cut_id,original_ordinal)
  REFERENCES mta_state.rationing_fact(cut_id,vf_ordinal) ON DELETE RESTRICT);

CREATE TABLE mta_state.rationing_lifetime (
 fact_cut_id uuid NOT NULL, original_ordinal bigint NOT NULL,
 initialization_id uuid NOT NULL REFERENCES mta.fresh_mta_productioninitialization(id) ON DELETE RESTRICT,
 born_position bigint NOT NULL CHECK(born_position>=0),
 end_position bigint, closing_cut_id uuid,
 PRIMARY KEY(fact_cut_id,original_ordinal),
 FOREIGN KEY(fact_cut_id,original_ordinal)
  REFERENCES mta_state.rationing_fact(cut_id,vf_ordinal) ON DELETE RESTRICT,
 FOREIGN KEY(closing_cut_id,fact_cut_id,original_ordinal)
  REFERENCES mta_state.rationing_expiry(cut_id,original_cut_id,original_ordinal) ON DELETE RESTRICT,
 CHECK((end_position IS NULL AND closing_cut_id IS NULL) OR
       (end_position IS NOT NULL AND closing_cut_id IS NOT NULL AND end_position>born_position)));
CREATE INDEX rationing_lifetime_cut ON mta_state.rationing_lifetime
 USING gist(int8range(born_position,end_position,'[)'));
CREATE INDEX rationing_lifetime_lineage ON mta_state.rationing_lifetime(initialization_id);
CREATE INDEX rationing_lifetime_closure ON mta_state.rationing_lifetime(closing_cut_id)
 WHERE closing_cut_id IS NOT NULL;

ALTER TABLE mta.fresh_mta_operationalstatecut ADD CONSTRAINT state_cut_root_hash CHECK(
 (root_body='' AND root_digest='') OR (root_body<>'' AND
 root_digest=encode(sha256(convert_to(root_body,'UTF8')),'hex')));

CREATE FUNCTION mta.state_storage_retained() RETURNS trigger LANGUAGE plpgsql
SET search_path=pg_catalog,mta AS $$
BEGIN RAISE EXCEPTION 'Operational storage history is retained'; END $$;
REVOKE ALL ON FUNCTION mta.state_storage_retained() FROM PUBLIC;

CREATE FUNCTION mta.require_pending_state_cut(identity uuid)
RETURNS mta.fresh_mta_operationalstatecut LANGUAGE plpgsql
SET search_path=pg_catalog,mta AS $$
DECLARE c mta.fresh_mta_operationalstatecut; table_owner name;
BEGIN
 SELECT pg_get_userbyid(relowner) INTO table_owner FROM pg_class
  WHERE oid='mta.fresh_mta_operationalstatecut'::regclass;
 IF current_user<>table_owner AND NOT EXISTS(SELECT 1 FROM pg_roles WHERE rolname=current_user AND rolsuper)
 THEN RAISE EXCEPTION 'Operational cut requires its trusted writer'; END IF;
 SELECT * INTO STRICT c FROM mta.fresh_mta_operationalstatecut WHERE id=identity FOR UPDATE;
 -- A pending cut cannot survive a commit (deferred seal constraint). Thus a
 -- visible pending cut belongs to this transaction, including nested savepoints.
 IF c.root_digest<>'' THEN RAISE EXCEPTION 'Operational cut is already sealed'; END IF;
 IF c.position>0 AND NOT EXISTS(SELECT 1 FROM mta.fresh_mta_calculationrun
   WHERE id=c.run_id AND status='RUNNING')
 THEN RAISE EXCEPTION 'Operational cut run is not pending'; END IF;
 RETURN c;
END $$;
REVOKE ALL ON FUNCTION mta.require_pending_state_cut(uuid) FROM PUBLIC;

CREATE FUNCTION mta.state_cut_owner() RETURNS trigger LANGUAGE plpgsql
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
 IF i.receipt_digest='' THEN RAISE EXCEPTION 'Operational cut initialization is unsealed'; END IF;
 IF NEW.position=0 THEN
  IF NOT EXISTS(SELECT 1 FROM pg_roles WHERE rolname=current_user AND rolsuper) AND
    NOT (current_setting('fresh.production_initialization',true)=i.id::text AND
      EXISTS(SELECT 1 FROM mta.fresh_mta_productioninitialization
        WHERE id=i.id AND xmin=pg_current_xact_id()::text::xid))
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
 RETURN NEW;
END $$;
REVOKE ALL ON FUNCTION mta.state_cut_owner() FROM PUBLIC;

CREATE FUNCTION mta.rationing_delta_owner() RETURNS trigger LANGUAGE plpgsql
SET search_path=pg_catalog,mta AS $$
DECLARE identity uuid; owners bigint; c mta.fresh_mta_operationalstatecut;
BEGIN
 IF TG_TABLE_NAME='rationing_lifetime' THEN
  SELECT min(fact_cut_id::text)::uuid,count(DISTINCT fact_cut_id) INTO identity,owners FROM new_rows;
 ELSE
  SELECT min(cut_id::text)::uuid,count(DISTINCT cut_id) INTO identity,owners FROM new_rows;
 END IF;
 IF owners=0 THEN RETURN NULL; END IF;
 IF owners<>1 THEN RAISE EXCEPTION 'A storage write must have one producing cut'; END IF;
 c=mta.require_pending_state_cut(identity);
 IF TG_TABLE_NAME='rationing_fact' THEN
  IF c.position>0 AND EXISTS(SELECT 1 FROM new_rows N JOIN mta.fresh_mta_calculationrun R
    ON R.id=c.run_id WHERE N."ReportDate" IS DISTINCT FROM R.business_date OR N."Dispatch" IS NOT NULL)
  THEN RAISE EXCEPTION 'New rationing facts require the current producer date'; END IF;
 ELSIF TG_TABLE_NAME='rationing_lifetime' THEN
  IF EXISTS(SELECT 1 FROM new_rows WHERE initialization_id<>c.initialization_id OR
      born_position<>c.position OR end_position IS NOT NULL OR closing_cut_id IS NOT NULL)
  THEN RAISE EXCEPTION 'Lifetime insertion differs from its fact owner'; END IF;
 ELSE
  IF c.position=0 OR EXISTS(SELECT 1 FROM new_rows N
    JOIN mta.fresh_mta_operationalstatecut P ON P.id=N.original_cut_id
    LEFT JOIN mta_state.rationing_lifetime L ON L.fact_cut_id=N.original_cut_id
     AND L.original_ordinal=N.original_ordinal
    WHERE N.position<>c.position OR P.initialization_id<>c.initialization_id OR P.family<>c.family OR
     P.root_digest='' OR P.position>=c.position OR L.fact_cut_id IS NULL OR
     (L.end_position IS NOT NULL AND L.end_position<=c.position))
  THEN RAISE EXCEPTION 'Revision or expiry requires a visible prior occurrence'; END IF;
 END IF;
 RETURN NULL;
END $$;
REVOKE ALL ON FUNCTION mta.rationing_delta_owner() FROM PUBLIC;

CREATE FUNCTION mta.rationing_lifetime_close() RETURNS trigger LANGUAGE plpgsql
SET search_path=pg_catalog,mta AS $$
DECLARE identity uuid; owners bigint; c mta.fresh_mta_operationalstatecut;
BEGIN
 SELECT min(closing_cut_id::text)::uuid,count(DISTINCT closing_cut_id) INTO identity,owners FROM new_rows;
 IF NOT EXISTS(SELECT 1 FROM new_rows) THEN RETURN NULL; END IF;
 IF owners<>1 THEN RAISE EXCEPTION 'Lifetime closure requires one producing cut'; END IF;
 c=mta.require_pending_state_cut(identity);
 IF c.position=0 OR EXISTS(SELECT 1 FROM old_rows O FULL JOIN new_rows N
   ON N.fact_cut_id=O.fact_cut_id AND N.original_ordinal=O.original_ordinal
   WHERE O.fact_cut_id IS NULL OR N.fact_cut_id IS NULL OR O.end_position IS NOT NULL OR
    O.closing_cut_id IS NOT NULL OR N.end_position IS DISTINCT FROM c.position OR
    N.closing_cut_id IS DISTINCT FROM c.id OR N.initialization_id<>c.initialization_id OR
    (to_jsonb(O)-ARRAY['end_position','closing_cut_id']) IS DISTINCT FROM
    (to_jsonb(N)-ARRAY['end_position','closing_cut_id'])) OR
   EXISTS(SELECT 1 FROM new_rows N LEFT JOIN mta_state.rationing_expiry E
    ON E.cut_id=c.id AND E.original_cut_id=N.fact_cut_id AND E.original_ordinal=N.original_ordinal
    WHERE E.cut_id IS NULL OR E.position<>c.position)
 THEN RAISE EXCEPTION 'Lifetime may close once against its exact immutable expiry'; END IF;
 RETURN NULL;
END $$;
REVOKE ALL ON FUNCTION mta.rationing_lifetime_close() FROM PUBLIC;

CREATE FUNCTION mta.require_state_cut_seal() RETURNS trigger LANGUAGE plpgsql
SET search_path=pg_catalog,mta AS $$
DECLARE c mta.fresh_mta_operationalstatecut; p mta.fresh_mta_operationalstatecut;
 b jsonb; image jsonb; anchor jsonb; original_digest text;
 facts bigint; revisions bigint; expired bigint; retained bigint;
BEGIN
 SELECT * INTO STRICT c FROM mta.fresh_mta_operationalstatecut WHERE id=NEW.id;
 IF c.root_digest='' THEN RAISE EXCEPTION 'Unsealed operational cut cannot commit'; END IF;
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
    jsonb_array_length(b->'fields') NOT IN (0,69) OR
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
REVOKE ALL ON FUNCTION mta.require_state_cut_seal() FROM PUBLIC;

CREATE TRIGGER state_cut_owner BEFORE INSERT OR UPDATE ON mta.fresh_mta_operationalstatecut
 FOR EACH ROW EXECUTE FUNCTION mta.state_cut_owner();
CREATE CONSTRAINT TRIGGER state_cut_complete AFTER INSERT OR UPDATE ON mta.fresh_mta_operationalstatecut
 DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION mta.require_state_cut_seal();
CREATE TRIGGER state_cut_retained BEFORE DELETE OR TRUNCATE ON mta.fresh_mta_operationalstatecut
 FOR EACH STATEMENT EXECUTE FUNCTION mta.state_storage_retained();
'''

for table in ('rationing_fact', 'rationing_dispatch', 'rationing_expiry', 'rationing_lifetime'):
    SQL += (f'CREATE TRIGGER rationing_insert AFTER INSERT ON mta_state.{table} '
            'REFERENCING NEW TABLE AS new_rows FOR EACH STATEMENT '
            'EXECUTE FUNCTION mta.rationing_delta_owner();\n')
    operations = 'DELETE OR TRUNCATE' if table == 'rationing_lifetime' else 'UPDATE OR DELETE OR TRUNCATE'
    SQL += (f'CREATE TRIGGER rationing_retained BEFORE {operations} ON mta_state.{table} '
            'FOR EACH STATEMENT EXECUTE FUNCTION mta.state_storage_retained();\n')
SQL += '''CREATE TRIGGER rationing_close AFTER UPDATE ON mta_state.rationing_lifetime
 REFERENCING OLD TABLE AS old_rows NEW TABLE AS new_rows FOR EACH STATEMENT
 EXECUTE FUNCTION mta.rationing_lifetime_close();
'''

for schema, table in [('mta', 'fresh_mta_operationalstatecut'), *[
        ('mta_state', 'rationing_' + name) for name in ('fact', 'dispatch', 'expiry', 'lifetime')]]:
    for suffix, op, reference in (
            ('insert', 'INSERT', 'NEW TABLE AS new_rows'),
            ('update', 'UPDATE', 'OLD TABLE AS old_rows NEW TABLE AS new_rows'),
            ('delete', 'DELETE', 'OLD TABLE AS old_rows'), ('truncate', 'TRUNCATE', '')):
        SQL += (f'CREATE TRIGGER ingestion_watch_{suffix} AFTER {op} ON {schema}.{table} '
                + (f'REFERENCING {reference} ' if reference else '')
                + "FOR EACH STATEMENT EXECUTE FUNCTION mta.ingestion_watch('operational');\n")


class Migration(migrations.Migration):
    dependencies = [('fresh_mta', '0249_operational_state_cuts')]
    # Deliberately no destructive downgrade of accepted history.
    operations = [migrations.RunSQL(SQL)]
