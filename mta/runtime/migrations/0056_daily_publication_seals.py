from django.db import migrations
from mta.runtime.publication_schema import INITIAL_FORWARD, REVERSE


class Migration(migrations.Migration):
    dependencies = [('fresh_mta', '0055_mdm_daily_archives')]
    operations = [migrations.RunSQL(INITIAL_FORWARD, REVERSE)]
