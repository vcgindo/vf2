"""Pin the qualified activation predecessor and repair tuple at insert time."""
from importlib import import_module
from django.db import migrations

PREVIOUS = import_module('mta.runtime.migrations.0096_cohort3_qualified_activation').FORWARD
FORWARD = PREVIOUS.replace(
    "R.id='77731d95-03f4-4a82-8498-404f944df73b'::uuid AND",
    "R.id='77731d95-03f4-4a82-8498-404f944df73b'::uuid AND R.predecessor_id IS NULL AND", 1).replace(
    "R.id='1b83fdca-d0ad-47d5-8694-414257ae68be'::uuid AND",
    "R.id='1b83fdca-d0ad-47d5-8694-414257ae68be'::uuid AND R.predecessor_id='77731d95-03f4-4a82-8498-404f944df73b'::uuid AND", 1).replace(
    "O.id='e0918a5d-2ce5-489a-8ef5-32b9ce605e88'::uuid AND",
    "O.id='e0918a5d-2ce5-489a-8ef5-32b9ce605e88'::uuid AND O.predecessor_id IS NULL AND", 1).replace(
    "O.id='2a6dbb31-3d1a-4f7b-aa55-6f710f85fc7d'::uuid AND",
    "O.id='2a6dbb31-3d1a-4f7b-aa55-6f710f85fc7d'::uuid AND O.predecessor_id='e0918a5d-2ce5-489a-8ef5-32b9ce605e88'::uuid AND", 1).replace(
    "AND X.run_id=R.id AND",
    "AND X.run_id=R.id AND X.predecessor_id IS NOT DISTINCT FROM O.predecessor_id AND X.run_output_digest=R.output_digest AND X.business_date=R.business_date AND")


class Migration(migrations.Migration):
    dependencies = [('fresh_mta', '0096_cohort3_qualified_activation')]
    operations = [migrations.RunSQL(FORWARD, PREVIOUS)]
