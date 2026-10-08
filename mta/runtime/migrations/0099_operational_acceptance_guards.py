"""Receipt-backed activation, atomic pair and append-only qualification evidence.

Required on fresh and upgraded PostgreSQL. No legacy or accepted data rewrite.
"""
from importlib import import_module
from django.db import migrations

PREVIOUS = import_module('mta.runtime.migrations.0097_cohort3_activation_lineage').FORWARD
PARITY = "R.parity_summary->>'status' IN ('PASS','PASS_WITH_LEGACY_FLAWS')"
OPERATIONAL = """EXISTS (
 SELECT 1 FROM mta.fresh_mta_operationalacceptance A
 WHERE A.run_id=R.id AND A.policy='supported-synthetic-operational-v1'
 AND A.receipt_digest=current_setting('fresh.operational_daily_activation',true)
 AND A.input_digest=R.input_digest AND A.input_manifest_digest=R.input_manifest_digest
 AND A.output_digest=R.output_digest AND A.production_digest=R.production_digest
 AND A.execution_revision=R.execution_revision
 AND A.predecessor_id IS NOT DISTINCT FROM R.predecessor_id
 AND A.publication_seal=P.seal_digest AND A.publication_seal=NEW.publication_seal
 AND A.configuration_digest=NEW.configuration_digest AND A.layers_digest=NEW.layers_digest
 AND A.permissions_digest=NEW.permissions_digest AND A.hierarchy_digest=NEW.hierarchy_digest
 AND A.activation_digest=NEW.activation_digest
 AND A.btr_generation::text=P.layers->'btr'->'receipt'->>'generation')"""
ACTIVATION = PREVIOUS.replace(PARITY, '(' + PARITY + ' OR ' + OPERATIONAL + ')', 1)

FORWARD = """
CREATE FUNCTION mta.guard_operational_acceptance() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF current_setting('fresh.operational_acceptance',true) IS DISTINCT FROM NEW.run_id::text THEN
  RAISE EXCEPTION 'Explicit verified operational acceptance owner required'; END IF;
 IF EXISTS (SELECT 1 FROM jsonb_each_text(to_jsonb(NEW)) E
   WHERE (E.key LIKE '%digest' OR E.key='publication_seal') AND E.value !~ '^[0-9a-f]{64}$') THEN
  RAISE EXCEPTION 'Operational acceptance digest shape differs'; END IF;
 PERFORM 1 FROM mta.fresh_mta_calculationrun R
 JOIN mta.fresh_mta_dailyuipublication P ON P.run_id=R.id
 JOIN mta.fresh_mta_operationalattempt O ON O.id=NEW.attempt_id
 WHERE R.id=NEW.run_id AND R.kind='DAILY_CHAIN' AND R.status='SUCCEEDED'
 AND R.input_payload->>'schema'='fresh-daily-input-manifest-v2'
 AND R.input_digest=NEW.input_digest AND R.input_manifest_digest=NEW.input_manifest_digest
 AND R.output_digest=NEW.output_digest AND R.production_digest=NEW.production_digest
 AND R.execution_revision=NEW.execution_revision
 AND R.predecessor_id IS NOT DISTINCT FROM NEW.predecessor_id
 AND P.status='READY' AND P.output_digest=R.output_digest AND P.seal_digest=NEW.publication_seal
 AND P.layers->'btr'->'receipt'->>'generation'=NEW.btr_generation::text
 AND O.run_id=R.id AND O.status='SUCCEEDED' AND O.repair_of_id IS NULL
 AND O.run_output_digest=R.output_digest AND O.business_date=R.business_date
 AND O.action_digest=NEW.action_digest AND O.configuration_id=NEW.operational_configuration_digest
 AND ((R.predecessor_id IS NULL AND O.predecessor_id IS NULL) OR EXISTS (
  SELECT 1 FROM mta.fresh_mta_operationalacceptance A
  JOIN mta.fresh_mta_calculationrun PR ON PR.id=A.run_id
  WHERE A.run_id=R.predecessor_id AND O.predecessor_id=A.attempt_id
  AND A.policy=NEW.policy AND PR.business_date=R.business_date-1))
 AND (NEW.repair_id IS NULL OR EXISTS (
  SELECT 1 FROM mta.fresh_mta_operationalattempt X WHERE X.id=NEW.repair_id
  AND X.run_id=R.id AND X.repair_of_id=O.id AND X.status='SUCCEEDED'
  AND X.configuration_id=O.configuration_id AND X.run_output_digest=O.run_output_digest
  AND X.action_digest=O.action_digest AND X.source_digest=O.source_digest
  AND X.business_date=O.business_date AND X.predecessor_id IS NOT DISTINCT FROM O.predecessor_id))
 AND (SELECT array_agg(E."group" ORDER BY E.ordinal) FROM mta.fresh_mta_operationaloperation E
      WHERE E.attempt_id=O.id AND E.status='SUCCEEDED')=ARRAY['O3','O2','O1','O4','O5','O6','O7','O8','O9']::varchar[]
 AND (SELECT count(*) FROM mta.fresh_mta_operationaloperation E WHERE E.attempt_id=O.id)=9;
 IF NOT FOUND THEN RAISE EXCEPTION 'Complete matching operational acceptance owners required'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER operational_acceptance_insert BEFORE INSERT ON mta.fresh_mta_operationalacceptance
 FOR EACH ROW EXECUTE FUNCTION mta.guard_operational_acceptance();
CREATE TRIGGER operational_acceptance_immutable BEFORE UPDATE OR DELETE OR TRUNCATE ON mta.fresh_mta_operationalacceptance
 FOR EACH STATEMENT EXECUTE FUNCTION mta.deny_daily_source_mutation();
CREATE FUNCTION mta.require_operational_acceptance_activation() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 PERFORM 1 FROM mta.fresh_mta_dailyuiactivation D WHERE D.publication_id=NEW.run_id
 AND D.publication_seal=NEW.publication_seal AND D.configuration_digest=NEW.configuration_digest
 AND D.layers_digest=NEW.layers_digest AND D.permissions_digest=NEW.permissions_digest
 AND D.hierarchy_digest=NEW.hierarchy_digest AND D.activation_digest=NEW.activation_digest;
 IF NOT FOUND THEN RAISE EXCEPTION 'Operational acceptance and activation must commit together'; END IF;
 RETURN NEW;
END $$;
CREATE CONSTRAINT TRIGGER operational_acceptance_pair AFTER INSERT ON mta.fresh_mta_operationalacceptance
 DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION mta.require_operational_acceptance_activation();
""" + ACTIVATION

REVERSE = PREVIOUS + """
DROP TRIGGER operational_acceptance_pair ON mta.fresh_mta_operationalacceptance;
DROP FUNCTION mta.require_operational_acceptance_activation();
DROP TRIGGER operational_acceptance_insert ON mta.fresh_mta_operationalacceptance;
DROP TRIGGER operational_acceptance_immutable ON mta.fresh_mta_operationalacceptance;
DROP FUNCTION mta.guard_operational_acceptance();
"""


class Migration(migrations.Migration):
    dependencies = [('fresh_mta', '0098_operational_acceptance')]
    operations = [migrations.RunSQL(FORWARD, REVERSE)]
