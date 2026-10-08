import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies=[('fresh_mta','0089_operational_intent_evaluation_digest')]
    operations=[
        migrations.CreateModel(name='OperationalInputSource',fields=[
            ('run',models.OneToOneField(on_delete=django.db.models.deletion.PROTECT,
                primary_key=True,serialize=False,to='fresh_mta.calculationrun')),
            ('policy',models.CharField(max_length=80)),
            ('input_digest',models.CharField(max_length=64)),
            ('schema_digest',models.CharField(max_length=64)),
            ('rows_digest',models.CharField(max_length=64)),
            ('images',models.JSONField()),
        ]),
        migrations.RunSQL('''
CREATE TRIGGER op_input_source_insert BEFORE INSERT ON mta.fresh_mta_operationalinputsource
 FOR EACH ROW EXECUTE FUNCTION mta.guard_operational_producer_insert();
CREATE TRIGGER op_input_source_immutable BEFORE UPDATE OR DELETE OR TRUNCATE
 ON mta.fresh_mta_operationalinputsource
 FOR EACH STATEMENT EXECUTE FUNCTION mta.deny_daily_source_mutation();
''','''
DROP TRIGGER op_input_source_immutable ON mta.fresh_mta_operationalinputsource;
DROP TRIGGER op_input_source_insert ON mta.fresh_mta_operationalinputsource;
'''),
    ]
