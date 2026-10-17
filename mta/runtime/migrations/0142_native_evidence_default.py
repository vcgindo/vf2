"""New native runs use production; historical rows and columns are unchanged."""
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('fresh_mta', '0141_logistics_guards')]
    operations = [
        migrations.AlterField(
            model_name='calculationrun',
            name='evidence_mode',
            field=models.CharField(default='production', max_length=16),
        ),
    ]
