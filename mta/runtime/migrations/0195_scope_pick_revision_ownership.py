from importlib import import_module
from django.db import migrations


OLD=import_module('mta.runtime.migrations.0168_report_guard_owner_sets').NEW_INGESTION
ADDED=r'''
 IF TG_TABLE_SCHEMA='mta' AND TG_TABLE_NAME='fresh_mta_scopepickfiles' AND TG_OP='INSERT' THEN
  IF NOT EXISTS(SELECT 1 FROM new_rows N
    LEFT JOIN mta.fresh_mta_runphaseacceptance P ON P.id=N.phase_id
    LEFT JOIN mta.fresh_mta_calculationrun R ON R.id=P.run_id
    LEFT JOIN mta.fresh_mta_mdmdailyinputcapture C ON C.run_id=R.id
    LEFT JOIN mta.fresh_mta_dailyphasesnapshot S ON S.id=P.snapshot_id
    WHERE P.id IS NULL OR P.phase IS DISTINCT FROM 'BPR' OR NOT P.state_sealed
      OR N.source_digest IS DISTINCT FROM P.digest OR R.kind IS DISTINCT FROM 'DAILY_CHAIN'
      OR R.status NOT IN ('RUNNING','SUCCEEDED') OR C.id IS NULL
      OR P.source_id IS DISTINCT FROM C.source_id OR P.input_digest IS DISTINCT FROM R.input_digest
      OR P.capture_digest IS DISTINCT FROM C.revision_digest OR C.status NOT IN ('CAPTURED','CONSUMED')
      OR S.acceptance_id IS DISTINCT FROM P.id OR S.run_id IS DISTINCT FROM R.id
      OR S.phase IS DISTINCT FROM 'BPR') THEN RETURN NULL; END IF;
 END IF;
'''
assert OLD.count(" IF kind='immutable' THEN")==1
NEW=OLD.replace(" IF kind='immutable' THEN",ADDED+" IF kind='immutable' THEN",1)


def transition(before,after):
    return ("DO $pre$ BEGIN IF NOT EXISTS(SELECT 1 FROM pg_proc P JOIN pg_namespace N ON N.oid=P.pronamespace "
        "WHERE N.nspname='mta' AND P.proname='ingestion_watch' AND P.pronargs=0 "
        "AND P.prosrc=$scope_pick_prior$"+before+"$scope_pick_prior$ AND P.prosecdef "
        "AND P.proconfig=ARRAY['search_path=pg_catalog, mta']::text[]) THEN "
        "RAISE EXCEPTION 'Exact predecessor ingestion guard required'; END IF; END $pre$;\n"
        'CREATE OR REPLACE FUNCTION mta.ingestion_watch() RETURNS trigger LANGUAGE plpgsql '
        'SECURITY DEFINER SET search_path=pg_catalog,mta AS $scope_pick_new$'+after+'$scope_pick_new$;\n')


FORWARD=transition(OLD,NEW)
REVERSE="""DO $pre$ BEGIN
 IF EXISTS(SELECT 1 FROM mta.fresh_mta_scopepickfiles) THEN
  RAISE EXCEPTION 'Accepted Pick file receipts require a compatible forward release'; END IF;
END $pre$;
"""
for operation,reference in (
        ('INSERT','NEW TABLE AS new_rows'),('UPDATE','OLD TABLE AS old_rows NEW TABLE AS new_rows'),
        ('DELETE','OLD TABLE AS old_rows'),('TRUNCATE','')):
    name='ingestion_watch_'+operation.lower()
    FORWARD+='CREATE TRIGGER '+name+' AFTER '+operation+' ON mta.fresh_mta_scopepickfiles '
    if reference:FORWARD+='REFERENCING '+reference+' '
    FORWARD+="FOR EACH STATEMENT EXECUTE FUNCTION mta.ingestion_watch('operational');\n"
    REVERSE+='DROP TRIGGER '+name+' ON mta.fresh_mta_scopepickfiles;\n'
REVERSE+=transition(NEW,OLD)


class Migration(migrations.Migration):

    dependencies = [
        ('fresh_mta', '0194_scope_pick_file_truncate'),
    ]

    operations = [
        migrations.RunSQL(FORWARD,REVERSE),
    ]
