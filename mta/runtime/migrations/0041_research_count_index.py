"""Cover scoped Research/BPR counts without fetching wide candidate rows."""
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('fresh_mta', '0040_research_availability_bands')]
    operations = [migrations.AddIndex(
        model_name='bprpreparedrow',
        index=models.Index(fields=['run', 'sku_key', 'location_key'],
                           condition=models.Q(s_ordinal__isnull=False),
                           name='fresh_bpr_count_keys'),
    )]
