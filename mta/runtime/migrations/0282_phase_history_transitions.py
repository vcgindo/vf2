"""Typed current history staging and an explicit compatible phase codec."""
from importlib import import_module
from django.db import migrations

LOGICAL = '3fc77ea744eaeaeeb6c01da3141fbd8926c85ecb832fc60b12b2f854e13fcb1e'
old = import_module('mta.runtime.migrations.0279_inherited_history_phase_projection')
# Retain the complete old predicate, including its inherited-image constraints.
SQL = old.SQL
SQL = SQL.replace("'fresh-phase-image-references-v3','fresh-phase-image-references-v4')",
    "'fresh-phase-image-references-v3','fresh-phase-image-references-v4','fresh-phase-image-references-v5')")
SQL = SQL.replace("manifest->>'storage_format'='fresh-phase-image-references-v4'",
    "manifest->>'storage_format' IN ('fresh-phase-image-references-v4','fresh-phase-image-references-v5')")
SQL=SQL.replace("('fresh-phase-image-references-v2','fresh-phase-image-references-v3','fresh-phase-image-references-v4','fresh-phase-image-references-v5')",
    "('fresh-phase-image-references-v2','fresh-phase-image-references-v3','fresh-phase-image-references-v4')")
# Only the new descriptor gets the new physical transition capability.
new_case = r"""
  WHEN manifest->>'storage_format'='fresh-phase-image-references-v5'
    AND code<>'2b307bcb0cad7f75cf0f2273938cd072fb4b25fe1191252691cb6e113873fc7c'
    AND manifest->'phase_contract'=jsonb_build_object(
      'schema','fresh-native-phase-logical-contract-v1','digest','3fc77ea744eaeaeeb6c01da3141fbd8926c85ecb832fc60b12b2f854e13fcb1e')
    AND jsonb_typeof(manifest#>'{state,history_changes}')='object'
    AND NOT EXISTS (
      SELECT FROM jsonb_each(manifest->'images') I WHERE I.value->>'storage_format'='phase-history-transition-v1'
      AND (I.value->>'run_id' IS DISTINCT FROM manifest#>>'{metadata,identity}'
        OR I.value->>'family' NOT IN ('closing/importer/RejectedMaster','closing/importer/RetiredNormsTbl','closing/dbm/NormChangeLogTbl')
        OR I.key NOT LIKE 'phase/'||(manifest->>'phase')||'/%'
        OR I.value->>'image' NOT LIKE 'phase/%'
        OR I.value->'sorted_prefix' IS DISTINCT FROM manifest#>ARRAY['state','history_changes',I.value->>'family','sorted_prefix']
        OR I.value->'additions' IS DISTINCT FROM manifest#>ARRAY['images',manifest#>>ARRAY['state','history_changes',I.value->>'family','additions','image']]
        OR I.value->'changes' IS DISTINCT FROM manifest#>ARRAY['images',manifest#>>ARRAY['state','history_changes',I.value->>'family','changes','image']]))
    THEN '3fc77ea744eaeaeeb6c01da3141fbd8926c85ecb832fc60b12b2f854e13fcb1e'
""".replace('3fc77ea744eaeaeeb6c01da3141fbd8926c85ecb832fc60b12b2f854e13fcb1e',LOGICAL)
SQL=SQL.replace('  ELSE NULL END',new_case+'  ELSE NULL END')
assert new_case in SQL
# v2-v4 cannot introduce a transition image, and v5 cannot introduce a terminal alias.
SQL=SQL.replace(' SELECT CASE',r""" SELECT CASE
  WHEN EXISTS (SELECT FROM jsonb_each(CASE WHEN jsonb_typeof(manifest->'images')='object'
    THEN manifest->'images' ELSE '{}'::jsonb END) I WHERE
    I.value->>'storage_format'='terminal-history-projection-v1' OR
    I.value->>'storage_format'='phase-history-transition-v1' AND
      manifest->>'storage_format' IS DISTINCT FROM 'fresh-phase-image-references-v5') THEN NULL
""")

ROWS = r"""
CREATE TABLE mta_state.phase_historychange (
 vf_run_id uuid NOT NULL REFERENCES mta.fresh_mta_calculationrun(id) ON DELETE RESTRICT,
 vf_image text NOT NULL CHECK(vf_image ~ '^phase/(PRE_BPR|BPR|DBM)/history-changes/(importer/(RejectedMaster|RetiredNormsTbl)|dbm/NormChangeLogTbl)$'),
 vf_ordinal bigint NOT NULL CHECK(vf_ordinal>=0),
 "OpeningOrdinal" bigint, "AdditionOrdinal" bigint, "SortKey" text COLLATE "C",
 PRIMARY KEY(vf_run_id,vf_image,vf_ordinal),
 CHECK (("OpeningOrdinal" IS NOT NULL AND "OpeningOrdinal">=0 AND "AdditionOrdinal" IS NULL AND "SortKey" IS NULL)
    OR ("OpeningOrdinal" IS NULL AND "AdditionOrdinal" IS NOT NULL AND "AdditionOrdinal">=0)));
CREATE UNIQUE INDEX phase_history_removed ON mta_state.phase_historychange(vf_run_id,vf_image,"OpeningOrdinal") WHERE "OpeningOrdinal" IS NOT NULL;
CREATE UNIQUE INDEX phase_history_added ON mta_state.phase_historychange(vf_run_id,vf_image,"AdditionOrdinal") WHERE "AdditionOrdinal" IS NOT NULL;
"""
for operation,refs in (('INSERT','NEW TABLE AS new_rows'),('UPDATE','OLD TABLE AS old_rows NEW TABLE AS new_rows'),('DELETE','OLD TABLE AS old_rows')):
    ROWS+='CREATE TRIGGER phase_rows_'+operation.lower()+' AFTER '+operation+' ON mta_state.phase_historychange REFERENCING '+refs+' FOR EACH STATEMENT EXECUTE FUNCTION mta.guard_phase_rows();'
for operation,refs in (('INSERT','NEW TABLE AS new_rows'),('UPDATE','OLD TABLE AS old_rows NEW TABLE AS new_rows'),('DELETE','OLD TABLE AS old_rows'),('TRUNCATE','')):
    ROWS+='CREATE TRIGGER ingestion_watch_'+operation.lower()+' AFTER '+operation+' ON mta_state.phase_historychange '+('REFERENCING '+refs if refs else '')+" FOR EACH STATEMENT EXECUTE FUNCTION mta.ingestion_watch('operational');"
ROWS+='CREATE TRIGGER phase_no_truncate BEFORE TRUNCATE ON mta_state.phase_historychange FOR EACH STATEMENT EXECUTE FUNCTION mta.deny_phase_truncate();'

class Migration(migrations.Migration):
    dependencies=[('fresh_mta','0281_producer_history_storage')]
    operations=[migrations.RunSQL(ROWS+SQL)]
