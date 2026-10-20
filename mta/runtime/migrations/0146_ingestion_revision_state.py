"""Keep certification immutable; generations have a separate guarded owner.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
from django.db import migrations, models
import django.db.models.deletion
import importlib


def split(apps, editor):
    cert = apps.get_model('fresh_mta', 'InitializationCertification')
    state = apps.get_model('fresh_mta', 'IngestionRevisionState')
    fields = ('master_epoch', 'configuration_epoch', 'fact_epoch', 'operational_epoch', 'action_epoch')
    for row in cert.objects.filter(status='CERTIFIED').iterator():
        state.objects.create(initialization_id=row.initialization_id,
            **{field: getattr(row, field) for field in fields})


def guards(apps, editor):
    # The applied prior migration is immutable. Reuse its frozen function text,
    # replacing only certificate mutation with revision-state mutation.
    old = importlib.import_module('mta.runtime.migrations.0145_ingestion_revision_guards')
    sql = old.SQL[old.SQL.index('CREATE FUNCTION mta.ingestion_watch()'):]
    sql = sql.replace('CREATE FUNCTION', 'CREATE OR REPLACE FUNCTION', 1)
    sql = sql.replace('UPDATE mta.fresh_mta_initializationcertification SET',
        'UPDATE mta.fresh_mta_ingestionrevisionstate SET')
    sql = sql.replace("WHERE status='CERTIFIED';", "WHERE initialization_id IN "
        "(SELECT initialization_id FROM mta.fresh_mta_initializationcertification WHERE status='CERTIFIED');")
    with editor.connection.cursor() as c:
        c.execute(sql)
        c.execute(r'''
CREATE OR REPLACE FUNCTION mta.ingestion_authority_guard() RETURNS trigger LANGUAGE plpgsql
SET search_path=pg_catalog,mta AS $$
DECLARE owner_name text;
BEGIN
 IF TG_OP IN ('TRUNCATE','DELETE') THEN RAISE EXCEPTION 'Ingestion authority is retained'; END IF;
 SELECT pg_get_userbyid(relowner) INTO owner_name FROM pg_class WHERE oid=TG_RELID;
 IF current_user<>owner_name AND NOT EXISTS(SELECT 1 FROM pg_roles WHERE rolname=current_user AND rolsuper)
 THEN RAISE EXCEPTION 'Ingestion authority requires its trusted table owner'; END IF;
 IF TG_OP='UPDATE' THEN
  IF TG_TABLE_NAME='fresh_mta_ingestionrevisionstate' THEN
   IF NEW.initialization_id<>OLD.initialization_id OR NEW.master_epoch<OLD.master_epoch
    OR NEW.configuration_epoch<OLD.configuration_epoch OR NEW.fact_epoch<OLD.fact_epoch
    OR NEW.operational_epoch<OLD.operational_epoch OR NEW.action_epoch<OLD.action_epoch
   THEN RAISE EXCEPTION 'Ingestion generations cannot regress or change owner'; END IF;
  ELSIF TG_TABLE_NAME='fresh_mta_masterinputrevision' THEN
   IF NOT (OLD.status='CANDIDATE' AND NEW.status='ACCEPTED'
     AND (to_jsonb(OLD)-'status')=(to_jsonb(NEW)-'status'))
   THEN RAISE EXCEPTION 'Master input revision is immutable'; END IF;
  ELSIF TG_TABLE_NAME='fresh_mta_initializationcertification' THEN
   IF NOT (OLD.status='CERTIFIED' AND NEW.status='INVALIDATED'
     AND (to_jsonb(OLD)-'status')=(to_jsonb(NEW)-'status'))
   THEN RAISE EXCEPTION 'Initialization certification is immutable'; END IF;
  ELSE RAISE EXCEPTION 'Ingestion compatibility receipt is immutable';
  END IF;
 END IF;
 RETURN NEW;
END $$;
REVOKE ALL ON FUNCTION mta.ingestion_authority_guard() FROM PUBLIC;
CREATE TRIGGER ingestion_authority BEFORE INSERT OR UPDATE OR DELETE
 ON mta.fresh_mta_ingestionrevisionstate FOR EACH ROW EXECUTE FUNCTION mta.ingestion_authority_guard();
CREATE TRIGGER ingestion_authority_truncate BEFORE TRUNCATE
 ON mta.fresh_mta_ingestionrevisionstate FOR EACH STATEMENT EXECUTE FUNCTION mta.ingestion_authority_guard();
''')


class Migration(migrations.Migration):
    dependencies = [('fresh_mta', '0145_ingestion_revision_guards')]
    operations = [
        migrations.CreateModel(name='IngestionRevisionState', fields=[
            ('initialization', models.OneToOneField(primary_key=True, serialize=False,
                on_delete=django.db.models.deletion.PROTECT, to='fresh_mta.productioninitialization')),
            *[(name, models.PositiveBigIntegerField(default=0)) for name in
                ('master_epoch', 'configuration_epoch', 'fact_epoch', 'operational_epoch', 'action_epoch')]]),
        migrations.RunPython(split, migrations.RunPython.noop),
        *[migrations.RemoveField(model_name='initializationcertification', name=name) for name in
            ('master_epoch', 'configuration_epoch', 'fact_epoch', 'operational_epoch', 'action_epoch')],
        migrations.AddField(model_name='ingestionreleasecompatibility', name='original_commit',
            field=models.CharField(max_length=40, default=''), preserve_default=False),
        migrations.AddField(model_name='ingestionreleasecompatibility', name='target_commit',
            field=models.CharField(max_length=40, default=''), preserve_default=False),
        migrations.RunPython(guards),
    ]
