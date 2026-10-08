from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies=[('fresh_mta','0090_operational_input_capture')]
    operations=[
        migrations.AddField(model_name='operationalbackup',name='qualification',field=models.CharField(default='',max_length=80)),
        migrations.AddField(model_name='operationalbackup',name='qualification_sha256',field=models.CharField(default='',max_length=64)),
        migrations.RemoveConstraint(model_name='operationalbackup',name='op_restore_status'),
        migrations.AddConstraint(model_name='operationalbackup',constraint=models.CheckConstraint(
            condition=models.Q(restore_status__in=['UNPROVED','RUNNING','FAILED','VERIFIED','QUALIFIED']),name='op_restore_status')),
    ]
