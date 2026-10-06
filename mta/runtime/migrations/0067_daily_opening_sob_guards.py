"""Seal the additive source-only representation; shared F2 storage is unchanged."""
from django.db import migrations

FORWARD = '''
CREATE TRIGGER daily_opening_sob_insert BEFORE INSERT ON mta.fresh_mta_dailyopeningsob
 FOR EACH ROW EXECUTE FUNCTION mta.guard_daily_source_insert();
CREATE TRIGGER daily_opening_sob_immutable BEFORE UPDATE OR DELETE OR TRUNCATE ON mta.fresh_mta_dailyopeningsob
 FOR EACH STATEMENT EXECUTE FUNCTION mta.deny_daily_source_mutation();
'''
REVERSE = '''
DROP TRIGGER daily_opening_sob_immutable ON mta.fresh_mta_dailyopeningsob;
DROP TRIGGER daily_opening_sob_insert ON mta.fresh_mta_dailyopeningsob;
'''


class Migration(migrations.Migration):
    dependencies = [('fresh_mta', '0066_daily_opening_sob')]
    operations = [migrations.RunSQL(FORWARD, REVERSE)]
