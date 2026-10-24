"""An absent explicit fence must deny the worker transition."""
from importlib import import_module
from django.db import migrations

_prior = import_module('mta.runtime.migrations.0177_scope_acceptance_guards').SQL
_body = _prior.split('CREATE FUNCTION mta.guard_scope_attempt()', 1)[1].split('$guard$;', 1)[0]
_fixed = _body.replace("current_setting('fresh.scope_fence',true)=OLD.id::text",
                      "current_setting('fresh.scope_fence',true) IS NOT DISTINCT FROM OLD.id::text")
assert _fixed != _body
FORWARD = 'CREATE OR REPLACE FUNCTION mta.guard_scope_attempt()'+_fixed+'$guard$;'
REVERSE = 'CREATE OR REPLACE FUNCTION mta.guard_scope_attempt()'+_body+'$guard$;'


class Migration(migrations.Migration):
    dependencies = [('fresh_mta', '0177_scope_acceptance_guards')]
    operations = [migrations.RunSQL(FORWARD, REVERSE)]
