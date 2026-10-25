"""Permit BPR-owned read dependencies for the explicit fresh UptoDBM request.

The reference still belongs to BPR; DBM admission must bind its separate receipt.
No accepted rows are changed or reinterpreted as terminal output.
"""
from importlib import import_module
from django.db import migrations

previous = import_module('mta.runtime.migrations.0219_scope_read_test_database_casefold')
OLD = previous.BODY
OLD_PREDICATE = """  OR NOT EXISTS(SELECT 1 FROM jsonb_array_elements(request_node->'object')
    WHERE value->>0='schema' AND value->1->>'scalar'='fresh-native-scope-request-v2')
  OR NOT EXISTS(SELECT 1 FROM jsonb_array_elements(request_node->'object')
    WHERE value->>0='scope' AND value->1->>'scalar'='UptoBPR')"""
PREDICATE = """  OR NOT EXISTS(SELECT 1 FROM (
    SELECT max(value->1->>'scalar') FILTER(WHERE value->>0='schema') AS schema,
           max(value->1->>'scalar') FILTER(WHERE value->>0='scope') AS scope
    FROM jsonb_array_elements(request_node->'object')) Q
    WHERE (Q.schema,Q.scope) IN (('fresh-native-scope-request-v2','UptoBPR'),
      ('fresh-native-upto-dbm-request-v1','UptoDBM')))"""
assert OLD.count(OLD_PREDICATE) == 1
BODY = OLD.replace(OLD_PREDICATE,PREDICATE)


def replace(old, new):
    return """LOCK TABLE mta.fresh_mta_scopereadreference IN ACCESS EXCLUSIVE MODE;
DO $pre$ BEGIN
 IF NOT EXISTS(SELECT 1 FROM pg_proc P JOIN pg_language L ON L.oid=P.prolang
  WHERE P.oid=to_regprocedure('mta.guard_scope_read_reference()')
   AND P.prosrc=$expected$"""+old+"""$expected$ AND NOT P.prosecdef
   AND P.proconfig=ARRAY['search_path=pg_catalog, mta'] AND L.lanname='plpgsql'
   AND P.prorettype='trigger'::regtype
   AND P.proowner=(SELECT relowner FROM pg_class WHERE oid='mta.fresh_mta_scopereadreference'::regclass))
 THEN RAISE EXCEPTION 'Exact scope read configuration guard required'; END IF;
END $pre$;
CREATE OR REPLACE FUNCTION mta.guard_scope_read_reference() RETURNS trigger LANGUAGE plpgsql
 SET search_path=pg_catalog,mta AS $guard$"""+new+'$guard$;\n'


class Migration(migrations.Migration):
    dependencies = [('fresh_mta','0223_bpr_history_completion')]
    operations = [migrations.RunSQL(replace(OLD,BODY))]
