from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('fresh_mta', '0193_scope_pick_files'),
    ]

    operations = [
        migrations.RunSQL(
            'CREATE TRIGGER scope_pick_files_no_truncate BEFORE TRUNCATE '
            'ON mta.fresh_mta_scopepickfiles FOR EACH STATEMENT '
            'EXECUTE FUNCTION mta.deny_accepted_truncate();',
            'DROP TRIGGER scope_pick_files_no_truncate ON mta.fresh_mta_scopepickfiles;'),
    ]
