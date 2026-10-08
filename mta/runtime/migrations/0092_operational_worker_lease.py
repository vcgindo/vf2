from django.db import migrations,models


class Migration(migrations.Migration):
    dependencies=[('fresh_mta','0091_operational_restore_qualification')]
    operations=[
        migrations.AddField(model_name='operationalattempt',name='lease_key',field=models.BigIntegerField(null=True)),
        migrations.AddField(model_name='operationalattempt',name='lease_owner',field=models.UUIDField(null=True)),
    ]
