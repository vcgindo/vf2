"""Stage, inspect or apply the separately selected retained initialization pack.

This operator wrapper refuses any second initialization. The native initializer's
existing explicit re-verification behavior and all calculation contracts remain
unchanged. Namespace registration remains a separate provisioner operation.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path

from mta.serialization import digest


MANIFEST = Path(__file__).with_name('optional-initialization.json')


def read_input(path):
    manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
    raw = Path(path).read_bytes()
    if (manifest['schema'] != 'vectorflow-optional-initialization-v1'
            or len(raw) != manifest['input_bytes']
            or hashlib.sha256(raw).hexdigest() != manifest['input_sha256']):
        raise ValueError('Selected optional initialization bytes differ')
    value = json.loads(raw)
    if (digest(value['configuration']) != manifest['configuration_digest']
            or digest(value['recipe']) != manifest['recipe_digest']
            or value['opening']['identity'] != manifest['opening_identity']
            or value['opening']['date'] != manifest['opening_date']
            or {owner: {table: len(rows) for table, rows in tables.items()}
                for owner, tables in value['masters'].items()} != manifest['master_counts']):
        raise ValueError('Selected optional configuration/recipe/master identity differs')
    return raw, manifest


def stage(path, destination):
    raw, manifest = read_input(path)
    destination = Path(destination)
    root = Path('/var/lib/vectorflow').resolve()
    if not destination.is_absolute() or not destination.resolve().is_relative_to(root):
        raise ValueError('Stage destination must be inside the owned mta_data volume')
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Never overwrite a previous transfer, including a partial or identical one.
    with destination.open('xb') as stream:
        stream.write(raw)
    if hashlib.sha256(destination.read_bytes()).hexdigest() != manifest['input_sha256']:
        raise ValueError('Transferred initialization identity differs; preserve failed transfer')
    return dict(status='OPTIONAL_INPUT_STAGED_NO_DATABASE_CHANGE', path=str(destination),
                input_sha256=manifest['input_sha256'], configuration_digest=manifest['configuration_digest'],
                recipe_digest=manifest['recipe_digest'])


def require_empty():
    from mta.runtime.models import ProductionInitialization, MdmSource, CalculationRun
    from mta.runtime.mdm_models import MdmTask, MdmSubTask
    from mta.runtime.mdm_daily_models import MdmDailyInputCapture
    if any(model.objects.exists() for model in (ProductionInitialization, MdmSource,
            CalculationRun, MdmTask, MdmSubTask, MdmDailyInputCapture)):
        raise ValueError('Optional bootstrap requires an untouched instance; second initialization is refused')


def initialize(path, *, apply=False):
    raw, manifest = read_input(path)
    import django
    django.setup()
    from django.core.management import call_command
    from django.db import connection, transaction
    from mta.runtime.models import ProductionInitialization, CalculationRun
    from mta.mdm.production_families import bootstrap_native_families, require_binding
    require_empty()
    arguments = dict(sha256=manifest['input_sha256'], configuration_digest=manifest['configuration_digest'],
                     recipe_digest=manifest['recipe_digest'])
    report = io.StringIO()
    call_command('initialize_production', str(path), inspect=True, stdout=report, **arguments)
    inspected = json.loads(report.getvalue())
    if not apply:
        return dict(status='OPTIONAL_INITIALIZATION_INSPECTED_NOT_APPLIED',
                    input_sha256=manifest['input_sha256'], inspection=inspected)
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_xact_lock(hashtextextended('fresh.production.initialization',0))")
        require_empty()
        receipt = io.StringIO()
        call_command('initialize_production', str(path), stdout=receipt, **arguments)
        value = json.loads(receipt.getvalue())
        if value['status'] != 'INITIALIZED':
            raise ValueError('Second initialization cannot be accepted by this wrapper')
        owner = ProductionInitialization.objects.select_related('source').get(pk=value['opening_id'])
        # Existing typed opening projection, normally also used before day one.
        # No execute_day, capture, recommendation or publication is invoked.
        seal = bootstrap_native_families(owner)
        require_binding(owner.source, read_only=True)
        if CalculationRun.objects.exists():
            raise ValueError('Initialization-only operation must not create a day')
        value.update(status='OPTIONAL_INITIALIZATION_APPLIED_NO_DAY',
                     integration_digest=seal.digest, accepted_day=False)
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--stage-to', type=Path)
    action.add_argument('--inspect', action='store_true')
    action.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    result = stage(args.input, args.stage_to) if args.stage_to else initialize(args.input, apply=args.apply)
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
