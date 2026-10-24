"""Prepared live-out sourcing and snapshot ownership before any BPR work."""
from importlib import import_module
from django.db import migrations

_initial = import_module('mta.runtime.migrations.0172_phase_snapshot_rows').SQL
_snapshot = _initial.split('CREATE FUNCTION mta.guard_phase_snapshot()', 1)[1].split('$guard$;', 1)[0]
_rows = import_module('mta.runtime.migrations.0173_phase_guard_variable').FORWARD
_prepared_snapshot = _snapshot.replace("NEW.phase NOT IN ('BPR','DBM')",
    "NEW.phase NOT IN ('PRE_BPR','BPR','DBM')").replace(
    "IF NEW.phase='BPR' AND NEW.parent_id IS NOT NULL THEN\n  RAISE EXCEPTION 'BPR snapshot has no earlier calculation snapshot'; END IF;",
    """IF NEW.phase='PRE_BPR' AND NEW.parent_id IS NOT NULL THEN
  RAISE EXCEPTION 'Prepared snapshot has no earlier calculation snapshot'; END IF;
 IF NEW.phase='BPR' AND NEW.parent_id IS NOT NULL THEN
  SELECT * INTO predecessor FROM mta.fresh_mta_dailyphasesnapshot WHERE id=NEW.parent_id;
  IF NOT FOUND OR predecessor.run_id<>NEW.run_id OR predecessor.phase<>'PRE_BPR'
   OR predecessor.input_digest<>NEW.input_digest OR predecessor.recipe_digest<>NEW.recipe_digest THEN
   RAISE EXCEPTION 'BPR snapshot requires its own prepared parent'; END IF;
 END IF;""")
_prepared_rows = _rows.replace("'^phase/(BPR|DBM)/.+$'", "'^phase/(PRE_BPR|BPR|DBM)/.+$'").replace(
    "('phase_pickband','phase_advancestock')", "('phase_pickband','phase_advancestock','phase_sourcing')")
FORWARD = r'''
CREATE TABLE mta_state.phase_sourcing (
 vf_run_id uuid NOT NULL REFERENCES mta.fresh_mta_calculationrun(id) ON DELETE RESTRICT,
 vf_image text NOT NULL, vf_ordinal bigint NOT NULL,
 sku_code text, location_code text, supplier text, sob text, moq numeric, pack_size numeric,
 PRIMARY KEY(vf_run_id,vf_image,vf_ordinal));
'''
FORWARD += 'CREATE OR REPLACE FUNCTION mta.guard_phase_snapshot()'+_prepared_snapshot+'$guard$;\n'+_prepared_rows
for operation, references in (('INSERT', 'NEW TABLE AS new_rows'),
        ('UPDATE', 'OLD TABLE AS old_rows NEW TABLE AS new_rows'),
        ('DELETE', 'OLD TABLE AS old_rows')):
    FORWARD += ('CREATE TRIGGER phase_rows_'+operation.lower()+' AFTER '+operation+
        ' ON mta_state.phase_sourcing REFERENCING '+references+
        ' FOR EACH STATEMENT EXECUTE FUNCTION mta.guard_phase_rows();\n')
for operation, references in (('INSERT', 'NEW TABLE AS new_rows'),
        ('UPDATE', 'OLD TABLE AS old_rows NEW TABLE AS new_rows'),
        ('DELETE', 'OLD TABLE AS old_rows'), ('TRUNCATE', '')):
    FORWARD += ('CREATE TRIGGER ingestion_watch_'+operation.lower()+' AFTER '+operation+
        ' ON mta_state.phase_sourcing'+(' REFERENCING '+references if references else '')+
        " FOR EACH STATEMENT EXECUTE FUNCTION mta.ingestion_watch('operational');\n")
FORWARD += ('CREATE TRIGGER phase_no_truncate BEFORE TRUNCATE ON mta_state.phase_sourcing '
            'FOR EACH STATEMENT EXECUTE FUNCTION mta.deny_phase_truncate();\n')
REVERSE = """DO $pre$ BEGIN
 IF EXISTS(SELECT 1 FROM mta.fresh_mta_dailyphasesnapshot WHERE phase='PRE_BPR') THEN
 RAISE EXCEPTION 'Prepared snapshots require a compatible forward release'; END IF;
END $pre$;
DROP TABLE mta_state.phase_sourcing;
"""+'CREATE OR REPLACE FUNCTION mta.guard_phase_snapshot()'+_snapshot+'$guard$;\n'+_rows


class Migration(migrations.Migration):
    dependencies = [('fresh_mta', '0174_prepared_phase_snapshot')]
    operations = [migrations.RunSQL(FORWARD, REVERSE)]
