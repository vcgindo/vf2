"""Explicit installation of supplier application owners; no report fallback."""
import hashlib
import json
import math
from pathlib import Path

from django.db import connection, transaction
from mta.mdm.source import DLL
from mta.mdm.supplier_input import FORMATS
from mta.runtime.mdm_models import MdmSource, MdmFamilySource
from mta.runtime.mdm_supplier_models import (MdmSupplierConfiguration,
                                            MdmSobRaw, MdmMoqRaw1, MdmMoqRaw2)
from mta.serialization import digest

SCHEMA = 'fresh-mdm-supplier-source-v1'
CONFIGURATION = {name: hashlib.sha256((Path(__file__).resolve().parents[1] /
    ('config/mdm_' + name + '.json')).read_bytes()).hexdigest() for name in ('sob', 'moq')}
MODELS = {'SOBDataRaw': MdmSobRaw, 'MOQDataRaw1': MdmMoqRaw1, 'MOQDataRaw2': MdmMoqRaw2}


def require_installed(source, master_id):
    from mta.presentation.context import PublicationUnavailable
    try:
        config = MdmSupplierConfiguration.objects.get(source=source)
        family = MdmFamilySource.objects.get(source=source, master_id=int(master_id))
    except (MdmSupplierConfiguration.DoesNotExist, MdmFamilySource.DoesNotExist):
        raise PublicationUnavailable('mdm_supplier_family_not_installed') from None
    from mta.mdm.initialization_contract import SOURCE_SCHEMA
    if source.receipt.get('schema') == SOURCE_SCHEMA:
        from mta.mdm.production_families import require_owner
        return require_owner(source, config, 'supplier')
    if (family.receipt.get('schema') != SCHEMA or family.receipt.get('dll_sha256') != DLL
            or source.dll_digest != DLL
            or family.receipt.get('configuration') != CONFIGURATION
            or family.receipt.get('moq_format') != config.moq_format
            or family.receipt.get('upload_log_active') != config.upload_log_active
            or family.digest != digest(family.receipt)
            or family.receipt.get('installation_digest') != config.receipt_digest):
        raise ValueError('Supplier application installation identity differs')
    from mta.mdm.integration_source import DAILY_OWNER_SCHEMA, verify_owner_anchor
    if config.provenance.get('schema') == DAILY_OWNER_SCHEMA:
        verify_owner_anchor(source, config.provenance)
        if (config.provenance.get('family') != 'supplier'
                or family.receipt.get('closing_binding_digest') != digest(config.provenance)):
            raise ValueError('Supplier accepted closing provenance differs')
    return config
