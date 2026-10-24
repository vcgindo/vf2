"""JSONB numeric equality must not admit fractional revision counters."""
from django.db import migrations

SQL=r'''
CREATE FUNCTION mta.guard_scope_cut_types() RETURNS trigger LANGUAGE plpgsql
 SET search_path=pg_catalog,mta AS $guard$
DECLARE item jsonb;
BEGIN
 IF TG_TABLE_NAME='fresh_mta_runscopeattempt' THEN
  FOR item IN SELECT NEW.revision_before UNION ALL SELECT NEW.revision_after UNION ALL SELECT NEW.revision_closed LOOP
   IF item IS NOT NULL AND NOT coalesce(mta.valid_scope_cut(item),false) THEN
    RAISE EXCEPTION 'Scoped header requires an exact integer revision cut'; END IF;
  END LOOP;
 ELSE
  IF NEW.revision_before IS NOT NULL AND NOT coalesce(mta.valid_scope_cut(NEW.revision_before),false)
   OR NEW.metadata ? 'revision_after' AND NOT coalesce(mta.valid_scope_cut(NEW.metadata->'revision_after'),false) THEN
   RAISE EXCEPTION 'Scoped phase requires an exact integer revision cut'; END IF;
 END IF;
 RETURN NEW;
END
$guard$;
REVOKE ALL ON FUNCTION mta.guard_scope_cut_types() FROM PUBLIC;
CREATE TRIGGER scope_attempt_cut_types BEFORE INSERT OR UPDATE ON mta.fresh_mta_runscopeattempt
 FOR EACH ROW EXECUTE FUNCTION mta.guard_scope_cut_types();
CREATE TRIGGER phase_acceptance_cut_types BEFORE INSERT OR UPDATE ON mta.fresh_mta_runphaseacceptance
 FOR EACH ROW EXECUTE FUNCTION mta.guard_scope_cut_types();
'''
REVERSE='''
DROP TRIGGER scope_attempt_cut_types ON mta.fresh_mta_runscopeattempt;
DROP TRIGGER phase_acceptance_cut_types ON mta.fresh_mta_runphaseacceptance;
DROP FUNCTION mta.guard_scope_cut_types();
'''


class Migration(migrations.Migration):
    dependencies=[('fresh_mta','0184_invalidated_scope_counter_freeze')]
    operations=[migrations.RunSQL(SQL,REVERSE)]
