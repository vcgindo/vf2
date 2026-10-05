from django.db import migrations
from mta.runtime.boroa_source_schema import FORWARD as SOURCE,REVERSE as SOURCE_REVERSE
from mta.runtime.boroa_prepared_schema import FORWARD as PREPARED,REVERSE as PREPARED_REVERSE

class Migration(migrations.Migration):
    dependencies=[('fresh_mta','0046_boroa_snapshot_and_prepared')]
    operations=[migrations.RunSQL(SOURCE,SOURCE_REVERSE),migrations.RunSQL(PREPARED,PREPARED_REVERSE)]
