"""Separate guarded BPR consumer statements from frozen scoped calculations.

Full still observes the original five aggregate counters. Existing captures have
no inferred baseline and keep their original strict comparison.
"""
from importlib import import_module
from django.db import migrations

OLD=import_module('mta.runtime.migrations.0202_scope_planning_guards').NEW
NEW=OLD.replace('static_change boolean:=true;',
    'static_change boolean:=true; bpr_action boolean:=false; bpr_operational boolean:=false;')
assert NEW!=OLD
anchor=" IF kind='immutable' THEN"
assert NEW.count(anchor)==1
NEW=NEW.replace(anchor,r'''
 IF TG_TABLE_SCHEMA='mta' AND TG_TABLE_NAME='fresh_mta_bprliveremark'
    AND TG_OP='INSERT' AND kind='action' THEN
  SELECT NOT EXISTS(SELECT 1 FROM new_rows N WHERE
    N.owner_id IS DISTINCT FROM 'BPRReport_RemarkDetails'
    OR N.actor_id IS DISTINCT FROM current_setting('fresh.daily_remark_actor',true)) INTO bpr_action;
 ELSIF TG_TABLE_SCHEMA='mta' AND TG_TABLE_NAME='fresh_mta_remarkowner'
    AND TG_OP='UPDATE' AND kind='operational' THEN
  SELECT NOT EXISTS(SELECT 1 FROM new_rows N FULL JOIN old_rows O USING(family) WHERE
    N.family IS DISTINCT FROM 'BPRReport_RemarkDetails'
    OR O.family IS DISTINCT FROM N.family OR N.next_ordinal<=O.next_ordinal
    OR (to_jsonb(N)-'next_ordinal') IS DISTINCT FROM (to_jsonb(O)-'next_ordinal')) INTO bpr_operational;
 END IF;
'''+anchor,1)
for kind in ('action','operational'):
    before=kind+'_epoch='+kind+'_epoch+1 WHERE initialization_id IN'
    after=(kind+'_epoch='+kind+'_epoch+1, bpr_remark_'+kind+'_epoch=bpr_remark_'+kind+
        '_epoch+CASE WHEN bpr_'+kind+' THEN 1 ELSE 0 END WHERE initialization_id IN')
    assert NEW.count(before)==1
    NEW=NEW.replace(before,after,1)

# The immutable predecessor stores this SQL constant inside its installer.
_authority=import_module('mta.runtime.migrations.0146_ingestion_revision_state')
_sql=next(value for value in _authority.guards.__code__.co_consts
    if isinstance(value,str) and 'CREATE OR REPLACE FUNCTION mta.ingestion_authority_guard()' in value)
OLD_AUTHORITY=_sql.split('AS $$',1)[1].split('$$;',1)[0]
NEW_AUTHORITY=OLD_AUTHORITY.replace('OR NEW.operational_epoch<OLD.operational_epoch OR NEW.action_epoch<OLD.action_epoch',
    '''OR NEW.operational_epoch<OLD.operational_epoch OR NEW.action_epoch<OLD.action_epoch
    OR NEW.bpr_remark_operational_epoch<OLD.bpr_remark_operational_epoch
    OR NEW.bpr_remark_action_epoch<OLD.bpr_remark_action_epoch''')
assert NEW_AUTHORITY!=OLD_AUTHORITY

NORMALIZE=r'''
DECLARE binding jsonb; policy jsonb; current_op bigint; current_action bigint;
 baseline_op bigint; baseline_action bigint; item text; keys text[]; complete boolean;
BEGIN
 SELECT R.production_manifest->'ingestion_preparation' INTO binding
  FROM mta.fresh_mta_calculationrun R WHERE R.id=target;
 IF NOT binding ? 'bpr_consumer_cut' THEN RETURN observed; END IF;
 policy=binding->'bpr_consumer_cut';
 IF jsonb_typeof(policy) IS DISTINCT FROM 'object' THEN
  RAISE EXCEPTION 'Scoped BPR consumer baseline is invalid'; END IF;
 SELECT array_agg(key ORDER BY key) INTO keys FROM jsonb_object_keys(policy) key;
 IF keys IS DISTINCT FROM ARRAY['action','capture_id','operational','provenance_digest','schema','watermark']::text[]
  OR policy->>'schema' IS DISTINCT FROM 'fresh-scoped-bpr-consumer-cut-v1'
  OR jsonb_typeof(policy->'provenance_digest') IS DISTINCT FROM 'string'
  OR (policy->>'provenance_digest') !~ '^[0-9a-f]{64}$' THEN
  RAISE EXCEPTION 'Scoped BPR consumer baseline is invalid'; END IF;
 FOREACH item IN ARRAY ARRAY['action','capture_id','operational','watermark'] LOOP
  IF jsonb_typeof(policy->item) IS DISTINCT FROM 'number' OR (policy->>item) !~ '^[0-9]+$' THEN
   RAISE EXCEPTION 'Scoped BPR consumer baseline requires bounded integer counters'; END IF;
  IF (policy->>item)::numeric>9223372036854775807 THEN
   RAISE EXCEPTION 'Scoped BPR consumer baseline requires bounded integer counters'; END IF;
 END LOOP;
 IF NOT coalesce(mta.valid_scope_cut(observed),false) THEN
  RAISE EXCEPTION 'Scoped observed revision cut is invalid'; END IF;
 baseline_op=(policy->>'operational')::bigint; baseline_action=(policy->>'action')::bigint;
 SELECT S.bpr_remark_operational_epoch,S.bpr_remark_action_epoch INTO current_op,current_action
  FROM mta.fresh_mta_ingestionrevisionstate S
  WHERE S.initialization_id::text=binding->>'initialization_id';
 IF current_op IS NULL OR baseline_op>current_op OR baseline_action>current_action
  OR current_op-baseline_op>(observed->>3)::bigint
  OR current_action-baseline_action>(observed->>4)::bigint THEN
  RAISE EXCEPTION 'Scoped BPR consumer counters regressed or exceed their aggregate'; END IF;
 SELECT EXISTS(SELECT 1 FROM mta.fresh_mta_remarkcapture C
  JOIN mta.fresh_mta_remarkowner O ON O.family=C.family
  WHERE C.id=(policy->>'capture_id')::bigint AND C.run_id=target
   AND C.family='BPRReport_RemarkDetails'
   AND C.provenance_digest=policy->>'provenance_digest' AND O.provenance_digest=C.provenance_digest
   AND C.watermark=(policy->>'watermark')::bigint AND O.next_ordinal>=C.watermark
   AND O.next_ordinal=(SELECT coalesce(max(L.ordinal)+1,0) FROM mta.fresh_mta_bprliveremark L
       WHERE L.owner_id=O.family)) INTO complete;
 IF NOT complete THEN RAISE EXCEPTION 'Scoped BPR consumer owner or complete journal prefix differs'; END IF;
 RETURN jsonb_set(jsonb_set(observed,'{3}',to_jsonb((observed->>3)::bigint-(current_op-baseline_op))),
  '{4}',to_jsonb((observed->>4)::bigint-(current_action-baseline_action)));
END
'''

_cuts=import_module('mta.runtime.migrations.0182_scoped_revision_ownership')
_retained=import_module('mta.runtime.migrations.0183_retained_scope_failure_cut')
OLD_NATIVE=_cuts.SQL.split('CREATE FUNCTION mta.scope_native_cut(target uuid)',1)[1].split('$body$;',1)[0]
OLD_RETAINED=_retained._retained
NEW_NATIVE=OLD_NATIVE.replace('RETURN observed;', 'RETURN mta.scope_bpr_consumer_cut(target,observed);')
NEW_RETAINED=OLD_RETAINED.replace('RETURN observed;', 'RETURN mta.scope_bpr_consumer_cut(target,observed);')
assert NEW_NATIVE!=OLD_NATIVE and NEW_RETAINED!=OLD_RETAINED


def exact(function,body,*,definer=False,configuration="ARRAY['search_path=pg_catalog, mta']::text[]"):
    return ("DO $pre$ BEGIN IF NOT EXISTS(SELECT 1 FROM pg_proc P WHERE P.oid='mta."+function+
        "'::regprocedure AND P.prosrc=$prior$"+body+"$prior$ AND P.prosecdef="+
        ('true' if definer else 'false')+' AND P.proconfig IS NOT DISTINCT FROM '+configuration+
        ") THEN RAISE EXCEPTION 'Exact predecessor function required: "+function+"'; END IF; END $pre$;\n")


transition=import_module('mta.runtime.migrations.0195_scope_pick_revision_ownership').transition
SQL=transition(OLD,NEW)
SQL+=exact('ingestion_authority_guard()',OLD_AUTHORITY)
SQL+=('CREATE OR REPLACE FUNCTION mta.ingestion_authority_guard() RETURNS trigger LANGUAGE plpgsql '
    'SET search_path=pg_catalog,mta AS $body$'+NEW_AUTHORITY+'$body$;\n')
SQL+=('CREATE FUNCTION mta.scope_bpr_consumer_cut(target uuid,observed jsonb) RETURNS jsonb LANGUAGE plpgsql '
    'SET search_path=pg_catalog,mta AS $body$'+NORMALIZE+'$body$;\n'
    'REVOKE ALL ON FUNCTION mta.scope_bpr_consumer_cut(uuid,jsonb) FROM PUBLIC;\n')
for function,before,after in (('scope_native_cut(uuid)',OLD_NATIVE,NEW_NATIVE),
        ('scope_retained_cut(uuid)',OLD_RETAINED,NEW_RETAINED)):
    SQL+=exact(function,before.split('AS $body$',1)[1])
    SQL+='CREATE OR REPLACE FUNCTION mta.'+function.split('(')[0]+'(target uuid)'+after+'$body$;\n'

REVERSE="""DO $pre$ BEGIN
 IF EXISTS(SELECT 1 FROM mta.fresh_mta_calculationrun
  WHERE production_manifest->'ingestion_preparation' ? 'bpr_consumer_cut') THEN
 RAISE EXCEPTION 'Scoped consumer baselines require a compatible forward release'; END IF;
END $pre$;
"""
for function,before,after in (('scope_native_cut(uuid)',OLD_NATIVE,NEW_NATIVE),
        ('scope_retained_cut(uuid)',OLD_RETAINED,NEW_RETAINED)):
    REVERSE+=exact(function,after.split('AS $body$',1)[1])
    REVERSE+='CREATE OR REPLACE FUNCTION mta.'+function.split('(')[0]+'(target uuid)'+before+'$body$;\n'
REVERSE+='DROP FUNCTION mta.scope_bpr_consumer_cut(uuid,jsonb);\n'
REVERSE+=exact('ingestion_authority_guard()',NEW_AUTHORITY)
REVERSE+=('CREATE OR REPLACE FUNCTION mta.ingestion_authority_guard() RETURNS trigger LANGUAGE plpgsql '
    'SET search_path=pg_catalog,mta AS $body$'+OLD_AUTHORITY+'$body$;\n')
REVERSE+=transition(NEW,OLD)


class Migration(migrations.Migration):
    dependencies=[('fresh_mta','0203_bpr_consumer_revision_deltas')]
    operations=[migrations.RunSQL(SQL,REVERSE)]
