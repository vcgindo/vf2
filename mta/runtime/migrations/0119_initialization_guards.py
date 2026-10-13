"""Native initialization seals and typed-image/current-owner write boundaries."""
from django.db import migrations

FORWARD = r'''
CREATE FUNCTION mta.native_initialization_pending(identity uuid) RETURNS boolean
LANGUAGE sql STABLE AS $$
 SELECT EXISTS(SELECT 1 FROM mta.fresh_mta_productioninitialization I
 JOIN mta.fresh_mta_mdmsource S ON S.id=I.source_id
 WHERE I.id=identity AND I.input_manifest_digest=''
 AND S.receipt->>'schema'='fresh-production-mdm-source-v1'
 AND I.id::text=current_setting('fresh.production_initialization',true))
$$;
CREATE FUNCTION mta.guard_native_initialization() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF TG_OP='TRUNCATE' THEN RAISE EXCEPTION 'Initialization cannot be truncated'; END IF;
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'Initialization cannot be deleted'; END IF;
 IF TG_OP='INSERT' THEN
  IF NEW.id::text IS DISTINCT FROM current_setting('fresh.production_initialization',true)
   THEN RAISE EXCEPTION 'Initialization requires its owned bootstrap'; END IF;
  RETURN NEW;
 END IF;
 IF OLD.input_manifest_digest<>'' OR NEW.id<>OLD.id OR NEW.source_id<>OLD.source_id
  OR NOT mta.native_initialization_pending(OLD.id)
  THEN RAISE EXCEPTION 'Sealed initialization is immutable'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER native_initialization BEFORE INSERT OR UPDATE OR DELETE
 ON mta.fresh_mta_productioninitialization FOR EACH ROW EXECUTE FUNCTION mta.guard_native_initialization();
CREATE TRIGGER native_initialization_truncate BEFORE TRUNCATE
 ON mta.fresh_mta_productioninitialization FOR EACH STATEMENT EXECUTE FUNCTION mta.guard_native_initialization();

CREATE FUNCTION mta.guard_native_opening_image() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF TG_OP<>'INSERT' THEN RAISE EXCEPTION 'Opening images are immutable'; END IF;
 IF NOT mta.native_initialization_pending(NEW.vf_initialization_id)
  THEN RAISE EXCEPTION 'Opening image requires its pending owned initialization'; END IF;
 RETURN NEW;
END $$;
DO $$ DECLARE item record; BEGIN
 FOR item IN SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname='mta_opening' LOOP
  EXECUTE format('CREATE TRIGGER native_opening BEFORE INSERT OR UPDATE OR DELETE ON mta_opening.%I FOR EACH ROW EXECUTE FUNCTION mta.guard_native_opening_image()',item.tablename);
  EXECUTE format('CREATE TRIGGER native_opening_truncate BEFORE TRUNCATE ON mta_opening.%I FOR EACH STATEMENT EXECUTE FUNCTION mta.guard_native_opening_image()',item.tablename);
 END LOOP;
END $$;

CREATE FUNCTION mta.guard_native_source() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF TG_OP='TRUNCATE' THEN
  IF EXISTS(SELECT 1 FROM mta.fresh_mta_mdmsource WHERE receipt->>'schema'='fresh-production-mdm-source-v1')
   THEN RAISE EXCEPTION 'Native source cannot be truncated'; END IF;
  RETURN NULL;
 END IF;
 IF OLD.receipt->>'schema'='fresh-production-mdm-source-v1'
  THEN RAISE EXCEPTION 'Native source identity is immutable'; END IF;
 IF TG_OP='UPDATE' AND NEW.receipt->>'schema'='fresh-production-mdm-source-v1'
  THEN RAISE EXCEPTION 'Existing source cannot be converted to a native owner'; END IF;
 IF TG_OP='DELETE' THEN RETURN OLD; ELSE RETURN NEW; END IF;
END $$;
CREATE TRIGGER native_source BEFORE UPDATE OR DELETE ON mta.fresh_mta_mdmsource
 FOR EACH ROW EXECUTE FUNCTION mta.guard_native_source();
CREATE TRIGGER native_source_truncate BEFORE TRUNCATE ON mta.fresh_mta_mdmsource
 FOR EACH STATEMENT EXECUTE FUNCTION mta.guard_native_source();

CREATE FUNCTION mta.guard_native_base_family() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE owner bigint; native boolean;
BEGIN
 IF TG_OP='TRUNCATE' THEN
  IF EXISTS(SELECT 1 FROM mta.fresh_mta_mdmsource WHERE receipt->>'schema'='fresh-production-mdm-source-v1')
   THEN RAISE EXCEPTION 'Native family ownership cannot be truncated'; END IF;
  RETURN NULL;
 END IF;
 IF TG_OP='DELETE' THEN owner=OLD.source_id; ELSE owner=NEW.source_id; END IF;
 native=EXISTS(SELECT 1 FROM mta.fresh_mta_mdmsource WHERE id=owner AND receipt->>'schema'='fresh-production-mdm-source-v1');
 IF TG_OP='UPDATE' THEN
  native=native OR EXISTS(SELECT 1 FROM mta.fresh_mta_mdmsource WHERE id=OLD.source_id AND receipt->>'schema'='fresh-production-mdm-source-v1');
 END IF;
 IF NOT native THEN IF TG_OP='DELETE' THEN RETURN OLD; ELSE RETURN NEW; END IF; END IF;
 IF TG_OP<>'INSERT' OR NEW.master_id NOT IN (2,3) OR NOT EXISTS(
  SELECT 1 FROM mta.fresh_mta_productioninitialization I WHERE I.source_id=owner AND mta.native_initialization_pending(I.id))
  THEN RAISE EXCEPTION 'Native base family requires its pending initialization'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER native_base_family BEFORE INSERT OR UPDATE OR DELETE ON mta.fresh_mta_mdmfamilysource
 FOR EACH ROW EXECUTE FUNCTION mta.guard_native_base_family();
CREATE TRIGGER native_base_family_truncate BEFORE TRUNCATE ON mta.fresh_mta_mdmfamilysource
 FOR EACH STATEMENT EXECUTE FUNCTION mta.guard_native_base_family();

CREATE OR REPLACE FUNCTION mta.active_mdm_current_source(owner bigint) RETURNS boolean
LANGUAGE sql STABLE AS $$
 SELECT EXISTS(SELECT 1 FROM mta.fresh_mta_mdmsource WHERE id=owner AND (
  receipt->>'schema'='fresh-production-mdm-source-v1' OR
  (receipt->>'schema'='fresh-mdm-daily-source-v1'
   AND receipt->>'artifact_sha256'='be33508fd9e5cd6b0224f02502f61b87a0cfb8cdce44cafb3d1f1c3e1384d847')))
$$;
'''

# Preserve the earlier guard's consumed-running-day rule. Only native bootstrap
# gains the stricter pending initialization predicate; historical owners retain
# their original behavior and receipts.
from importlib import import_module
previous = import_module('mta.runtime.migrations.0109_active_mdm_current_guards')
start = previous.FORWARD.index('CREATE FUNCTION mta.guard_active_mdm_current()')
end = previous.FORWARD.index('END $$;', start) + len('END $$;')
guard = previous.FORWARD[start:end].replace('CREATE FUNCTION', 'CREATE OR REPLACE FUNCTION', 1)
guard = guard.replace("AND NOT EXISTS(SELECT 1 FROM mta.fresh_mta_mdmdailyinputcapture WHERE source_id=owner)",
    """AND NOT EXISTS(SELECT 1 FROM mta.fresh_mta_mdmdailyinputcapture WHERE source_id=owner)
  AND (NOT EXISTS(SELECT 1 FROM mta.fresh_mta_mdmsource WHERE id=owner AND receipt->>'schema'='fresh-production-mdm-source-v1')
       OR EXISTS(SELECT 1 FROM mta.fresh_mta_productioninitialization I WHERE I.source_id=owner AND mta.native_initialization_pending(I.id)))""")
FORWARD += guard

REVERSE = r'''
DROP TRIGGER native_base_family ON mta.fresh_mta_mdmfamilysource;
DROP TRIGGER native_base_family_truncate ON mta.fresh_mta_mdmfamilysource;
DROP FUNCTION mta.guard_native_base_family();
DROP TRIGGER native_source ON mta.fresh_mta_mdmsource;
DROP TRIGGER native_source_truncate ON mta.fresh_mta_mdmsource;
DROP FUNCTION mta.guard_native_source();
DO $$ DECLARE item record; BEGIN
 FOR item IN SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname='mta_opening' LOOP
  EXECUTE format('DROP TRIGGER native_opening ON mta_opening.%I',item.tablename);
  EXECUTE format('DROP TRIGGER native_opening_truncate ON mta_opening.%I',item.tablename);
 END LOOP;
END $$;
DROP FUNCTION mta.guard_native_opening_image();
DROP TRIGGER native_initialization ON mta.fresh_mta_productioninitialization;
DROP TRIGGER native_initialization_truncate ON mta.fresh_mta_productioninitialization;
DROP FUNCTION mta.guard_native_initialization();
DROP FUNCTION mta.native_initialization_pending(uuid);
'''
REVERSE += previous.FORWARD[:previous.FORWARD.index('CREATE FUNCTION mta.guard_active_mdm_current()')].replace(
    'CREATE FUNCTION', 'CREATE OR REPLACE FUNCTION', 1)
REVERSE += previous.FORWARD[start:end].replace('CREATE FUNCTION', 'CREATE OR REPLACE FUNCTION', 1)


class Migration(migrations.Migration):
    dependencies = [('fresh_mta', '0118_initialization_typed_storage')]
    operations = [migrations.RunSQL(FORWARD, REVERSE)]
