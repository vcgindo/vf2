"""Approved fixture consumer bootstrap; daily consumption guards stay strict."""
from importlib import import_module
from django.db import migrations

prior = import_module('mta.runtime.migrations.0097_nms_seasonality_capture_guards').FORWARD
CURRENT = ('CREATE FUNCTION mta.guard_season_current()' + prior.split(
    'CREATE FUNCTION mta.guard_season_current()', 1)[1].split(
    'CREATE FUNCTION mta.guard_season_owner()', 1)[0]).replace(
        'CREATE FUNCTION', 'CREATE OR REPLACE FUNCTION', 1)
old_clause = 'IF NOT consuming OR NEW.revision<>0'
assert old_clause in CURRENT
NEW_CURRENT = CURRENT.replace(old_clause,
    'IF NOT (consuming OR mta.target_mdm_install_owned(owner)) OR NEW.revision<>0')
TABLES = ('mdmfixturephaseout', 'mdmfixturephasein', 'mdmfixturephasemap',
          'mdmfixtureseasonstatus')

FORWARD = r'''
CREATE FUNCTION mta.target_mdm_install_owned(owner bigint) RETURNS boolean
LANGUAGE sql STABLE AS $$
 SELECT COALESCE(current_setting('fresh.target_mdm_install',true)=owner::text,false)
 AND current_database()='test_freshvcf_stage2_vm_20261003_002'
 AND EXISTS(SELECT 1 FROM mta.fresh_mta_mdmtargetfixture f
 JOIN mta.fresh_mta_mdmsource s ON s.id=f.source_id
 WHERE f.source_id=owner AND f.run_id='bfd75b4b-a9df-4a08-82d3-852e3324b623'
 AND s.digest='eccbec8cf5f61f87f80bdf65715dee350e616041e7957f27daead42bab4b975d'
 AND f.receipt->>'schema'='fresh-mdm-target3005-consumer-fixture-v1'
 AND f.receipt->>'authority'='call_63dfc3ff84c84f43a2855554d598e52e:0')
$$;
CREATE FUNCTION mta.guard_target_mdm_receipt() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF TG_OP<>'INSERT' THEN RAISE EXCEPTION 'Target MDM receipt is immutable'; END IF;
 IF NOT COALESCE(NEW.source_id::text=current_setting('fresh.target_mdm_install',true)
 AND current_database()='test_freshvcf_stage2_vm_20261003_002'
 AND NEW.run_id='bfd75b4b-a9df-4a08-82d3-852e3324b623'
 AND NEW.receipt->>'schema'='fresh-mdm-target3005-consumer-fixture-v1'
 AND NEW.receipt->>'authority'='call_63dfc3ff84c84f43a2855554d598e52e:0'
 AND EXISTS(SELECT 1 FROM mta.fresh_mta_mdmsource s WHERE s.id=NEW.source_id
 AND s.digest='eccbec8cf5f61f87f80bdf65715dee350e616041e7957f27daead42bab4b975d'),false)
 THEN RAISE EXCEPTION 'Target MDM receipt requires exact authorized fixture installation'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER target_mdm_receipt BEFORE INSERT OR UPDATE OR DELETE
 ON mta.fresh_mta_mdmtargetfixture FOR EACH ROW EXECUTE FUNCTION mta.guard_target_mdm_receipt();
CREATE FUNCTION mta.guard_target_mdm_projection() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF TG_OP<>'INSERT' THEN RAISE EXCEPTION 'Target MDM projection is immutable'; END IF;
 IF NOT mta.target_mdm_install_owned(NEW.source_id)
 THEN RAISE EXCEPTION 'Target MDM projection requires exact owned installation'; END IF;
 RETURN NEW;
END $$;
'''
FORWARD += ''.join('CREATE TRIGGER target_mdm_projection BEFORE INSERT OR UPDATE OR DELETE '
    'ON mta.fresh_mta_' + table + ' FOR EACH ROW EXECUTE FUNCTION mta.guard_target_mdm_projection();'
    for table in TABLES)
FORWARD += NEW_CURRENT
REVERSE = CURRENT + ''.join('DROP TRIGGER target_mdm_projection ON mta.fresh_mta_' + table + ';'
    for table in TABLES) + '''
DROP TRIGGER target_mdm_receipt ON mta.fresh_mta_mdmtargetfixture;
DROP FUNCTION mta.guard_target_mdm_receipt();
DROP FUNCTION mta.guard_target_mdm_projection();
DROP FUNCTION mta.target_mdm_install_owned(bigint);
'''


class Migration(migrations.Migration):
    dependencies = [('fresh_mta', '0104_mdm_target_fixture')]
    operations = [migrations.RunSQL(FORWARD, REVERSE)]
