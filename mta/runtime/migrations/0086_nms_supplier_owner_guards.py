from django.db import migrations

FORWARD = r'''
CREATE FUNCTION mta.guard_supplier_raw() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE source bigint;
BEGIN
 IF TG_OP='DELETE' THEN source=OLD.source_id; ELSE source=NEW.source_id; END IF;
 IF TG_OP='INSERT' AND current_setting('fresh.mdm_supplier_bootstrap',true)=source::text
  AND NOT EXISTS(SELECT 1 FROM mta.fresh_mta_mdmdailyinputcapture WHERE source_id=source)
  THEN RETURN NEW; END IF;
 PERFORM 1 FROM mta.fresh_mta_mdmdailyinputcapture C
 JOIN mta.fresh_mta_calculationrun R ON R.id=C.run_id
 WHERE C.run_id::text=current_setting('fresh.mdm_consuming_run',true)
 AND C.source_id=source AND C.status='CAPTURED' AND R.status='RUNNING' FOR UPDATE OF C,R;
 IF NOT FOUND OR TG_OP='UPDATE' THEN RAISE EXCEPTION 'Supplier raw requires owned daily replacement'; END IF;
 IF TG_OP='DELETE' THEN RETURN OLD; ELSE RETURN NEW; END IF;
END $$;
CREATE FUNCTION mta.guard_supplier_archive() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF TG_OP<>'INSERT' THEN RAISE EXCEPTION 'Supplier archive is retained'; END IF;
 PERFORM 1 FROM mta.fresh_mta_mdmdailyinputcapture C
 JOIN mta.fresh_mta_calculationrun R ON R.id=C.run_id
 WHERE C.run_id=NEW.run_id AND C.run_id::text=current_setting('fresh.mdm_consuming_run',true)
 AND C.source_id=NEW.source_id AND C.status='CAPTURED' AND R.status='RUNNING' FOR UPDATE OF C,R;
 IF NOT FOUND THEN RAISE EXCEPTION 'Supplier archive requires owned daily consumption'; END IF;
 RETURN NEW;
END $$;
'''
RAW = ('mdmsobraw', 'mdmmoqraw1', 'mdmmoqraw2')
ARCHIVES = ('mdmsobarchive', 'mdmmoqwithdestinationarchive', 'mdmmoqwithoutdestinationarchive')
for table in (*RAW, *ARCHIVES):
    function = 'guard_supplier_raw' if table in RAW else 'guard_supplier_archive'
    FORWARD += ('CREATE TRIGGER supplier_owner BEFORE INSERT OR UPDATE OR DELETE ON mta.fresh_mta_' + table
                + ' FOR EACH ROW EXECUTE FUNCTION mta.' + function + '();\n')
    FORWARD += ('CREATE TRIGGER supplier_truncate BEFORE TRUNCATE ON mta.fresh_mta_' + table
                + ' FOR EACH STATEMENT EXECUTE FUNCTION mta.deny_daily_source_mutation();\n')
FORWARD += '''CREATE TRIGGER supplier_config_immutable BEFORE UPDATE OR DELETE OR TRUNCATE
 ON mta.fresh_mta_mdmsupplierconfiguration FOR EACH STATEMENT EXECUTE FUNCTION mta.deny_daily_source_mutation();'''
REVERSE = 'DROP TRIGGER supplier_config_immutable ON mta.fresh_mta_mdmsupplierconfiguration;\n'
for table in (*RAW, *ARCHIVES):
    REVERSE += ('DROP TRIGGER supplier_owner ON mta.fresh_mta_' + table + ';\n'
                'DROP TRIGGER supplier_truncate ON mta.fresh_mta_' + table + ';\n')
REVERSE += 'DROP FUNCTION mta.guard_supplier_archive(); DROP FUNCTION mta.guard_supplier_raw();'


class Migration(migrations.Migration):
    dependencies = [('fresh_mta', '0085_nms_supplier_input_images')]
    operations = [migrations.RunSQL(FORWARD, REVERSE)]
