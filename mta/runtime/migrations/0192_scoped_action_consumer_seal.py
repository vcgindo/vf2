"""Action chain and downstream phase must seal the exact bound revision."""
from importlib import import_module
from django.db import migrations

_actions=import_module('mta.runtime.migrations.0191_scoped_action_ownership')
_final=import_module('mta.runtime.migrations.0188_day_final_ownership')
COMMAND_BODY=_actions.COMMAND_BODY.replace(
 "(TG_OP='INSERT' AND NEW.scope_parent_revision<>mta.scope_action_revision(NEW.run_id))",
 "NEW.scope_parent_revision<>mta.scope_action_revision(NEW.run_id)")
assert COMMAND_BODY!=_actions.COMMAND_BODY
PHASE_BODY=_final._phase
_anchor=" IF TG_OP='INSERT' THEN"
assert PHASE_BODY.count(_anchor)==1
PHASE_BODY=PHASE_BODY.replace(_anchor,r'''
 IF TG_OP='UPDATE' AND (
   coalesce(NEW.metadata->'action_revision','0'::jsonb) IS DISTINCT FROM to_jsonb(claim.action_revision)
   OR (NEW.metadata ? 'action_revision' AND
      (jsonb_typeof(NEW.metadata->'action_revision') IS DISTINCT FROM 'number'
       OR NEW.metadata->>'action_revision' !~ '^(0|[1-9][0-9]*)$'))) THEN
  RAISE EXCEPTION 'Phase consumer must seal its exact action revision'; END IF;
''' + _anchor)
SQL=('CREATE OR REPLACE FUNCTION mta.guard_command_seal() RETURNS trigger LANGUAGE plpgsql '
     'SET search_path=pg_catalog,mta AS $guard$'+COMMAND_BODY+'$guard$;\n'
     +'CREATE OR REPLACE FUNCTION mta.guard_phase_acceptance()'+PHASE_BODY+'$guard$;')
REVERSE=('CREATE OR REPLACE FUNCTION mta.guard_command_seal() RETURNS trigger LANGUAGE plpgsql '
     'SET search_path=pg_catalog,mta AS $guard$'+_actions.COMMAND_BODY+'$guard$;\n'
     +'CREATE OR REPLACE FUNCTION mta.guard_phase_acceptance()'+_final._phase+'$guard$;')


class Migration(migrations.Migration):
    dependencies=[('fresh_mta','0191_scoped_action_ownership')]
    operations=[migrations.RunSQL(SQL,REVERSE)]
