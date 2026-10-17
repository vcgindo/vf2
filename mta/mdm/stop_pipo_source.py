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
    from mta.mdm.initialization_contract import SOURCE_SCHEMA
    if source.receipt.get('schema') == SOURCE_SCHEMA:
        from mta.mdm.production_families import require_owner
        return require_owner(source, owner, 'stop_pipo')
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
