"""Serialize v3 appends with sealing without a run-FK/generation deadlock.

FOR SHARE still prevents immutable source UPDATE/DELETE and permits FK readers.
DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
from importlib import import_module
from django.db import migrations

source=import_module('mta.runtime.migrations.0156_daily_report_generation_guards')
rows=import_module('mta.runtime.migrations.0159_report_reference_ownership')
old_generation='CREATE FUNCTION mta.guard_report_generation()'+source.SQL.split('CREATE FUNCTION mta.guard_report_generation()',1)[1].split('CREATE TRIGGER report_generation_guard',1)[0]
old_generation=old_generation.replace('CREATE FUNCTION','CREATE OR REPLACE FUNCTION',1)
new_generation=old_generation.replace("AND production_manifest->>'version'='3' FOR UPDATE;", "AND production_manifest->>'version'='3' FOR SHARE;")
old_rows=rows.new_rows_function
predicate=""" IF NOT EXISTS(SELECT 1 FROM mta.fresh_mta_dailyreportgeneration G
  JOIN mta.fresh_mta_calculationrun R ON R.id=G.run_id
  WHERE G.run_id=owner AND G.status='INCOMPLETE' AND R.status='SUCCEEDED'
   AND G.source_digest=R.production_digest AND R.production_manifest->>'version'='3') THEN"""
locked=""" PERFORM 1 FROM mta.fresh_mta_dailyreportgeneration G
  JOIN mta.fresh_mta_calculationrun R ON R.id=G.run_id
  WHERE G.run_id=owner AND G.status='INCOMPLETE' AND R.status='SUCCEEDED'
   AND G.source_digest=R.production_digest AND R.production_manifest->>'version'='3'
  FOR UPDATE OF G;
 IF NOT FOUND THEN"""
if predicate not in old_rows or new_generation==old_generation:
    raise ValueError('Frozen v3 guard definition differs')
new_rows=old_rows.replace(predicate,locked,1)


class Migration(migrations.Migration):
    dependencies=[('fresh_mta','0160_report_consumer_source_ownership')]
    operations=[migrations.RunSQL(new_generation+new_rows,old_generation+old_rows)]
