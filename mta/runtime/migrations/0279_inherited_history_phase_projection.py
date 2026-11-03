"""Qualify existing SuggestionsLog projections without copying their payload."""
from importlib import import_module
from django.db import migrations


previous = import_module('mta.runtime.migrations.0278_inherited_history_phase_boundary')
# Frozen phase report stages. Do not import a mutable application registry.
REPORT_STAGES = (
    'controls', 'norm-change-export', 'norm-change-history', 'norm0-60-export',
    'norm0-90-export', 'norm0-export', 'norm1-advisory', 'norm1-export',
    'norm2-export', 'phase-recommendation-30', 'phase-recommendation-60',
    'phase-recommendation-90')
REPORT_PATHS = ','.join("'phase/DBM/report-facts/"+s+"/SuggestionsLog'" for s in REPORT_STAGES)

BOUNDARY = r'''
  WHEN jsonb_typeof(COALESCE(manifest->'images','{}'::jsonb)) <> 'object' THEN NULL
  WHEN EXISTS (
    SELECT 1 FROM jsonb_each(CASE WHEN jsonb_typeof(manifest->'images')='object'
      THEN manifest->'images' ELSE '{}'::jsonb END) AS image(key,value)
    WHERE image.value->>'storage_format'='inherited-control-history-v1' AND (
      manifest->>'storage_format' IS NULL OR manifest->>'storage_format' NOT IN (
        'fresh-phase-image-references-v3','fresh-phase-image-references-v4')
      OR manifest->>'phase' IS NULL OR manifest->>'phase' NOT IN ('PRE_BPR','BPR','DBM')
      OR image.value->>'image' IS NULL OR image.value->>'image' NOT IN (
        'phase/PRE_BPR/controls/suggestions_log','phase/BPR/controls/suggestions_log',
        'phase/DBM/controls/suggestions_log')
      OR image.value->>'run_id' IS NULL
      OR image.value->>'run_id' IS DISTINCT FROM manifest#>>'{metadata,identity}'
      OR (CASE
        WHEN image.key=('phase/'||(manifest->>'phase')||'/controls/suggestions_log') THEN true
        WHEN manifest->>'storage_format'='fresh-phase-image-references-v4'
          AND manifest->>'phase'='DBM' AND image.value->>'table'='DBM/SuggestionsLog'
          AND manifest#>'{images,phase/DBM/controls/suggestions_log}'=image.value
          AND manifest#>'{state,control_final,suggestions_log}'=
            '{"image":"phase/DBM/controls/suggestions_log"}'::jsonb THEN
          image.key='phase/DBM/dbm/SuggestionsLog' OR (
            image.key IN (REPORT_PATHS)
            AND manifest#>'{images,phase/DBM/dbm/SuggestionsLog}'=image.value
            AND manifest#>'{state,final_dbm,SuggestionsLog}'=
              '{"image":"phase/DBM/dbm/SuggestionsLog"}'::jsonb)
        ELSE false END) IS NOT TRUE
    )
  ) THEN NULL
'''.replace('REPORT_PATHS', REPORT_PATHS)

assert previous.SQL.count(previous.BOUNDARY) == 1
SQL = previous.SQL.replace(previous.BOUNDARY, BOUNDARY).replace(
    "('fresh-phase-image-references-v2','fresh-phase-image-references-v3')",
    "('fresh-phase-image-references-v2','fresh-phase-image-references-v3','fresh-phase-image-references-v4')")


class Migration(migrations.Migration):
    dependencies = [('fresh_mta', '0278_inherited_history_phase_boundary')]
    # Replace only the existing capability predicate; preserve all data, original
    # producer identities, function OID and privileges. No downgrade after v4 writes.
    operations = [migrations.RunSQL(SQL)]
