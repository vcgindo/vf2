"""Revoked admission can retire its worker, never admit a new business write."""
from importlib import import_module
from django.db import migrations

_prior=import_module('mta.runtime.migrations.0182_scoped_revision_ownership')
_native=_prior.SQL.split('CREATE FUNCTION mta.scope_native_cut(target uuid)',1)[1].split('$body$;',1)[0]
_retained=_native.replace("C.status='CERTIFIED'","C.status IN ('CERTIFIED','INVALIDATED')")
assert _retained!=_native
SQL='CREATE FUNCTION mta.scope_retained_cut(target uuid)'+_retained+'$body$;\n'
SQL+='REVOKE ALL ON FUNCTION mta.scope_retained_cut(uuid) FROM PUBLIC;\n'
_anchor=' observed=mta.scope_native_cut(NEW.run_id); expected=mta.scope_expected_cut(NEW.run_id);'
assert _prior._attempt.count(_anchor)==1
_attempt=_prior._attempt.replace('observed jsonb; expected jsonb;',
    'observed jsonb; expected jsonb; certification_status text;').replace(_anchor,r'''
 IF TG_OP='UPDATE' AND NEW.status='FAILED' THEN
  observed=mta.scope_retained_cut(NEW.run_id);
  IF observed IS NOT NULL THEN
   SELECT C.status INTO STRICT certification_status FROM mta.fresh_mta_initializationcertification C
    WHERE C.initialization_id::text=parent.production_manifest->'ingestion_preparation'->>'initialization_id'
     AND C.receipt_digest=parent.production_manifest->'ingestion_preparation'->>'certification_digest';
   IF certification_status<>'CERTIFIED' THEN
    IF NEW.failure->>'certification_status' IS DISTINCT FROM certification_status THEN
     RAISE EXCEPTION 'Revoked scoped worker must retain its certification diagnostic'; END IF;
   ELSIF NEW.failure ? 'certification_status' THEN
    RAISE EXCEPTION 'Scoped certification diagnostic differs'; END IF;
  END IF;
 ELSE observed=mta.scope_native_cut(NEW.run_id); END IF;
 expected=mta.scope_expected_cut(NEW.run_id);
''')
SQL+='CREATE OR REPLACE FUNCTION mta.guard_scope_attempt()'+_attempt+'$guard$;'
REVERSE="""DO $pre$ BEGIN
 IF EXISTS(SELECT 1 FROM mta.fresh_mta_runscopeattempt WHERE failure ? 'certification_status') THEN
 RAISE EXCEPTION 'Retained scoped failure requires a compatible forward release'; END IF;
END $pre$;
"""+'CREATE OR REPLACE FUNCTION mta.guard_scope_attempt()'+_prior._attempt+'$guard$;\nDROP FUNCTION mta.scope_retained_cut(uuid);'


class Migration(migrations.Migration):
    dependencies=[('fresh_mta','0182_scoped_revision_ownership')]
    operations=[migrations.RunSQL(SQL,REVERSE)]
