"""Native supplier capture images; no queue business payload in JSON metadata."""
from django.db import migrations


TABLES = {
    'input_supplier_sob': '"WhCode" text, "SOB" double precision',
    'input_supplier_moq_with_destination': '"WhCode" text, "MOQ" bigint',
    'input_supplier_moq_without_destination': '"MOQ" bigint',
}


class Migration(migrations.Migration):
    dependencies = [('fresh_mta', '0084_nms_supplier_archives')]
    operations = [migrations.RunSQL(
        'CREATE TABLE mta_state.' + name + ' (vf_run_id uuid NOT NULL REFERENCES '
        'mta.fresh_mta_calculationrun(id) ON DELETE RESTRICT, vf_image text NOT NULL, '
        'vf_ordinal bigint NOT NULL, "id" bigint, "SKUCode" text, "SupplierCode" text, '
        + extra + ', "ActionType" bigint, "Approved" boolean, "Reverted" boolean, '
        'PRIMARY KEY(vf_run_id,vf_image,vf_ordinal))',
        'DROP TABLE mta_state.' + name) for name, extra in TABLES.items()]
