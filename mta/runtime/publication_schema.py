"""Seals for finite daily sources and completed UI publication receipts."""
FORWARD = r"""
CREATE FUNCTION mta.deny_daily_source_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'Daily source rows and receipt are immutable'; END $$;
CREATE FUNCTION mta.guard_daily_source_insert() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 PERFORM 1 FROM mta.fresh_mta_calculationrun WHERE id=NEW.run_id
 AND kind='DAILY_CHAIN' AND status='RUNNING' FOR UPDATE;
 IF NOT FOUND THEN RAISE EXCEPTION 'Daily sources require running calculation publication'; END IF;
 IF EXISTS(SELECT 1 FROM mta.fresh_mta_dailysourcereceipt WHERE run_id=NEW.run_id) THEN
  RAISE EXCEPTION 'Daily source receipt already sealed';
 END IF;
 IF TG_TABLE_NAME='fresh_mta_dailysourcereceipt' THEN
  IF NEW.input_digest IS DISTINCT FROM
  (SELECT input_digest FROM mta.fresh_mta_calculationrun WHERE id=NEW.run_id) THEN
   RAISE EXCEPTION 'Daily source input identity differs';
  END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE FUNCTION mta.guard_daily_ui_publication() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'Daily UI publication evidence is retained'; END IF;
 IF TG_OP='UPDATE' THEN
  IF OLD.status='READY' OR NEW.run_id IS DISTINCT FROM OLD.run_id
   OR NEW.output_digest IS DISTINCT FROM OLD.output_digest
   OR NEW.source_digest IS DISTINCT FROM OLD.source_digest
   OR NEW.configuration_digest IS DISTINCT FROM OLD.configuration_digest
   OR NEW.recipe_digest IS DISTINCT FROM OLD.recipe_digest THEN
   RAISE EXCEPTION 'Daily UI publication identity or ready seal is immutable';
  END IF;
 END IF;
 IF NEW.status='READY' AND (NEW.seal_digest='' OR NEW.sealed_at IS NULL) THEN
  RAISE EXCEPTION 'Ready publication requires seal';
 END IF;
 RETURN NEW;
END $$;
CREATE FUNCTION mta.guard_daily_ui_attempt() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF TG_OP='DELETE' OR OLD.status<>'BUILDING' THEN
  RAISE EXCEPTION 'Completed daily UI attempts are immutable';
 END IF;
 IF NEW.publication_id IS DISTINCT FROM OLD.publication_id THEN
  RAISE EXCEPTION 'Daily UI attempt owner is immutable';
 END IF;
 RETURN NEW;
END $$;
"""
for prefix, table in (('daily_source','fresh_mta_dailysourcereceipt'),
                      ('daily_color','fresh_mta_dailycolorsequence')):
    FORWARD += f'''
CREATE TRIGGER {prefix}_insert BEFORE INSERT ON mta.{table} FOR EACH ROW EXECUTE FUNCTION mta.guard_daily_source_insert();
CREATE TRIGGER {prefix}_immutable BEFORE UPDATE OR DELETE OR TRUNCATE ON mta.{table} FOR EACH STATEMENT EXECUTE FUNCTION mta.deny_daily_source_mutation();
'''
FORWARD += r"""
CREATE TRIGGER daily_ui_seal BEFORE UPDATE OR DELETE ON mta.fresh_mta_dailyuipublication
 FOR EACH ROW EXECUTE FUNCTION mta.guard_daily_ui_publication();
CREATE TRIGGER daily_ui_no_truncate BEFORE TRUNCATE ON mta.fresh_mta_dailyuipublication
 FOR EACH STATEMENT EXECUTE FUNCTION mta.deny_daily_source_mutation();
CREATE TRIGGER daily_attempt_seal BEFORE UPDATE OR DELETE ON mta.fresh_mta_dailyuipublicationattempt
 FOR EACH ROW EXECUTE FUNCTION mta.guard_daily_ui_attempt();
CREATE TRIGGER daily_attempt_no_truncate BEFORE TRUNCATE ON mta.fresh_mta_dailyuipublicationattempt
 FOR EACH STATEMENT EXECUTE FUNCTION mta.deny_daily_source_mutation();
"""
REVERSE = r"""
DROP TRIGGER daily_attempt_no_truncate ON mta.fresh_mta_dailyuipublicationattempt;
DROP TRIGGER daily_attempt_seal ON mta.fresh_mta_dailyuipublicationattempt;
DROP TRIGGER daily_ui_no_truncate ON mta.fresh_mta_dailyuipublication;
DROP TRIGGER daily_ui_seal ON mta.fresh_mta_dailyuipublication;
DROP TRIGGER daily_color_immutable ON mta.fresh_mta_dailycolorsequence;
DROP TRIGGER daily_color_insert ON mta.fresh_mta_dailycolorsequence;
DROP TRIGGER daily_source_immutable ON mta.fresh_mta_dailysourcereceipt;
DROP TRIGGER daily_source_insert ON mta.fresh_mta_dailysourcereceipt;
DROP FUNCTION mta.guard_daily_ui_attempt();
DROP FUNCTION mta.guard_daily_ui_publication();
DROP FUNCTION mta.guard_daily_source_insert();
DROP FUNCTION mta.deny_daily_source_mutation();
"""

# 0056 is already applied. Preserve its original SQL and correct the typed
# NEW-record branch only through the following additive migration.
INITIAL_FORWARD = FORWARD.replace(
 " IF TG_TABLE_NAME='fresh_mta_dailysourcereceipt' THEN\n  IF NEW.input_digest IS DISTINCT FROM\n  (SELECT input_digest FROM mta.fresh_mta_calculationrun WHERE id=NEW.run_id) THEN\n   RAISE EXCEPTION 'Daily source input identity differs';\n  END IF;",
 " IF TG_TABLE_NAME='fresh_mta_dailysourcereceipt' AND NEW.input_digest IS DISTINCT FROM\n (SELECT input_digest FROM mta.fresh_mta_calculationrun WHERE id=NEW.run_id) THEN\n  RAISE EXCEPTION 'Daily source input identity differs';")
