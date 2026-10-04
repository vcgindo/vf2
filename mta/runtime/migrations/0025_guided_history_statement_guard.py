from django.db import migrations
from mta.runtime import guided_history_schema


class Migration(migrations.Migration):
    dependencies = [('fresh_mta', '0024_guided_history_receipt_verification')]
    operations = [migrations.RunSQL(guided_history_schema.BUILD_CORRECTIVE,
                                    guided_history_schema.BUILD_CORRECTIVE_REVERSE)]
