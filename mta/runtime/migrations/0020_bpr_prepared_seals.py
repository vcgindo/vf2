"""Seal BPR fixture prepared rows and the receipt written after their proof."""
from django.db import migrations
from mta.runtime.bpr_prepared_schema import FORWARD, REVERSE


class Migration(migrations.Migration):
    dependencies = [('fresh_mta', '0019_bpr_prepared_candidates')]
    operations = [migrations.RunSQL(FORWARD, REVERSE)]
