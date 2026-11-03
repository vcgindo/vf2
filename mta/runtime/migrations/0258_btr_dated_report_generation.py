"""Bind a dated BTR generation to its own accepted imports and predecessor."""
from importlib import import_module

from django.db import migrations


original = import_module('mta.runtime.migrations.0161_report_generation_insert_serialization')
old_body = original.new_generation.split('AS $$', 1)[1].split('$$;', 1)[0]

DECLARATIONS = """
DECLARE
 source text;
 owner_day date;
 previous_id uuid;
 images jsonb;
 previous_directory jsonb;
 previous_status text;
 block jsonb;
 path text;
 history jsonb;
 kinds jsonb;
 anchor jsonb;
 daily jsonb := '[]'::jsonb;
 expected jsonb;
"""

# A v1 predecessor has no directory. The first v2 receipt instead anchors
# its own complete accepted BPR history. Later receipts inherit only blocks
# that can still overlap the current 90-day window.
CHECK_DIRECTORY = """
 IF TG_OP='UPDATE' AND NEW.version=2 THEN
  SELECT business_date,predecessor_id,production_manifest->'images'
   INTO STRICT owner_day,previous_id,images
   FROM mta.fresh_mta_calculationrun WHERE id=NEW.run_id AND evidence_mode='production';
  SELECT status,metadata->'btr_calendar' INTO previous_status,previous_directory
   FROM mta.fresh_mta_dailyreportgeneration WHERE run_id=previous_id AND version=2 FOR SHARE;
  IF FOUND AND (previous_status<>'READY' OR previous_directory IS NULL
     OR (previous_directory->>'day')::date >= owner_day) THEN
   RAISE EXCEPTION 'A dated BTR successor requires its sealed earlier predecessor'; END IF;
  history := images->'closing/btr/BPR';
  IF previous_directory IS NULL THEN
   path := 'closing/btr/BPR';
  ELSE
   path := 'reports/bpr/vf_RationedReqReport';
   IF (previous_directory#>>'{anchor,day}')::date > owner_day-90 THEN
    anchor := previous_directory->'anchor';
   END IF;
   SELECT coalesce(jsonb_agg(item ORDER BY ordinal),'[]'::jsonb) INTO daily
    FROM jsonb_array_elements(previous_directory->'daily') WITH ORDINALITY AS d(item,ordinal)
    WHERE (item->>'day')::date > owner_day-90;
  END IF;
  IF history->>'image' IS DISTINCT FROM 'closing/btr/BPR'
     OR history->>'table' IS DISTINCT FROM 'BTR/BPR'
     OR images->path->>'image' IS DISTINCT FROM path
     OR images->path->>'table' IS DISTINCT FROM
      (CASE WHEN previous_directory IS NULL THEN 'BTR/BPR' ELSE 'BPR/vf_RationedReqReport' END)
     OR (images->path->>'digest' ~ '^[0-9a-f]{64}$') IS NOT TRUE THEN
   RAISE EXCEPTION 'BTR generation requires its accepted typed import'; END IF;
  IF history->'count'='0'::jsonb THEN
   kinds := '[]'::jsonb;
  ELSE
   SELECT jsonb_agg(f->2 ORDER BY ordinal) INTO kinds
    FROM unnest(ARRAY['PhysicalInventoryPen','PhysicalInventoryColor','DispatchPen','DispatchColor',
                      'TechPen','TechColor','EcoPen','EcoColor']) WITH ORDINALITY AS o(name,ordinal)
    JOIN jsonb_array_elements(history->'fields') f ON f->>1=o.name;
   IF jsonb_array_length(kinds) IS DISTINCT FROM 8 OR EXISTS (
    SELECT 1 FROM jsonb_array_elements_text(kinds) k WHERE k IS NULL OR k NOT IN ('str','int','float')
   ) THEN RAISE EXCEPTION 'Invalid BTR source field representation'; END IF;
  END IF;
  block := jsonb_build_object('run',NEW.run_id,'day',owner_day,'source',images->path->'digest','wire',kinds);
  IF previous_directory IS NULL THEN anchor := block;
  ELSE daily := daily || jsonb_build_array(block); END IF;
  expected := jsonb_build_object('format','btr-dated-import-v1','run',NEW.run_id,'day',owner_day,
                                 'production',source,'anchor',anchor,'daily',daily);
  IF NEW.metadata->>'schema' IS DISTINCT FROM 'fresh-derived-report-generation-v2'
     OR NEW.metadata->'btr_calendar' IS DISTINCT FROM expected THEN
   RAISE EXCEPTION 'BTR date directory differs from its accepted source lineage'; END IF;
 END IF;
"""

new_body = old_body.replace('DECLARE source text;', DECLARATIONS).replace(
    'OR NEW.version<>1', 'OR NEW.version NOT IN (1,2)').replace(' RETURN NEW;', CHECK_DIRECTORY + ' RETURN NEW;')


def replace_guard(before, after):
    # Keep the installed function owner, ACL and function attributes.
    return """
DO $upgrade$
DECLARE target regprocedure := 'mta.guard_report_generation()'::regprocedure;
 definition text := pg_get_functiondef(target);
BEGIN
 IF (SELECT prosrc FROM pg_proc WHERE oid=target) IS DISTINCT FROM $old$BEFORE_BODY$old$
    OR strpos(definition,$old$BEFORE_BODY$old$)=0 THEN
  RAISE EXCEPTION 'Expected the exact previous report generation guard'; END IF;
 EXECUTE replace(definition,$old$BEFORE_BODY$old$,$new$AFTER_BODY$new$);
END $upgrade$;
""".replace('BEFORE_BODY', before).replace('AFTER_BODY', after)


class Migration(migrations.Migration):
    dependencies = [('fresh_mta', '0257_postbtr_consumer_read')]
    operations = [migrations.RunSQL(replace_guard(old_body, new_body), """
DO $$ BEGIN
 IF EXISTS (SELECT 1 FROM mta.fresh_mta_dailyreportgeneration WHERE version=2) THEN
  RAISE EXCEPTION 'Retained dated report generation requires its guard'; END IF;
END $$;
""" + replace_guard(new_body, old_body))]
