"""Explicit optional input procedure; never part of installation or startup.

**DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.**
"""
import argparse
import hashlib
import json
from pathlib import Path


def inspect_input(path):
    manifest = json.loads(Path(__file__).with_name('optional-initialization.json').read_text())
    raw = Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != manifest['input_sha256']:
        raise ValueError('Optional input identity differs; substitution is prohibited')
    from mta.mdm.initialization_contract import decode
    decode(raw, manifest['input_sha256'], expected_configuration=manifest['configuration_digest'],
           expected_recipe=manifest['recipe_digest'])
    return manifest


def initialize(path, *, apply=False):
    import os
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'release.mta_settings')
    import django
    django.setup()
    manifest = inspect_input(path)
    if not apply:
        from django.core.management import call_command
        call_command('initialize_production', str(path), sha256=manifest['input_sha256'],
            configuration_digest=manifest['configuration_digest'],
            recipe_digest=manifest['recipe_digest'], inspect=True)
        return dict(status='OPTIONAL_INPUT_INSPECTED_NOT_APPLIED', accepted_day=False)
    from django.db import transaction, connection
    from mta.runtime.models import ProductionInitialization, MdmSource, CalculationRun
    from mta.runtime.mdm_models import MdmTask, MdmSubTask, MdmDraft
    from mta.runtime.mdm_daily_models import MdmDailyInputCapture
    from mta.mdm.initialization import initialize as native_initialize
    from mta.mdm.production_families import bootstrap_native_families
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_xact_lock(hashtextextended('fresh.production.initialization',0))")
        if any(model.objects.exists() for model in (ProductionInitialization, MdmSource,
                CalculationRun, MdmDailyInputCapture, MdmTask, MdmSubTask, MdmDraft)):
            raise ValueError('Optional procedure requires untouched target; second apply refused')
        owner, created = native_initialize(Path(path).read_bytes(), manifest['input_sha256'],
            expected_configuration=manifest['configuration_digest'], expected_recipe=manifest['recipe_digest'])
        if not created:
            raise ValueError('Optional procedure must create exactly one initialization')
        bootstrap_native_families(owner)
    return dict(status='OPTIONAL_INITIALIZATION_ONLY', opening_id=str(owner.pk),
        source_digest=owner.source.digest, opening_date=owner.opening_date.isoformat(),
        input_sha256=owner.input_sha256, configuration_digest=owner.configuration_digest,
        recipe_digest=owner.recipe_sha256, implementation_digest=owner.implementation_digest,
        content_digest=owner.input_digest, receipt_digest=owner.receipt_digest, accepted_day=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    print(json.dumps(initialize(args.input, apply=args.apply), sort_keys=True))
