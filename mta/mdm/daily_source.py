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
APPROVAL_DAY_ARTIFACT_SHA = 'be33508fd9e5cd6b0224f02502f61b87a0cfb8cdce44cafb3d1f1c3e1384d847'
# Exact pre-master13 adapter in deployed delivery image a002. Its immutable
# receipts remain readable only for their original family roster.
LEGACY_ADAPTER_SHA = 'efea1668e97ae63e76789f79e3927d5d406696a012db5b25c3ac9c375bf8eb51'
FORCE_SCHEMA = 'fresh-mdm-daily-force-source-v1'
FORCE_ADAPTER_SHA = '2f8c7400d0a9a34790d881fc477067c050a189a9c6d6b664b3cff03d40c1a8eb'
SEASON_SCHEMA = 'fresh-mdm-daily-season-source-v1'
SEASON_ADAPTER_SHA = '4a17f6ac18811c7daed26c2ff5f672e04ed2ea576612515974a5f772acb5b46e'
STOP_ADAPTER_SHA = 'e15d8fe67270c7ec7e10c80b82b8b7f6e53db7b7f659974973f0637d67d2235c'
PHASE_ADAPTER_SHA = '118b06f3fbee192ef2f5ca161f6ff1849b4b1f57ac4651896ce92117a227bdaf'
# c55a115 adapter keeps its original root/roster checks after this additive path.
COMBINED_ADAPTER_SHA = '4afb12a88bef2c3671cd22cd66ee243760cd642e6894b6bc9172e53d28d0d4b1'
SOURCE_SCHEMAS = (SCHEMA, FORCE_SCHEMA, SEASON_SCHEMA)


def adapter_digest():
    return digest({name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
                   for name in ('daily_source.py', 'daily_source_install.py', 'families.py',
                                'owned_namespace.py')})


def configuration_digest():
    root=Path(__file__).resolve().parents[1]/'config'
    return {name:hashlib.sha256((root/name).read_bytes()).hexdigest()
            for name in ('mdm_sku.json','mdm_location.json','mdm_skuloc.json')}


def require_root(source, *, artifact_sha256, artifact_schema):
    """Verify immutable original ownership, without extending its family roster."""
    from mta.mdm.initialization_contract import SOURCE_SCHEMA
    if source.receipt.get('schema') == SOURCE_SCHEMA:
        from mta.mdm.production_families import require_initialization
        require_initialization(source, input_sha256=artifact_sha256, input_schema=artifact_schema)
        return source.receipt['families']
    receipt = source.receipt
    if source.dll_digest != DLL or not isinstance(receipt, dict):
        raise ValueError('Daily MDM canonical DLL/source receipt differs')
    current_adapter = adapter_digest()
    if (receipt.get('schema') not in SOURCE_SCHEMAS or digest(receipt) != source.digest
            or receipt.get('artifact_sha256') != artifact_sha256
            or receipt.get('artifact_schema') != artifact_schema
            or receipt.get('adapter_sha256') not in (current_adapter, LEGACY_ADAPTER_SHA, FORCE_ADAPTER_SHA, SEASON_ADAPTER_SHA, STOP_ADAPTER_SHA, PHASE_ADAPTER_SHA, COMBINED_ADAPTER_SHA)):
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
    if 'owned_namespace' in receipt:
        from mta.mdm.owned_namespace import verify_binding
        namespace = receipt['owned_namespace']
        if (not isinstance(namespace, dict)
                or namespace.get('artifact_sha256') != artifact_sha256
                or namespace.get('adapter_sha256') != receipt['adapter_sha256']):
            raise ValueError('Daily MDM namespace root identity differs')
        verify_binding(receipt)
    return families


def require_binding(source, *, artifact_sha256, artifact_schema):
    from mta.mdm.initialization_contract import SOURCE_SCHEMA
    if source.receipt.get('schema') == SOURCE_SCHEMA:
        from mta.mdm.production_families import (require_initialization,
                                                 require_binding as require_native)
        require_initialization(source, input_sha256=artifact_sha256, input_schema=artifact_schema)
        from mta.runtime.mdm_integration_models import MdmSourceIntegration
        if MdmSourceIntegration.objects.filter(source=source).exists():
            require_native(source)
        return source
    families = require_root(source, artifact_sha256=artifact_sha256,
                            artifact_schema=artifact_schema)
    from mta.mdm.integration_source import installed_binding
    if installed_binding(source) is not None:
        # Separate current identity; never widen a historical adapter's roster.
        return source
    receipt = source.receipt
    current_adapter = adapter_digest()
    installed = {row.master_id: row for row in
                 MdmFamilySource.objects.filter(source=source)}
    base_installed = set(installed) - {6, 7, 8, 9}
    accepted_root = receipt['adapter_sha256'] == current_adapter and receipt['schema'] == SCHEMA
    if set(installed).intersection({7, 8, 9}) not in (set(), {7, 8, 9}):
        raise ValueError('Phase controls require their complete shared owner roster')
    if accepted_root:
        ids = set(installed)
        if (not {2, 3} <= ids or ids - set(range(2, 14))
                or any(ids & group not in (set(), group)
                       for group in ({4, 5}, {7, 8, 9}, {10, 11, 12}))):
            raise ValueError('Complete shared daily MDM owners not installed')
    elif base_installed not in ({2, 3}, {2, 3, 4, 5}, {2, 3, 13}, {2, 3, 4, 5, 13}, {2, 3, 10, 11, 12}):
        raise ValueError('Location and SKU-location daily MDM owners not installed')
    expected_schema = SEASON_SCHEMA if 10 in installed else FORCE_SCHEMA if 13 in installed else SCHEMA
    if not accepted_root and (receipt.get('schema') != expected_schema
            or 10 in installed and receipt['adapter_sha256'] not in (current_adapter, SEASON_ADAPTER_SHA, STOP_ADAPTER_SHA, PHASE_ADAPTER_SHA, COMBINED_ADAPTER_SHA)
            or receipt['adapter_sha256'] == SEASON_ADAPTER_SHA and base_installed != {2, 3, 10, 11, 12}
            or 13 in installed and receipt['adapter_sha256'] not in (current_adapter, FORCE_ADAPTER_SHA, STOP_ADAPTER_SHA, PHASE_ADAPTER_SHA, COMBINED_ADAPTER_SHA)):
        raise ValueError('Daily MDM source is not bound to this registered artifact/adapter')
    for master_id, family in installed.items():
        if master_id in (7, 8, 9):
            from mta.mdm.phase_controls_source import require_installed
            require_installed(source)
            continue
        if master_id == 6:
            from mta.mdm.stop_pipo_source import require_installed
            require_installed(source)
            continue
        if master_id in (10, 11, 12):
            from mta.mdm.season_source import require_installed
            owner = require_installed(source)
            if accepted_root:
                from mta.mdm.integration_source import DAILY_OWNER_SCHEMA
                if owner.provenance.get('schema') != DAILY_OWNER_SCHEMA:
                    raise ValueError('Daily root cannot inherit historical Seasonality authority')
            continue
        if master_id == 13:
            from mta.mdm.force_source import require_installed
            owner = require_installed(source)
            if accepted_root:
                from mta.mdm.integration_source import DAILY_OWNER_SCHEMA
                if owner.provenance.get('schema') != DAILY_OWNER_SCHEMA:
                    raise ValueError('Daily root cannot inherit historical Force authority')
            continue
        if master_id in (4, 5):
            from mta.mdm.supplier_source import require_installed
            require_installed(source, master_id)
            continue
        expected = families[str(master_id)]
        if family.receipt != expected or family.digest != digest(expected):
            raise ValueError('Daily MDM family installation identity differs')
    return source
