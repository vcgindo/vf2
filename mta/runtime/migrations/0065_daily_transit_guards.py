from django.db import migrations


TABLES = ('fresh_mta_dailytransitraw', 'fresh_mta_dailytransitrow')
FORWARD = '''
CREATE FUNCTION mta.guard_daily_transit_insert() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 PERFORM 1 FROM mta.fresh_mta_calculationrun WHERE id=NEW.run_id
   AND kind='DAILY_CHAIN' AND status='RUNNING' FOR UPDATE;
 IF NOT FOUND THEN RAISE EXCEPTION 'Transit source requires running daily owner'; END IF;
 RETURN NEW;
END $$;
'''
REVERSE = ''
for table in TABLES:
    FORWARD += f'''
CREATE TRIGGER daily_transit_insert BEFORE INSERT ON mta.{table}
 FOR EACH ROW EXECUTE FUNCTION mta.guard_daily_transit_insert();
CREATE TRIGGER daily_transit_immutable BEFORE UPDATE OR DELETE OR TRUNCATE ON mta.{table}
 FOR EACH STATEMENT EXECUTE FUNCTION mta.deny_daily_source_mutation();
'''
    REVERSE += f'''
DROP TRIGGER daily_transit_immutable ON mta.{table};
DROP TRIGGER daily_transit_insert ON mta.{table};
'''
REVERSE += 'DROP FUNCTION mta.guard_daily_transit_insert();'


class Migration(migrations.Migration):
    dependencies = [('fresh_mta', '0064_dailytransitraw_dailytransitrow')]
    operations = [migrations.RunSQL(FORWARD, REVERSE)]
