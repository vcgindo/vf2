"""Date-typed supplied daily transaction facts; no timestamp coercion."""
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [('fresh_mta', '0120_native_mdm_openings')]
    operations = [migrations.RunSQL('''
CREATE TABLE mta_state.input_production_transaction (
 vf_run_id uuid NOT NULL REFERENCES mta.fresh_mta_calculationrun(id) ON DELETE RESTRICT,
 vf_image text NOT NULL, vf_ordinal bigint NOT NULL,
 "WhCode" text, "TransactedItemCount" bigint, "TotalItems" bigint, "ReportDate" date,
 PRIMARY KEY(vf_run_id,vf_image,vf_ordinal));
''', 'DROP TABLE mta_state.input_production_transaction;')]
