"""Authenticate incremental BTR imports at the original operational commit."""
from django.db import migrations


SQL = """
CREATE FUNCTION mta.check_btr_import_sources() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog,mta AS $$
DECLARE
 h constant text := 'closing/btr/BPR';
 d constant text := 'reports/bpr/vf_RationedReqReport';
 item jsonb := NEW.production_manifest->'images'->h;
 incoming jsonb := NEW.production_manifest->'images'->d;
 prior jsonb;
 prior_day date;
 anchor jsonb;
 daily jsonb := '[]'::jsonb;
 survivors bigint;
 expired bigint;
 total bigint;
BEGIN
 IF NEW.kind<>'DAILY_CHAIN' OR NEW.evidence_mode<>'production' OR NEW.status<>'SUCCEEDED'
    OR NEW.production_manifest->>'version' IS DISTINCT FROM '3'
    OR item->>'storage_format' IS DISTINCT FROM 'btr-daily-imports-v1'
    OR item->>'table' IS DISTINCT FROM 'BTR/BPR' OR item->>'image' IS DISTINCT FROM h
    OR incoming->>'table' IS DISTINCT FROM 'BPR/vf_RationedReqReport' OR incoming->>'image' IS DISTINCT FROM d
    OR (incoming->>'digest' ~ '^[0-9a-f]{64}$') IS NOT TRUE
    OR (item->>'digest' ~ '^[0-9a-f]{64}$') IS NOT TRUE THEN
  RAISE EXCEPTION 'Invalid operational BTR import source'; END IF;
 -- The existing qualified cut authenticates the initialization, capture,
 -- settings and own predecessor. Reuse its custody without another chain.
 SELECT p.business_date,p.production_manifest->'images'->h INTO prior_day,prior
 FROM mta.fresh_mta_calculationrun p
 JOIN mta.fresh_mta_operationalstatecut prev ON prev.run_id=p.id AND prev.family='rationing_history'
 JOIN mta.fresh_mta_operationalstatecut cur ON cur.parent_id=prev.id AND cur.run_id=NEW.id
 WHERE p.id=NEW.predecessor_id AND p.status='SUCCEEDED' AND p.business_date<NEW.business_date
  AND p.production_manifest->>'version'='3' AND prev.root_digest<>'' AND cur.root_digest<>''
  AND cur.initialization_id=prev.initialization_id;
 IF NOT FOUND OR prior->>'image' IS DISTINCT FROM h OR prior->>'table' IS DISTINCT FROM 'BTR/BPR'
 THEN RAISE EXCEPTION 'BTR import requires the exact accepted predecessor'; END IF;
 IF prior ? 'storage_format' THEN
  IF prior->>'storage_format' IS DISTINCT FROM 'btr-daily-imports-v1' THEN
   RAISE EXCEPTION 'Unsupported prior BTR import'; END IF;
  anchor := prior#>'{sources,anchor}';
  daily := prior#>'{sources,daily}';
 ELSE
  anchor := jsonb_build_object('owner',NEW.predecessor_id,'day',prior_day,
                               'count',prior->'count','digest',prior->'digest');
 END IF;
 IF jsonb_typeof(anchor)='object' THEN
  SELECT count(*) INTO expired FROM mta_state.btr_bpr a
   WHERE a.vf_run_id=(anchor->>'owner')::uuid AND a.vf_image=h AND
    (a."ReportDate"=NEW.business_date OR
     (a."ReportDate">prior_day-90 AND a."ReportDate"<=NEW.business_date-90 AND NOT EXISTS
      (SELECT FROM jsonb_array_elements(daily) b WHERE (b->>'day')::date=a."ReportDate")));
  survivors := (anchor->>'count')::bigint-expired;
  IF survivors<0 THEN RAISE EXCEPTION 'Invalid BTR anchor remainder'; END IF;
  anchor := CASE WHEN survivors>0 THEN jsonb_set(anchor,'{count}',to_jsonb(survivors)) END;
 END IF;
 SELECT coalesce(jsonb_agg(b ORDER BY ord),'[]'::jsonb) INTO daily
  FROM jsonb_array_elements(daily) WITH ORDINALITY a(b,ord) WHERE (b->>'day')::date>NEW.business_date-90;
 daily := daily || jsonb_build_array(jsonb_build_object('owner',NEW.id,'day',NEW.business_date,
                           'count',incoming->'count','digest',incoming->'digest'));
 SELECT coalesce(survivors,0)+sum((b->>'count')::bigint) INTO total FROM jsonb_array_elements(daily) b;
 IF item->'sources' IS DISTINCT FROM jsonb_build_object('anchor',anchor,'daily',daily)
    OR item->'count' IS DISTINCT FROM to_jsonb(total)
    OR incoming->'count' IS DISTINCT FROM to_jsonb((SELECT count(*) FROM mta_state.bpr_vf_rationedreqreport
                                                    WHERE vf_run_id=NEW.id AND vf_image=d))
    OR EXISTS (SELECT FROM mta_state.btr_bpr WHERE vf_run_id=NEW.id AND vf_image=h) THEN
  RAISE EXCEPTION 'Operational BTR import directory differs from its accepted sources'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER btr_import_sources BEFORE INSERT OR UPDATE OF production_manifest,status,predecessor_id,business_date
 ON mta.fresh_mta_calculationrun FOR EACH ROW
 WHEN (NEW.production_manifest#>'{images,closing/btr/BPR}' ? 'storage_format')
 EXECUTE FUNCTION mta.check_btr_import_sources();
"""

REVERSE = """
DO $$ BEGIN IF EXISTS (SELECT FROM mta.fresh_mta_calculationrun
 WHERE production_manifest#>>'{images,closing/btr/BPR,storage_format}'='btr-daily-imports-v1') THEN
 RAISE EXCEPTION 'Retained operational BTR import sources require their guard'; END IF; END $$;
DROP TRIGGER btr_import_sources ON mta.fresh_mta_calculationrun;
DROP FUNCTION mta.check_btr_import_sources();
"""


class Migration(migrations.Migration):
    dependencies = [('fresh_mta','0259_btr_date_pair_lookup')]
    operations = [migrations.RunSQL(SQL, REVERSE)]
