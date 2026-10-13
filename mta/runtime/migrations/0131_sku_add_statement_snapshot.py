"""Validate duplicate SKU occurrences against the calling INSERT snapshot.

0130 remains immutable: component proof found that a STABLE helper called from
a VOLATILE trigger's SPI expression sees prior rows of the same INSERT. The
validation trigger itself must be STABLE. No business table or seal is rewritten.
"""
from importlib import import_module

from django.db import migrations

previous = import_module('mta.runtime.migrations.0130_native_synchronous_sku_add')
old_guard = previous.FORWARD[previous.FORWARD.index('CREATE OR REPLACE FUNCTION'):]
start = old_guard.index('  PERFORM pg_advisory_xact_lock')
end = old_guard.index('\n END IF;', start)
guard = old_guard[:start] + '''  -- The earlier STABLE row trigger has validated this exact row.
  RETURN NEW;''' + old_guard[end:]

FORWARD = r'''
CREATE FUNCTION mta.lock_native_sku_add(owner bigint) RETURNS void
LANGUAGE plpgsql VOLATILE AS $$
BEGIN
 -- Production acquires this lock before its queue reads/INSERT snapshot. A
 -- direct competing INSERT must fail, not wait and use an obsolete snapshot.
 IF NOT pg_try_advisory_xact_lock(hashtextextended('fresh-mdm-supplier:' || owner::text,0))
  THEN RAISE EXCEPTION 'Native SKU Add source is owned by another publication or capture'; END IF;
 PERFORM 1 FROM mta.fresh_mta_mdmsource WHERE id=owner FOR UPDATE;
END $$;
CREATE FUNCTION mta.guard_native_sku_add() RETURNS trigger
LANGUAGE plpgsql STABLE AS $$
BEGIN
 IF current_setting('fresh.sku_add_source',true)=NEW.source_id::text
  AND coalesce(current_setting('fresh.sku_add_task',true),'')<>'' THEN
  PERFORM mta.lock_native_sku_add(NEW.source_id);
  IF NOT mta.native_sku_add_row(TG_TABLE_NAME,to_jsonb(NEW))
   THEN RAISE EXCEPTION 'Native synchronous SKU Add requires its exact approved task and queue row'; END IF;
 END IF;
 RETURN NEW;
END $$;
'''
for table in ('mdmskuattributes', 'mdmskudescription'):
    # PostgreSQL fires same-kind triggers in name order. Validation is mandatory
    # before active_mdm_current can return for this branch; a marker alone never
    # admits any row. Normal bootstrap/daily INSERTs pass straight through.
    FORWARD += f'''
CREATE TRIGGER a_native_sku_add BEFORE INSERT ON mta.fresh_mta_{table}
 FOR EACH ROW EXECUTE FUNCTION mta.guard_native_sku_add();
'''
FORWARD += guard

REVERSE = old_guard + r'''
DROP TRIGGER a_native_sku_add ON mta.fresh_mta_mdmskuattributes;
DROP TRIGGER a_native_sku_add ON mta.fresh_mta_mdmskudescription;
DROP FUNCTION mta.guard_native_sku_add();
DROP FUNCTION mta.lock_native_sku_add(bigint);
'''


class Migration(migrations.Migration):
    dependencies = [('fresh_mta', '0130_native_synchronous_sku_add')]
    operations = [migrations.RunSQL(FORWARD, REVERSE)]
