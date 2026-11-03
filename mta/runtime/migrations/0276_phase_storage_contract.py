"""Separate immutable phase implementation provenance from its logical contract."""
from importlib import import_module
from django.db import migrations

# Frozen migration literals: never import the mutable application contract.
LEGACY_RECIPE = '2b307bcb0cad7f75cf0f2273938cd072fb4b25fe1191252691cb6e113873fc7c'
LOGICAL = '938547791982517980a4febf79022f299645040f0e41a364b49db70c1d73b774'
ORIGINAL = import_module('mta.runtime.migrations.0177_scope_acceptance_guards')._snapshot

CONTRACT = r'''
CREATE FUNCTION mta.phase_logical_contract(code text, manifest jsonb) RETURNS text
LANGUAGE sql IMMUTABLE STRICT SET search_path=pg_catalog,mta AS $contract$
 SELECT CASE
  WHEN manifest->>'schema' IS DISTINCT FROM 'fresh-native-phase-state-v1'
    OR code !~ '^[0-9a-f]{64}$' THEN NULL
  WHEN NOT manifest ? 'phase_contract' AND NOT manifest ? 'storage_format'
    AND code='LEGACY_RECIPE' THEN 'LOGICAL'
  WHEN code<>'LEGACY_RECIPE'
    AND manifest->'phase_contract'=jsonb_build_object(
      'schema','fresh-native-phase-logical-contract-v1','digest','LOGICAL')
    AND manifest->>'storage_format'='fresh-phase-image-references-v2' THEN 'LOGICAL'
  ELSE NULL END
$contract$;
REVOKE ALL ON FUNCTION mta.phase_logical_contract(text,jsonb) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION mta.phase_logical_contract(text,jsonb) TO vectorflow_mta_owner;
'''.replace('LEGACY_RECIPE', LEGACY_RECIPE).replace('LOGICAL', LOGICAL)

assert ORIGINAL.count('predecessor.recipe_digest<>NEW.recipe_digest') == 2
assert ORIGINAL.count("OR NEW.recipe_digest !~ '^[0-9a-f]{64}$'") == 1
UPDATED = ORIGINAL.replace('predecessor.recipe_digest<>NEW.recipe_digest',
    'mta.phase_logical_contract(predecessor.recipe_digest,predecessor.manifest) IS DISTINCT FROM '
    'mta.phase_logical_contract(NEW.recipe_digest,NEW.manifest)').replace(
    "OR NEW.recipe_digest !~ '^[0-9a-f]{64}$'",
    "OR mta.phase_logical_contract(NEW.recipe_digest,NEW.manifest) IS NULL "
    "OR NEW.recipe_digest !~ '^[0-9a-f]{64}$'")
SQL = CONTRACT+'CREATE OR REPLACE FUNCTION mta.guard_phase_snapshot()'+UPDATED+'$guard$;'


class Migration(migrations.Migration):
    dependencies = [('fresh_mta', '0275_history_family_name_width')]
    # Once a new-format child exists, reverting the old guard is not a safe
    # rollback strategy. Preserve the failed upgrade journal and typed prefix.
    operations = [migrations.RunSQL(SQL)]
