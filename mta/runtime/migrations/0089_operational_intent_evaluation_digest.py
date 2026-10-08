from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('fresh_mta', '0088_operational_sku_log_columns')]
    operations = [
        migrations.AddField(
            model_name='operationalintentevaluation',
            name='evaluated_digest',
            field=models.CharField(max_length=64, default=''),
            preserve_default=False,
        ),
    ]
