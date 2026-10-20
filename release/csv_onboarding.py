"""Finish an exact existing CSV opening using the image's native operations.

Host-mounted operator, like daily_serving_check: never replace sealed image code.
DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path


def reconcile(receipt, input_directory=None):
    from django.db import connection
    from mta.runtime.models import ProductionInitialization, CalculationRun
    from mta.runtime.mdm_daily_models import MdmDailyInputCapture
    from mta.mdm.owned_namespace import _registered_identity, _receipt_identity
    if ProductionInitialization.objects.count() != 1:
        raise ValueError('Expected the one recorded initialization; no loading or replacement performed')
    initial = ProductionInitialization.objects.select_related('source').get()
    recorded = receipt['initialization']
    fields = dict(opening_id=str(initial.pk), source_digest=initial.source.digest,
                  input_sha256=initial.input_sha256)
    if any(recorded.get(key) != value for key, value in fields.items()):
        raise ValueError('Onboarding receipt belongs to another initialization; preserve both and use its matching state directory')
    with connection.cursor() as cursor:
        cursor.execute('SELECT current_database(),oid::bigint FROM pg_database WHERE datname=current_database()')
        database, oid = cursor.fetchone()
        namespace = _receipt_identity(_registered_identity(cursor))['registration_id']
    registration = receipt['registration']
    if (registration.get('database'), registration.get('database_oid'),
            registration.get('namespace')) != (database, oid, namespace):
        raise ValueError('Onboarding receipt belongs to another database/namespace; no state changed')
    if CalculationRun.objects.exists() or MdmDailyInputCapture.objects.exists():
        raise ValueError('Daily work already exists; use csv-day, never repeat onboarding')
    if input_directory is not None:
        root = Path(input_directory)
        pins = {name: hashlib.sha256((root / name).read_bytes()).hexdigest()
                for name in ('binding-template.json', 'permissions.json')}
        if receipt.get('pack_pins') is not None:
            if receipt['pack_pins'] != pins:
                raise ValueError('Opening binding/access files changed; preserve the recorded configuration')
        else:
            # Compatibility with pre-fix receipts: recover their pins from the
            # already-bound files and active Compose access pin, never adopt a
            # changed template/access catalogue just because the DB matches.
            from django.conf import settings
            template = json.loads((root / 'binding-template.json').read_text())
            template.update(initialization_id=str(initial.pk), source_digest=initial.source.digest)
            if (json.loads((root / 'binding.json').read_text()) != template
                    or pins['permissions.json'] != settings.VF_MTA_PERMISSIONS_SHA256):
                raise ValueError('Existing binding/access configuration differs; cannot resume automatically')
    return initial


def complete(receipt, *, inspect=False, input_directory=None):
    from release.native_identity import require_current
    require_current()
    initial = reconcile(receipt, input_directory)
    if not inspect:
        from mta.mdm.production_families import bootstrap_native_families
        from mta.mdm.families import installed_ids
        bootstrap_native_families(initial)
        if installed_ids(initial.source, read_only=True) != list(range(1, 14)):
            raise ValueError('Native MDM family completion is incomplete')
    return dict(status='OPENING_RECONCILED' if inspect else 'MDM_FAMILIES_READY',
                opening_id=str(initial.pk), source_digest=initial.source.digest,
                input_sha256=initial.input_sha256, accepted_day=False)


def check():
    from mta.presentation.installation_metadata import require_installation
    from mta.mdm.families import installed_ids
    from urllib.error import HTTPError
    import urllib.request
    source = require_installation()
    if source is None or installed_ids(source, read_only=True) != list(range(1, 14)):
        raise ValueError('Initialized master serving is incomplete')
    for path, body in (('GetAllReports', None),
                       ('GetMasterUIConfiguration', b'{"screenType":"MDM"}')):
        request = urllib.request.Request('http://127.0.0.1:8000/api/mta/' + path,
            data=body, headers={'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                json.load(response)
        except HTTPError as exc:
            # These private endpoints must reach the unchanged gateway identity
            # guard (403), not fail native installation admission (503).
            if exc.code != 403 or json.load(exc) != {'error': 'gateway_identity_required'}:
                raise
        else:
            raise ValueError('Private metadata unexpectedly admitted an unauthenticated request')
    return dict(status='INITIALIZED_MASTER_SERVING_READY', families=list(range(1, 14)),
                source_digest=source.digest, gateway_identity_required=True, accepted_day=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('inspect', 'complete', 'check'))
    parser.add_argument('--receipt')
    parser.add_argument('--input-directory')
    args = parser.parse_args()
    import runpy
    identity = Path('/opt/vectorflow/release.json')
    if identity.exists():
        runpy.run_path(str(identity.with_name('image_entrypoint.py')))['configure'](identity)
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'release.mta_settings')
    import django
    django.setup()
    if args.operation == 'check':
        result = check()
    else:
        result = complete(json.loads(Path(args.receipt).read_text(encoding='utf-8-sig')),
                          inspect=args.operation == 'inspect', input_directory=args.input_directory)
    print(json.dumps(result, sort_keys=True))
