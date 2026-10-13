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


def source():
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
    elif result.dll_digest != DLL:
        raise PublicationUnavailable('mdm_source_not_installed')
    from mta.mdm.integration_source import require_read_binding
    require_read_binding(result)
    return result


def install_sku(path):
    """Install qualified raw masters once; never reset or borrow report rows."""
    rows = {}
    for table, expected in PINS.items():
        raw = gzip.decompress((Path(path) / (table.replace('/', '-') + '.json.gz')).read_bytes())
        if hashlib.sha256(raw).hexdigest() != expected:
            raise ValueError('MDM source identity mismatch: ' + table)
        rows[table] = json.loads(raw)
    with transaction.atomic():
        if MdmSource.objects.filter(digest=SOURCE_DIGEST).exists():
            raise ValueError('MDM source already installed; reset is prohibited')
        installed = MdmSource.objects.create(digest=SOURCE_DIGEST, dll_digest=DLL,
            database_name='VFTEST_Fresh_S2_VM_20261003_002_Importer',
            receipt={name: {'sha256': PINS[name], 'rows': len(values)} for name, values in rows.items()})
        for table, model in (('SKUAttributeData', MdmSkuAttributes), ('SKUDescriptionTbl', MdmSkuDescription)):
            for owner in ('Importer', 'BPR', 'BTR', 'DBM'):
                name = table if owner == 'Importer' else owner + '/' + table
                model.objects.bulk_create([model(source=installed, owner=owner, ordinal=i, **row)
                    for i, row in enumerate(rows[name], 1)], batch_size=500)
        MdmSkuUse.objects.bulk_create([MdmSkuUse(source=installed,ordinal=i,**row)
            for i,row in enumerate(rows['SkuUse'],1)],batch_size=2000)
        # Initial bulk installation needs current expression-index statistics;
        # autovacuum cannot see these rows before the install transaction commits.
        with connection.cursor() as cursor:
            for model in (MdmSkuAttributes,MdmSkuDescription):
                cursor.execute('ANALYZE '+connection.ops.quote_name(model._meta.db_table))
    return installed
