"""Immutable, explicitly installed current-display acceptance fixtures."""
from django.db import migrations


FORWARD = r'''
CREATE FUNCTION mta.guard_force_display() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF TG_OP<>'INSERT' THEN RAISE EXCEPTION 'Force display fixture is immutable'; END IF;
 IF NOT COALESCE(NEW.source_id::text=current_setting('fresh.force_display_source',true),false)
 THEN RAISE EXCEPTION 'Force display fixture requires explicit installation'; END IF;
 RETURN NEW;
END $$;
'''
REVERSE = ''
for table in ('mdmforcedisplayowner', 'mdmforcedisplayrow'):
    FORWARD += f'''
CREATE TRIGGER force_display_write BEFORE INSERT OR UPDATE OR DELETE ON mta.fresh_mta_{table}
 FOR EACH ROW EXECUTE FUNCTION mta.guard_force_display();
CREATE TRIGGER force_display_truncate BEFORE TRUNCATE ON mta.fresh_mta_{table}
 FOR EACH STATEMENT EXECUTE FUNCTION mta.deny_daily_source_mutation();
'''
    REVERSE += f'''DROP TRIGGER force_display_write ON mta.fresh_mta_{table};
DROP TRIGGER force_display_truncate ON mta.fresh_mta_{table};'''
REVERSE += 'DROP FUNCTION mta.guard_force_display();'


class Migration(migrations.Migration):
    dependencies = [('fresh_mta', '0094_nms_force_display_fixture')]
    operations = [migrations.RunSQL(FORWARD, REVERSE)]
