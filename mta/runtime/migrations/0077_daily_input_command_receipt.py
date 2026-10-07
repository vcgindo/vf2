from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [('fresh_mta', '0076_daily_evidence_policy')]
    operations = [migrations.RunSQL(
        sql='CREATE TABLE mta_state.input_command_receipt (vf_run_id uuid NOT NULL REFERENCES mta.fresh_mta_calculationrun(id) ON DELETE RESTRICT, vf_image text NOT NULL, vf_ordinal bigint NOT NULL, id bigint, digest text, "before" text, "after" text, PRIMARY KEY(vf_run_id,vf_image,vf_ordinal))',
        reverse_sql='DROP TABLE mta_state.input_command_receipt',
    )]
