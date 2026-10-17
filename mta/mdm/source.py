"""Explicit source installation and selection for the SKU application owner."""
import gzip
import hashlib
import json
from pathlib import Path

from django.conf import settings
from django.db import connection, transaction

from mta.presentation.context import PublicationUnavailable
from mta.runtime.mdm_models import MdmSource, MdmSkuAttributes, MdmSkuDescription, MdmSkuUse

DLL = '0222eb96677a8f06250c4bba9eb0d477ac2dab6c88d35b214a33e7a9248bb346'
PINS = {
    'MasterMapper': 'b2f12de2c9de951aad470570050b4b0b3247aec0bacb85df53310e199aa458d1',
    'UI_MDMConfig': 'd71a1992187f0fedd9dcfb47e64bce776325a4b7bcef6474ca06531f85f7e10b',
    'SKUAttributeData': '517799d9110c68dcbbe302b6b0dc46599f49f6378b41bd2a8181d771d65011d2',
    'SKUDescriptionTbl': '21ef9efac39807a5357733ef8589ea2679e82f697bcc653f4f9dbd2530749f0b',
    'SkuUse': 'f518e27c133619e0b7383ce88965c1fc1a918c123346be609302389c8c50035f',
}
TARGETS = json.loads((Path(__file__).resolve().parents[1] / 'config/mdm_sku_targets.json').read_text())
PINS.update({name: receipt['sha256'] for name, receipt in TARGETS.items()})
SOURCE_DIGEST = hashlib.sha256(json.dumps(PINS, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def source(*, read_only=False):
    digest = settings.VF_MDM_SOURCE_DIGEST
    if not digest:
        raise PublicationUnavailable('mdm_source_not_selected')
    result = MdmSource.objects.filter(digest=digest).first()
    if result is None:
        raise PublicationUnavailable('mdm_source_not_installed')
    if result.receipt.get('schema') == 'fresh-production-mdm-source-v1':
        from mta.mdm.native_source import require_base
        for master_id in (1, 2, 3):
            require_base(result, master_id)
    else:
        raise PublicationUnavailable('historical_mdm_source_mode_removed')
    from mta.mdm.integration_source import require_read_binding
    require_read_binding(result, read_only=read_only)
    return result
