from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [('fresh_mta', '0077_daily_input_command_receipt')]
    operations = [migrations.RunSQL(
        sql='CREATE TABLE mta_state.input_sob (vf_run_id uuid NOT NULL REFERENCES mta.fresh_mta_calculationrun(id) ON DELETE RESTRICT, vf_image text NOT NULL, vf_ordinal bigint NOT NULL, "SKUCode" text, "WHCode" text, "SupplierCode" text, "SOB" numeric, PRIMARY KEY(vf_run_id,vf_image,vf_ordinal))',
        reverse_sql='DROP TABLE mta_state.input_sob',
    )]
