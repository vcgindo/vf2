"""Keep the BTR import trigger private when upgrading a populated namespace."""
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [('fresh_mta', '0260_btr_import_source_guard')]
    operations = [migrations.RunSQL(
        'REVOKE EXECUTE ON FUNCTION mta.check_btr_import_sources() FROM PUBLIC;',
        migrations.RunSQL.noop)]
