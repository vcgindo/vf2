"""Retained failure writes do not advance an invalidated owner's counters."""
from importlib import import_module
from django.db import migrations

_prior=import_module('mta.runtime.migrations.0183_retained_scope_failure_cut')
_body=_prior._attempt.replace('NEW.revision_closed IS DISTINCT FROM mta.scope_cut_next(expected)',
    "NEW.revision_closed IS DISTINCT FROM (CASE WHEN certification_status='INVALIDATED' "
    'THEN expected ELSE mta.scope_cut_next(expected) END)')
assert _body!=_prior._attempt
FORWARD='CREATE OR REPLACE FUNCTION mta.guard_scope_attempt()'+_body+'$guard$;'
REVERSE="""DO $pre$ BEGIN
 IF EXISTS(SELECT 1 FROM mta.fresh_mta_runscopeattempt WHERE failure ? 'certification_status') THEN
 RAISE EXCEPTION 'Invalidated scoped evidence requires a compatible forward release'; END IF;
END $pre$;
"""+'CREATE OR REPLACE FUNCTION mta.guard_scope_attempt()'+_prior._attempt+'$guard$;'


class Migration(migrations.Migration):
    dependencies=[('fresh_mta','0183_retained_scope_failure_cut')]
    operations=[migrations.RunSQL(FORWARD,REVERSE)]
