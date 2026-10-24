"""Retain 0180's whole capture-header freeze while permitting owned completion."""
from importlib import import_module
from django.db import migrations

_prior=import_module('mta.runtime.migrations.0180_scoped_capture_evidence')
_body=_prior.SQL.split('CREATE OR REPLACE FUNCTION mta.guard_scoped_capture_status()',1)[1].split('$guard$;',1)[0]
_body=_body.replace('WHERE A.run_id=OLD.run_id) THEN',"""WHERE A.run_id=OLD.run_id) AND NOT (
   OLD.status='CAPTURED' AND NEW.status='CONSUMED' AND NEW.consumed_at IS NOT NULL
   AND (to_jsonb(OLD)-ARRAY['status','consumed_at']) IS NOT DISTINCT FROM
       (to_jsonb(NEW)-ARRAY['status','consumed_at'])
   AND current_setting('fresh.mdm_consuming_run',true)=OLD.run_id::text
   AND mta.pending_day_final(NEW.run_id)) THEN""")
assert _body!=_prior.SQL.split('CREATE OR REPLACE FUNCTION mta.guard_scoped_capture_status()',1)[1].split('$guard$;',1)[0]
_old=import_module('mta.runtime.migrations.0188_day_final_ownership')


class Migration(migrations.Migration):
    dependencies=[('fresh_mta','0188_day_final_ownership')]
    operations=[migrations.RunSQL('CREATE OR REPLACE FUNCTION mta.guard_scoped_capture_status()'+_body+'$guard$;',
        'CREATE OR REPLACE FUNCTION mta.guard_scoped_capture_status()'+_old._capture+'$guard$;')]
