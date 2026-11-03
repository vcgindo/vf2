"""Allow PostBTR to bind its consumed projection to the same run's sealed cut."""
from importlib import import_module

from django.db import migrations


placement = import_module('mta.runtime.migrations.0231_runtime_report_placement_guards')

# This is the existing PostBTR source order, including the inferred Dispatch.
# The legacy five-key projection continues to bind the candidate's row bytes.
REFERENCE_CHECK = r"""
  AND CASE WHEN (P.metadata->'authority') ? 'rationing_source' THEN
   P.placement='PostBTR' AND P.owner_kind IN ('FULL_COMPLETION','SCOPED_FINAL')
   AND EXISTS (
    SELECT 1
    FROM mta.fresh_mta_operationalstatecut H
    CROSS JOIN LATERAL (SELECT P.metadata#>'{authority,images,images,BTR/RationingHistory}' AS item) I
    WHERE H.run_id=R.id AND H.family='rationing_history' AND H.position>0
     AND H.root_digest<>'' AND H.input_digest=P.input_digest AND H.settings_digest=P.profile_digest
     AND I.item->>'image'='runtime-report/'||P.id::text||'/BTR/RationingHistory'
     AND I.item->>'table'='placement/BTR/RationingHistory'
     AND I.item->'count'=NULLIF(H.root_body,'')::jsonb->'count'
     AND I.item->>'digest' ~ '^[0-9a-f]{64}$'
     AND CASE WHEN I.item->'count'='0'::jsonb THEN I.item->'fields'='[]'::jsonb ELSE
      (SELECT array_agg(F.field->>0 ORDER BY F.ord)
       FROM jsonb_array_elements(I.item->'fields') WITH ORDINALITY AS F(field,ord))
       =ARRAY['ParentWhCode','ParentWhName','SKUCode','SKUName','WhCode','WhName','IsNormed',
              'Req','ParentNorm','RationedReq','SupplierDispatchReq','DispatchPen','DispatchColor',
              'Dispatch','ReportDate','Stock','GIT']::text[] END
     AND P.metadata#>'{authority,rationing_source}'=jsonb_build_object(
        'format','postbtr-rationing-cut-v1','cut_id',H.id::text,'root_digest',H.root_digest,
        'projection_digest',I.item->>'digest')
     AND (R.status='RUNNING' OR
        (R.production_manifest#>>'{images,closing/btr/RationingHistory,cut_id}'=H.id::text
         AND R.production_manifest#>>'{images,closing/btr/RationingHistory,digest}'=H.root_digest
         AND R.production_manifest#>>'{images,closing/btr/RationingHistory,storage_format}'='rationing-occurrences-v1')))
  ELSE true END
"""


def insert_before(body, marker, addition):
    if body.count(marker) != 1:
        raise ValueError('Expected the exact previous placement guard')
    return body.replace(marker, addition + marker)


PLACEMENT_SOURCE = insert_before(placement.PLACEMENT_SOURCE, "  AND ((P.placement='PostImporter'", REFERENCE_CHECK)
assert placement.SOURCE.count(placement.PLACEMENT_SOURCE) == 1
SOURCE = placement.SOURCE.replace(placement.PLACEMENT_SOURCE, PLACEMENT_SOURCE)
COMMIT = insert_before(placement.RECEIPT_COMMIT, "  IF actual<>(item->>'count')", """
  IF logical='BTR/RationingHistory' AND (P.metadata->'authority') ? 'rationing_source' THEN
   IF actual<>0 THEN RAISE EXCEPTION 'Referenced PostBTR history also contains payload rows'; END IF;
   CONTINUE;
  END IF;
""")


def guards(old_source, old_commit, new_source, new_commit):
    return (
        placement.exact('mta.runtime_report_publication_source(mta.fresh_mta_runtimereportpublication)', old_source)
        + placement.exact('mta.check_runtime_report_placement()', old_commit)
        + placement.function('runtime_report_publication_source', 'P mta.fresh_mta_runtimereportpublication',
                             'boolean', 'sql', new_source, replace=True, stable=True)
        + placement.function('check_runtime_report_placement', '', 'trigger', 'plpgsql', new_commit, replace=True))


REVERSE_CHECK = """
DO $check$ BEGIN
 IF EXISTS(SELECT 1 FROM mta.fresh_mta_runtimereportpublication
           WHERE (metadata->'authority') ? 'rationing_source') THEN
  RAISE EXCEPTION 'PostBTR references require a compatible reader';
 END IF;
END $check$;
"""


class Migration(migrations.Migration):
    dependencies = [('fresh_mta', '0254_rationing_anchor_revision_ownership')]
    operations = [migrations.RunSQL(
        guards(placement.SOURCE, placement.RECEIPT_COMMIT, SOURCE, COMMIT),
        REVERSE_CHECK + guards(SOURCE, COMMIT, placement.SOURCE, placement.RECEIPT_COMMIT))]
