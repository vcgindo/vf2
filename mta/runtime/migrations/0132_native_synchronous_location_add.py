"""Separate persisted master2 authorization for canonical Location Add."""
from importlib import import_module
from django.db import migrations

HELPER = r'''
CREATE FUNCTION mta.native_location_add_row(target text, candidate jsonb) RETURNS boolean
LANGUAGE sql STABLE AS $$
 WITH invocation AS (
  SELECT T.*, string_to_array(replace(coalesce(T."ColumnList",''),'WHDescription,',''),',') AS columns
  FROM mta.fresh_mta_mdmtask T
  JOIN mta.fresh_mta_mdmsource S ON S.id=T.source_id
  JOIN mta.fresh_mta_productioninitialization I ON I.source_id=S.id
  WHERE T.id::text=current_setting('fresh.location_add_task',true)
   AND S.id::text=current_setting('fresh.location_add_source',true)
   AND S.id=(candidate->>'source_id')::bigint
   AND S.receipt->>'schema'='fresh-production-mdm-source-v1'
   AND I.input_manifest_digest<>'' AND I.receipt_digest<>''
   AND T."MasterId"='2' AND T."Actiontype"=1
 ), backed AS (
  SELECT DISTINCT R."TaskId", lower(rtrim(R."WHCode")) AS code
  FROM mta.fresh_mta_mdmlocationrequested R
  JOIN mta.fresh_mta_mdmlocationhistory H
   ON H.source_id=R.source_id AND H."TaskId"=R."TaskId"
   AND lower(rtrim(H."WHCode"))=lower(rtrim(R."WHCode"))
  WHERE R.source_id=(candidate->>'source_id')::bigint
   AND R."Approved" AND H."Status"='3'
 ), existing AS (
  SELECT "WHCode", ordinal FROM mta.fresh_mta_mdmlocationattributes
  WHERE target='fresh_mta_mdmlocationattributes'
   AND source_id=(candidate->>'source_id')::bigint AND owner=candidate->>'owner'
  UNION ALL
  SELECT "WHCode", ordinal FROM mta.fresh_mta_mdmlocationdescription
  WHERE target='fresh_mta_mdmlocationdescription'
   AND source_id=(candidate->>'source_id')::bigint AND owner=candidate->>'owner'
 ), eligible AS (
  -- All source queue occurrences participate, including other approved tasks.
  -- STABLE uses the INSERT's prestatement image: duplicate absent codes must
  -- not disappear after an earlier row in the same INSERT has been written.
  SELECT Q.*, row_number() OVER (ORDER BY Q.id) +
   coalesce((SELECT max(ordinal) FROM existing),0) AS next_ordinal
  FROM mta.fresh_mta_mdmlocationapproved Q
  WHERE Q.source_id=(candidate->>'source_id')::bigint
   AND NOT EXISTS(SELECT 1 FROM existing E
                  WHERE lower(rtrim(E."WHCode"))=lower(rtrim(Q."WHCode")))
 )
 SELECT EXISTS (
  SELECT 1 FROM invocation T CROSS JOIN eligible Q
  WHERE candidate->>'owner' IN ('Importer','BPR','BTR','DBM')
   AND target IN ('fresh_mta_mdmlocationattributes','fresh_mta_mdmlocationdescription')
   AND NOT ('WHDescription'=ANY(T.columns))
   AND 'WHCode'=ANY(T.columns)
   AND EXISTS(SELECT 1 FROM backed B JOIN mta.fresh_mta_mdmlocationapproved A
      ON A.source_id=T.source_id AND lower(rtrim(A."WHCode"))=B.code
      WHERE B."TaskId"=T."TaskID")
   AND EXISTS(SELECT 1 FROM backed B WHERE B.code=lower(rtrim(Q."WHCode")))
   AND (candidate->>'ordinal')::bigint=Q.next_ordinal
   AND candidate - ARRAY['id','source_id','owner','ordinal'] = (
    SELECT jsonb_object_agg(K.key, CASE
      WHEN target='fresh_mta_mdmlocationdescription' OR K.key=ANY(T.columns)
      THEN to_jsonb(Q)->K.key ELSE 'null'::jsonb END)
    FROM jsonb_object_keys(candidate - ARRAY['id','source_id','owner','ordinal']) AS K(key)
   )
 )
$$;
'''

previous = import_module('mta.runtime.migrations.0131_sku_add_statement_snapshot')
old_guard = previous.guard
anchor = ' PERFORM 1 FROM mta.fresh_mta_mdmsource WHERE id=owner FOR UPDATE;'
assert old_guard.count(anchor) == 1
guard = old_guard.replace(anchor, r'''
 IF TG_OP='INSERT' AND TG_TABLE_NAME IN ('fresh_mta_mdmlocationattributes','fresh_mta_mdmlocationdescription')
  AND current_setting('fresh.location_add_source',true)=owner::text
  AND coalesce(current_setting('fresh.location_add_task',true),'')<>'' THEN
  -- Mandatory earlier STABLE master2 trigger validates the exact row.
  RETURN NEW;
 END IF;
''' + anchor)

FORWARD = HELPER + r'''
CREATE FUNCTION mta.lock_native_location_add(owner bigint) RETURNS void
LANGUAGE plpgsql VOLATILE AS $$
BEGIN
 -- Production acquires this lock before its queue reads/INSERT snapshot. A
 -- direct competing INSERT must fail, not wait and use an obsolete snapshot.
 IF NOT pg_try_advisory_xact_lock(hashtextextended('fresh-mdm-supplier:' || owner::text,0))
  THEN RAISE EXCEPTION 'Native Location Add source is owned by another publication or capture'; END IF;
 PERFORM 1 FROM mta.fresh_mta_mdmsource WHERE id=owner FOR UPDATE;
END $$;
CREATE FUNCTION mta.guard_native_location_add() RETURNS trigger
LANGUAGE plpgsql STABLE AS $$
BEGIN
 IF current_setting('fresh.location_add_source',true)=NEW.source_id::text
  AND coalesce(current_setting('fresh.location_add_task',true),'')<>'' THEN
  PERFORM mta.lock_native_location_add(NEW.source_id);
  IF NOT mta.native_location_add_row(TG_TABLE_NAME,to_jsonb(NEW))
   THEN RAISE EXCEPTION 'Native synchronous Location Add requires its exact approved task and queue row'; END IF;
 END IF;
 RETURN NEW;
END $$;
'''
for table in ('mdmlocationattributes', 'mdmlocationdescription'):
    # PostgreSQL fires same-kind triggers in name order. Validation is mandatory
    # before active_mdm_current can return for this branch; a marker alone never
    # admits any row. Normal bootstrap/daily INSERTs pass straight through.
    FORWARD += f'''
CREATE TRIGGER a_native_location_add BEFORE INSERT ON mta.fresh_mta_{table}
 FOR EACH ROW EXECUTE FUNCTION mta.guard_native_location_add();
'''
FORWARD += guard
REVERSE = old_guard + r'''
DROP TRIGGER a_native_location_add ON mta.fresh_mta_mdmlocationattributes;
DROP TRIGGER a_native_location_add ON mta.fresh_mta_mdmlocationdescription;
DROP FUNCTION mta.guard_native_location_add();
DROP FUNCTION mta.lock_native_location_add(bigint);
DROP FUNCTION mta.native_location_add_row(text,jsonb);
'''

class Migration(migrations.Migration):
    dependencies = [('fresh_mta', '0131_sku_add_statement_snapshot')]
    operations = [migrations.RunSQL(FORWARD, REVERSE)]
