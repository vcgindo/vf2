"""Permit bounded current-row updates only inside the existing owned day.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
from importlib import import_module
from django.db import migrations

REVERSE=import_module('mta.runtime.migrations.0124_native_inactive_current_guard').FORWARD
anchor=" IF TG_OP='UPDATE' THEN RAISE EXCEPTION 'Active MDM current replacement cannot update rows'; END IF;"
assert REVERSE.count(anchor)==1
FORWARD=REVERSE.replace(anchor,""" IF TG_OP='UPDATE' AND (
  NEW.id IS DISTINCT FROM OLD.id OR NEW.source_id IS DISTINCT FROM OLD.source_id
  OR NEW.ordinal IS DISTINCT FROM OLD.ordinal
  OR to_jsonb(NEW)->'owner' IS DISTINCT FROM to_jsonb(OLD)->'owner'
  OR to_jsonb(NEW)->'use_kind' IS DISTINCT FROM to_jsonb(OLD)->'use_kind')
 THEN RAISE EXCEPTION 'Incremental current projection cannot move its occurrence'; END IF;""")
for table in ('mdmlocationattributes','mdmlocationdescription'):
    FORWARD+=f"""
CREATE TRIGGER native_location_projection_update BEFORE UPDATE
 ON mta.fresh_mta_{table} FOR EACH STATEMENT
 EXECUTE FUNCTION mta.guard_location_projection_statement();
"""
    REVERSE+=f'DROP TRIGGER native_location_projection_update ON mta.fresh_mta_{table};\n'

class Migration(migrations.Migration):
    dependencies=[('fresh_mta','0152_batch_temporal_wire')]
    operations=[migrations.RunSQL(FORWARD,REVERSE)]
