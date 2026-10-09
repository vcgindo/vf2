"""Join the independently applied MDM and operational migration histories."""
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('fresh_mta', '0101_mdm_source_integration'),
        ('fresh_mta', '0102_text_vehicle_input'),
    ]
    operations = []
