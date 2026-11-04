"""Support bounded BTR page lookups in the accepted import anchor."""
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [('fresh_mta', '0285_adopted_transition_revision')]
    operations = [migrations.RunSQL("""
CREATE INDEX btr_anchor_source_pair ON mta_state.btr_bpr
 (vf_run_id, lower(rtrim("SKUCode",' ')), lower(rtrim("WHCode",' ')), "ReportDate", vf_ordinal)
 WHERE vf_image='closing/btr/BPR';
""", 'DROP INDEX mta_state.btr_anchor_source_pair;')]
