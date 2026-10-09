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
    p = owner.provenance
    if (source.dll_digest != DLL or p.get('schema') != OWNER_SCHEMA
            or p.get('configuration_sha256') != configuration_sha()
            or p.get('artifact_sha256') != ARTIFACT_SHA
            or p.get('supplement') != SUPPLEMENT
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


@transaction.atomic
def install(raw, expected):
    if expected != ARTIFACT_SHA or hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError('Seasonality requires the exact registered ten-pair artifact')
    root = Path(__file__).resolve().parents[2]
    manifest = json.loads((root / 'baseline/manifest.json').read_text(encoding='utf-8'))
    if expected not in {r['sha256'] for r in manifest['retained_resources']}:
        raise ValueError('Seasonality artifact is not registered')
    artifact = json.loads(raw)
    case = artifact['case']
    if case['profile']['force_flags'] != dict(from_ui=True, ignore_master_norm=False, nms_active=False):
        raise ValueError('Seasonality retained flags differ')
    with connection.cursor() as cursor:
        cursor.execute('SELECT current_database()')
        database = cursor.fetchone()[0]
    if database != 'freshvcf_nms_sob_moq_001':
        raise ValueError('Seasonality installation requires its exclusively owned database')
    if MdmSeasonOwner.objects.exists():
        raise ValueError('Seasonality already installed; replacement/reset prohibited')
    batches = consumer_batches(artifact)
    families = {str(mid): {'owners': []} for mid in (1, 2, 3)}
    for family, model, kwargs, rows, path in batches:
        families[str(family)]['owners'].append(dict(model=model.__name__, **kwargs,
            input_path=path, rows=len(rows), digest=digest(storage(rows)),
            fields=[f.name for f in business_fields(model)]))
    receipt = dict(schema=SEASON_SCHEMA, artifact_sha256=expected, artifact_schema=artifact['schema'],
        adapter_sha256=adapter_digest(), families=families, database=database,
        opening_date=case['opening_date'], canonical=dict(dll=DLL,
            bpr_metadata_copy=BPR_COPY_SHA, mdm_use_queries_il=IL_SHA),
        configuration=configuration_digest(), supplement=SUPPLEMENT,
        initial_workflows='New isolated master10/11/12 owner; prior sources unchanged')
    source = MdmSource.objects.create(digest=digest(receipt), dll_digest=DLL,
                                     database_name=database, receipt=receipt)
    for _, model, kwargs, rows, path in batches:
        model.objects.bulk_create([model(source=source, ordinal=i, **kwargs, **row)
            for i, row in enumerate(rows, 1)], batch_size=500)
        actual = list(model.objects.filter(source=source, **kwargs).order_by('ordinal')
            .values(*[f.name for f in business_fields(model)]))
        if storage(actual) != storage(rows):
            raise ValueError('Seasonality typed opening differs: ' + path)
    for mid in (2, 3):
        MdmFamilySource.objects.create(source=source, master_id=mid,
            digest=digest(families[str(mid)]), receipt=families[str(mid)])
    opening = case['opening']
    queue, current = opening['control_aux']['season_requests'], opening['dbm']['Seasonality']
    eligible = [{n: r[n] for n in ('SKUCode', 'WhCode', 'Norm')} for r in opening['importer']['MasterData']]
    if len(eligible) != 10 or queue or current:
        raise ValueError('Registered Seasonality opening roster differs')
    provenance = dict(schema=OWNER_SCHEMA, artifact_sha256=expected, dll_sha256=DLL,
        configuration_sha256=configuration_sha(), supplement=SUPPLEMENT,
        root_state_digest=digest(opening), opening_date=case['opening_date'],
        eligibility_digest=digest(eligible), opening_queue_digest=digest(queue),
        opening_current_digest=digest(current))
    MdmSeasonOwner.objects.create(source=source, provenance=provenance,
        receipt_digest=digest(provenance), root_state_digest=provenance['root_state_digest'],
        closing_queue_digest=digest(queue), closing_current_digest=digest(current))
    for mid in (10, 11, 12):
        MdmFamilySource.objects.create(source=source, master_id=mid,
            digest=digest(provenance), receipt=provenance)
    with connection.cursor() as cursor:
        cursor.execute("SELECT set_config('fresh.season_eligibility_source',%s,true)", [str(source.pk)])
    try:
        MdmSeasonEligibility.objects.bulk_create([MdmSeasonEligibility(source=source,
            ordinal=i, **r) for i, r in enumerate(eligible, 1)])
    finally:
        with connection.cursor() as cursor:
            cursor.execute("SELECT set_config('fresh.season_eligibility_source','',true)")
    from mta.mdm.daily_input import install_pair_exclusions
    install_pair_exclusions(source, deepcopy(case['static_day']['exclusions']),
        provenance=dict(schema='fresh-season-exclusion-opening-v1', artifact_sha256=expected,
                        input_path='/case/static_day/exclusions'))
    require_installed(source)
    from mta.mdm.daily_source import require_binding
    require_binding(source, artifact_sha256=expected, artifact_schema=artifact['schema'])
    return source
