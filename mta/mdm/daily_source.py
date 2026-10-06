"""Fail-closed identity binding for a separately installed synthetic MDM source.

This verifier does not install sources or make the April fixture eligible for a
synthetic day. The installer must bind its complete three-family receipts to the
registered artifact and this versioned adapter before the runner can use it.
"""
import hashlib
from pathlib import Path

from mta.mdm.source import DLL
from mta.runtime.mdm_models import MdmFamilySource
from mta.serialization import digest

SCHEMA = 'fresh-mdm-daily-source-v1'
ARTIFACT_SHA = '7ee7d940da3bab89ffeeddff94b4f2a7d9abace4aacdd589d698df6de85c24fc'


def adapter_digest():
    return digest({name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
                   for name in ('daily_source.py', 'daily_source_install.py', 'families.py')})


def configuration_digest():
    root=Path(__file__).resolve().parents[1]/'config'
    return {name:hashlib.sha256((root/name).read_bytes()).hexdigest()
            for name in ('mdm_sku.json','mdm_location.json','mdm_skuloc.json')}


def require_binding(source, *, artifact_sha256, artifact_schema):
    receipt = source.receipt
    if source.dll_digest != DLL or not isinstance(receipt, dict):
        raise ValueError('Daily MDM canonical DLL/source receipt differs')
    if (receipt.get('schema') != SCHEMA or digest(receipt) != source.digest
            or receipt.get('artifact_sha256') != artifact_sha256
            or receipt.get('artifact_schema') != artifact_schema
            or receipt.get('adapter_sha256') != adapter_digest()):
        raise ValueError('Daily MDM source is not bound to this registered artifact/adapter')
    if receipt.get('configuration') != configuration_digest():
        raise ValueError('Daily MDM source configuration differs')
    families = receipt.get('families')
    if not isinstance(families, dict) or set(families) != {'1', '2', '3'}:
        raise ValueError('Complete three-family daily MDM source required')
    # Each family's immutable installation receipt binds its full owner bags,
    # not just row counts. Root identity includes the SKU receipt directly.
    if not all(isinstance(item, dict) and item for item in families.values()):
        raise ValueError('Daily MDM family installation receipt missing')
    installed = {row.master_id: row for row in
                 MdmFamilySource.objects.filter(source=source)}
    if set(installed) != {2, 3}:
        raise ValueError('Location and SKU-location daily MDM owners not installed')
    for master_id, family in installed.items():
        expected = families[str(master_id)]
        if family.receipt != expected or family.digest != digest(expected):
            raise ValueError('Daily MDM family installation identity differs')
    return source
