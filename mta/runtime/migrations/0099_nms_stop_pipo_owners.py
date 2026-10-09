"""Hand-authored master6 typed owners and guards; unapplied source port."""

import django.db.models.deletion
from django.db import migrations, models


FORWARD = r'''
CREATE FUNCTION mta.guard_stop_pipo_queue() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE owner bigint; deciding boolean; installing boolean; consuming boolean;
BEGIN
 owner=CASE WHEN TG_OP='DELETE' THEN OLD.source_id ELSE NEW.source_id END;
 deciding=COALESCE(mta.supplier_decision_owned(owner),false);
 installing=COALESCE(current_setting('fresh.stop_pipo_install',true)=owner::text,false);
 consuming=mta.force_consumption_owned(owner);
 IF TG_OP='DELETE' THEN
  IF NOT consuming THEN RAISE EXCEPTION 'Stop PIPO deletion requires owned consumption'; END IF;
  RETURN OLD;
 END IF;
 IF TG_OP='UPDATE' THEN RAISE EXCEPTION 'Stop PIPO queue is append-only'; END IF;
 IF NEW.revision<>0 OR NOT(deciding OR installing)
 THEN RAISE EXCEPTION 'Stop PIPO insert requires owned decision or installation'; END IF;
 IF deciding THEN
  UPDATE mta.fresh_mta_mdmstoppipoowner SET generation=generation+1 WHERE source_id=owner;
 END IF;
 RETURN NEW;
END $$;
CREATE FUNCTION mta.guard_stop_pipo_task_revision() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'Stop PIPO task revision is retained'; END IF;
 IF NOT COALESCE(mta.supplier_decision_owned(NEW.source_id),false)
 THEN RAISE EXCEPTION 'Stop PIPO task revision requires owned decision'; END IF;
 IF TG_OP='INSERT' THEN
  IF NEW.revision<>0 THEN RAISE EXCEPTION 'Stop PIPO task revision starts at zero'; END IF;
 ELSIF NEW.revision<>OLD.revision+1 OR (to_jsonb(NEW)-'revision')<>(to_jsonb(OLD)-'revision') THEN
  RAISE EXCEPTION 'Stop PIPO task revision must advance once';
 END IF;
 RETURN NEW;
END $$;
CREATE FUNCTION mta.guard_stop_pipo_owner() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'Stop PIPO source ownership is retained'; END IF;
 IF (to_jsonb(NEW)-ARRAY['generation','last_run_id','closing_queue_digest'])
   <>(to_jsonb(OLD)-ARRAY['generation','last_run_id','closing_queue_digest'])
 THEN RAISE EXCEPTION 'Stop PIPO installation identity is immutable'; END IF;
 IF NEW.generation<>OLD.generation THEN
  IF NOT COALESCE(mta.supplier_decision_owned(OLD.source_id),false)
   OR NEW.generation<>OLD.generation+1
   OR NEW.last_run_id IS DISTINCT FROM OLD.last_run_id
   OR NEW.closing_queue_digest<>OLD.closing_queue_digest
  THEN RAISE EXCEPTION 'Stop PIPO generation requires owned decision'; END IF;
 ELSE
  IF NOT mta.force_consumption_owned(OLD.source_id)
   OR NEW.last_run_id::text<>current_setting('fresh.mdm_consuming_run',true)
  THEN RAISE EXCEPTION 'Stop PIPO closing requires owned consumption'; END IF;
 END IF;
 RETURN NEW;
END $$;

CREATE TRIGGER stop_pipo_queue_owner BEFORE INSERT OR UPDATE OR DELETE
 ON mta.fresh_mta_mdmstoppipoqueue FOR EACH ROW EXECUTE FUNCTION mta.guard_stop_pipo_queue();
CREATE TRIGGER stop_pipo_queue_truncate BEFORE TRUNCATE
 ON mta.fresh_mta_mdmstoppipoqueue FOR EACH STATEMENT EXECUTE FUNCTION mta.deny_daily_source_mutation();
CREATE TRIGGER stop_pipo_task_revision_owner BEFORE INSERT OR UPDATE OR DELETE
 ON mta.fresh_mta_mdmstoppipotaskrevision FOR EACH ROW EXECUTE FUNCTION mta.guard_stop_pipo_task_revision();
CREATE TRIGGER stop_pipo_task_revision_truncate BEFORE TRUNCATE
 ON mta.fresh_mta_mdmstoppipotaskrevision FOR EACH STATEMENT EXECUTE FUNCTION mta.deny_daily_source_mutation();
CREATE TRIGGER stop_pipo_owner_update BEFORE UPDATE OR DELETE
 ON mta.fresh_mta_mdmstoppipoowner FOR EACH ROW EXECUTE FUNCTION mta.guard_stop_pipo_owner();
CREATE TRIGGER stop_pipo_owner_truncate BEFORE TRUNCATE
 ON mta.fresh_mta_mdmstoppipoowner FOR EACH STATEMENT EXECUTE FUNCTION mta.deny_daily_source_mutation();
CREATE TRIGGER stop_pipo_consumed_owner BEFORE INSERT OR UPDATE OR DELETE
 ON mta.fresh_mta_mdmstoppipoconsumed FOR EACH ROW EXECUTE FUNCTION mta.guard_force_consumed();
CREATE TRIGGER stop_pipo_consumed_truncate BEFORE TRUNCATE
 ON mta.fresh_mta_mdmstoppipoconsumed FOR EACH STATEMENT EXECUTE FUNCTION mta.deny_daily_source_mutation();

CREATE TABLE mta_state.input_stop_pipo_queue (
 vf_run_id uuid NOT NULL REFERENCES mta.fresh_mta_calculationrun(id) ON DELETE RESTRICT,
 vf_image text NOT NULL, vf_ordinal bigint NOT NULL,
 "id" bigint, "revision" bigint, "SKUCode" text, "WhCode" text,
 PRIMARY KEY(vf_run_id,vf_image,vf_ordinal));
CREATE TRIGGER stop_pipo_input_owner BEFORE INSERT OR UPDATE OR DELETE
 ON mta_state.input_stop_pipo_queue FOR EACH ROW EXECUTE FUNCTION mta.guard_supplier_input_image();
CREATE TRIGGER stop_pipo_input_truncate BEFORE TRUNCATE
 ON mta_state.input_stop_pipo_queue FOR EACH STATEMENT EXECUTE FUNCTION mta.deny_daily_source_mutation();

CREATE TABLE mta_state.input_stop_pipo_task_revision (
 vf_run_id uuid NOT NULL REFERENCES mta.fresh_mta_calculationrun(id) ON DELETE RESTRICT,
 vf_image text NOT NULL, vf_ordinal bigint NOT NULL,
 "task_id" text, "revision" bigint,
 PRIMARY KEY(vf_run_id,vf_image,vf_ordinal));
CREATE TRIGGER stop_pipo_input_owner BEFORE INSERT OR UPDATE OR DELETE
 ON mta_state.input_stop_pipo_task_revision FOR EACH ROW EXECUTE FUNCTION mta.guard_supplier_input_image();
CREATE TRIGGER stop_pipo_input_truncate BEFORE TRUNCATE
 ON mta_state.input_stop_pipo_task_revision FOR EACH STATEMENT EXECUTE FUNCTION mta.deny_daily_source_mutation();
'''

REVERSE = r'''
DROP TABLE mta_state.input_stop_pipo_task_revision;
DROP TABLE mta_state.input_stop_pipo_queue;
DROP TRIGGER stop_pipo_consumed_truncate ON mta.fresh_mta_mdmstoppipoconsumed;
DROP TRIGGER stop_pipo_consumed_owner ON mta.fresh_mta_mdmstoppipoconsumed;
DROP TRIGGER stop_pipo_owner_truncate ON mta.fresh_mta_mdmstoppipoowner;
DROP TRIGGER stop_pipo_owner_update ON mta.fresh_mta_mdmstoppipoowner;
DROP TRIGGER stop_pipo_task_revision_truncate ON mta.fresh_mta_mdmstoppipotaskrevision;
DROP TRIGGER stop_pipo_task_revision_owner ON mta.fresh_mta_mdmstoppipotaskrevision;
DROP TRIGGER stop_pipo_queue_truncate ON mta.fresh_mta_mdmstoppipoqueue;
DROP TRIGGER stop_pipo_queue_owner ON mta.fresh_mta_mdmstoppipoqueue;
DROP FUNCTION mta.guard_stop_pipo_owner();
DROP FUNCTION mta.guard_stop_pipo_task_revision();
DROP FUNCTION mta.guard_stop_pipo_queue();
'''


class Migration(migrations.Migration):

    dependencies = [
        ('fresh_mta', '0098_nms_season_eligibility_install'),
    ]

    operations = [
        migrations.CreateModel(
            name='MdmDraftStopPipo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('RowId', models.IntegerField()),
                ('DraftId', models.CharField(max_length=50)),
                ('IsSelected', models.CharField(max_length=50, null=True)),
                ('SKUCode', models.CharField(max_length=50, null=True)),
                ('PhaseOutSKUName', models.CharField(max_length=125, null=True)),
                ('WHCode', models.CharField(max_length=50, null=True)),
                ('LocationName', models.CharField(max_length=125, null=True)),
                ('OriginalNorm', models.IntegerField(null=True)),
                ('CurrentNorm', models.IntegerField(null=True)),
                ('LastNormChangeDate', models.DateField(null=True)),
                ('PhaseOutStartDate', models.DateField(null=True)),
                ('PhaseInSkuCode', models.CharField(max_length=50, null=True)),
                ('PhaseInSkuName', models.CharField(max_length=125, null=True)),
                ('PhaseInCurrNorm', models.IntegerField(null=True)),
                ('PhaseInTargetNorm', models.IntegerField(null=True)),
                ('Warning', models.TextField(null=True)),
                ('Error', models.TextField(null=True)),
                ('source', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='fresh_mta.mdmsource')),
            ],
        ),
        migrations.CreateModel(
            name='MdmStopPipoHistory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('SKUCode', models.CharField(max_length=50, null=True)),
                ('WhCode', models.CharField(max_length=50, null=True)),
                ('ActionType', models.IntegerField(null=True)),
                ('TaskId', models.CharField(max_length=50, null=True)),
                ('ApproverId', models.TextField(null=True)),
                ('Status', models.CharField(max_length=50, null=True)),
                ('Comments', models.TextField(null=True)),
                ('ApprovedBy', models.IntegerField(null=True)),
                ('source', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='fresh_mta.mdmsource')),
            ],
            options={'abstract': False},
        ),
        migrations.CreateModel(
            name='MdmStopPipoOwner',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('provenance', models.JSONField()),
                ('receipt_digest', models.CharField(max_length=64)),
                ('closing_queue_digest', models.CharField(max_length=64)),
                ('generation', models.PositiveBigIntegerField(default=0)),
                ('last_run', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='fresh_mta.calculationrun')),
                ('source', models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, to='fresh_mta.mdmsource')),
            ],
        ),
        migrations.CreateModel(
            name='MdmStopPipoQueue',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('SKUCode', models.CharField(max_length=50, null=True)),
                ('WhCode', models.CharField(max_length=50, null=True)),
                ('revision', models.PositiveBigIntegerField(default=0)),
                ('source', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='fresh_mta.mdmsource')),
            ],
            options={'abstract': False},
        ),
        migrations.CreateModel(
            name='MdmStopPipoRequested',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('SKUCode', models.CharField(max_length=50, null=True)),
                ('WhCode', models.CharField(max_length=50, null=True)),
                ('ActionType', models.IntegerField(null=True)),
                ('Approved', models.BooleanField(null=True)),
                ('Reverted', models.BooleanField(null=True)),
                ('TaskId', models.CharField(max_length=50, null=True)),
                ('source', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='fresh_mta.mdmsource')),
            ],
            options={'abstract': False},
        ),
        migrations.CreateModel(
            name='MdmStopPipoTaskRevision',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('task_id', models.CharField(max_length=50)),
                ('revision', models.PositiveBigIntegerField(default=0)),
                ('source', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='fresh_mta.mdmsource')),
            ],
            options={
                'constraints': [models.UniqueConstraint(fields=('source', 'task_id'), name='mdm_stop_pipo_task_revision')],
            },
        ),
        migrations.CreateModel(
            name='MdmStopPipoConsumed',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('SKUCode', models.CharField(max_length=50, null=True)),
                ('WhCode', models.CharField(max_length=50, null=True)),
                ('source_pk', models.PositiveBigIntegerField()),
                ('revision', models.PositiveBigIntegerField()),
                ('ordinal', models.PositiveBigIntegerField()),
                ('cleared', models.BooleanField()),
                ('run', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='fresh_mta.calculationrun')),
                ('source', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='fresh_mta.mdmsource')),
            ],
            options={
                'constraints': [models.UniqueConstraint(fields=('run', 'ordinal'), name='mdm_stop_pipo_consumed_ordinal')],
            },
        ),
        migrations.RunSQL(FORWARD, REVERSE),
    ]
