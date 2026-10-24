"""Scoped PRE_BPR effects and Importer current partitions share one owner."""
from importlib import import_module
from django.db import migrations

# Frozen participants of daily_input._apply_consumption_effects, including its
# native task-prune roster. Extra permission is never granted by these guards.
SOURCE_TABLES = (
    'mdmskuapproved', 'mdmlocationapproved', 'mdmskulocaddapproved',
    'mdmskulocmodifyapproved', 'mdmskulocremoveapproved',
    'mdmdailyskuarchive', 'mdmdailylocationarchive', 'mdmdailyskulocaddarchive',
    'mdmdailyskulocmodifyarchive', 'mdmdailyskulocremovearchive',
    'mdmsobapproved', 'mdmmoqwithdestinationapproved', 'mdmmoqwithoutdestinationapproved',
    'mdmsobarchive', 'mdmmoqwithdestinationarchive', 'mdmmoqwithoutdestinationarchive',
    'mdmsobraw', 'mdmmoqraw1', 'mdmmoqraw2',
    'mdmforcequeue', 'mdmforceconsumed', 'mdmforceuploadlog', 'mdmforceowner',
    'mdmseasonqueue', 'mdmseasonconsumed', 'mdmseasoncurrent', 'mdmseasonowner',
    'mdmstoppipoqueue', 'mdmstoppipoconsumed', 'mdmstoppipoowner',
    'mdmphaseoutqueue', 'mdmphaseoutconsumed', 'mdmphaseinnormqueue',
    'mdmphaseinnormconsumed', 'mdmphasecontrolsowner',
    'mdmpairexclusionsource', 'mdmpairexclusion', 'mdmtask', 'mdmsubtask',
    'mdmskuhistory', 'mdmskurequested', 'mdmlocationhistory', 'mdmlocationrequested',
    'mdmskulochistory', 'mdmskulocaddrequested', 'mdmskulocmodifyrequested', 'mdmskulocremoverequested',
    'mdmsobhistory', 'mdmsobrequested', 'mdmmoqhistory', 'mdmmoqrequested',
    'mdmforcehistory', 'mdmforcerequested', 'mdmseasonhistory', 'mdmseasonrequested',
    'mdmseasonstatushistory', 'mdmseasonstatusrequested', 'mdmstoppipohistory', 'mdmstoppiporequested',
    'mdmphaseouthistory', 'mdmphaseoutrequested', 'mdmphaseinnormhistory', 'mdmphaseinnormrequested',
)
CAPTURE_TABLES = ('mdmdailyinputoccurrence', 'mdmdailyinputtask', 'mdmdailyinputhistory')
CURRENT_TABLES = import_module('mta.runtime.migrations.0109_active_mdm_current_guards').TABLES

SQL = r'''
CREATE FUNCTION mta.pending_prepared_effects(owner bigint) RETURNS boolean
 LANGUAGE sql STABLE SET search_path=pg_catalog,mta AS $body$
 SELECT EXISTS(SELECT 1 FROM mta.fresh_mta_runphaseacceptance P
 JOIN mta.fresh_mta_runscopeattempt A ON A.id=P.attempt_id
 JOIN mta.fresh_mta_mdmdailyinputcapture C ON C.run_id=P.run_id
 JOIN mta.fresh_mta_calculationrun R ON R.id=P.run_id
 WHERE P.phase='PRE_BPR' AND NOT P.state_sealed AND C.source_id=owner
  AND P.source_id=owner AND A.run_id=R.id AND A.status='ACTIVE'
  AND R.status='RUNNING' AND R.kind='DAILY_CHAIN' AND C.status='CAPTURED'
  AND P.input_digest=R.input_digest AND A.input_digest=R.input_digest
  AND A.input_manifest_digest=R.input_manifest_digest AND P.capture_digest=C.revision_digest
  AND R.id::text=current_setting('fresh.mdm_consuming_run',true)
  AND P.id::text=current_setting('fresh.scope_phase',true)
  AND A.worker_token::text=current_setting('fresh.scope_worker',true))
$body$;
REVOKE ALL ON FUNCTION mta.pending_prepared_effects(bigint) FROM PUBLIC;
CREATE FUNCTION mta.guard_prepared_effect() RETURNS trigger LANGUAGE plpgsql
 SET search_path=pg_catalog,mta AS $guard$
DECLARE consuming_id uuid; owner bigint; row_value jsonb;
BEGIN
 consuming_id=nullif(current_setting('fresh.mdm_consuming_run',true),'')::uuid;
 row_value=CASE WHEN TG_OP='DELETE' THEN to_jsonb(OLD) ELSE to_jsonb(NEW) END;
 IF TG_ARGV[0]='capture' AND EXISTS(SELECT 1 FROM mta.fresh_mta_runscopeattempt A
   WHERE A.run_id=(row_value->>'capture_id')::uuid) AND
   consuming_id IS DISTINCT FROM (row_value->>'capture_id')::uuid THEN
  RAISE EXCEPTION 'Scoped capture effect evidence requires its owned transaction'; END IF;
 IF consuming_id IS NULL OR NOT EXISTS(SELECT 1 FROM mta.fresh_mta_runscopeattempt A WHERE A.run_id=consuming_id) THEN
  IF TG_OP='DELETE' THEN RETURN OLD; ELSE RETURN NEW; END IF;
 END IF;
 IF TG_ARGV[0]='capture' THEN
  SELECT C.source_id INTO STRICT owner FROM mta.fresh_mta_mdmdailyinputcapture C
   WHERE C.run_id=(row_value->>'capture_id')::uuid AND C.run_id=consuming_id;
 ELSE owner=(row_value->>'source_id')::bigint; END IF;
 IF NOT coalesce(mta.pending_prepared_effects(owner),false) THEN
  RAISE EXCEPTION 'Scoped MDM effects require their exact pending PRE_BPR acceptance'; END IF;
 IF TG_OP='UPDATE' AND (to_jsonb(OLD)->'source_id',to_jsonb(OLD)->'capture_id') IS DISTINCT FROM
                      (to_jsonb(NEW)->'source_id',to_jsonb(NEW)->'capture_id') THEN
  RAISE EXCEPTION 'Scoped MDM effects cannot move their source or capture'; END IF;
 IF TG_ARGV[0]='current' AND (
    current_setting('fresh.mdm_current_run',true) IS DISTINCT FROM consuming_id::text
    OR coalesce(row_value->>'owner','Importer')<>'Importer') THEN
  RAISE EXCEPTION 'PRE_BPR can publish only its Importer current partitions'; END IF;
 IF TG_OP='DELETE' THEN RETURN OLD; ELSE RETURN NEW; END IF;
END
$guard$;
REVOKE ALL ON FUNCTION mta.guard_prepared_effect() FROM PUBLIC;
'''

_current_sql = import_module('mta.runtime.migrations.0153_incremental_current_guards').FORWARD
_current = _current_sql.split('CREATE OR REPLACE FUNCTION mta.guard_active_mdm_current()',1)[1].split('END $$;',1)[0]+'END $$;'
_anchor = " IF TG_OP='INSERT' AND current_setting('fresh.mdm_current_bootstrap',true)=owner::text"
assert _current.count(_anchor) == 1
_new_current = _current.replace(_anchor, r'''
 IF coalesce(mta.pending_prepared_effects(owner),false) THEN
  IF current_setting('fresh.mdm_current_run',true) IS DISTINCT FROM current_setting('fresh.mdm_consuming_run',true)
   OR coalesce((CASE WHEN TG_OP='DELETE' THEN to_jsonb(OLD) ELSE to_jsonb(NEW) END)->>'owner','Importer')<>'Importer'
   THEN RAISE EXCEPTION 'Prepared current publication requires its Importer partition'; END IF;
  IF TG_OP='DELETE' THEN RETURN OLD; ELSE RETURN NEW; END IF;
 END IF;
''' + _anchor)
SQL += 'CREATE OR REPLACE FUNCTION mta.guard_active_mdm_current()'+_new_current+'\n'

_projection_sql = import_module('mta.runtime.migrations.0134_native_closing_projection_guards').FORWARD
_projection = _projection_sql.split('CREATE FUNCTION mta.guard_location_projection_statement()',1)[1].split('END $$;',1)[0]+'END $$;'
_anchor = " corrected=EXISTS(SELECT 1 FROM mta.fresh_mta_mdmsourceintegration"
assert _projection.count(_anchor) == 1
_new_projection = _projection.replace(_anchor, r'''
 IF coalesce(mta.pending_prepared_effects(C.source_id),false)
  AND C.run_id::text=current_setting('fresh.mdm_consuming_run',true) THEN RETURN NULL; END IF;
''' + _anchor)
SQL += 'CREATE OR REPLACE FUNCTION mta.guard_location_projection_statement()'+_new_projection+'\n'
for kind, tables in (('source',SOURCE_TABLES),('capture',CAPTURE_TABLES),('current',CURRENT_TABLES)):
    for table in tables:
        SQL += ('CREATE TRIGGER scoped_prepared_effect BEFORE INSERT OR UPDATE OR DELETE '
                'ON mta.fresh_mta_'+table+' FOR EACH ROW EXECUTE FUNCTION '
                "mta.guard_prepared_effect('"+kind+"');\n")

REVERSE = """DO $pre$ BEGIN
 IF EXISTS(SELECT 1 FROM mta.fresh_mta_runscopeattempt) THEN
 RAISE EXCEPTION 'Scoped effects require a compatible forward release'; END IF;
END $pre$;
"""
for table in (*SOURCE_TABLES,*CAPTURE_TABLES,*CURRENT_TABLES):
    REVERSE += 'DROP TRIGGER scoped_prepared_effect ON mta.fresh_mta_'+table+';\n'
REVERSE += ('CREATE OR REPLACE FUNCTION mta.guard_active_mdm_current()'+_current+'\n'
    +'CREATE OR REPLACE FUNCTION mta.guard_location_projection_statement()'+_projection+'\n'
    +'DROP FUNCTION mta.guard_prepared_effect(); DROP FUNCTION mta.pending_prepared_effects(bigint);')


class Migration(migrations.Migration):
    dependencies = [('fresh_mta','0178_scope_fence_null_denial')]
    operations = [migrations.RunSQL(SQL, REVERSE)]
