import django.db.models.deletion
import uuid
from django.db import migrations, models


# New PostgreSQL custody/shape guard, additive to Django's generated model.
SQL=r'''
CREATE FUNCTION mta.guard_scope_pick_files() RETURNS trigger LANGUAGE plpgsql
 SET search_path=pg_catalog,mta AS $guard$
DECLARE P mta.fresh_mta_runphaseacceptance%ROWTYPE;
 item record;
BEGIN
 IF TG_OP<>'INSERT' THEN RAISE EXCEPTION 'Accepted scope Pick files are immutable'; END IF;
 SELECT * INTO P FROM mta.fresh_mta_runphaseacceptance WHERE id=NEW.phase_id;
 IF NOT FOUND OR P.phase<>'BPR' OR NOT P.state_sealed OR P.snapshot_id IS NULL
  OR NEW.phase_id::text IS DISTINCT FROM current_setting('fresh.scope_pick_phase',true)
  OR NEW.source_digest IS DISTINCT FROM P.digest
  OR NEW.source_digest !~ '^[0-9a-f]{64}$' OR NEW.recipe_digest !~ '^[0-9a-f]{64}$'
  OR NEW.digest !~ '^[0-9a-f]{64}$' OR jsonb_typeof(NEW.files)<>'object'
  OR NOT EXISTS(SELECT 1 FROM mta.fresh_mta_calculationrun R
    JOIN mta.fresh_mta_mdmdailyinputcapture C ON C.run_id=R.id
    JOIN mta.fresh_mta_dailyphasesnapshot S ON S.id=P.snapshot_id
    WHERE R.id=P.run_id AND R.kind='DAILY_CHAIN' AND R.status IN ('RUNNING','SUCCEEDED')
      AND P.input_digest=R.input_digest AND P.source_id=C.source_id
      AND P.capture_digest=C.revision_digest AND C.status IN ('CAPTURED','CONSUMED')
      AND S.acceptance_id=P.id AND S.run_id=R.id AND S.phase='BPR') THEN
  RAISE EXCEPTION 'Scope Pick files require exact accepted BPR ownership';
 END IF;
 IF (SELECT count(*) FROM jsonb_object_keys(NEW.files))<>4
  OR NOT NEW.files ?& ARRAY['LogisticPickListReport.csv','LogisticRemainingQtySummary.csv',
      'LogisticRemainingQtyDetails.csv','TransportReqSummaryRpt.csv'] THEN
  RAISE EXCEPTION 'Scope Pick files require exact four-file roster';
 END IF;
 FOR item IN SELECT * FROM jsonb_each(NEW.files) LOOP
  IF jsonb_typeof(item.value)<>'object' OR (SELECT count(*) FROM jsonb_object_keys(item.value))<>2
   OR NOT item.value ?& ARRAY['size','sha256']
   OR jsonb_typeof(item.value->'size')<>'number'
   OR coalesce(item.value->>'size','') !~ '^(0|[1-9][0-9]*)$'
   OR coalesce(item.value->>'sha256','') !~ '^[0-9a-f]{64}$' THEN
   RAISE EXCEPTION 'Scope Pick file metadata differs';
  END IF;
 END LOOP;
 RETURN NEW;
END $guard$;
REVOKE ALL ON FUNCTION mta.guard_scope_pick_files() FROM PUBLIC;
CREATE TRIGGER scope_pick_files_immutable BEFORE INSERT OR UPDATE OR DELETE
 ON mta.fresh_mta_scopepickfiles FOR EACH ROW EXECUTE FUNCTION mta.guard_scope_pick_files();
'''
REVERSE='DROP TRIGGER scope_pick_files_immutable ON mta.fresh_mta_scopepickfiles; DROP FUNCTION mta.guard_scope_pick_files();'


class Migration(migrations.Migration):

    dependencies = [
        ('fresh_mta', '0192_scoped_action_consumer_seal'),
    ]

    operations = [
        migrations.CreateModel(
            name='ScopePickFiles',
            fields=[
                ('phase', models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, primary_key=True, related_name='pick_files', serialize=False, to='fresh_mta.runphaseacceptance')),
                ('source_digest', models.CharField(max_length=64)),
                ('recipe_digest', models.CharField(max_length=64)),
                ('directory', models.UUIDField(default=uuid.uuid4)),
                ('files', models.JSONField()),
                ('digest', models.CharField(max_length=64)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.RunSQL(SQL,REVERSE),
    ]
