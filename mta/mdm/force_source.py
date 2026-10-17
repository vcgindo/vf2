"""Additive, registered master13 fixture admission; prior sources stay intact."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from django.conf import settings
from django.db import connection, transaction
from mta.mdm.daily_source import FORCE_SCHEMA, adapter_digest, configuration_digest
from mta.mdm.daily_source_install import owners, business_fields, BPR_COPY_SHA, IL_SHA
from mta.mdm.source import DLL
from mta.runtime.mdm_models import MdmSource, MdmFamilySource
from mta.runtime.mdm_force_models import MdmForceOwner, MdmForceQueue
from mta.serialization import digest, storage

ARTIFACT_SHA = 'a7e12b4a0ea39c4e0122076df8f6a6268e749dca73a51387278878511281993f'
TRIAL_SOURCE_SHA = '226c7a586431be8a4b74ce6692ca5611d08d93b2e2315c1a2439c94c5ac44ff9'
OWNER_SCHEMA = 'fresh-mdm-force-owner-v1'
OWNED_DATABASE = 'freshvcf_nms_sob_moq_001'
TRIAL_OVERRIDE = dict(parameter='FNC_MatchMasterNorm', before='1', after='0',
    authorization='call_41c8e71cd567475fbcb750bf95fc6e7b:0', nms_active=False)
HIERARCHY_SUPPLEMENT = dict(
    proposal_sha256='56e5156303b0275b5512947ec8c9762fef89d29ed831f6653b9d4b2fcc21d5c5',
    permission_sha256='18df4d8e84633848062c45e1896615a7a46d350d0c0cd8657f38cb7b0948c356',
    authorization='call_96d9f196a5d94d4ba0c9b88b4228e4a9:0',
    boundary='Importer MDM consumer SL1-3/LL1-3 only; operational opening unchanged')


def apply_working_fixture_setting(snapshot, prior):
    """Project the approved flag into its actual producer-owned working table.

    The immutable registered opening/capture stays intact. chain.SHARED_CONTROLS
    refreshes controls.dbm_settings from DBMSettingsTbl before the force stage.
    This exact isolated source opt-in must therefore cover that working copy too.
    """
    if snapshot.get('source_digest') != TRIAL_SOURCE_SHA:
        return
    opening = snapshot['force']['anchor']['run_id'] is None
    for rows, expected in ((prior['controls']['dbm_settings'], '0'),
                           (prior['dbm']['DBMSettingsTbl'], '1' if opening else '0')):
        matches = [r for r in rows if r['Parameter'] == TRIAL_OVERRIDE['parameter']]
        if len(matches) != 1 or matches[0]['Value'] != expected:
            raise ValueError('Force fixture master-match working setting differs')
        matches[0]['Value'] = '0'


def consumer_batches(artifact):
    raw = Path(settings.VF_MTA_PERMISSIONS_FILE).read_bytes()
    if hashlib.sha256(raw).hexdigest() != HIERARCHY_SUPPLEMENT['permission_sha256']:
        raise ValueError('Force consumer hierarchy requires its approved catalogue')
    catalogue = json.loads(raw)
    batches = owners(artifact)
    changed = 0
    for _, model, kwargs, rows, _ in batches:
        kind, code, prefix = {'MdmSkuAttributes': ('products', 'SKUCode', 'SL'),
            'MdmLocationAttributes': ('locations', 'WHCode', 'LL')}.get(
                model.__name__, (None, None, None))
        if kind is None or kwargs.get('owner') != 'Importer':
            continue
        for row in rows:
            matches = [r for r in catalogue[kind]['attributes'] if r['code'] == row[code]]
            if len(matches) != 1:
                raise ValueError('Force consumer hierarchy identity differs')
            for i in (1, 2, 3):
                field = prefix + str(i)
                value = matches[0]['level_' + str(i)]
                if row[field] is not None or row['c' + str(i)] != value:
                    raise ValueError('Force consumer hierarchy exceeds approved mapping')
                row[field] = value
            changed += 1
    if changed != 11:
        raise ValueError('Force consumer hierarchy occurrence roster differs')
    return batches




def configuration_sha():
    path = Path(__file__).resolve().parents[1] / 'config/mdm_force.json'
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require_installed(source):
    owner = MdmForceOwner.objects.get(source=source)
    from mta.mdm.initialization_contract import SOURCE_SCHEMA
    if source.receipt.get('schema') == SOURCE_SCHEMA:
        from mta.mdm.production_families import require_owner
        return require_owner(source, owner, 'force')
    from mta.mdm.target_fixture import require_family
    if require_family(source, owner, 'force'):
        return owner
    family = MdmFamilySource.objects.get(source=source, master_id=13)
    from mta.mdm.integration_source import DAILY_OWNER_SCHEMA, verify_owner_anchor
    if owner.provenance.get('schema') == DAILY_OWNER_SCHEMA:
        p = owner.provenance
        verify_owner_anchor(source, p)
        if (p.get('configuration_sha256') != configuration_sha()
                or p.get('family') != 'force'
                or p.get('root_state_digest') != owner.root_state_digest
                or p.get('opening_digest') != owner.opening_digest
                or digest(p) != owner.receipt_digest
                or family.receipt != p or family.digest != owner.receipt_digest):
            raise ValueError('Force accepted closing installation differs')
        return owner
    if (source.dll_digest != DLL or owner.provenance.get('schema') != OWNER_SCHEMA
            or owner.provenance.get('configuration_sha256') != configuration_sha()
            or owner.provenance.get('artifact_sha256') != ARTIFACT_SHA
            or owner.provenance.get('fixture_override') != TRIAL_OVERRIDE
            or owner.provenance.get('hierarchy_supplement') != HIERARCHY_SUPPLEMENT
            or owner.provenance.get('root_state_digest') != owner.root_state_digest
            or digest(owner.provenance) != owner.receipt_digest
            or family.receipt != owner.provenance or family.digest != owner.receipt_digest):
        raise ValueError('Force source installation identity differs')
    return owner
