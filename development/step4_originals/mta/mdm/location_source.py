"""Install the pinned Location family onto an already installed MDM source."""
import gzip
import hashlib
import json
from pathlib import Path

from django.db import connection, transaction

from mta.runtime.mdm_models import (MdmFamilySource, MdmLocationAttributes,
    MdmLocationDescription, MdmLocationUse)

DLL = '0222eb96677a8f06250c4bba9eb0d477ac2dab6c88d35b214a33e7a9248bb346'
PINS = {
    'MasterMapper': 'b73777a137d61f0bc83b0a83e048d756792c29a405b9c2f2b5808db611960fb1',
    'UI_MDMConfig': '0e9e12f71329c418f2419379d2dc79b2d6789f1eee5484c13b9afda11c5575c6',
    'LOCATION_PERMISSION': '3e13bb4538904bbb7582695688f5f2215fda13e87b13d95f2004c77e653be4fa',
    'LocationAttributeData': '83c24f0eaf22efab08df4d8e22958a19b85d1e61d4d21c10866c6efc43a0f03c',
    'SiteDescriptionTbl': 'a9c4593b44632b0a328b0991caac12881993ed5618a3028128d94e43431f758c',
    'DraftLocationMaster': '7fabc51f2c3dc0a6443950ad78a799876d3ce3ebeba13e79b0deb600c8e8f10c',
    'UIUploadLogNMSLocations': '4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945',
    'delete-use-direct': '5f7b0b5f32ff7b700039a5630e00a7df78867050b9b4a39a7fa6e3a835dfc8a1',
    'delete-use-parent': '0c91338b8f9af33b94cb760d78c358e7c7a866a998cd321711051790d760336f',
}
TARGETS = json.loads((Path(__file__).resolve().parents[1] / 'config/mdm_location_targets.json').read_text())
PINS.update({name: receipt['sha256'] for name, receipt in TARGETS.items()})
SOURCE_DIGEST = hashlib.sha256(json.dumps(PINS, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def _read(path, name):
    raw = gzip.decompress((Path(path) / (name.replace('/', '-') + '.json.gz')).read_bytes())
    if hashlib.sha256(raw).hexdigest() != PINS[name]:
        raise ValueError('MDM Location source identity mismatch: ' + name)
    return json.loads(raw)


def installed(source):
    return MdmFamilySource.objects.filter(source=source, master_id=2,
        digest=SOURCE_DIGEST).exists()


def install_location(path, source):
    """Install qualified raw bags once without changing the SKU root receipt."""
    if source.dll_digest != DLL:
        raise ValueError('MDM Location DLL identity mismatch')
    rows = {name: _read(path, name) for name in PINS}
    with transaction.atomic():
        if MdmFamilySource.objects.filter(source=source, master_id=2).exists():
            raise ValueError('MDM Location source already installed; reset is prohibited')
        item = lambda name: {'sha256': PINS[name], 'rows': len(rows[name])}
        family = MdmFamilySource.objects.create(source=source, master_id=2,
            digest=SOURCE_DIGEST, receipt={
                'processed': {name: item(name) for name in
                    ('LocationAttributeData', 'SiteDescriptionTbl',
                     'delete-use-direct', 'delete-use-parent')},
                'supporting': {name: item(name) for name in
                    ('MasterMapper', 'UI_MDMConfig', 'LOCATION_PERMISSION',
                     'DraftLocationMaster', 'UIUploadLogNMSLocations')},
                'evidence_only': {name: item(name) for name in TARGETS},
            })
        for table, model in (('LocationAttributeData', MdmLocationAttributes),
                             ('SiteDescriptionTbl', MdmLocationDescription)):
            model.objects.bulk_create([model(source=source, owner='Importer', ordinal=i, **row)
                for i, row in enumerate(rows[table], 1)], batch_size=500)
        uses = []
        for kind in ('direct', 'parent'):
            for ordinal, row in enumerate(rows['delete-use-' + kind], 1):
                code = row['LocCode' if kind == 'direct' else 'ParentWhCode']
                uses.append(MdmLocationUse(source=source, use_kind=kind,
                    ordinal=ordinal, WHCode=code))
        MdmLocationUse.objects.bulk_create(uses, batch_size=2000)
        with connection.cursor() as cursor:
            for model in (MdmLocationAttributes, MdmLocationDescription):
                cursor.execute('ANALYZE ' + connection.ops.quote_name(model._meta.db_table))
    return family
