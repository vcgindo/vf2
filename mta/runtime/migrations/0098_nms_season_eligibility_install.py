"""The approved upload-only opening lookup has one explicit installation writer."""
from django.db import migrations

FORWARD = r'''
CREATE FUNCTION mta.guard_season_eligibility_insert() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF NOT COALESCE(NEW.source_id::text=current_setting('fresh.season_eligibility_source',true),false)
 THEN RAISE EXCEPTION 'Seasonality eligibility requires explicit fixture installation'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER season_eligibility_insert BEFORE INSERT ON mta.fresh_mta_mdmseasoneligibility
 FOR EACH ROW EXECUTE FUNCTION mta.guard_season_eligibility_insert();
'''
REVERSE = '''DROP TRIGGER season_eligibility_insert ON mta.fresh_mta_mdmseasoneligibility;
DROP FUNCTION mta.guard_season_eligibility_insert();'''


class Migration(migrations.Migration):
    dependencies = [('fresh_mta', '0097_nms_seasonality_capture_guards')]
    operations = [migrations.RunSQL(FORWARD, REVERSE)]
