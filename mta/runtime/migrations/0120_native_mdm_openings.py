"""Native optional MDM owners rooted in the sealed production initialization."""
import django.db.models.deletion
from importlib import import_module
from django.db import migrations, models


FORWARD = r'''
CREATE FUNCTION mta.native_mdm_family_bootstrap(owner bigint) RETURNS boolean
LANGUAGE sql STABLE AS $$
 SELECT EXISTS(SELECT 1 FROM mta.fresh_mta_productioninitialization I
 JOIN mta.fresh_mta_mdmsource S ON S.id=I.source_id
 WHERE I.source_id=owner AND I.input_manifest_digest<>''
 AND S.receipt->>'schema'='fresh-production-mdm-source-v1'
 AND I.id::text=current_setting('fresh.native_mdm_families',true)
 AND NOT EXISTS(SELECT 1 FROM mta.fresh_mta_calculationrun)
 AND NOT EXISTS(SELECT 1 FROM mta.fresh_mta_mdmdailyinputcapture C WHERE C.source_id=owner)
 AND NOT EXISTS(SELECT 1 FROM mta.fresh_mta_mdmsourceintegration X WHERE X.source_id=owner))
$$;

CREATE OR REPLACE FUNCTION mta.guard_native_base_family() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE owner bigint; native boolean; init_id text;
BEGIN
 IF TG_OP='TRUNCATE' THEN
  IF EXISTS(SELECT 1 FROM mta.fresh_mta_mdmsource WHERE receipt->>'schema'='fresh-production-mdm-source-v1')
   THEN RAISE EXCEPTION 'Native family ownership cannot be truncated'; END IF;
  RETURN NULL;
 END IF;
 IF TG_OP='DELETE' THEN owner=OLD.source_id; ELSE owner=NEW.source_id; END IF;
 native=EXISTS(SELECT 1 FROM mta.fresh_mta_mdmsource WHERE id=owner AND receipt->>'schema'='fresh-production-mdm-source-v1');
 IF TG_OP='UPDATE' THEN native=native OR EXISTS(SELECT 1 FROM mta.fresh_mta_mdmsource WHERE id=OLD.source_id AND receipt->>'schema'='fresh-production-mdm-source-v1'); END IF;
 IF NOT native THEN IF TG_OP='DELETE' THEN RETURN OLD; ELSE RETURN NEW; END IF; END IF;
 IF TG_OP<>'INSERT' THEN RAISE EXCEPTION 'Native family ownership is immutable'; END IF;
 SELECT id::text INTO init_id FROM mta.fresh_mta_productioninitialization WHERE source_id=owner;
 IF NEW.master_id IN (2,3) THEN
  IF NOT EXISTS(SELECT 1 FROM mta.fresh_mta_productioninitialization I WHERE I.source_id=owner AND mta.native_initialization_pending(I.id))
   THEN RAISE EXCEPTION 'Native base family requires its pending initialization'; END IF;
 ELSIF NEW.master_id BETWEEN 4 AND 13 THEN
  IF NOT mta.native_mdm_family_bootstrap(owner)
   OR NEW.receipt->>'schema'<>'fresh-production-mdm-opening-owner-v1'
   OR NEW.receipt->>'source_digest'<>(SELECT digest FROM mta.fresh_mta_mdmsource WHERE id=owner)
   OR NEW.receipt->>'initialization_id'<>init_id
   THEN RAISE EXCEPTION 'Native optional family requires its owned opening bootstrap'; END IF;
 ELSE RAISE EXCEPTION 'Unknown native family owner'; END IF;
 RETURN NEW;
END $$;

CREATE FUNCTION mta.guard_native_integration() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF TG_OP='TRUNCATE' THEN
  IF EXISTS(SELECT 1 FROM mta.fresh_mta_mdmsourceintegration I JOIN mta.fresh_mta_mdmsource S ON S.id=I.source_id
   WHERE S.receipt->>'schema'='fresh-production-mdm-source-v1') THEN RAISE EXCEPTION 'Native integration cannot be truncated'; END IF;
  RETURN NULL;
 END IF;
 IF TG_OP='UPDATE' THEN
  IF OLD.receipt->>'schema'='fresh-production-mdm-integration-v1'
   OR NEW.receipt->>'schema'='fresh-production-mdm-integration-v1'
   OR EXISTS(SELECT 1 FROM mta.fresh_mta_mdmsource S
      WHERE S.id IN (OLD.source_id,NEW.source_id) AND S.receipt->>'schema'='fresh-production-mdm-source-v1')
   THEN RAISE EXCEPTION 'Native integration cannot be converted or replaced'; END IF;
  RETURN NEW;
 END IF;
 IF TG_OP='DELETE' THEN
  IF OLD.receipt->>'schema'='fresh-production-mdm-integration-v1'
   OR EXISTS(SELECT 1 FROM mta.fresh_mta_mdmsource S WHERE S.id=OLD.source_id AND S.receipt->>'schema'='fresh-production-mdm-source-v1')
   THEN RAISE EXCEPTION 'Native integration is immutable'; END IF;
  RETURN OLD;
 END IF;
 IF EXISTS(SELECT 1 FROM mta.fresh_mta_mdmsource S WHERE S.id=NEW.source_id AND S.receipt->>'schema'='fresh-production-mdm-source-v1') THEN
  IF NOT mta.native_mdm_family_bootstrap(NEW.source_id)
   OR NEW.receipt->>'schema'<>'fresh-production-mdm-integration-v1'
   OR NEW.receipt->>'initialization_id'<>current_setting('fresh.native_mdm_families',true)
   OR (SELECT array_agg(master_id ORDER BY master_id) FROM mta.fresh_mta_mdmfamilysource WHERE source_id=NEW.source_id)
      <>ARRAY[2,3,4,5,6,7,8,9,10,11,12,13]::smallint[]
   THEN RAISE EXCEPTION 'Native integration requires its complete owned bootstrap'; END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER native_integration BEFORE INSERT OR UPDATE OR DELETE ON mta.fresh_mta_mdmsourceintegration
 FOR EACH ROW EXECUTE FUNCTION mta.guard_native_integration();
CREATE TRIGGER native_integration_truncate BEFORE TRUNCATE ON mta.fresh_mta_mdmsourceintegration
 FOR EACH STATEMENT EXECUTE FUNCTION mta.guard_native_integration();

CREATE OR REPLACE FUNCTION mta.guard_force_queue() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE owner bigint; deciding boolean; consuming boolean; bootstrapping boolean;
BEGIN
 owner=CASE WHEN TG_OP='DELETE' THEN OLD.source_id ELSE NEW.source_id END;
 deciding=COALESCE(mta.supplier_decision_owned(owner),false); consuming=mta.force_consumption_owned(owner);
 bootstrapping=mta.native_mdm_family_bootstrap(owner);
 IF TG_OP='DELETE' THEN IF NOT consuming THEN RAISE EXCEPTION 'Force deletion requires owned consumption'; END IF; RETURN OLD; END IF;
 IF TG_OP='INSERT' THEN IF NEW.revision<>0 OR NOT(deciding OR consuming OR bootstrapping) THEN RAISE EXCEPTION 'Force insert requires owned input writer'; END IF;
 ELSE IF NOT deciding OR NEW.revision<>OLD.revision+1 OR (to_jsonb(NEW)-'NewNorm'-'revision')<>(to_jsonb(OLD)-'NewNorm'-'revision') THEN RAISE EXCEPTION 'Force update requires owned scalar revision'; END IF; END IF;
 IF deciding AND NOT bootstrapping THEN UPDATE mta.fresh_mta_mdmforceowner SET generation=generation+1 WHERE source_id=owner; END IF;
 RETURN NEW;
END $$;
CREATE OR REPLACE FUNCTION mta.guard_force_upload_log() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE owner bigint;
BEGIN
 owner=CASE WHEN TG_OP='DELETE' THEN OLD.source_id ELSE NEW.source_id END;
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'Force upload log is retained'; END IF;
 IF TG_OP='INSERT' THEN IF NOT (COALESCE(mta.supplier_decision_owned(owner),false) OR mta.native_mdm_family_bootstrap(owner)) THEN RAISE EXCEPTION 'Force upload log insert requires owned decision'; END IF;
 ELSE IF NOT mta.force_consumption_owned(owner) OR NEW.source_id<>OLD.source_id OR (to_jsonb(NEW)-'OldNorm')<>(to_jsonb(OLD)-'OldNorm') THEN RAISE EXCEPTION 'Force upload log update requires owned OldNorm consumption'; END IF; END IF;
 RETURN NEW;
END $$;
CREATE OR REPLACE FUNCTION mta.guard_season_queue() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE owner bigint; deciding boolean; consuming boolean; bootstrapping boolean;
BEGIN
 owner=CASE WHEN TG_OP='DELETE' THEN OLD.source_id ELSE NEW.source_id END;
 deciding=COALESCE(mta.supplier_decision_owned(owner),false); consuming=mta.force_consumption_owned(owner); bootstrapping=mta.native_mdm_family_bootstrap(owner);
 IF TG_OP='DELETE' THEN IF NOT consuming THEN RAISE EXCEPTION 'Seasonality deletion requires owned consumption'; END IF; RETURN OLD; END IF;
 IF TG_OP='INSERT' THEN IF NEW.revision<>0 OR NOT(deciding OR bootstrapping) THEN RAISE EXCEPTION 'Seasonality input requires owned decision'; END IF;
 ELSE IF NOT deciding OR NEW.revision<>OLD.revision+1 OR (to_jsonb(NEW)-ARRAY['revision','StartDate','EndDate','TargetNorm','DeltaNormPercentage','UpperLowerCap','BuildupDuration'])<>(to_jsonb(OLD)-ARRAY['revision','StartDate','EndDate','TargetNorm','DeltaNormPercentage','UpperLowerCap','BuildupDuration']) THEN RAISE EXCEPTION 'Seasonality update requires native input-field revision'; END IF; END IF;
 IF NOT bootstrapping THEN UPDATE mta.fresh_mta_mdmseasonowner SET generation=generation+1 WHERE source_id=owner; END IF;
 RETURN NEW;
END $$;
CREATE OR REPLACE FUNCTION mta.guard_season_current() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE owner bigint; deciding boolean; consuming boolean;
BEGIN
 owner=CASE WHEN TG_OP='DELETE' THEN OLD.source_id ELSE NEW.source_id END; deciding=COALESCE(mta.supplier_decision_owned(owner),false); consuming=mta.force_consumption_owned(owner);
 IF TG_OP='DELETE' THEN IF NOT consuming THEN RAISE EXCEPTION 'Seasonality replacement requires owned consumption'; END IF; RETURN OLD; END IF;
 IF TG_OP='INSERT' THEN IF NOT (consuming OR mta.target_mdm_install_owned(owner) OR mta.season_accepted_closing_owned(owner) OR mta.native_mdm_family_bootstrap(owner)) OR NEW.revision<>0 THEN RAISE EXCEPTION 'Seasonality current requires produced closing'; END IF;
 ELSE IF NOT deciding OR NEW.revision<>OLD.revision+1 OR (to_jsonb(NEW)-ARRAY['revision','Status','Comment'])<>(to_jsonb(OLD)-ARRAY['revision','Status','Comment']) THEN RAISE EXCEPTION 'Seasonality decision may change only status/comment'; END IF; UPDATE mta.fresh_mta_mdmseasonowner SET generation=generation+1 WHERE source_id=owner; END IF;
 RETURN NEW;
END $$;

CREATE FUNCTION mta.guard_native_mdm_opening_row() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE owner bigint; provenance jsonb;
BEGIN
 IF TG_OP<>'INSERT' THEN RETURN NEW; END IF;
 owner=NEW.source_id;
 IF NOT EXISTS(SELECT 1 FROM mta.fresh_mta_mdmsource S WHERE S.id=owner AND S.receipt->>'schema'='fresh-production-mdm-source-v1') THEN RETURN NEW; END IF;
 IF NOT mta.native_mdm_family_bootstrap(owner) THEN
  IF NOT EXISTS(SELECT 1 FROM mta.fresh_mta_mdmsourceintegration I WHERE I.source_id=owner AND I.receipt->>'schema'='fresh-production-mdm-integration-v1')
   THEN RAISE EXCEPTION 'Native MDM row requires its owned opening bootstrap'; END IF;
  IF TG_TABLE_NAME IN ('fresh_mta_mdmsupplierconfiguration','fresh_mta_mdmforceowner','fresh_mta_mdmseasonowner','fresh_mta_mdmstoppipoowner','fresh_mta_mdmphasecontrolsowner')
   OR current_setting('fresh.mdm_supplier_bootstrap',true)=owner::text
   OR current_setting('fresh.stop_pipo_install',true)=owner::text
   OR current_setting('fresh.phase_controls_install',true)=owner::text
   OR current_setting('fresh.season_eligibility_source',true)=owner::text
   THEN RAISE EXCEPTION 'Native MDM opening writer cannot be reused after sealing'; END IF;
  RETURN NEW;
 END IF;
 IF TG_TABLE_NAME IN ('fresh_mta_mdmsupplierconfiguration','fresh_mta_mdmforceowner','fresh_mta_mdmseasonowner','fresh_mta_mdmstoppipoowner','fresh_mta_mdmphasecontrolsowner') THEN
  provenance=NEW.provenance;
  IF provenance->>'schema'<>'fresh-production-mdm-opening-owner-v1'
   OR provenance->>'source_digest'<>(SELECT digest FROM mta.fresh_mta_mdmsource WHERE id=owner)
   OR provenance->>'initialization_id'<>current_setting('fresh.native_mdm_families',true)
   THEN RAISE EXCEPTION 'Native MDM owner provenance differs'; END IF;
 END IF;
 RETURN NEW;
END $$;
'''

NATIVE_TABLES = ('mdmsupplierconfiguration', 'mdmsobraw', 'mdmmoqraw1', 'mdmmoqraw2',
    'mdmforceowner', 'mdmforcequeue', 'mdmforceuploadlog',
    'mdmseasonowner', 'mdmseasonqueue', 'mdmseasoncurrent', 'mdmseasoneligibility',
    'mdmstoppipoowner', 'mdmstoppipoqueue',
    'mdmphasecontrolsowner', 'mdmphaseoutqueue', 'mdmphaseinnormqueue')
for table in NATIVE_TABLES:
    FORWARD += (f'CREATE TRIGGER native_mdm_opening_row BEFORE INSERT ON mta.fresh_mta_{table} '
                'FOR EACH ROW EXECUTE FUNCTION mta.guard_native_mdm_opening_row();\n')

REVERSE = ''.join(f'DROP TRIGGER native_mdm_opening_row ON mta.fresh_mta_{table};\n'
                  for table in NATIVE_TABLES)
REVERSE += r'''
DROP FUNCTION mta.guard_native_mdm_opening_row();
DROP TRIGGER native_integration_truncate ON mta.fresh_mta_mdmsourceintegration;
DROP TRIGGER native_integration ON mta.fresh_mta_mdmsourceintegration;
DROP FUNCTION mta.guard_native_integration();
'''


def _function(module, name, next_name):
    sql = import_module(module).FORWARD
    start = sql.index('CREATE FUNCTION mta.'+name+'()')
    end = sql.index('CREATE FUNCTION mta.'+next_name+'()', start)
    return sql[start:end].replace('CREATE FUNCTION', 'CREATE OR REPLACE FUNCTION', 1)


def _single_function(module, name):
    sql = import_module(module).FORWARD
    start = sql.index('CREATE FUNCTION mta.'+name+'()')
    end = sql.index('END $$;', start) + len('END $$;')
    return sql[start:end].replace('CREATE FUNCTION', 'CREATE OR REPLACE FUNCTION', 1)


REVERSE += _function('mta.runtime.migrations.0091_nms_force_capture_guards',
                     'guard_force_queue', 'guard_force_task_revision')
REVERSE += _function('mta.runtime.migrations.0093_nms_force_terminal_ownership',
                     'guard_force_upload_log', 'guard_force_consumed')
REVERSE += _function('mta.runtime.migrations.0097_nms_seasonality_capture_guards',
                     'guard_season_queue', 'guard_season_current')
REVERSE += import_module('mta.runtime.migrations.0107_mdm_season_accepted_closing').NEW_CURRENT
REVERSE += _single_function('mta.runtime.migrations.0119_initialization_guards',
                            'guard_native_base_family')
REVERSE += 'DROP FUNCTION mta.native_mdm_family_bootstrap(bigint);'


class Migration(migrations.Migration):
    dependencies = [('fresh_mta', '0119_initialization_guards')]
    operations = [
        migrations.AddField(model_name='mdmstoppipoowner', name='root_state_digest',
            field=models.CharField(default='', max_length=64)),
        migrations.AlterField(model_name='mdmstoppipoowner', name='last_run',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT,
                                    to='fresh_mta.calculationrun')),
        migrations.AddField(model_name='mdmphasecontrolsowner', name='root_state_digest',
            field=models.CharField(default='', max_length=64)),
        migrations.AlterField(model_name='mdmphasecontrolsowner', name='last_run',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT,
                                    to='fresh_mta.calculationrun')),
        migrations.RunSQL(FORWARD, REVERSE),
    ]
