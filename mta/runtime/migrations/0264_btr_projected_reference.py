"""Seal a combined display/reference generation against its own typed rows."""
from django.db import migrations, models


SQL = """
CREATE FUNCTION mta.check_btr_projected_reference() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE actual_bounds jsonb; actual_counts jsonb; total bigint;
BEGIN
 IF TG_OP='UPDATE' AND OLD.version=4 AND
    ROW(NEW.id,NEW.version,NEW.run_id,NEW.source_digest,NEW.lineage,NEW.business_date,NEW.source_kind)
    IS DISTINCT FROM ROW(OLD.id,OLD.version,OLD.run_id,OLD.source_digest,OLD.lineage,OLD.business_date,OLD.source_kind)
 THEN RAISE EXCEPTION 'Combined BTR source identity is immutable'; END IF;
 IF NEW.version<>4 THEN RETURN NEW; END IF;
 IF TG_OP='UPDATE' AND OLD.version<>4 THEN RAISE EXCEPTION 'Combined BTR requires its own attempt'; END IF;
 IF NOT EXISTS (SELECT FROM mta.fresh_mta_calculationrun r
    JOIN mta.fresh_mta_dailyreportgeneration d ON d.run_id=r.id
    WHERE r.id=NEW.run_id AND r.status='SUCCEEDED' AND r.kind='DAILY_CHAIN'
      AND NEW.source_kind=r.kind AND NEW.business_date=r.business_date
      AND NEW.lineage->>'run'=r.id::text AND NEW.lineage->'version'='4'::jsonb
      AND NEW.lineage->>'production_digest'=r.production_digest AND NEW.lineage->>'output_digest'=r.output_digest
      AND d.version=3 AND d.status='READY' AND NEW.lineage->>'dated_report_digest'=d.digest)
 THEN RAISE EXCEPTION 'Combined BTR requires its own completed dated source'; END IF;
 IF TG_OP='INSERT' AND (NEW.status<>'BUILDING' OR NEW.eligible OR NEW.qualification<>'{}'::jsonb)
 THEN RAISE EXCEPTION 'Combined BTR must start privately'; END IF;
 IF NEW.status='READY' THEN
   SELECT jsonb_object_agg(b,jsonb_build_array(lo,hi)),jsonb_object_agg(b,n),sum(n)
   INTO actual_bounds,actual_counts,total
   FROM (SELECT kinds.b,min(p.id) lo,max(p.id) hi,count(p.id) n
    FROM (VALUES ('tech'),('eco')) kinds(b)
    LEFT JOIN mta.fresh_mta_btrpresentationrow p ON p.generation_id=NEW.id AND p.branch=kinds.b
    GROUP BY kinds.b) counts;
   IF NOT NEW.eligible OR NEW.row_count<>total OR (NEW.rows_digest ~ '^[0-9a-f]{64}$') IS NOT TRUE
      OR NEW.qualification ? 'reference_generation'
      OR NEW.qualification->'reference_projection' IS DISTINCT FROM
         jsonb_build_object('format','btr-display-reference-v1','bounds',actual_bounds)
      OR actual_counts IS DISTINCT FROM NEW.qualification->'populations'
      OR actual_counts->'tech' IS DISTINCT FROM NEW.lineage#>'{images,tech_A,count}'
      OR actual_counts->'eco' IS DISTINCT FROM NEW.lineage#>'{images,eco_A,count}'
      OR EXISTS (SELECT FROM mta.fresh_mta_btrjoinreference WHERE generation_id=NEW.id)
   THEN RAISE EXCEPTION 'Combined BTR reference bounds, population or ownership differ'; END IF;
 END IF;
 RETURN NEW;
END $$;
REVOKE EXECUTE ON FUNCTION mta.check_btr_projected_reference() FROM PUBLIC;
CREATE TRIGGER check_btr_projected_reference BEFORE INSERT OR UPDATE ON mta.fresh_mta_btrreportinggeneration
FOR EACH ROW EXECUTE FUNCTION mta.check_btr_projected_reference();
"""

REVERSE = """
DO $$ BEGIN
 IF EXISTS (SELECT FROM mta.fresh_mta_btrreportinggeneration WHERE version=4)
 THEN RAISE EXCEPTION 'Retained combined BTR requires its guard'; END IF;
END $$;
DROP TRIGGER check_btr_projected_reference ON mta.fresh_mta_btrreportinggeneration;
DROP FUNCTION mta.check_btr_projected_reference();
"""


class Migration(migrations.Migration):
    dependencies = [('fresh_mta','0263_btr_compact_report_guard')]
    operations = [
        migrations.AddIndex('btrpresentationrow', models.Index(fields=['generation','branch','id'],
                                                             name='fresh_btr_display_order')),
        migrations.RunSQL(SQL, REVERSE),
    ]
