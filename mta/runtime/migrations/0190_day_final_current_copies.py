"""Final publication may write only the remaining BTR master copies."""
from importlib import import_module
from django.db import migrations

_prior=import_module('mta.runtime.migrations.0186_scoped_current_copies')
_pending=_prior.SQL.split('CREATE FUNCTION mta.pending_scoped_current(owner bigint)',1)[1].split('$body$;',1)[0]
_pending=_pending.replace(' SELECT P.phase FROM',""" SELECT CASE WHEN EXISTS(
  SELECT 1 FROM mta.fresh_mta_mdmdailyinputcapture C
  JOIN mta.fresh_mta_calculationrun R ON R.id=C.run_id
  WHERE C.source_id=owner AND C.status='CONSUMED' AND R.status='RUNNING'
   AND R.id::text=current_setting('fresh.mdm_current_run',true)
   AND mta.pending_day_final(R.id)) THEN 'DAY_FINAL' ELSE (
 SELECT P.phase FROM""")+') END\n'
_guard=_prior.SQL.split('CREATE FUNCTION mta.guard_scoped_current_copy()',1)[1].split('$guard$;',1)[0]
_guard=_guard.replace("WHEN 'PRE_BPR' THEN 'Importer' ELSE accepted_phase",
    "WHEN 'PRE_BPR' THEN 'Importer' WHEN 'DAY_FINAL' THEN 'BTR' ELSE accepted_phase")
_guard=_guard.replace("accepted_phase IN ('BPR','DBM')", "accepted_phase IN ('BPR','DBM','DAY_FINAL')")
SQL=('CREATE OR REPLACE FUNCTION mta.pending_scoped_current(owner bigint)'+_pending+'$body$;\n'
     +'CREATE OR REPLACE FUNCTION mta.guard_scoped_current_copy()'+_guard+'$guard$;')
REVERSE="""DO $pre$ BEGIN
 IF EXISTS(SELECT 1 FROM mta.fresh_mta_runphaseacceptance WHERE phase='DAY_FINAL') THEN
 RAISE EXCEPTION 'Final current copies require a compatible forward release'; END IF;
END $pre$;
"""+('CREATE OR REPLACE FUNCTION mta.pending_scoped_current(owner bigint)'
    +_prior.SQL.split('CREATE FUNCTION mta.pending_scoped_current(owner bigint)',1)[1].split('$body$;',1)[0]+'$body$;\n'
    +'CREATE OR REPLACE FUNCTION mta.guard_scoped_current_copy()'
    +_prior.SQL.split('CREATE FUNCTION mta.guard_scoped_current_copy()',1)[1].split('$guard$;',1)[0]+'$guard$;')


class Migration(migrations.Migration):
    dependencies=[('fresh_mta','0189_day_final_capture_header')]
    operations=[migrations.RunSQL(SQL,REVERSE)]
