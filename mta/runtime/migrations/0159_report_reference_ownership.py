"""Classify remaining derived reference bags; guard old identities on UPDATE.

Old runs retain invalidation and no report path becomes a general write bypass.
DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
from importlib import import_module
from django.db import migrations

revision=import_module('mta.runtime.migrations.0157_report_revision_ownership')
rows=import_module('mta.runtime.migrations.0158_derived_report_row_guards')
REFERENCES=('fresh_mta_guidedavailabilitysnapshotreference',
    'fresh_mta_researchavailabilitymembership','fresh_mta_researchavailabilityband')


def current_body():
    extra="WHEN TG_TABLE_SCHEMA='mta' AND TG_TABLE_NAME=ANY(ARRAY["+','.join("'"+table+"'" for table in REFERENCES)+"] ) THEN report_join='LEFT JOIN mta.fresh_mta_calculationrun R ON R.id=N.run_id'; report_filter='TRUE';\n"
    return revision.current_body().replace(' ELSE report_join=NULL;',extra+' ELSE report_join=NULL;',1)


old_rows_function=rows.SQL.split('CREATE TRIGGER',1)[0]
new_rows_function=old_rows_function.replace('CREATE FUNCTION','CREATE OR REPLACE FUNCTION',1).replace(
    ' IF NOT touches THEN RETURN NULL; END IF;',
    """ IF TG_OP='UPDATE' AND NOT touches THEN
  EXECUTE 'SELECT EXISTS(SELECT 1 FROM old_rows N JOIN mta.fresh_mta_calculationrun R ON '||join_sql||
   ' WHERE R.production_manifest->>''version''=''3'' AND ('||filter_sql||'))' INTO touches;
 END IF;
 IF NOT touches THEN RETURN NULL; END IF;""",1)
FORWARD='CREATE OR REPLACE FUNCTION mta.ingestion_watch() RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,mta AS $$'+current_body()+'$$;'+new_rows_function
REVERSE=revision.FORWARD+old_rows_function.replace('CREATE FUNCTION','CREATE OR REPLACE FUNCTION',1)


class Migration(migrations.Migration):
    dependencies=[('fresh_mta','0158_derived_report_row_guards')]
    operations=[migrations.RunSQL(FORWARD,REVERSE)]
