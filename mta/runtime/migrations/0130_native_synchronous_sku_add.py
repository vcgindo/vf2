"""Admit canonical native SKU Add INSERTs backed by persisted approval rows."""
from importlib import import_module

from django.db import migrations


HELPER = r'''
CREATE FUNCTION mta.native_sku_add_row(target text, candidate jsonb) RETURNS boolean
LANGUAGE sql STABLE AS $$
 WITH invocation AS (
  SELECT T.*, string_to_array(replace(coalesce(T."ColumnList",''),'SKUDescription,',''),',') AS columns
  FROM mta.fresh_mta_mdmtask T
  JOIN mta.fresh_mta_mdmsource S ON S.id=T.source_id
  JOIN mta.fresh_mta_productioninitialization I ON I.source_id=S.id
  WHERE T.id::text=current_setting('fresh.sku_add_task',true)
   AND S.id::text=current_setting('fresh.sku_add_source',true)
   AND S.id=(candidate->>'source_id')::bigint
   AND S.receipt->>'schema'='fresh-production-mdm-source-v1'
   AND I.input_manifest_digest<>'' AND I.receipt_digest<>''
   AND T."MasterId"='1' AND T."Actiontype"=1
 ), backed AS (
  SELECT DISTINCT R."TaskId", lower(rtrim(R."SKUCode")) AS code
  FROM mta.fresh_mta_mdmskurequested R
  JOIN mta.fresh_mta_mdmskuhistory H
   ON H.source_id=R.source_id AND H."TaskId"=R."TaskId"
   AND lower(rtrim(H."SKUCode"))=lower(rtrim(R."SKUCode"))
  WHERE R.source_id=(candidate->>'source_id')::bigint
   AND R."Approved" AND H."Status"='3'
 ), existing AS (
  SELECT "SKUCode", ordinal FROM mta.fresh_mta_mdmskuattributes
  WHERE target='fresh_mta_mdmskuattributes'
   AND source_id=(candidate->>'source_id')::bigint AND owner=candidate->>'owner'
  UNION ALL
  SELECT "SKUCode", ordinal FROM mta.fresh_mta_mdmskudescription
  WHERE target='fresh_mta_mdmskudescription'
   AND source_id=(candidate->>'source_id')::bigint AND owner=candidate->>'owner'
 ), eligible AS (
  -- All source queue occurrences participate, including other approved tasks.
  -- STABLE uses the INSERT's prestatement image: duplicate absent codes must
  -- not disappear after an earlier row in the same INSERT has been written.
  SELECT Q.*, row_number() OVER (ORDER BY Q.id) +
   coalesce((SELECT max(ordinal) FROM existing),0) AS next_ordinal
  FROM mta.fresh_mta_mdmskuapproved Q
  WHERE Q.source_id=(candidate->>'source_id')::bigint
   AND NOT EXISTS(SELECT 1 FROM existing E
                  WHERE lower(rtrim(E."SKUCode"))=lower(rtrim(Q."SKUCode")))
 )
 SELECT EXISTS (
  SELECT 1 FROM invocation T CROSS JOIN eligible Q
  WHERE candidate->>'owner' IN ('Importer','BPR','BTR','DBM')
   AND target IN ('fresh_mta_mdmskuattributes','fresh_mta_mdmskudescription')
   AND NOT ('SKUDescription'=ANY(T.columns))
   AND 'SKUCode'=ANY(T.columns)
   AND EXISTS(SELECT 1 FROM backed B JOIN mta.fresh_mta_mdmskuapproved A
      ON A.source_id=T.source_id AND lower(rtrim(A."SKUCode"))=B.code
      WHERE B."TaskId"=T."TaskID")
   AND EXISTS(SELECT 1 FROM backed B WHERE B.code=lower(rtrim(Q."SKUCode")))
   AND (candidate->>'ordinal')::bigint=Q.next_ordinal
   AND candidate - ARRAY['id','source_id','owner','ordinal'] = (
    SELECT jsonb_object_agg(K.key, CASE
      WHEN target='fresh_mta_mdmskudescription' OR K.key=ANY(T.columns)
      THEN to_jsonb(Q)->K.key ELSE 'null'::jsonb END)
    FROM jsonb_object_keys(candidate - ARRAY['id','source_id','owner','ordinal']) AS K(key)
   )
 )
$$;
'''

previous = import_module('mta.runtime.migrations.0124_native_inactive_current_guard')
REVERSE = previous.FORWARD + '\nDROP FUNCTION mta.native_sku_add_row(text,jsonb);'
anchor = ' PERFORM 1 FROM mta.fresh_mta_mdmsource WHERE id=owner FOR UPDATE;'
assert previous.FORWARD.count(anchor) == 1
FORWARD = HELPER + previous.FORWARD.replace(anchor, r'''
 -- Same lock order as native decision/daily capture; never take source row
 -- lock first on this branch, which would invert the application lock order.
 IF TG_OP='INSERT' AND TG_TABLE_NAME IN ('fresh_mta_mdmskuattributes','fresh_mta_mdmskudescription')
  AND current_setting('fresh.sku_add_source',true)=owner::text
  AND coalesce(current_setting('fresh.sku_add_task',true),'')<>'' THEN
  PERFORM pg_advisory_xact_lock(hashtextextended('fresh-mdm-supplier:' || owner::text,0));
  PERFORM 1 FROM mta.fresh_mta_mdmsource WHERE id=owner FOR UPDATE;
  IF mta.native_sku_add_row(TG_TABLE_NAME,to_jsonb(NEW)) THEN RETURN NEW; END IF;
  RAISE EXCEPTION 'Native synchronous SKU Add requires its exact approved task and queue row';
 END IF;
''' + anchor)


class Migration(migrations.Migration):
    dependencies = [('fresh_mta', '0129_skuloc_modify_audit_nullable_parent')]
    operations = [migrations.RunSQL(FORWARD, REVERSE)]
