"""Seal accepted daily metadata; lifecycle status remains independently mutable.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
from django.db import migrations

SQL = """
CREATE FUNCTION mta.accepted_daily_seal() RETURNS trigger LANGUAGE plpgsql
SET search_path=pg_catalog,mta AS $$
BEGIN
 IF OLD.accepted_facts <> '{}'::jsonb THEN
  IF TG_OP='DELETE' THEN RAISE EXCEPTION 'Accepted daily owner is immutable'; END IF;
  IF (to_jsonb(NEW)-ARRAY['phase','status','error','updated_at','run_id',
        'prior_selection_digest','candidate_selection_digest']) IS DISTINCT FROM
     (to_jsonb(OLD)-ARRAY['phase','status','error','updated_at','run_id',
        'prior_selection_digest','candidate_selection_digest']) THEN
    RAISE EXCEPTION 'Accepted daily preparation is immutable';
  END IF;
  IF OLD.run_id IS NOT NULL AND NEW.run_id IS DISTINCT FROM OLD.run_id THEN
    RAISE EXCEPTION 'Accepted daily run cannot be rebound';
  END IF;
 END IF;
 IF TG_OP='DELETE' THEN RETURN OLD; END IF;
 RETURN NEW;
END $$;
REVOKE ALL ON FUNCTION mta.accepted_daily_seal() FROM PUBLIC;
CREATE TRIGGER accepted_daily_seal BEFORE UPDATE OR DELETE ON mta.fresh_mta_dailyfeedattempt
FOR EACH ROW EXECUTE FUNCTION mta.accepted_daily_seal();
"""


class Migration(migrations.Migration):
    dependencies = [('fresh_mta','0150_ingestion_typed_batch_guards')]
    operations = [migrations.RunSQL(SQL, 'DROP TRIGGER accepted_daily_seal ON mta.fresh_mta_dailyfeedattempt; '
                                   'DROP FUNCTION mta.accepted_daily_seal();')]
