"""Database guards for captured daily inputs and append-only live remarks."""
FORWARD = r'''
CREATE FUNCTION mta.guard_daily_request_capture() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE target uuid;
BEGIN
 IF TG_TABLE_NAME='fresh_mta_dailyrequestcapture' THEN target=NEW.run_id;
 ELSE target=NEW.capture_id;
 END IF;
 PERFORM 1 FROM mta.fresh_mta_calculationrun WHERE id=target
   AND kind='DAILY_CHAIN' AND status='RUNNING' FOR UPDATE;
 IF NOT FOUND THEN RAISE EXCEPTION 'Request capture requires running daily input owner'; END IF;
 RETURN NEW;
END $$;
CREATE FUNCTION mta.guard_daily_pair_capture() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 PERFORM 1 FROM mta.fresh_mta_mdmdailyinputcapture C
 JOIN mta.fresh_mta_calculationrun R ON R.id=C.run_id
 WHERE C.run_id=NEW.capture_id AND C.status='CAPTURED'
   AND R.kind='DAILY_CHAIN' AND R.status='RUNNING' FOR UPDATE OF C,R;
 IF NOT FOUND THEN RAISE EXCEPTION 'Pair capture requires running daily input owner'; END IF;
 RETURN NEW;
END $$;
CREATE FUNCTION mta.guard_daily_remark_capture() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE target uuid;
BEGIN
 IF TG_TABLE_NAME='fresh_mta_remarkcapture' THEN target=NEW.run_id;
 ELSE SELECT run_id INTO target FROM mta.fresh_mta_remarkcapture WHERE id=NEW.capture_id;
 END IF;
 PERFORM 1 FROM mta.fresh_mta_calculationrun WHERE id=target
   AND kind='DAILY_CHAIN' AND status='RUNNING' FOR UPDATE;
 IF NOT FOUND THEN RAISE EXCEPTION 'Remark capture requires running daily input owner'; END IF;
 RETURN NEW;
END $$;
CREATE FUNCTION mta.guard_daily_live_remark() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF NEW.actor_id IS DISTINCT FROM current_setting('fresh.daily_remark_actor',true)
   OR NEW.owner_id IS DISTINCT FROM TG_ARGV[0] THEN
   RAISE EXCEPTION 'Daily remark requires matching actor and family owner';
 END IF;
 PERFORM 1 FROM mta.fresh_mta_remarkowner WHERE family=NEW.owner_id
   AND next_ordinal<=NEW.ordinal FOR UPDATE;
 IF NOT FOUND THEN RAISE EXCEPTION 'Daily remark ordinal precedes its owner'; END IF;
 RETURN NEW;
END $$;
CREATE FUNCTION mta.guard_daily_remark_owner() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'Daily remark owner is retained'; END IF;
 IF NEW.family IS DISTINCT FROM OLD.family
  OR NEW.provenance_digest IS DISTINCT FROM OLD.provenance_digest
  OR NEW.provenance_receipt IS DISTINCT FROM OLD.provenance_receipt
  OR NEW.initialized_at IS DISTINCT FROM OLD.initialized_at
  OR NEW.next_ordinal<OLD.next_ordinal THEN
   RAISE EXCEPTION 'Daily remark owner provenance and high-water identity are retained';
 END IF;
 RETURN NEW;
END $$;
'''

CAPTURES = (
    ('fresh_mta_dailyrequestcapture', 'guard_daily_request_capture'),
    ('fresh_mta_dailycapturedrequest', 'guard_daily_request_capture'),
    ('fresh_mta_mdmdailypairexclusion', 'guard_daily_pair_capture'),
    ('fresh_mta_remarkcapture', 'guard_daily_remark_capture'),
    ('fresh_mta_bprcapturedremark', 'guard_daily_remark_capture'),
    ('fresh_mta_borcapturedremark', 'guard_daily_remark_capture'),
    ('fresh_mta_boroacapturedremark', 'guard_daily_remark_capture'),
)
LIVE = (
    ('fresh_mta_bprliveremark', 'BPRReport_RemarkDetails'),
    ('fresh_mta_borliveremarkdaily', 'BORReport_RemarkDetails'),
    ('fresh_mta_boroaliveremarkdaily', 'BORReport_OARemarkDetails'),
)
for table, function in CAPTURES:
    FORWARD += f'''
CREATE TRIGGER daily_capture_insert BEFORE INSERT ON mta.{table}
 FOR EACH ROW EXECUTE FUNCTION mta.{function}();
CREATE TRIGGER daily_capture_immutable BEFORE UPDATE OR DELETE OR TRUNCATE ON mta.{table}
 FOR EACH STATEMENT EXECUTE FUNCTION mta.deny_daily_source_mutation();
'''
for table, family in LIVE:
    FORWARD += f'''
CREATE TRIGGER daily_live_insert BEFORE INSERT ON mta.{table}
 FOR EACH ROW EXECUTE FUNCTION mta.guard_daily_live_remark('{family}');
CREATE TRIGGER daily_live_immutable BEFORE UPDATE OR DELETE OR TRUNCATE ON mta.{table}
 FOR EACH STATEMENT EXECUTE FUNCTION mta.deny_daily_source_mutation();
'''
FORWARD += '''
CREATE TRIGGER daily_remark_owner_update BEFORE UPDATE OR DELETE ON mta.fresh_mta_remarkowner
 FOR EACH ROW EXECUTE FUNCTION mta.guard_daily_remark_owner();
CREATE TRIGGER daily_remark_owner_no_truncate BEFORE TRUNCATE ON mta.fresh_mta_remarkowner
 FOR EACH STATEMENT EXECUTE FUNCTION mta.deny_daily_source_mutation();
'''
REVERSE = '''
DROP TRIGGER daily_remark_owner_no_truncate ON mta.fresh_mta_remarkowner;
DROP TRIGGER daily_remark_owner_update ON mta.fresh_mta_remarkowner;
'''
for table, _ in LIVE:
    REVERSE += f'DROP TRIGGER daily_live_immutable ON mta.{table};\nDROP TRIGGER daily_live_insert ON mta.{table};\n'
for table, _ in CAPTURES:
    REVERSE += f'DROP TRIGGER daily_capture_immutable ON mta.{table};\nDROP TRIGGER daily_capture_insert ON mta.{table};\n'
for function in ('guard_daily_request_capture', 'guard_daily_pair_capture',
                 'guard_daily_remark_capture', 'guard_daily_live_remark',
                 'guard_daily_remark_owner'):
    REVERSE += f'DROP FUNCTION mta.{function}();\n'
