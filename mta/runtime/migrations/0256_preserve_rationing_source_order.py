"""Retain the admitted opening column order and its inherited daily descriptor."""
from importlib import import_module
import json

from django.db import migrations


prior = import_module('mta.runtime.migrations.0253_anchor_final_initialization')
shape_sql = import_module('mta.runtime.migrations.0251_operational_cut_qualification').SQL
exact = import_module('mta.runtime.migrations.0231_runtime_report_placement_guards').exact
roster = json.loads(shape_sql.split("roster constant jsonb='", 1)[1].split("';", 1)[0])
names = json.dumps([name for name, _ in roster])

# For an inherited representation, validate exactly the same names and types by
# passing the descriptors in schema order to the original strict predicate.
# Anchor provenance below still compares the complete original descriptor.
original = "mta.rationing_fields_valid(b->'fields',(b->>'count')::bigint) IS NOT TRUE"
extended = f"""({original} AND NOT coalesce((
   (c.position=0 OR
    (SELECT jsonb_agg(d->0 ORDER BY n) FROM jsonb_array_elements(b->'fields') WITH ORDINALITY X(d,n))
    =(SELECT jsonb_agg(d->0 ORDER BY n) FROM mta.fresh_mta_operationalstatecut parent,
      LATERAL jsonb_array_elements(parent.root_body::jsonb->'fields') WITH ORDINALITY X(d,n)
      WHERE parent.id=c.parent_id))
   AND mta.rationing_fields_valid((
    SELECT jsonb_agg(d ORDER BY N.ordinal)
    FROM jsonb_array_elements(b->'fields') X(d)
    LEFT JOIN jsonb_array_elements('{names}'::jsonb) WITH ORDINALITY N(name,ordinal)
      ON d->0=N.name), (b->>'count')::bigint)),false))"""
assert prior.SQL.count(original) == 1
SQL = prior.SQL.replace(original, extended)
SIGNATURE = 'mta.require_state_cut_seal()'
REVERSE = """
DO $check$ BEGIN
 IF EXISTS(SELECT 1 FROM mta.fresh_mta_operationalstatecut
           WHERE NOT mta.rationing_fields_valid(root_body::jsonb->'fields',(root_body::jsonb->>'count')::bigint))
 THEN RAISE EXCEPTION 'Accepted source column order requires a compatible release'; END IF;
END $check$;
"""


class Migration(migrations.Migration):
    dependencies = [('fresh_mta', '0255_postbtr_rationing_reference')]
    operations = [migrations.RunSQL(exact(SIGNATURE, prior.SQL.split('$$')[1]) + SQL,
                                   REVERSE + exact(SIGNATURE, SQL.split('$$')[1]) + prior.SQL)]
