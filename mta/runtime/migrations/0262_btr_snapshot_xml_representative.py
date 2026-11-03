"""Keep repeated snapshot XML on one immutable ordinal of the same image."""
from importlib import import_module

from django.db import migrations


directory = import_module('mta.runtime.migrations.0258_btr_dated_report_generation')
table = 'mta_state.btr_btrsnapshotforui'
xml = ','.join(f'"{field}{branch}"' for field in ('BPP', 'Colors')
               for branch in ('Tech', 'Econ', 'Dispatch', 'PhysicalInv'))

# Existing receipts read their own physical values. A compact insert cannot be
# accepted under an older recipe, even if an operator sets the writer GUC.
old_recipe = """
 IF TG_OP='UPDATE' AND EXISTS (
    SELECT FROM mta_state.btr_btrsnapshotforui
    WHERE vf_run_id=NEW.run_id AND vf_image='closing/btr/BTRSnapshotForUI'
      AND vf_xml_ordinal IS NOT NULL
 ) THEN RAISE EXCEPTION 'Snapshot XML references require a compatible report generation'; END IF;
"""
guard = directory.new_body.replace(' RETURN NEW;', old_recipe + ' RETURN NEW;')

forward = f"""
ALTER TABLE {table} ADD COLUMN vf_xml_ordinal bigint;
ALTER TABLE {table} ADD CONSTRAINT btr_snapshot_xml_shape CHECK (
  vf_xml_ordinal IS NULL OR (
    vf_image='closing/btr/BTRSnapshotForUI' AND vf_xml_ordinal BETWEEN 0 AND vf_ordinal AND
    ((vf_ordinal=vf_xml_ordinal AND num_nonnulls({xml})=8)
     OR (vf_ordinal<>vf_xml_ordinal AND num_nonnulls({xml})=0))
  )
);
ALTER TABLE {table} ADD CONSTRAINT btr_snapshot_xml_owner
  FOREIGN KEY (vf_run_id,vf_image,vf_xml_ordinal)
  REFERENCES {table}(vf_run_id,vf_image,vf_ordinal);
CREATE INDEX btr_snapshot_xml_members ON {table}(vf_run_id,vf_image,vf_xml_ordinal,vf_ordinal)
 WHERE vf_xml_ordinal IS NOT NULL;
CREATE INDEX btr_snapshot_xml_owners ON {table}(vf_run_id,vf_image,vf_ordinal)
 WHERE vf_xml_ordinal=vf_ordinal;
"""

reverse = f"""
DO $$ BEGIN
 IF EXISTS (SELECT FROM {table} WHERE vf_xml_ordinal IS NOT NULL) THEN
  RAISE EXCEPTION 'Retained snapshot XML references require their reader';
 END IF;
END $$;
ALTER TABLE {table} DROP COLUMN vf_xml_ordinal;
"""


class Migration(migrations.Migration):
    dependencies = [('fresh_mta', '0261_btr_import_trigger_acl')]
    operations = [migrations.RunSQL(forward + directory.replace_guard(directory.new_body, guard),
                                    reverse + directory.replace_guard(guard, directory.new_body))]
