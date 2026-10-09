"""Bind master6 to an existing accepted, same-source daily publication.

This does not manufacture a source, profile, opening or publication acceptance.
No installed environment is automatically opted in by deploying this module.
"""
import hashlib
from pathlib import Path
from django.db import connection, transaction
from mta.mdm.source import DLL
from mta.runtime.mdm_models import MdmFamilySource, MdmSource
from mta.runtime.mdm_daily_models import MdmDailyInputCapture
from mta.runtime.mdm_stop_pipo_models import MdmStopPipoOwner, MdmStopPipoQueue
from mta.serialization import digest

SCHEMA = 'fresh-mdm-stop-pipo-owner-v1'


def configuration_sha():
    return hashlib.sha256((Path(__file__).resolve().parents[1] /
                          'config/mdm_stop_pipo.json').read_bytes()).hexdigest()


def require_installed(source):
    owner = MdmStopPipoOwner.objects.get(source=source)
    from mta.mdm.target_fixture import require_family
    if require_family(source, owner, 'stop_pipo'):
        return owner
    p = owner.provenance
    if (source.dll_digest != DLL or p.get('schema') != SCHEMA
            or p.get('source_digest') != source.digest
            or p.get('configuration_sha256') != configuration_sha()
            or digest(p) != owner.receipt_digest):
        raise ValueError('StopPIPO source binding differs')
    family = MdmFamilySource.objects.get(source=source, master_id=6)
    if family.receipt != p or family.digest != owner.receipt_digest:
        raise ValueError('StopPIPO family binding differs')
    return owner


@transaction.atomic
def bind(source, run):
    """Explicit onboarding from this source's already accepted own closing.

    Existing fixture-only source admission remains fixture-only. In particular,
    this cannot bind an unrelated terminal run to a newly invented MDM source.
    """
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
        raise ValueError('StopPIPO binding requires the explicit accepted publication')
    if (MdmStopPipoOwner.objects.filter(source=source).exists()
            or MdmFamilySource.objects.filter(source=source, master_id=6).exists()
            or MdmDailyInputCapture.objects.filter(source=source, status='CAPTURED',
                                                   retries__isnull=True).exists()):
        raise ValueError('StopPIPO binding requires a fresh family and no pending capture')
    MdmDailyInputCapture.objects.get(run=run, source=source, status='CONSUMED')
    if MdmDailyInputCapture.objects.filter(source=source, run__predecessor=run,
                                          run__status='SUCCEEDED').exists():
        raise ValueError('StopPIPO cannot bind an earlier consumed predecessor')
    closing = read_outputs(run)['ClosingState'][0]
    rows = closing['control_aux']['phase_stops']
    if any(set(r) != {'SKUCode', 'WhCode'} for r in rows):
        raise ValueError('Canonical PhaseOutStop field roster differs')
    p = dict(schema=SCHEMA, source_digest=source.digest, dll_digest=DLL,
        configuration_sha256=configuration_sha(), run_id=str(run.pk),
        output_digest=run.output_digest, opening_queue_digest=digest(rows))
    owner = MdmStopPipoOwner.objects.create(source=source, provenance=p,
        receipt_digest=digest(p), closing_queue_digest=digest(rows), last_run=run)
    MdmFamilySource.objects.create(source=source, master_id=6, receipt=p, digest=owner.receipt_digest)
    with connection.cursor() as cursor:
        cursor.execute("SELECT set_config('fresh.stop_pipo_install', %s, true)", [str(source.pk)])
    MdmStopPipoQueue.objects.bulk_create([MdmStopPipoQueue(source=source, **r) for r in rows])
    with connection.cursor() as cursor:
        cursor.execute("SELECT set_config('fresh.stop_pipo_install', '', true)")
    return owner
