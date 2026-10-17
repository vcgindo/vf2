"""Install the pinned master-3 current and eligibility owners once."""
import gzip
import hashlib
import json
from pathlib import Path

from django.db import connection, transaction

from mta.runtime.mdm_models import MdmFamilySource
from mta.runtime.mdm_skuloc_models import MdmSkuLocCurrent, MdmSkuLocMasterPair, MdmSkuLocPair

DLL='0222eb96677a8f06250c4bba9eb0d477ac2dab6c88d35b214a33e7a9248bb346'
PINS={
    'MasterMapper':'f79abdd32852235854c7feb31256cf1d50872c6881238152f8a24911c9cf12ca',
    'UI_MDMConfig':'aa8b3c9fe0a8981f34f42fd94d1af34f35a6f3455be99545f962aa6fcb755c12',
    'NMSAllItems':'edef70a262d9b5592d7970c2df53df626a4bbae25be567b671d1a42a20bb1179',
    'SkuLocAttributeData':'4d4119b73a06bf212dcd0ae65f046e50c13cec5f96dda78f409cb5eff49c9528',
    'MasterData':'698f03975728da6022162a2d5518cea404eb8c2c2ab99bd0a0691189be91f2c3',
}
COUNTS={'MasterMapper':1,'UI_MDMConfig':37,'NMSAllItems':97097,
        'SkuLocAttributeData':97097,'MasterData':97097}
SOURCE_DIGEST=hashlib.sha256(json.dumps(PINS,sort_keys=True,separators=(',',':')).encode()).hexdigest()




def _read(path,name):
    target=Path(path)/(name+'.json.gz')
    with gzip.open(target,'rt',encoding='utf-8') as stream:
        result=json.load(stream)
    if len(result)!=COUNTS[name]:
        raise ValueError('MDM SKU-location source row count mismatch: '+name)
    return result


def installed(source):
    return MdmFamilySource.objects.filter(source=source,master_id=3,digest=SOURCE_DIGEST).exists()
