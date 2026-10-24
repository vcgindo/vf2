"""Resolve the phase-name ambiguity found by the first migrated row proof."""
from importlib import import_module
from django.db import migrations

_original = import_module('mta.runtime.migrations.0172_phase_snapshot_rows').SQL
_body = _original.split('CREATE FUNCTION mta.guard_phase_rows()', 1)[1].split('$guard$;', 1)[0]
_corrected = _body.replace('phase text;', 'target_phase text;').replace(
    "phase=split_part(item.image,'/',2);", "target_phase=split_part(item.image,'/',2);").replace(
    'S.phase=phase)', 'S.phase=target_phase)')
FORWARD = 'CREATE OR REPLACE FUNCTION mta.guard_phase_rows()'+_corrected+'$guard$;'
REVERSE = 'CREATE OR REPLACE FUNCTION mta.guard_phase_rows()'+_body+'$guard$;'


class Migration(migrations.Migration):
    dependencies = [('fresh_mta', '0172_phase_snapshot_rows')]
    operations = [migrations.RunSQL(FORWARD, REVERSE)]
