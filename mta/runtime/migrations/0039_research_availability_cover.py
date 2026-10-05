"""Cover Research page availability without fetching wide 90-day history rows."""
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [('fresh_mta', '0038_history_prepared_memberships')]
    operations = [migrations.RunSQL(
        'CREATE INDEX fresh_research_availability_cover '
        'ON mta_state.btr_buffertrendphysicalinv '
        '(vf_run_id, vf_image, lower(rtrim("SKUCode",\' \')), '
        'lower(rtrim("WhCode",\' \'))) '
        'INCLUDE ("SKUCode", "WhCode", vf_ordinal, "Availability_01_30", "Availability_31_60", '
        '"Availability_61_90")',
        'DROP INDEX mta_state.fresh_research_availability_cover',
    )]
