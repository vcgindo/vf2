from django.db import migrations
from mta.runtime.daily_input_schema import FORWARD, REVERSE


class Migration(migrations.Migration):
    dependencies = [('fresh_mta', '0060_daily_remark_sources')]
    operations = [migrations.RunSQL(FORWARD, REVERSE)]
