"""Keep frozen placement custody separate from current action read ownership."""
from importlib import import_module
from django.db import migrations

prior = import_module('mta.runtime.migrations.0235_registered_scope_read_attachment')
OLD = prior.BODY
predicate = 'BPR.action_revision=H.action_revision'
assert OLD.count(predicate) == 1
# runtime_report_publication_source still binds the file revision to its
# ORIGINAL accepted scope attempt. The inherited action guard owns the live
# read revision. A publication from a later action cut must never be attached.
BODY = OLD.replace(predicate, 'BPR.action_revision<=H.action_revision', 1)
replace_read = import_module('mta.runtime.migrations.0230_runtime_report_publication_guards').replace_read
SQL = replace_read(OLD, BODY)
REVERSE = r'''DO $stop$ BEGIN
 IF EXISTS(SELECT 1 FROM mta.fresh_mta_scopereadreference R
   JOIN mta.fresh_mta_scopereportgeneration H ON H.id=R.report_generation_id
   JOIN mta.fresh_mta_runtimereportpublication P
     ON P.id::text=R.metadata#>>'{runtime_reports,post_bpr,id}'
   WHERE R.metadata#>>'{runtime_reports,schema}'='fresh-registered-placement-read-configuration-v1'
     AND P.action_revision<>H.action_revision) THEN
  RAISE EXCEPTION 'Action-refreshed registered reads require the forward guard'; END IF;
END $stop$;
''' + replace_read(BODY, OLD)


class Migration(migrations.Migration):
    dependencies = [('fresh_mta', '0237_intake_diagnostic_guards')]
    operations = [migrations.RunSQL(SQL, REVERSE)]
