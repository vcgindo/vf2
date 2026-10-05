from django.db import migrations
from mta.runtime import bor_prepared_schema


class Migration(migrations.Migration):
    dependencies=[('fresh_mta','0044_bor_prepared_membership')]
    operations=[migrations.RunSQL(bor_prepared_schema.FORWARD,bor_prepared_schema.REVERSE)]
