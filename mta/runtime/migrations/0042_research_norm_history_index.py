"""Serve the Research daily modal's exact native pair history in source order."""
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [('fresh_mta', '0041_research_count_index')]
    operations = [migrations.RunSQL(
        'CREATE INDEX fresh_research_norm_history '
        'ON mta_state.dbm_normchangelogtbl '
        '(vf_run_id,vf_image,"SKUCode","WHCode",vf_ordinal) '
        'INCLUDE ("OldNorm","NewNorm","NormChangeDate","NormChangeReason")',
        'DROP INDEX mta_state.fresh_research_norm_history',
    )]
