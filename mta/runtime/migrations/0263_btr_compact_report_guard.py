"""Admit the compact snapshot only at the owning dated report's seal."""
from importlib import import_module

from django.db import migrations


previous = import_module('mta.runtime.migrations.0262_btr_snapshot_xml_representative')
directory = previous.directory
schema = "NEW.metadata->>'schema' IS DISTINCT FROM 'fresh-derived-report-generation-v2'"
dated = directory.CHECK_DIRECTORY.replace('NEW.version=2', 'NEW.version IN (2,3)').replace(
    'AND version=2 FOR SHARE', 'AND version IN (2,3) FOR SHARE').replace(
    schema, "NEW.metadata->>'schema' IS DISTINCT FROM ('fresh-derived-report-generation-v'||NEW.version)")

compact = """
 IF TG_OP='UPDATE' AND NEW.version=3 THEN
  snapshot := NEW.metadata#>'{images,closing/btr/BTRSnapshotForUI}';
  IF snapshot->>'storage_format' IS DISTINCT FROM 'btr-snapshot-xml-ordinal-v1'
     OR snapshot->>'table' IS DISTINCT FROM 'BTR/BTRSnapshotForUI'
     OR snapshot->>'image' IS DISTINCT FROM 'closing/btr/BTRSnapshotForUI'
     OR (snapshot->>'digest' ~ '^[0-9a-f]{64}$') IS NOT TRUE
     OR jsonb_typeof(snapshot->'reuse_before') IS DISTINCT FROM 'number'
     OR jsonb_typeof(snapshot->'count') IS DISTINCT FROM 'number'
  THEN RAISE EXCEPTION 'Missing compact BTR snapshot contract'; END IF;
  SELECT count(*), max(vf_ordinal) INTO cardinality, last_ordinal
   FROM mta_state.btr_btrsnapshotforui
   WHERE vf_run_id=NEW.run_id AND vf_image='closing/btr/BTRSnapshotForUI';
  IF snapshot->'count' IS DISTINCT FROM to_jsonb(cardinality)
     OR coalesce(last_ordinal,-1)<>cardinality-1 OR
     (snapshot->>'reuse_before')::bigint NOT BETWEEN 0 AND cardinality
     OR EXISTS (
       SELECT FROM mta_state.btr_btrsnapshotforui s
       LEFT JOIN mta_state.btr_btrsnapshotforui owner
         ON owner.vf_run_id=s.vf_run_id AND owner.vf_image=s.vf_image
         AND owner.vf_ordinal=s.vf_xml_ordinal AND owner.vf_xml_ordinal=owner.vf_ordinal
       WHERE s.vf_run_id=NEW.run_id AND s.vf_image='closing/btr/BTRSnapshotForUI'
         AND (owner.vf_ordinal IS NULL OR
           (s.vf_ordinal<>s.vf_xml_ordinal AND s.vf_xml_ordinal>=(snapshot->>'reuse_before')::bigint))
     )
  THEN RAISE EXCEPTION 'Compact BTR snapshot owner, count or ordinal differs'; END IF;
 END IF;
"""

guard = previous.guard.replace('NEW.version NOT IN (1,2)', 'NEW.version NOT IN (1,2,3)').replace(
    directory.CHECK_DIRECTORY, dated).replace(previous.old_recipe, previous.old_recipe.replace(
        "TG_OP='UPDATE' AND EXISTS", "TG_OP='UPDATE' AND NEW.version<>3 AND EXISTS")).replace(
    ' previous_status text;', ' previous_status text; snapshot jsonb; cardinality bigint; last_ordinal bigint;'
).replace(' RETURN NEW;', compact + ' RETURN NEW;')


class Migration(migrations.Migration):
    dependencies = [('fresh_mta', '0262_btr_snapshot_xml_representative')]
    operations = [migrations.RunSQL(directory.replace_guard(previous.guard, guard), """
DO $$ BEGIN
 IF EXISTS (SELECT FROM mta.fresh_mta_dailyreportgeneration WHERE version=3) THEN
  RAISE EXCEPTION 'Retained compact report requires its guard';
 END IF;
END $$;
""" + directory.replace_guard(guard, previous.guard))]
