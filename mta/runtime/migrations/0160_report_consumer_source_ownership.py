"""BOR consumer snapshots are rebuildable from committed typed source facts.

Operational BOR/RRR histories and live user remarks retain their original owner.
DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
from importlib import import_module
from django.db import migrations

prior=import_module('mta.runtime.migrations.0159_report_reference_ownership')
CONSUMER_SOURCES=('fresh_mta_borsourcerow','fresh_mta_borsobrow',
    'fresh_mta_bormoqrow','fresh_mta_borinitialremark','fresh_mta_borsourcereceipt',
    'fresh_mta_boroasourcerow','fresh_mta_boroarequirement',
    'fresh_mta_boroainitialremark','fresh_mta_boroasourcereceipt')


def current_body():
    extra="WHEN TG_TABLE_SCHEMA='mta' AND TG_TABLE_NAME=ANY(ARRAY["+','.join("'"+table+"'" for table in CONSUMER_SOURCES)+"] ) THEN report_join='LEFT JOIN mta.fresh_mta_calculationrun R ON R.id=N.run_id'; report_filter='TRUE';\n"
    return prior.current_body().replace(' ELSE report_join=NULL;',extra+' ELSE report_join=NULL;',1)


def function(body):
    return 'CREATE OR REPLACE FUNCTION mta.ingestion_watch() RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,mta AS $$'+body+'$$;'


class Migration(migrations.Migration):
    dependencies=[('fresh_mta','0159_report_reference_ownership')]
    operations=[migrations.RunSQL(function(current_body()),function(prior.current_body()))]
