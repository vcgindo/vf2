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


def registered_case(raw):
    """The single approved fixture override, never a canonical input rewrite."""
    if hashlib.sha256(raw).hexdigest() != ARTIFACT_SHA:
        raise ValueError('Force trial requires its exact registered artifact')
    artifact = json.loads(raw)
    case = artifact['case']
    if case['profile']['force_flags'] != dict(from_ui=True, ignore_master_norm=False, nms_active=False):
        raise ValueError('Force trial retained flags differ')
    rows = [row for row in case['opening']['controls']['dbm_settings']
            if row['Parameter'] == 'FNC_MatchMasterNorm']
    if len(rows) != 1 or rows[0]['Value'] != '1':
        raise ValueError('Force trial retained master-match setting differs')
    rows[0]['Value'] = '0'
    case['profile']['force_flags']['ignore_master_norm'] = True
    return artifact


def configuration_sha():
    path = Path(__file__).resolve().parents[1] / 'config/mdm_force.json'
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require_installed(source):
    owner = MdmForceOwner.objects.get(source=source)
    from mta.mdm.target_fixture import require_family
    if require_family(source, owner, 'force'):
        return owner
    family = MdmFamilySource.objects.get(source=source, master_id=13)
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


@transaction.atomic
def install(raw, expected):
    if expected != ARTIFACT_SHA or hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError('Force source requires its exact registered ten-pair artifact')
    root = Path(__file__).resolve().parents[2]
    manifest = json.loads((root / 'baseline/manifest.json').read_text(encoding='utf-8'))
    if expected not in {row['sha256'] for row in manifest['retained_resources']}:
        raise ValueError('Force artifact is not registered')
    artifact = registered_case(raw)
    with connection.cursor() as cursor:
        cursor.execute('SELECT current_database()')
        database = cursor.fetchone()[0]
    if database != OWNED_DATABASE:
        raise ValueError('Force fixture installation requires its exclusively owned database')
    if MdmForceOwner.objects.exists():
        raise ValueError('Force fixture already installed; no replacement or reset')
    batches = consumer_batches(artifact)
    families = {str(mid): {'owners': []} for mid in (1, 2, 3)}
    for family, model, kwargs, rows, path in batches:
        families[str(family)]['owners'].append(dict(model=model.__name__, **kwargs,
            input_path=path, rows=len(rows), digest=digest(storage(rows)),
            fields=[field.name for field in business_fields(model)]))
    receipt = dict(schema=FORCE_SCHEMA, artifact_sha256=expected, artifact_schema=artifact['schema'],
        adapter_sha256=adapter_digest(), families=families, database=database,
        opening_date=artifact['case']['opening_date'],
        canonical=dict(dll=DLL, bpr_metadata_copy=BPR_COPY_SHA, mdm_use_queries_il=IL_SHA),
        configuration=configuration_digest(),
        fixture_override=TRIAL_OVERRIDE,
        hierarchy_supplement=HIERARCHY_SUPPLEMENT,
        initial_workflows='New isolated master13 source; prior family sources untouched')
    source = MdmSource.objects.create(digest=digest(receipt), dll_digest=DLL,
        database_name=database, receipt=receipt)
    for _, model, kwargs, rows, path in batches:
        model.objects.bulk_create([model(source=source, ordinal=i, **kwargs, **row)
            for i, row in enumerate(rows, 1)], batch_size=500)
        actual = list(model.objects.filter(source=source, **kwargs).order_by('ordinal')
                      .values(*[field.name for field in business_fields(model)]))
        if storage(actual) != storage(rows):
            raise ValueError('Force source typed opening differs: ' + path)
    for master_id in (2, 3):
        item = families[str(master_id)]
        MdmFamilySource.objects.create(source=source, master_id=master_id,
            digest=digest(item), receipt=item)
    opening = artifact['case']['opening']['importer']['ForceNormChange']
    provenance = dict(schema=OWNER_SCHEMA, artifact_sha256=expected,
        configuration_sha256=configuration_sha(), dll_sha256=DLL,
        opening_date=artifact['case']['opening_date'],
        input_path='/case/opening/importer/ForceNormChange', opening_digest=digest(opening),
        fixture_override=TRIAL_OVERRIDE, hierarchy_supplement=HIERARCHY_SUPPLEMENT,
        root_state_digest=digest(artifact['case']['opening']))
    MdmForceOwner.objects.create(source=source, provenance=provenance,
        receipt_digest=digest(provenance), opening_digest=digest(opening), closing_digest=digest(opening),
        root_state_digest=provenance['root_state_digest'],
        closing_log_digest=digest(artifact['case']['opening']['controls']['upload_log']))
    MdmFamilySource.objects.create(source=source, master_id=13,
        digest=digest(provenance), receipt=provenance)
    from mta.mdm.supplier_revisions import source_lock
    with source_lock(source.pk, deciding=True):
        MdmForceQueue.objects.bulk_create([MdmForceQueue(source=source, **row) for row in opening])
    from mta.mdm.daily_input import install_pair_exclusions
    install_pair_exclusions(source, deepcopy(artifact['case']['static_day']['exclusions']),
        provenance=dict(schema='fresh-force-exclusion-opening-v1', artifact_sha256=expected,
                        input_path='/case/static_day/exclusions'))
    require_installed(source)
    from mta.mdm.daily_source import require_binding
    require_binding(source, artifact_sha256=expected, artifact_schema=artifact['schema'])
    return source
