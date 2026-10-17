"""Register one exact Cohort6 operation configuration after the first run."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from uuid import UUID

from django.core.management.base import BaseCommand, CommandError


CONFIGURATION_KEYS = frozenset(
    ('source_digest', 'bindings', 'settings', 'tables', 'alerts'))
PLACEHOLDER = '$FIRST_RUN_INPUT_DIGEST'
RUN_RECEIPT_KEYS = frozenset((
    'status', 'run_id', 'business_date', 'input_digest', 'output_digest',
    'validation_digest', 'evidence_mode', 'seconds', 'publication',
))


def _read(path, expected_sha=None):
    raw = Path(path).read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    if expected_sha is not None and actual != expected_sha:
        raise ValueError('Bound configuration SHA256 differs')
    try:
        return json.loads(raw), actual
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError('Bound file is not valid JSON') from error


def _ordered(rows, fields, name):
    if (not isinstance(rows, list)
            or any(not isinstance(row, dict) or set(row) != fields
                   for row in rows)
            or [row['ordinal'] for row in rows] != list(range(len(rows)))):
        raise ValueError('Exact ordered ' + name + ' roster required')


def configuration_value(path, expected_sha, input_digest):
    value, source_sha = _read(path, expected_sha)
    if (not isinstance(value, dict) or set(value) != CONFIGURATION_KEYS
            or not isinstance(value['source_digest'], str)
            or len(value['source_digest']) != 64
            or not isinstance(value['bindings'], dict)):
        raise ValueError('Exact Cohort6 operation configuration required')
    occurrences = sum(item == PLACEHOLDER for item in _walk(value))
    if (value['bindings'].get('opening_input_digest') != PLACEHOLDER
            or occurrences != 1):
        raise ValueError('Unique first-run input placeholder required')
    _ordered(value['settings'], {'ordinal', 'name', 'value'}, 'setting')
    _ordered(value['tables'],
             {'ordinal', 'database_name', 'table_name', 'condition'}, 'table')
    _ordered(value['alerts'], {'ordinal', 'name', 'active'}, 'alert')
    result = deepcopy(value)
    result['bindings']['opening_input_digest'] = input_digest
    return result, source_sha


def _walk(value):
    if isinstance(value, dict):
        for item in value.values():
            yield from _walk(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk(item)
    else:
        yield value


def first_run_receipt(path):
    value, receipt_sha = _read(path)
    if (not isinstance(value, dict) or set(value) != RUN_RECEIPT_KEYS
            or value.get('status') != 'SUCCEEDED'
            or value.get('business_date') != '2026-06-06'
            or not isinstance(value.get('run_id'), str) or not value['run_id']
            or any(not isinstance(value.get(name), str) or len(value[name]) != 64
                   for name in ('input_digest', 'output_digest'))
            or not isinstance(value.get('validation_digest'), str)):
        raise ValueError('Exact successful first-day receipt required')
    try:
        UUID(value['run_id'])
    except (ValueError, TypeError, AttributeError) as error:
        raise ValueError('Exact successful first-day receipt required') from error
    return value, receipt_sha


class Command(BaseCommand):
    help = __doc__

    def add_arguments(self, parser):
        parser.add_argument('--configuration', type=Path, required=True)
        parser.add_argument('--sha256', required=True)
        parser.add_argument('--first-run-receipt', type=Path, required=True)

    def handle(self, *args, **options):
        try:
            receipt, receipt_sha = first_run_receipt(
                options['first_run_receipt'])
            value, configuration_sha = configuration_value(
                options['configuration'], options['sha256'],
                receipt['input_digest'])
            from mta.runtime.models import CalculationRun
            run = CalculationRun.objects.select_related(
                'mdm_input_capture__source').get(pk=receipt['run_id'])
            if (run.kind != 'DAILY_CHAIN' or run.status != 'SUCCEEDED'
                    or str(run.business_date) != '2026-06-06'
                    or run.input_digest != receipt['input_digest']
                    or run.output_digest != receipt['output_digest']):
                raise ValueError('First-day run identity differs from receipt')
            source = run.mdm_input_capture.source
            source_receipt = source.receipt
            namespace = (source_receipt.get('owned_namespace')
                         if isinstance(source_receipt, dict) else None)
            if (not isinstance(namespace, dict)
                    or source.database_name != namespace.get('database_name')):
                raise ValueError('Owned MDM source receipt required')
            from mta.mdm.daily_source import require_binding
            require_binding(source,
                artifact_sha256=source_receipt.get('artifact_sha256'),
                artifact_schema=source_receipt.get('artifact_schema'))
            from mta.runtime.operational_attempts import (
                configuration_value as read_configuration,
                register_configuration,
            )
            owner = register_configuration(**value)
            installed = read_configuration(owner)
            if installed != {'policy': owner.policy, **value}:
                raise ValueError('Registered operation configuration differs')
            result = {
                'configuration_id': str(owner.pk),
                'configuration_digest': str(owner.pk),
                'configuration_source_sha256': configuration_sha,
                'first_run_receipt_sha256': receipt_sha,
                'first_run': {name: receipt[name] for name in
                              ('run_id', 'business_date', 'input_digest',
                               'output_digest')},
                'mdm_source': {'id': str(source.pk), 'digest': source.digest,
                               'database': source.database_name},
                'configuration': installed,
            }
            self.stdout.write(json.dumps(result, sort_keys=True))
        except Exception as error:
            raise CommandError(str(error)) from error
