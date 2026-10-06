"""State-aware guards for mutable daily source owners and MDM audit stamps."""
FORWARD = r'''
CREATE FUNCTION mta.guard_daily_request_owner() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'Request source provenance is retained'; END IF;
 IF NEW.name IS DISTINCT FROM OLD.name OR NEW.provenance IS DISTINCT FROM OLD.provenance
  OR NEW.provenance_digest IS DISTINCT FROM OLD.provenance_digest
  OR NEW.revision<OLD.revision
  OR current_setting('fresh.daily_request_owner',true) IS DISTINCT FROM OLD.name THEN
  RAISE EXCEPTION 'Request owner update requires unchanged provenance and explicit owner';
 END IF;
 RETURN NEW;
END $$;
CREATE FUNCTION mta.guard_daily_request_current() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE source text;
BEGIN
 IF TG_OP='DELETE' THEN source=OLD.owner_id; ELSE source=NEW.owner_id; END IF;
 IF current_setting('fresh.daily_request_owner',true) IS DISTINCT FROM source THEN
  RAISE EXCEPTION 'Current requests require explicit source ownership'; END IF;
 IF TG_OP='UPDATE' AND (NEW.owner_id IS DISTINCT FROM OLD.owner_id OR NEW.ordinal IS DISTINCT FROM OLD.ordinal)
 THEN RAISE EXCEPTION 'Current request occurrence identity is retained'; END IF;
 IF TG_OP='DELETE' THEN RETURN OLD; ELSE RETURN NEW; END IF;
END $$;
CREATE FUNCTION mta.guard_daily_mdm_evidence() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE target uuid; mutable text[]; prior jsonb; after_value jsonb;
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'MDM capture evidence is retained'; END IF;
 IF TG_TABLE_NAME='fresh_mta_mdmdailyinputcapture' THEN
  target=OLD.run_id; mutable=ARRAY['status','consumed_at'];
  IF OLD.status<>'CAPTURED' OR NEW.status<>'CONSUMED' OR NEW.consumed_at IS NULL THEN
   RAISE EXCEPTION 'Invalid MDM capture transition'; END IF;
 ELSIF TG_TABLE_NAME='fresh_mta_mdmdailyinputoccurrence' THEN
  target=OLD.capture_id; mutable=ARRAY['archived_at','cleared_at'];
 ELSE target=OLD.capture_id; mutable=ARRAY['transitioned_at'];
 END IF;
 prior=to_jsonb(OLD); after_value=to_jsonb(NEW);
 IF (prior-mutable) IS DISTINCT FROM (after_value-mutable)
  OR current_setting('fresh.mdm_consuming_run',true) IS DISTINCT FROM target::text THEN
   RAISE EXCEPTION 'MDM evidence permits only owned consumption audit stamps'; END IF;
 PERFORM 1 FROM mta.fresh_mta_mdmdailyinputcapture C
 JOIN mta.fresh_mta_calculationrun R ON R.id=C.run_id
 WHERE C.run_id=target AND C.status='CAPTURED' AND R.status='RUNNING' FOR UPDATE OF C,R;
 IF NOT FOUND THEN RAISE EXCEPTION 'MDM capture is no longer consumable'; END IF;
 RETURN NEW;
END $$;
CREATE FUNCTION mta.guard_daily_pair_owner() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'Pair exclusion source provenance is retained'; END IF;
 IF (to_jsonb(NEW)-ARRAY['digest','row_count']) IS DISTINCT FROM
    (to_jsonb(OLD)-ARRAY['digest','row_count']) THEN
  RAISE EXCEPTION 'Pair exclusion provenance is immutable'; END IF;
 PERFORM 1 FROM mta.fresh_mta_mdmdailyinputcapture C
 JOIN mta.fresh_mta_calculationrun R ON R.id=C.run_id
 WHERE C.run_id::text=current_setting('fresh.mdm_consuming_run',true)
 AND C.source_id=OLD.source_id AND C.status='CAPTURED' AND R.status='RUNNING' FOR UPDATE OF C,R;
 IF NOT FOUND THEN RAISE EXCEPTION 'Pair source update requires owned daily consumption'; END IF;
 RETURN NEW;
END $$;
CREATE FUNCTION mta.guard_daily_pair_current() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE source bigint;
BEGIN
 IF TG_OP='DELETE' THEN source=OLD.source_id; ELSE source=NEW.source_id; END IF;
 IF TG_OP='INSERT' AND current_setting('fresh.mdm_pair_bootstrap',true)=source::text
  AND NOT EXISTS(SELECT 1 FROM mta.fresh_mta_mdmdailyinputcapture WHERE source_id=source) THEN RETURN NEW; END IF;
 PERFORM 1 FROM mta.fresh_mta_mdmdailyinputcapture C
 JOIN mta.fresh_mta_calculationrun R ON R.id=C.run_id
 WHERE C.run_id::text=current_setting('fresh.mdm_consuming_run',true)
 AND C.source_id=source AND C.status='CAPTURED' AND R.status='RUNNING' FOR UPDATE OF C,R;
 IF NOT FOUND OR TG_OP='UPDATE' THEN RAISE EXCEPTION 'Pair rows require owned replacement'; END IF;
 IF TG_OP='DELETE' THEN RETURN OLD; ELSE RETURN NEW; END IF;
END $$;
CREATE OR REPLACE FUNCTION mta.guard_daily_live_remark() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE next_value bigint; expected bigint;
BEGIN
 IF NEW.actor_id IS DISTINCT FROM current_setting('fresh.daily_remark_actor',true)
   OR NEW.owner_id IS DISTINCT FROM TG_ARGV[0] THEN
   RAISE EXCEPTION 'Daily remark requires matching actor and family owner'; END IF;
 SELECT next_ordinal INTO next_value FROM mta.fresh_mta_remarkowner WHERE family=NEW.owner_id FOR UPDATE;
 IF NOT FOUND THEN RAISE EXCEPTION 'Missing daily remark owner'; END IF;
 EXECUTE format('SELECT COALESCE(max(ordinal)+1,0) FROM mta.%I WHERE owner_id=$1', TG_TABLE_NAME)
  INTO expected USING NEW.owner_id;
 IF NEW.ordinal<>expected OR NEW.ordinal<next_value THEN
  RAISE EXCEPTION 'Daily remarks require contiguous append ordinals'; END IF;
 RETURN NEW;
END $$;
CREATE OR REPLACE FUNCTION mta.guard_daily_remark_owner() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE owned_table text; actual_count bigint;
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'Daily remark owner is retained'; END IF;
 IF (to_jsonb(NEW)-'next_ordinal') IS DISTINCT FROM (to_jsonb(OLD)-'next_ordinal')
  OR NEW.next_ordinal<OLD.next_ordinal THEN
  RAISE EXCEPTION 'Daily remark owner provenance is retained'; END IF;
 owned_table=CASE OLD.family WHEN 'BPRReport_RemarkDetails' THEN 'fresh_mta_bprliveremark'
  WHEN 'BORReport_RemarkDetails' THEN 'fresh_mta_borliveremarkdaily'
  WHEN 'BORReport_OARemarkDetails' THEN 'fresh_mta_boroaliveremarkdaily' END;
 IF owned_table IS NULL THEN RAISE EXCEPTION 'Unknown remark owner'; END IF;
 EXECUTE format('SELECT count(*) FROM mta.%I WHERE owner_id=$1',owned_table)
  INTO actual_count USING OLD.family;
 IF NEW.next_ordinal<>actual_count THEN RAISE EXCEPTION 'Remark high-water mark must match contiguous journal'; END IF;
 RETURN NEW;
END $$;
CREATE FUNCTION mta.guard_daily_mdm_insert() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE target uuid;
BEGIN
 IF TG_TABLE_NAME='fresh_mta_mdmdailyinputcapture' THEN target=NEW.run_id;
 ELSE
  target=NEW.capture_id;
  PERFORM 1 FROM mta.fresh_mta_mdmdailyinputcapture WHERE run_id=target AND status='CAPTURED';
  IF NOT FOUND THEN RAISE EXCEPTION 'MDM occurrence owner is sealed'; END IF;
 END IF;
 PERFORM 1 FROM mta.fresh_mta_calculationrun WHERE id=target AND kind='DAILY_CHAIN'
  AND status='RUNNING' FOR UPDATE;
 IF NOT FOUND THEN RAISE EXCEPTION 'MDM input evidence requires running owner'; END IF;
 RETURN NEW;
END $$;
'''
TRIGGERS = (
    ('daily_request_owner', 'fresh_mta_dailyrequestowner', 'UPDATE OR DELETE', 'guard_daily_request_owner'),
    ('daily_request_current', 'fresh_mta_dailyopenrequest', 'INSERT OR UPDATE OR DELETE', 'guard_daily_request_current'),
    ('daily_pair_owner', 'fresh_mta_mdmpairexclusionsource', 'UPDATE OR DELETE', 'guard_daily_pair_owner'),
    ('daily_pair_current', 'fresh_mta_mdmpairexclusion', 'INSERT OR UPDATE OR DELETE', 'guard_daily_pair_current'),
)
for table in ('fresh_mta_mdmdailyinputcapture', 'fresh_mta_mdmdailyinputoccurrence',
              'fresh_mta_mdmdailyinputtask', 'fresh_mta_mdmdailyinputhistory'):
    TRIGGERS += (('daily_mdm_evidence', table, 'UPDATE OR DELETE', 'guard_daily_mdm_evidence'),)
    TRIGGERS += (('daily_mdm_insert', table, 'INSERT', 'guard_daily_mdm_insert'),)
for name, table, events, function in TRIGGERS:
    FORWARD += f'CREATE TRIGGER {name} BEFORE {events} ON mta.{table} FOR EACH ROW EXECUTE FUNCTION mta.{function}();\n'
    FORWARD += f'CREATE TRIGGER {name}_truncate BEFORE TRUNCATE ON mta.{table} FOR EACH STATEMENT EXECUTE FUNCTION mta.deny_daily_source_mutation();\n'
REVERSE = ''
for name, table, _, _ in TRIGGERS:
    REVERSE += f'DROP TRIGGER {name}_truncate ON mta.{table};\nDROP TRIGGER {name} ON mta.{table};\n'
for function in ('guard_daily_request_owner','guard_daily_request_current',
                 'guard_daily_mdm_evidence','guard_daily_pair_owner','guard_daily_pair_current',
                 'guard_daily_mdm_insert'):
    REVERSE += f'DROP FUNCTION mta.{function}();\n'
# Restore the prior applied live-insert guard on a reverse transition.
from mta.runtime.daily_input_schema import FORWARD as PRIOR
for name in ('guard_daily_live_remark', 'guard_daily_remark_owner'):
    body = PRIOR.split('CREATE FUNCTION mta.'+name+'()', 1)[1].split('END $$;', 1)[0]
    REVERSE += 'CREATE OR REPLACE FUNCTION mta.'+name+'()'+body+'END $$;\n'
