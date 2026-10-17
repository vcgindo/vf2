"""Explicit admission of the separately approved, isolated Seasonality source."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from django.conf import settings
from django.db import connection, transaction

from mta.mdm.daily_source import SEASON_SCHEMA, adapter_digest, configuration_digest
from mta.mdm.daily_source_install import owners, business_fields, BPR_COPY_SHA, IL_SHA
from mta.mdm.source import DLL
from mta.runtime.mdm_models import MdmSource, MdmFamilySource
from mta.runtime.mdm_season_models import (MdmSeasonOwner, MdmSeasonEligibility,
                                          MdmSeasonQueue, MdmSeasonCurrent)
from mta.serialization import digest, storage

ARTIFACT_SHA = 'a7e12b4a0ea39c4e0122076df8f6a6268e749dca73a51387278878511281993f'
OWNER_SCHEMA = 'fresh-mdm-season-owner-v1'
SUPPLEMENT = dict(
    authorization='call_b54a0359e44d4719885a37c5f695ee9f:0',
    proposal_sha256='93ecfb5222e60759eedd9c84a0e2fb6496b35660a444f2d04bb9f4b0301f6763',
    permissions_sha256='18df4d8e84633848062c45e1896615a7a46d350d0c0cd8657f38cb7b0948c356',
    boundary='Seasonality consumer hierarchy and upload eligibility only; validation clock in owned request harness')


def configuration_sha():
    return hashlib.sha256((Path(__file__).resolve().parents[1] /
        'config/mdm_season.json').read_bytes()).hexdigest()


def require_installed(source):
    owner = MdmSeasonOwner.objects.get(source=source)
    from mta.mdm.initialization_contract import SOURCE_SCHEMA
    if source.receipt.get('schema') == SOURCE_SCHEMA:
        from mta.mdm.production_families import require_owner
        return require_owner(source, owner, 'season')
    from mta.mdm.target_fixture import require_family
    if require_family(source, owner, 'season'):
        return owner
    p = owner.provenance
    from mta.mdm.integration_source import DAILY_OWNER_SCHEMA, verify_owner_anchor
    accepted = p.get('schema') == DAILY_OWNER_SCHEMA
    if accepted:
        verify_owner_anchor(source, p)
        if p.get('family') != 'season':
            raise ValueError('Seasonality accepted closing family differs')
    if (source.dll_digest != DLL or not accepted and p.get('schema') != OWNER_SCHEMA
            or p.get('configuration_sha256') != configuration_sha()
            or not accepted and p.get('artifact_sha256') != ARTIFACT_SHA
            or not accepted and p.get('supplement') != SUPPLEMENT
            or p.get('root_state_digest') != owner.root_state_digest
            or digest(p) != owner.receipt_digest):
        raise ValueError('Seasonality source installation identity differs')
    installed = list(MdmFamilySource.objects.filter(source=source, master_id__in=(10, 11, 12)))
    if len(installed) != 3 or any(r.receipt != p or r.digest != owner.receipt_digest for r in installed):
        raise ValueError('Complete Seasonality family installation required')
    eligible = list(MdmSeasonEligibility.objects.filter(source=source).order_by('ordinal')
                    .values('SKUCode', 'WhCode', 'Norm'))
    if digest(storage(eligible)) != p['eligibility_digest']:
        raise ValueError('Seasonality upload eligibility fixture differs')
    return owner




def consumer_batches(artifact):
    raw = Path(settings.VF_MTA_PERMISSIONS_FILE).read_bytes()
    if hashlib.sha256(raw).hexdigest() != SUPPLEMENT['permissions_sha256']:
        raise ValueError('Seasonality hierarchy requires the approved catalogue')
    catalogue = json.loads(raw)
    batches = owners(artifact)
    changed = 0
    for _, model, kwargs, rows, _ in batches:
        kind, code, prefix = {'MdmSkuAttributes': ('products', 'SKUCode', 'SL'),
            'MdmLocationAttributes': ('locations', 'WHCode', 'LL')}.get(model.__name__, (None, None, None))
        if kind is None or kwargs.get('owner') != 'Importer':
            continue
        for row in rows:
            matches = [r for r in catalogue[kind]['attributes'] if r['code'] == row[code]]
            if len(matches) != 1:
                raise ValueError('Seasonality hierarchy identity differs')
            for i in (1, 2, 3):
                field, value = prefix + str(i), matches[0]['level_' + str(i)]
                if row[field] is not None or row['c' + str(i)] != value:
                    raise ValueError('Seasonality hierarchy exceeds approved mapping')
                row[field] = value
            changed += 1
    if changed != 11:
        raise ValueError('Seasonality hierarchy occurrence roster differs')
    return batches
