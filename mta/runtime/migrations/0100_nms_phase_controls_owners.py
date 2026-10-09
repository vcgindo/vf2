"""Hand-authored masters7/8/9 typed owners and guards; unapplied source port."""

import django.db.models.deletion
from django.db import migrations, models


FORWARD = r'''
CREATE FUNCTION mta.guard_phase_controls_queue() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE owner bigint; deciding boolean; installing boolean; consuming boolean;
BEGIN
 owner=CASE WHEN TG_OP='DELETE' THEN OLD.source_id ELSE NEW.source_id END;
 deciding=COALESCE(mta.supplier_decision_owned(owner),false);
 installing=COALESCE(current_setting('fresh.phase_controls_install',true)=owner::text,false);
 consuming=mta.force_consumption_owned(owner);
 IF TG_OP='DELETE' THEN
  IF NOT consuming THEN RAISE EXCEPTION 'Phase-control deletion requires owned consumption'; END IF;
  RETURN OLD;
 END IF;
 IF TG_OP='UPDATE' THEN RAISE EXCEPTION 'Phase-control queue is append-only'; END IF;
 IF NEW.revision<>0 OR NOT(deciding OR installing OR consuming)
 THEN RAISE EXCEPTION 'Phase-control insert requires owned decision, installation or consumption'; END IF;
 IF deciding THEN
  UPDATE mta.fresh_mta_mdmphasecontrolsowner SET generation=generation+1 WHERE source_id=owner;
 END IF;
 RETURN NEW;
END $$;
CREATE FUNCTION mta.guard_phase_controls_task_revision() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'Phase-control task revision is retained'; END IF;
 IF NOT COALESCE(mta.supplier_decision_owned(NEW.source_id),false)
   OR NEW.master_id NOT IN (7,8,9)
 THEN RAISE EXCEPTION 'Phase-control task revision requires owned master decision'; END IF;
 IF TG_OP='INSERT' THEN
  IF NEW.revision<>0 THEN RAISE EXCEPTION 'Phase-control task revision starts at zero'; END IF;
 ELSIF NEW.revision<>OLD.revision+1 OR (to_jsonb(NEW)-'revision')<>(to_jsonb(OLD)-'revision') THEN
  RAISE EXCEPTION 'Phase-control task revision must advance once';
 END IF;
 RETURN NEW;
END $$;
CREATE FUNCTION mta.guard_phase_controls_owner() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'Phase-control source ownership is retained'; END IF;
 IF (to_jsonb(NEW)-ARRAY['generation','last_run_id','closing_queue_digest'])
   <>(to_jsonb(OLD)-ARRAY['generation','last_run_id','closing_queue_digest'])
 THEN RAISE EXCEPTION 'Phase-control installation identity is immutable'; END IF;
 IF NEW.generation<>OLD.generation THEN
  IF NOT COALESCE(mta.supplier_decision_owned(OLD.source_id),false)
   OR NEW.generation<>OLD.generation+1
   OR NEW.last_run_id IS DISTINCT FROM OLD.last_run_id
   OR NEW.closing_queue_digest<>OLD.closing_queue_digest
  THEN RAISE EXCEPTION 'Phase-control generation requires owned decision'; END IF;
 ELSE
  IF NOT mta.force_consumption_owned(OLD.source_id)
   OR NEW.last_run_id::text<>current_setting('fresh.mdm_consuming_run',true)
  THEN RAISE EXCEPTION 'Phase-control closing requires owned consumption'; END IF;
 END IF;
 RETURN NEW;
END $$;

CREATE TRIGGER phase_controls_queue_owner BEFORE INSERT OR UPDATE OR DELETE
 ON mta.fresh_mta_mdmphaseoutqueue FOR EACH ROW EXECUTE FUNCTION mta.guard_phase_controls_queue();
CREATE TRIGGER phase_controls_queue_truncate BEFORE TRUNCATE
 ON mta.fresh_mta_mdmphaseoutqueue FOR EACH STATEMENT EXECUTE FUNCTION mta.deny_daily_source_mutation();
CREATE TRIGGER phase_controls_queue_owner BEFORE INSERT OR UPDATE OR DELETE
 ON mta.fresh_mta_mdmphaseinnormqueue FOR EACH ROW EXECUTE FUNCTION mta.guard_phase_controls_queue();
CREATE TRIGGER phase_controls_queue_truncate BEFORE TRUNCATE
 ON mta.fresh_mta_mdmphaseinnormqueue FOR EACH STATEMENT EXECUTE FUNCTION mta.deny_daily_source_mutation();
CREATE TRIGGER phase_controls_task_revision_owner BEFORE INSERT OR UPDATE OR DELETE
 ON mta.fresh_mta_mdmphasecontrolstaskrevision FOR EACH ROW EXECUTE FUNCTION mta.guard_phase_controls_task_revision();
CREATE TRIGGER phase_controls_task_revision_truncate BEFORE TRUNCATE
 ON mta.fresh_mta_mdmphasecontrolstaskrevision FOR EACH STATEMENT EXECUTE FUNCTION mta.deny_daily_source_mutation();
CREATE TRIGGER phase_controls_owner_update BEFORE UPDATE OR DELETE
 ON mta.fresh_mta_mdmphasecontrolsowner FOR EACH ROW EXECUTE FUNCTION mta.guard_phase_controls_owner();
CREATE TRIGGER phase_controls_owner_truncate BEFORE TRUNCATE
 ON mta.fresh_mta_mdmphasecontrolsowner FOR EACH STATEMENT EXECUTE FUNCTION mta.deny_daily_source_mutation();
CREATE TRIGGER phase_controls_consumed_owner BEFORE INSERT OR UPDATE OR DELETE
 ON mta.fresh_mta_mdmphaseoutconsumed FOR EACH ROW EXECUTE FUNCTION mta.guard_force_consumed();
CREATE TRIGGER phase_controls_consumed_truncate BEFORE TRUNCATE
 ON mta.fresh_mta_mdmphaseoutconsumed FOR EACH STATEMENT EXECUTE FUNCTION mta.deny_daily_source_mutation();
CREATE TRIGGER phase_controls_consumed_owner BEFORE INSERT OR UPDATE OR DELETE
 ON mta.fresh_mta_mdmphaseinnormconsumed FOR EACH ROW EXECUTE FUNCTION mta.guard_force_consumed();
CREATE TRIGGER phase_controls_consumed_truncate BEFORE TRUNCATE
 ON mta.fresh_mta_mdmphaseinnormconsumed FOR EACH STATEMENT EXECUTE FUNCTION mta.deny_daily_source_mutation();

CREATE TABLE mta_state.input_phase_out_queue (
 vf_run_id uuid NOT NULL REFERENCES mta.fresh_mta_calculationrun(id) ON DELETE RESTRICT,
 vf_image text NOT NULL, vf_ordinal bigint NOT NULL,
 "id" bigint, "revision" bigint, "SKUCode" text, "WhCode" text,
 "PhaseInSKUCode" text, "Approved" boolean,
 PRIMARY KEY(vf_run_id,vf_image,vf_ordinal));
CREATE TRIGGER phase_controls_input_owner BEFORE INSERT OR UPDATE OR DELETE
 ON mta_state.input_phase_out_queue FOR EACH ROW EXECUTE FUNCTION mta.guard_supplier_input_image();
CREATE TRIGGER phase_controls_input_truncate BEFORE TRUNCATE
 ON mta_state.input_phase_out_queue FOR EACH STATEMENT EXECUTE FUNCTION mta.deny_daily_source_mutation();

CREATE TABLE mta_state.input_phase_in_norm_queue (
 vf_run_id uuid NOT NULL REFERENCES mta.fresh_mta_calculationrun(id) ON DELETE RESTRICT,
 vf_image text NOT NULL, vf_ordinal bigint NOT NULL,
 "id" bigint, "revision" bigint, "SKUCode" text, "WhCode" text,
 "TargetNorm" bigint, "Approved" boolean,
 PRIMARY KEY(vf_run_id,vf_image,vf_ordinal));
CREATE TRIGGER phase_controls_input_owner BEFORE INSERT OR UPDATE OR DELETE
 ON mta_state.input_phase_in_norm_queue FOR EACH ROW EXECUTE FUNCTION mta.guard_supplier_input_image();
CREATE TRIGGER phase_controls_input_truncate BEFORE TRUNCATE
 ON mta_state.input_phase_in_norm_queue FOR EACH STATEMENT EXECUTE FUNCTION mta.deny_daily_source_mutation();

CREATE TABLE mta_state.input_phase_controls_task_revision (
 vf_run_id uuid NOT NULL REFERENCES mta.fresh_mta_calculationrun(id) ON DELETE RESTRICT,
 vf_image text NOT NULL, vf_ordinal bigint NOT NULL,
 "master_id" bigint, "task_id" text, "revision" bigint,
 PRIMARY KEY(vf_run_id,vf_image,vf_ordinal));
CREATE TRIGGER phase_controls_input_owner BEFORE INSERT OR UPDATE OR DELETE
 ON mta_state.input_phase_controls_task_revision FOR EACH ROW EXECUTE FUNCTION mta.guard_supplier_input_image();
CREATE TRIGGER phase_controls_input_truncate BEFORE TRUNCATE
 ON mta_state.input_phase_controls_task_revision FOR EACH STATEMENT EXECUTE FUNCTION mta.deny_daily_source_mutation();
'''

REVERSE = r'''
DROP TABLE mta_state.input_phase_controls_task_revision;
DROP TABLE mta_state.input_phase_in_norm_queue;
DROP TABLE mta_state.input_phase_out_queue;
DROP TRIGGER phase_controls_consumed_truncate ON mta.fresh_mta_mdmphaseinnormconsumed;
DROP TRIGGER phase_controls_consumed_owner ON mta.fresh_mta_mdmphaseinnormconsumed;
DROP TRIGGER phase_controls_consumed_truncate ON mta.fresh_mta_mdmphaseoutconsumed;
DROP TRIGGER phase_controls_consumed_owner ON mta.fresh_mta_mdmphaseoutconsumed;
DROP TRIGGER phase_controls_owner_truncate ON mta.fresh_mta_mdmphasecontrolsowner;
DROP TRIGGER phase_controls_owner_update ON mta.fresh_mta_mdmphasecontrolsowner;
DROP TRIGGER phase_controls_task_revision_truncate ON mta.fresh_mta_mdmphasecontrolstaskrevision;
DROP TRIGGER phase_controls_task_revision_owner ON mta.fresh_mta_mdmphasecontrolstaskrevision;
DROP TRIGGER phase_controls_queue_truncate ON mta.fresh_mta_mdmphaseinnormqueue;
DROP TRIGGER phase_controls_queue_owner ON mta.fresh_mta_mdmphaseinnormqueue;
DROP TRIGGER phase_controls_queue_truncate ON mta.fresh_mta_mdmphaseoutqueue;
DROP TRIGGER phase_controls_queue_owner ON mta.fresh_mta_mdmphaseoutqueue;
DROP FUNCTION mta.guard_phase_controls_owner();
DROP FUNCTION mta.guard_phase_controls_task_revision();
DROP FUNCTION mta.guard_phase_controls_queue();
'''


class Migration(migrations.Migration):

    dependencies = [
        ('fresh_mta', '0099_nms_stop_pipo_owners'),
    ]

    operations = [
        migrations.CreateModel(
            name='MdmDraftAddPipo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('RowId', models.IntegerField()),
                ('DraftId', models.CharField(max_length=50)),
                ('SKUCode', models.TextField(null=True)),
                ('WhCode', models.TextField(null=True)),
                ('PhaseInSKUCode', models.TextField(null=True)),
                ('TargetNorm', models.TextField(null=True)),
                ('Warning', models.TextField(null=True)),
                ('Error', models.TextField(null=True)),
                ('source', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='fresh_mta.mdmsource')),
            ],
        ),
        migrations.CreateModel(
            name='MdmPhaseControlsOwner',
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
            name='MdmPhaseControlsTaskRevision',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('master_id', models.PositiveSmallIntegerField()),
                ('task_id', models.CharField(max_length=50)),
                ('revision', models.PositiveBigIntegerField(default=0)),
                ('source', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='fresh_mta.mdmsource')),
            ],
            options={
                'constraints': [models.UniqueConstraint(fields=('source', 'master_id', 'task_id'), name='mdm_phase_controls_task_rev')],
            },
        ),
        migrations.CreateModel(
            name='MdmPhaseInNormHistory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('SKUCode', models.CharField(max_length=50, null=True)),
                ('WhCode', models.CharField(max_length=50, null=True)),
                ('ActionType', models.IntegerField(null=True)),
                ('TaskId', models.CharField(max_length=50, null=True)),
                ('ApproverId', models.TextField(null=True)),
                ('Status', models.CharField(max_length=50, null=True)),
                ('Comments', models.TextField(null=True)),
                ('ApprovedBy', models.CharField(max_length=50, null=True)),
                ('TargetNorm', models.IntegerField(null=True)),
                ('source', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='fresh_mta.mdmsource')),
            ],
            options={'abstract': False},
        ),
        migrations.CreateModel(
            name='MdmPhaseInNormQueue',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('SKUCode', models.CharField(max_length=50, null=True)),
                ('WhCode', models.CharField(max_length=50, null=True)),
                ('TargetNorm', models.IntegerField(null=True)),
                ('Approved', models.BooleanField(null=True)),
                ('revision', models.PositiveBigIntegerField(default=0)),
                ('source', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='fresh_mta.mdmsource')),
            ],
            options={'abstract': False},
        ),
        migrations.CreateModel(
            name='MdmPhaseInNormRequested',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('SKUCode', models.CharField(max_length=50, null=True)),
                ('WhCode', models.CharField(max_length=50, null=True)),
                ('ActionType', models.IntegerField(null=True)),
                ('Approved', models.BooleanField(null=True)),
                ('Reverted', models.BooleanField(null=True)),
                ('TaskId', models.CharField(max_length=50, null=True)),
                ('TargetNorm', models.IntegerField(null=True)),
                ('source', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='fresh_mta.mdmsource')),
            ],
            options={'abstract': False},
        ),
        migrations.CreateModel(
            name='MdmPhaseOutHistory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('SKUCode', models.CharField(max_length=50, null=True)),
                ('WhCode', models.CharField(max_length=50, null=True)),
                ('ActionType', models.IntegerField(null=True)),
                ('TaskId', models.CharField(max_length=50, null=True)),
                ('ApproverId', models.TextField(null=True)),
                ('Status', models.CharField(max_length=50, null=True)),
                ('Comments', models.TextField(null=True)),
                ('ApprovedBy', models.CharField(max_length=50, null=True)),
                ('PhaseInSKUCode', models.CharField(max_length=50, null=True)),
                ('source', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='fresh_mta.mdmsource')),
            ],
            options={'abstract': False},
        ),
        migrations.CreateModel(
            name='MdmPhaseOutQueue',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('SKUCode', models.CharField(max_length=50, null=True)),
                ('WhCode', models.CharField(max_length=50, null=True)),
                ('PhaseInSKUCode', models.CharField(max_length=50, null=True)),
                ('Approved', models.BooleanField(null=True)),
                ('revision', models.PositiveBigIntegerField(default=0)),
                ('source', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='fresh_mta.mdmsource')),
            ],
            options={'abstract': False},
        ),
        migrations.CreateModel(
            name='MdmPhaseOutRequested',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('SKUCode', models.CharField(max_length=50, null=True)),
                ('WhCode', models.CharField(max_length=50, null=True)),
                ('ActionType', models.IntegerField(null=True)),
                ('Approved', models.BooleanField(null=True)),
                ('Reverted', models.BooleanField(null=True)),
                ('TaskId', models.CharField(max_length=50, null=True)),
                ('PhaseInSKUCode', models.CharField(max_length=50, null=True)),
                ('source', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='fresh_mta.mdmsource')),
            ],
            options={'abstract': False},
        ),
        migrations.CreateModel(
            name='MdmPhaseInNormConsumed',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('SKUCode', models.CharField(max_length=50, null=True)),
                ('WhCode', models.CharField(max_length=50, null=True)),
                ('source_pk', models.PositiveBigIntegerField()),
                ('revision', models.PositiveBigIntegerField()),
                ('ordinal', models.PositiveBigIntegerField()),
                ('Approved', models.BooleanField(null=True)),
                ('TargetNorm', models.IntegerField(null=True)),
                ('run', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='fresh_mta.calculationrun')),
                ('source', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='fresh_mta.mdmsource')),
            ],
            options={
                'constraints': [models.UniqueConstraint(fields=('run', 'ordinal'), name='mdm_phase_in_consumed_ordinal')],
            },
        ),
        migrations.CreateModel(
            name='MdmPhaseOutConsumed',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('SKUCode', models.CharField(max_length=50, null=True)),
                ('WhCode', models.CharField(max_length=50, null=True)),
                ('source_pk', models.PositiveBigIntegerField()),
                ('revision', models.PositiveBigIntegerField()),
                ('ordinal', models.PositiveBigIntegerField()),
                ('Approved', models.BooleanField(null=True)),
                ('PhaseInSKUCode', models.CharField(max_length=50, null=True)),
                ('run', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='fresh_mta.calculationrun')),
                ('source', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='fresh_mta.mdmsource')),
            ],
            options={
                'constraints': [models.UniqueConstraint(fields=('run', 'ordinal'), name='mdm_phase_out_consumed_ordinal')],
            },
        ),
        migrations.RunSQL(FORWARD, REVERSE),
    ]
