"""Native v2 closing identities; historical upgrades stay on pinned releases.

**DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.**
"""
import hashlib
from pathlib import Path
import uuid
from mta.mdm.location_projection import VERSION
from mta.serialization import digest
ROOT = Path(__file__).resolve().parents[2]

def source_files(root=ROOT):
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for area in ('mta', 'vectorflow') for p in sorted((root/area).rglob('*'))
        if p.is_file() and p.suffix in ('.py', '.json') and '__pycache__' not in p.parts}

def source_manifest_digest():
    from release.native_identity import require_current
    require_current()
    return digest(source_files())


def integration_identity(source, initialization, seal):
    """A fresh seal must identify the actual current native source exactly."""
    from mta.mdm.production_families import adapter_digest
    identity = dict(adapter_digest=adapter_digest(), closing_projection_version=VERSION,
                    source_manifest_digest=source_manifest_digest())
    if identity != {key: seal.receipt.get(key) for key in identity}:
        raise ValueError('Native integration source differs; historical installations stay pinned')
    return identity


def run_identity(run, source):
    from mta.runtime.mdm_integration_models import MdmSourceIntegration
    seal = MdmSourceIntegration.objects.get(source=source)
    if seal.receipt.get('closing_projection_version') != VERSION:
        raise ValueError('Historical closing projection requires its pinned original release')
    return dict(version=VERSION, transition_id=None, source_digest=source.digest,
        adapter_digest=seal.receipt['adapter_digest'], integration_digest=seal.digest,
        source_manifest_digest=seal.receipt['source_manifest_digest'])


def admit(source, business_date, parent):
    from mta.runtime.mdm_integration_models import MdmSourceIntegration
    seal = MdmSourceIntegration.objects.get(source=source)
    if seal.receipt.get('closing_projection_version') != VERSION:
        raise ValueError('Historical closing projection requires its pinned original release')
    if parent is not None:
        if parent.status != 'SUCCEEDED' or parent.kind != 'DAILY_CHAIN':
            raise ValueError('Closing projection requires a successful daily predecessor')
        verified_receipt(parent, source)


def capture_identity(capture):
    values = {f.attname:getattr(capture,f.attname) for f in capture._meta.fields
        if f.name not in ('captured_at','consumed_at','status')}
    return digest({key:str(value) if isinstance(value,uuid.UUID) else value
                   for key,value in values.items()})

def verified_receipt(run, source):
    from mta.runtime.mdm_projection_models import MdmClosingProjectionReceipt
    from mta.runtime.mdm_daily_models import MdmDailyInputCapture
    expected = run_identity(run, source)
    receipt = MdmClosingProjectionReceipt.objects.filter(run=run).first()
    capture = MdmDailyInputCapture.objects.get(run=run,source=source,status='CONSUMED')
    if (receipt is None or receipt.status != 'SEALED'
            or any(getattr(receipt,k) != v for k,v in expected.items())
            or receipt.capture_digest != capture_identity(capture)
            or receipt.digest != digest(receipt.metadata)
            or set(receipt.metadata) != {'version','partitions','sources'}
            or receipt.metadata['version'] != VERSION):
        raise ValueError('Native closing projection receipt is missing or differs')
    return receipt
