"""Stage-owned commands reuse the ordinary immutable typed action writer."""
from importlib import import_module
from django.db import migrations, models
import django.db.models.deletion

_accepted=import_module('mta.runtime.migrations.0169_accepted_state_ownership')
_cuts=import_module('mta.runtime.migrations.0182_scoped_revision_ownership')
_attempts=import_module('mta.runtime.migrations.0184_invalidated_scope_counter_freeze')
_final=import_module('mta.runtime.migrations.0188_day_final_ownership')

SQL=r'''
CREATE FUNCTION mta.scope_action_revision(target uuid) RETURNS bigint
 LANGUAGE sql STABLE SET search_path=pg_catalog,mta AS $body$
 SELECT coalesce(max(id),0) FROM mta.fresh_mta_runcommand
 WHERE run_id=target AND phase_acceptance_id IS NOT NULL AND state_sealed
$body$;
CREATE FUNCTION mta.actionable_scope_phase(target uuid, accepted uuid) RETURNS boolean
 LANGUAGE sql STABLE SET search_path=pg_catalog,mta AS $body$
 SELECT EXISTS(SELECT 1 FROM mta.fresh_mta_runphaseacceptance P
 JOIN mta.fresh_mta_calculationrun R ON R.id=P.run_id
 JOIN mta.fresh_mta_runscopeattempt A ON A.id=P.attempt_id
 JOIN mta.fresh_mta_mdmdailyinputcapture C ON C.run_id=R.id
 CROSS JOIN LATERAL mta.scope_head(R.id) H
 WHERE R.id=target AND P.id=accepted AND P.state_sealed AND R.status='RUNNING'
  AND R.kind='DAILY_CHAIN' AND R.output_digest='' AND C.status='CAPTURED'
  AND P.source_id=C.source_id AND P.capture_digest=C.revision_digest
  AND P.input_digest=R.input_digest AND A.input_manifest_digest=R.input_manifest_digest
  AND A.status='RELEASED' AND A.run_id=R.id
  AND ((P.phase='BPR' AND A.scope='UptoBPR') OR (P.phase='DBM' AND A.scope='UptoDBM'))
  AND (H.phase,H.digest)=(P.phase,P.digest)
  AND NOT EXISTS(SELECT 1 FROM mta.fresh_mta_runscopeattempt N WHERE N.run_id=R.id
   AND ((N.created_at,N.id)>(A.created_at,A.id) OR N.status='ACTIVE')))
$body$;
CREATE FUNCTION mta.pending_scope_action(target uuid, image text, physical text) RETURNS boolean
 LANGUAGE sql STABLE SET search_path=pg_catalog,mta AS $body$
 SELECT EXISTS(SELECT 1 FROM mta.fresh_mta_runcommand C
 WHERE C.run_id=target AND NOT C.state_sealed AND C.state_manifest='{}'::jsonb
  AND mta.actionable_scope_phase(target,C.phase_acceptance_id)
  AND image='action/'||C.id::text||'/'||CASE physical
   WHEN 'dbm_normacceptancetbl' THEN 'NormAcceptanceTbl'
   WHEN 'dbm_normsinsleepmodetbl' THEN 'NormsInSleepModeTbl'
   WHEN 'dbm_suggestions' THEN 'Suggestions' END
  AND (physical='dbm_normacceptancetbl' AND C.payload->>'operation' IN ('APPLY','SLEEP')
   OR physical IN ('dbm_normsinsleepmodetbl','dbm_suggestions') AND C.payload->>'operation'='SLEEP'))
$body$;
'''

COMMAND_BODY=_accepted.COMMAND_BODY.replace(
 "(to_jsonb(OLD)-'state_manifest') IS DISTINCT FROM (to_jsonb(NEW)-'state_manifest')",
 "(to_jsonb(OLD)-ARRAY['state_manifest','scope_revision_after']) IS DISTINCT FROM "
 "(to_jsonb(NEW)-ARRAY['state_manifest','scope_revision_after'])")
_start=COMMAND_BODY.index(' IF NOT FOUND OR parent.kind')
_stop=COMMAND_BODY.index(" operation=NEW.payload",_start)
COMMAND_BODY=COMMAND_BODY[:_start]+r'''
 IF NOT FOUND OR parent.kind<>'DAILY_CHAIN' THEN RAISE EXCEPTION 'Command parent absent'; END IF;
 IF NEW.phase_acceptance_id IS NULL THEN
  IF parent.status<>'SUCCEEDED' OR NEW.scope_parent_revision<>0
    OR NEW.scope_revision_before IS NOT NULL OR NEW.scope_revision_after IS NOT NULL
    OR EXISTS(SELECT 1 FROM mta.fresh_mta_calculationrun
     WHERE predecessor_id=NEW.run_id AND status IN ('RUNNING','SUCCEEDED')) THEN
   RAISE EXCEPTION 'Command requires an eligible completed parent'; END IF;
 ELSE
  IF NOT mta.actionable_scope_phase(NEW.run_id,NEW.phase_acceptance_id)
    OR coalesce(NEW.payload->>'operation','') NOT IN ('APPLY','SLEEP')
    OR NEW.digest !~ '^[0-9a-f]{64}$' OR NEW.before_digest !~ '^[0-9a-f]{64}$'
    OR NEW.after_digest !~ '^[0-9a-f]{64}$'
    OR (TG_OP='INSERT' AND NEW.scope_parent_revision<>mta.scope_action_revision(NEW.run_id)) THEN
   RAISE EXCEPTION 'Scoped action requires its exact released stage/action head'; END IF;
  IF mta.scope_native_cut(NEW.run_id) IS NULL THEN
   IF NEW.scope_revision_before IS NOT NULL OR NEW.scope_revision_after IS NOT NULL THEN
    RAISE EXCEPTION 'Uncertified action cannot invent native cuts'; END IF;
  ELSIF NOT coalesce(mta.valid_scope_cut(NEW.scope_revision_before),false) THEN
   RAISE EXCEPTION 'Scoped action requires exact integer revision cuts';
  ELSIF TG_OP='INSERT' THEN
   IF NEW.scope_revision_before IS DISTINCT FROM mta.scope_expected_cut(NEW.run_id)
     OR NEW.scope_revision_before IS DISTINCT FROM mta.scope_native_cut(NEW.run_id)
     OR NEW.scope_revision_after IS NOT NULL THEN
    RAISE EXCEPTION 'Scoped action native revision changed'; END IF;
  ELSIF NOT coalesce(mta.valid_scope_cut(NEW.scope_revision_after),false)
    OR NEW.scope_revision_after IS DISTINCT FROM mta.scope_cut_next(mta.scope_native_cut(NEW.run_id)) THEN
   RAISE EXCEPTION 'Scoped action must seal its exact owned native cut'; END IF;
 END IF;
''' + COMMAND_BODY[_stop:]
SQL+='CREATE OR REPLACE FUNCTION mta.guard_command_seal() RETURNS trigger LANGUAGE plpgsql '
SQL+='SET search_path=pg_catalog,mta AS $guard$'+COMMAND_BODY+'$guard$;\n'

_expected=_cuts.SQL.split('CREATE FUNCTION mta.scope_expected_cut(target uuid)',1)[1].split('$body$;',1)[0]
_anchor="    WHERE P.run_id=target AND P.state_sealed LOOP"
assert _expected.count(_anchor)==1
_expected=_expected.replace(_anchor,"""    WHERE P.run_id=target AND P.state_sealed
  UNION ALL SELECT C.scope_revision_after FROM mta.fresh_mta_runcommand C
    WHERE C.run_id=target AND C.phase_acceptance_id IS NOT NULL AND C.state_sealed LOOP""")
SQL+='CREATE OR REPLACE FUNCTION mta.scope_expected_cut(target uuid)'+_expected+'$body$;\n'
_attempt=_attempts._body.replace('OR NEW.action_revision<>0',
    'OR NEW.action_revision<>mta.scope_action_revision(NEW.run_id)')
assert _attempt!=_attempts._body
SQL+='CREATE OR REPLACE FUNCTION mta.guard_scope_attempt()'+_attempt+'$guard$;\n'
_rows=_final._rows.replace('AND NOT mta.pending_day_final(item.owner) THEN',
    "AND NOT mta.pending_day_final(item.owner)\n"
    "       AND NOT (TG_OP='INSERT' AND mta.pending_scope_action(item.owner,item.image,TG_TABLE_NAME)) THEN")
assert _rows!=_final._rows
SQL+=_rows
for fn in ('scope_action_revision(uuid)','actionable_scope_phase(uuid,uuid)',
           'pending_scope_action(uuid,text,text)'):
    SQL+='REVOKE ALL ON FUNCTION mta.'+fn+' FROM PUBLIC;\n'

REVERSE=r'''DO $pre$ BEGIN
 IF EXISTS(SELECT 1 FROM mta.fresh_mta_runcommand WHERE phase_acceptance_id IS NOT NULL) THEN
  RAISE EXCEPTION 'Scoped actions require a compatible forward release'; END IF;
END $pre$;
'''
REVERSE+=('CREATE OR REPLACE FUNCTION mta.guard_command_seal() RETURNS trigger LANGUAGE plpgsql '
    'SET search_path=pg_catalog,mta AS $guard$'+_accepted.COMMAND_BODY+'$guard$;\n')
REVERSE+='CREATE OR REPLACE FUNCTION mta.guard_scope_attempt()'+_attempts._body+'$guard$;\n'
REVERSE+='CREATE OR REPLACE FUNCTION mta.scope_expected_cut(target uuid)'+_cuts.SQL.split(
    'CREATE FUNCTION mta.scope_expected_cut(target uuid)',1)[1].split('$body$;',1)[0]+'$body$;\n'
REVERSE+=_final._rows
for fn in ('pending_scope_action(uuid,text,text)','actionable_scope_phase(uuid,uuid)','scope_action_revision(uuid)'):
    REVERSE+='DROP FUNCTION mta.'+fn+';\n'


class Migration(migrations.Migration):
    dependencies=[('fresh_mta','0190_day_final_current_copies')]
    operations=[
        migrations.AddField(model_name='runcommand',name='phase_acceptance',field=models.ForeignKey(
            null=True,blank=True,on_delete=django.db.models.deletion.PROTECT,
            related_name='actions',to='fresh_mta.runphaseacceptance')),
        migrations.AddField(model_name='runcommand',name='scope_parent_revision',
            field=models.PositiveBigIntegerField(default=0,db_default=0)),
        migrations.AddField(model_name='runcommand',name='scope_revision_before',field=models.JSONField(null=True)),
        migrations.AddField(model_name='runcommand',name='scope_revision_after',field=models.JSONField(null=True)),
        migrations.RunSQL(SQL,REVERSE),
    ]
