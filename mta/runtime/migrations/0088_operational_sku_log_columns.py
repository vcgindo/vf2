from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('fresh_mta', '0087_operational_authorization_guards')]

    operations = [
        migrations.AddField(
            model_name='operationalnativeimporteruiuploadlognmsskus',
            name='field_25',
            field=models.BigIntegerField(db_column='ElephantOrderCapping', null=True),
        ),
        migrations.AddField(
            model_name='operationalnativeimporteruiuploadlognmsskus',
            name='field_26',
            field=models.DecimalField(db_column='Weight', max_digits=13, decimal_places=3, null=True),
        ),
        migrations.AddField(
            model_name='operationalnativeimporteruiuploadlognmsskus',
            name='field_27',
            field=models.DecimalField(db_column='Volume', max_digits=13, decimal_places=3, null=True),
        ),
    ]
