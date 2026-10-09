"""Explicit masters7–9 ownership from an accepted same-source closing only."""
import hashlib
from pathlib import Path
from django.db import connection, transaction
from mta.mdm.source import DLL
from mta.runtime.mdm_models import MdmFamilySource, MdmSource
from mta.runtime.mdm_daily_models import MdmDailyInputCapture
from mta.runtime.mdm_phase_controls_models import (
    MdmPhaseControlsOwner, MdmPhaseOutQueue, MdmPhaseInNormQueue)
from mta.serialization import digest

SCHEMA = 'fresh-mdm-phase-controls-owner-v1'
FIELDS = {
    'phase_requests': ('SKUCode', 'WhCode', 'PhaseInSKUCode', 'Approved'),
    'phase_in_requests': ('SKUCode', 'WhCode', 'TargetNorm', 'Approved'),
}
QUEUES = {'phase_requests': MdmPhaseOutQueue, 'phase_in_requests': MdmPhaseInNormQueue}


def configuration_sha():
    return hashlib.sha256((Path(__file__).resolve().parents[1] /
                          'config/mdm_phase_controls.json').read_bytes()).hexdigest()


def require_installed(source):
    owner = MdmPhaseControlsOwner.objects.get(source=source)
    from mta.mdm.target_fixture import require_family
    if require_family(source, owner, 'phase_controls'):
        return owner
    p = owner.provenance
    if (source.dll_digest != DLL or p.get('schema') != SCHEMA
            or p.get('source_digest') != source.digest or p.get('dll_digest') != DLL
            or p.get('configuration_sha256') != configuration_sha()
            or digest(p) != owner.receipt_digest):
        raise ValueError('Phase controls source binding differs')
    for master_id in (7, 8, 9):
        family = MdmFamilySource.objects.get(source=source, master_id=master_id)
        if family.receipt != p or family.digest != owner.receipt_digest:
            raise ValueError('Phase controls family binding differs')
    return owner


@transaction.atomic
def bind(source, run):
    from mta.mdm.daily_source import require_binding
    from mta.mdm.supplier_revisions import lock_transaction
    from mta.presentation.context import selected_run
    from mta.runtime.services import read_outputs
    lock_transaction(source.pk)
    source = MdmSource.objects.select_for_update().get(pk=source.pk)
    from mta.mdm.integration_source import require_unsealed
    require_unsealed(source)
    require_binding(source, artifact_sha256=source.receipt['artifact_sha256'],
                    artifact_schema=source.receipt['artifact_schema'])
    if selected_run().pk != run.pk:
        raise ValueError('Phase controls require the accepted selected publication')
    if (MdmPhaseControlsOwner.objects.filter(source=source).exists()
            or MdmFamilySource.objects.filter(source=source, master_id__in=(7, 8, 9)).exists()
            or MdmDailyInputCapture.objects.filter(source=source, status='CAPTURED',
                                                   retries__isnull=True).exists()):
        raise ValueError('Phase controls require new owners and no pending capture')
    MdmDailyInputCapture.objects.get(source=source, run=run, status='CONSUMED')
    if MdmDailyInputCapture.objects.filter(source=source, run__predecessor=run,
                                          run__status='SUCCEEDED').exists():
        raise ValueError('Phase controls cannot bind an earlier predecessor')
    auxiliary = read_outputs(run)['ClosingState'][0]['control_aux']
    rows = {name: auxiliary[name] for name in FIELDS}
    if any(set(r) != set(FIELDS[name]) for name in FIELDS for r in rows[name]):
        raise ValueError('Phase controls closing field roster differs')
    p = dict(schema=SCHEMA, source_digest=source.digest, dll_digest=DLL,
        configuration_sha256=configuration_sha(), run_id=str(run.pk),
        output_digest=run.output_digest, opening_queue_digest=digest(rows))
    owner = MdmPhaseControlsOwner.objects.create(source=source, provenance=p,
        receipt_digest=digest(p), closing_queue_digest=digest(rows), last_run=run)
    for master_id in (7, 8, 9):
        MdmFamilySource.objects.create(source=source, master_id=master_id,
            receipt=p, digest=owner.receipt_digest)
    with connection.cursor() as cursor:
        cursor.execute("SELECT set_config('fresh.phase_controls_install', %s, true)", [str(source.pk)])
    for name, model in QUEUES.items():
        model.objects.bulk_create([model(source=source, **r) for r in rows[name]])
    with connection.cursor() as cursor:
        cursor.execute("SELECT set_config('fresh.phase_controls_install', '', true)")
    return owner
