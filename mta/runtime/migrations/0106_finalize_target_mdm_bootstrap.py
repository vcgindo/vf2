"""Close fixture bootstrap permanently when its immutable receipt is inserted."""
from django.db import migrations

FORWARD = r'''
CREATE OR REPLACE FUNCTION mta.target_mdm_install_owned(owner bigint) RETURNS boolean
LANGUAGE plpgsql VOLATILE AS $$
DECLARE source_digest text;
BEGIN
 IF NOT COALESCE(current_setting('fresh.target_mdm_install',true)=owner::text,false)
 OR current_database()<>'test_freshvcf_stage2_vm_20261003_002' THEN RETURN false; END IF;
 SELECT digest INTO source_digest FROM mta.fresh_mta_mdmsource WHERE id=owner FOR UPDATE;
 IF source_digest IS DISTINCT FROM 'eccbec8cf5f61f87f80bdf65715dee350e616041e7957f27daead42bab4b975d'
 OR NOT EXISTS(SELECT 1 FROM mta.fresh_mta_calculationrun
 WHERE id='bfd75b4b-a9df-4a08-82d3-852e3324b623' AND kind='LEGACY_UI_FIXTURE')
 THEN RETURN false; END IF;
 RETURN NOT EXISTS(SELECT 1 FROM mta.fresh_mta_mdmtargetfixture WHERE source_id=owner);
END $$;
CREATE OR REPLACE FUNCTION mta.guard_target_mdm_receipt() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF TG_OP<>'INSERT' THEN RAISE EXCEPTION 'Target MDM receipt is immutable'; END IF;
 IF NOT COALESCE(mta.target_mdm_install_owned(NEW.source_id)
 AND NEW.run_id='bfd75b4b-a9df-4a08-82d3-852e3324b623'
 AND NEW.receipt->>'schema'='fresh-mdm-target3005-consumer-fixture-v1'
 AND NEW.receipt->>'authority'='call_63dfc3ff84c84f43a2855554d598e52e:0'
 AND NEW.receipt->>'input_digest'='bdc91dd88e99b9d3aeb353bbf8e22b8ad23e07832e66281e0ebdb5681b4357d3',false)
 THEN RAISE EXCEPTION 'Target MDM receipt requires exact authorized fixture finalization'; END IF;
 RETURN NEW;
END $$;
'''


class Migration(migrations.Migration):
    dependencies = [('fresh_mta', '0105_mdm_target_fixture_guards')]
    # Reopening a finalized fixture is intentionally not a supported reverse.
    operations = [migrations.RunSQL(FORWARD)]
