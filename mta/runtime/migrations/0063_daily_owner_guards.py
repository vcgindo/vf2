from django.db import migrations
from mta.runtime.daily_owner_schema import FORWARD, REVERSE


class Migration(migrations.Migration):
    dependencies = [('fresh_mta', '0062_daily_remark_cutoff')]
    operations = [migrations.RunSQL(FORWARD, REVERSE)]
