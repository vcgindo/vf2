"""Support bounded page lookups in the already accepted daily BPR facts."""
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [('fresh_mta', '0258_btr_dated_report_generation')]
    operations = [migrations.RunSQL("""
CREATE INDEX btr_daily_source_pair ON mta_state.bpr_vf_rationedreqreport
 (vf_run_id, lower(rtrim("SKUCode",' ')), lower(rtrim("WhCode",' ')), vf_ordinal)
 WHERE vf_image='reports/bpr/vf_RationedReqReport';
""", 'DROP INDEX mta_state.btr_daily_source_pair;')]
