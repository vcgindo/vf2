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
    from mta.mdm.initialization_contract import SOURCE_SCHEMA
    if source.receipt.get('schema') == SOURCE_SCHEMA:
        from mta.mdm.production_families import require_owner
        return require_owner(source, owner, 'phase_controls')
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
