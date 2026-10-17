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




def installed(source):
    return MdmFamilySource.objects.filter(source=source, master_id=2,
        digest=SOURCE_DIGEST).exists()
