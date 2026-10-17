"""Register exact native operational configuration through existing typed owners."""
import hashlib
import json
from pathlib import Path
from uuid import UUID
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

CONFIGURATION_KEYS = frozenset(('source_digest', 'bindings', 'settings', 'tables', 'alerts'))


def _ordered(rows, fields, name):
    if (not isinstance(rows, list) or any(not isinstance(row, dict) or set(row) != fields for row in rows)
            or [row['ordinal'] for row in rows] != list(range(len(rows)))):
        raise ValueError('Exact ordered ' + name + ' roster required')


def read_configuration(path, expected_sha):
    raw = Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_sha:
        raise ValueError('Bound configuration SHA256 differs')
    value = json.loads(raw)
    if not isinstance(value, dict) or set(value) != CONFIGURATION_KEYS:
        raise ValueError('Exact operation configuration required')
    if (not isinstance(value['source_digest'], str) or len(value['source_digest']) != 64
            or not isinstance(value['bindings'], dict)):
        raise ValueError('Explicit source and bindings required')
    if '$FIRST_RUN_INPUT_DIGEST' in json.dumps(value):
        raise ValueError('Configuration placeholders are not supported')
    _ordered(value['settings'], {'ordinal', 'name', 'value'}, 'setting')
    _ordered(value['tables'], {'ordinal', 'database_name', 'table_name', 'condition'}, 'table')
    _ordered(value['alerts'], {'ordinal', 'name', 'active'}, 'alert')
    return value


class Command(BaseCommand):
    help = __doc__

    def add_arguments(self, parser):
        parser.add_argument('--configuration', type=Path, required=True)
        for name in ('sha256', 'run-id', 'input-digest', 'output-digest', 'mdm-source-digest'):
            parser.add_argument('--' + name, required=True)

    def handle(self, *args, **options):
        try:
            value = read_configuration(options['configuration'], options['sha256'])
            UUID(options['run_id'])
            from mta.runtime.models import CalculationRun
            run = CalculationRun.objects.select_related('mdm_input_capture__source').get(pk=options['run_id'])
            if (run.kind != 'DAILY_CHAIN' or run.status != 'SUCCEEDED' or run.evidence_mode != 'production'
                    or run.input_digest != options['input_digest'] or run.output_digest != options['output_digest']):
                raise ValueError('Exact succeeded native run identity required')
            source = run.mdm_input_capture.source
            from mta.mdm.initialization_contract import SOURCE_SCHEMA
            namespace = source.receipt.get('owned_namespace')
            if (source.receipt.get('schema') != SOURCE_SCHEMA or source.digest != options['mdm_source_digest']
                    or not isinstance(namespace, dict) or source.database_name != namespace.get('database_name')):
                raise ValueError('Exact native source/namespace required')
            from mta.mdm.production_families import require_binding
            require_binding(source, read_only=True)
            from mta.runtime.services import read_outputs
            read_outputs(run)
            if value['bindings'].get('opening_input_digest') != run.input_digest:
                raise ValueError('Configuration must bind the actual native opening input')
            # Reuse the existing finite operation/tool contract before any registration.
            from mta.runtime.operational_runner import validate_configuration
            from mta.runtime.operational_attempts import register_configuration, configuration_value
            from mta.runtime.operational_attempts import POLICY
            from mta.serialization import digest
            expected = {'policy': POLICY, **value}
            expected_identity = digest(expected)
            # Validate finite runner/ZIP metadata before the existing typed owner.
            from mta.runtime.operational_runner import RUNNER_POLICY, ROSTER
            tool = value['bindings'].get('zip_tool')
            if (value['bindings'].get('runner_policy') != RUNNER_POLICY
                    or value['bindings'].get('operation_roster') != ROSTER
                    or not isinstance(tool, dict) or set(tool) != {'path','sha256'}
                    or not isinstance(tool['path'], str) or not Path(tool['path']).is_absolute()
                    or not isinstance(tool['sha256'], str) or len(tool['sha256']) != 64):
                raise ValueError('Exact native operational runner and pinned ZIP tool required')
            with transaction.atomic():
                owner = register_configuration(**value)
                installed = configuration_value(owner)
                if installed != expected or str(owner.pk) != expected_identity:
                    raise ValueError('Registered operation configuration differs')
                validate_configuration(owner)
            self.stdout.write(json.dumps(dict(configuration_id=str(owner.pk),
                configuration_source_sha256=options['sha256'], run_id=str(run.pk),
                input_digest=run.input_digest, output_digest=run.output_digest,
                mdm_source_digest=source.digest, configuration=installed), sort_keys=True))
        except Exception as error:
            raise CommandError(str(error)) from error
