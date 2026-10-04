"""Date-window access for retained Guided history; no state/schema remapping."""
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [('fresh_mta', '0017_btr_snapshot_scope_indexes')]
    operations = [migrations.RunSQL(
        'CREATE INDEX fresh_guided_history_date ON mta_state.btr_bpr '
        '(vf_run_id, vf_image, "ReportDate") '
        'INCLUDE ("SKUCode", "WHCode", "PhysicalInventoryColor", vf_ordinal)',
        'DROP INDEX mta_state.fresh_guided_history_date',
    )]
