"""Hand-authored immutable combined-source metadata; unapplied source port."""
import django.db.models.deletion
from django.db import migrations, models


FORWARD = r'''
CREATE FUNCTION mta.guard_mdm_source_integration() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF TG_OP<>'INSERT' THEN RAISE EXCEPTION 'MDM integration identity is immutable'; END IF;
 IF jsonb_typeof(NEW.receipt)<>'object' OR octet_length(NEW.receipt::text)>16384
 THEN RAISE EXCEPTION 'MDM integration requires bounded metadata'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER mdm_source_integration_guard
 BEFORE INSERT OR UPDATE OR DELETE ON mta.fresh_mta_mdmsourceintegration
 FOR EACH ROW EXECUTE FUNCTION mta.guard_mdm_source_integration();
CREATE TRIGGER mdm_source_integration_truncate
 BEFORE TRUNCATE ON mta.fresh_mta_mdmsourceintegration
 FOR EACH STATEMENT EXECUTE FUNCTION mta.deny_daily_source_mutation();
'''
REVERSE = r'''
DROP TRIGGER mdm_source_integration_guard ON mta.fresh_mta_mdmsourceintegration;
DROP TRIGGER mdm_source_integration_truncate ON mta.fresh_mta_mdmsourceintegration;
DROP FUNCTION mta.guard_mdm_source_integration();
'''


class Migration(migrations.Migration):
    dependencies = [('fresh_mta', '0100_nms_phase_controls_owners')]
    operations = [
        migrations.CreateModel(name='MdmSourceIntegration', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True,
                                       serialize=False, verbose_name='ID')),
            ('digest', models.CharField(max_length=64, unique=True)),
            ('receipt', models.JSONField()),
            ('source', models.OneToOneField(on_delete=django.db.models.deletion.PROTECT,
                                            to='fresh_mta.mdmsource')),
        ]),
        migrations.RunSQL(FORWARD, REVERSE),
    ]
