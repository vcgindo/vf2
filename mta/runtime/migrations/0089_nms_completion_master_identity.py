"""Keep supplier supersession qualified by the frozen master identity."""
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [('fresh_mta', '0088_nms_supplier_revision_guards')]
    operations = [migrations.RunSQL(
        'ALTER TABLE mta_state.input_mdm_completion ADD COLUMN master_id text',
        'ALTER TABLE mta_state.input_mdm_completion DROP COLUMN master_id')]
