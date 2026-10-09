"""Exact human-approved 3005 consumer admission; no daily acceptance is issued.

This source remains a legacy UI fixture. The original daily binders/captures
are deliberately not reused or relaxed to claim a computed closing.
"""
import hashlib
from pathlib import Path
from django.db import connection, transaction
from mta.serialization import digest, storage
from mta.runtime.mdm_models import MdmSource, MdmFamilySource
from mta.runtime.mdm_target_fixture_models import (MdmTargetFixture,
    MdmFixturePhaseOut, MdmFixturePhaseIn, MdmFixturePhaseMap, MdmFixtureSeasonStatus)

SCHEMA = 'fresh-mdm-target3005-consumer-fixture-v1'
AUTHORITY = 'call_63dfc3ff84c84f43a2855554d598e52e:0'
SOURCE = 'eccbec8cf5f61f87f80bdf65715dee350e616041e7957f27daead42bab4b975d'
RUN = 'bfd75b4b-a9df-4a08-82d3-852e3324b623'
DATABASE = 'test_freshvcf_stage2_vm_20261003_002'
MANIFEST = 'afe42593ca2abdf5e2395433ac70834723f4eac1dfa5a2982192c7688906b836'
INPUT_DIGEST = 'bdc91dd88e99b9d3aeb353bbf8e22b8ad23e07832e66281e0ebdb5681b4357d3'
ELIGIBILITY_DIGEST = 'a8e7a0cffe350c19f32e59b71d66b11362ae65762e834f3aa32a2442e8f7502c'
GROUPS = {'stop_pipo': (6,), 'phase_controls': (7, 8, 9),
          'season': (10, 11, 12), 'force': (13,)}
PROJECTIONS = {
    'closing/dbm/PhaseOutTbl': ('DBM/PhaseOutTbl', MdmFixturePhaseOut),
    'closing/dbm/PhaseInTbl': ('DBM/PhaseInTbl', MdmFixturePhaseIn),
    'closing/control_aux/phase_map': ('DBM/PhaseInPhaseOutMap', MdmFixturePhaseMap),
    'closing/control_aux/season_status': ('DBM/SeasonalityStatus', MdmFixtureSeasonStatus),
}


def configurations():
    root = Path(__file__).resolve().parents[1] / 'config'
    return {name: hashlib.sha256((root / ('mdm_' + name + '.json')).read_bytes()).hexdigest()
            for name in ('sob', 'moq', *GROUPS)}


def fields(model):
    return [f.name for f in model._meta.local_concrete_fields
            if f.name not in ('id', 'source', 'ordinal', 'revision')]


def require(source):
    from mta.mdm.source import DLL
    from mta.presentation import fixture
    from mta.presentation.context import selected_run
    row = MdmTargetFixture.objects.get(source=source)
    p = row.receipt
    run = selected_run()
    if (source.digest != SOURCE or source.dll_digest != DLL
            or connection.settings_dict['NAME'] != DATABASE or not fixture.enabled()
            or str(run.pk) != RUN or row.run_id != run.pk
            or p.get('schema') != SCHEMA or p.get('authority') != AUTHORITY
            or p.get('source_digest') != SOURCE or p.get('run_id') != RUN
            or p.get('dataset_manifest_sha256') != MANIFEST
            or p.get('input_digest') != INPUT_DIGEST
            or p.get('configuration') != configurations() or digest(p) != row.digest):
        raise ValueError('Target MDM consumer fixture identity differs')
    return row


def require_family(source, owner, group):
    """Return false only for the untouched original owner contract."""
    if owner.provenance.get('schema') != SCHEMA:
        return False
    row = require(source)
    expected = dict(schema=SCHEMA, authority=AUTHORITY, fixture_digest=row.digest,
                    source_digest=SOURCE, group=group)
    if (owner.provenance != expected or owner.receipt_digest != digest(expected)
            or owner.last_run_id != row.run_id):
        raise ValueError('Target MDM family owner differs')
    families = list(MdmFamilySource.objects.filter(source=source, master_id__in=GROUPS[group]))
    if len(families) != len(GROUPS[group]) or any(
            f.receipt != expected or f.digest != digest(expected) for f in families):
        raise ValueError('Target MDM complete family receipt differs')
    return True


def consumer_rows(source, run, path):
    """Only MDM consumers may read these separate native fixture projections."""
    from mta.presentation.selective import image_rows
    if getattr(source, 'digest', None) != SOURCE:
        return image_rows(run, path)
    if MdmTargetFixture.objects.filter(source=source).exists():
        owner = require(source)
        if owner.run_id != run.pk:
            raise ValueError('Target MDM selected fixture differs')
        if path in PROJECTIONS:
            name, model = PROJECTIONS[path]
            rows = list(model.objects.filter(source=source).order_by('ordinal').values(*fields(model)))
            if digest(storage(rows)) != owner.receipt['tables'][name]['digest']:
                raise ValueError('Target MDM immutable projection differs: ' + name)
            return rows
    return image_rows(run, path)


def daily_pair_rows(source, run, sku, location):
    """Bound the fixture graph in SQL; preserve date ties by source ordinal."""
    from mta.presentation.selective import image_metadata, image_query
    from mta.runtime.relational_state import quote, wire_value
    from mta.mdm.task_reads import sql_key
    owner = require(source)
    if owner.run_id != run.pk:
        raise ValueError('Target MDM selected fixture differs')
    path = 'closing/dbm/DailyConsumption'
    item = image_metadata(run, path)
    fields = {name: (column, kind) for name, column, kind in item['fields']}
    query, params = image_query(run, path, metadata=item)
    names = ('ReportDate', 'Stock', 'GIT')
    select = ','.join(quote(fields[n][0]) for n in names)
    where = ' AND '.join('lower(rtrim(' + quote(fields[n][0]) + '))=%s'
                         for n in ('SKUCode', 'WhCode'))
    with connection.cursor() as c:
        c.execute('SELECT ' + select + ' FROM (' + query + ') h WHERE ' + where +
            ' ORDER BY ' + quote(fields['ReportDate'][0]) +
            ' DESC NULLS LAST,vf_ordinal LIMIT 180', [*params, sql_key(sku), sql_key(location)])
        return [{n: wire_value(v, fields[n][1]) for n, v in zip(names, row)}
                for row in c.fetchall()]


@transaction.atomic
def install(package, expected_digest):
    """Install only the approved target envelope, atomically and without reset."""
    from mta.mdm.source import DLL
    from mta.mdm.supplier_source import install as install_supplier
    from mta.runtime.mdm_skuloc_models import MdmSkuLocCurrent
    from mta.mdm.skuloc_source import PINS, COUNTS, SOURCE_DIGEST as SKULOC_DIGEST
    from mta.runtime.mdm_force_models import MdmForceOwner
    from mta.runtime.mdm_season_models import MdmSeasonOwner, MdmSeasonCurrent, MdmSeasonEligibility
    from mta.runtime.mdm_stop_pipo_models import MdmStopPipoOwner
    from mta.runtime.mdm_phase_controls_models import MdmPhaseControlsOwner
    from mta.runtime.mdm_daily_models import MdmDailyInputCapture
    from mta.runtime.mdm_integration_models import MdmSourceIntegration
    from mta.presentation.context import selected_run
    from mta.presentation import fixture
    from mta.mdm.supplier_revisions import lock_transaction

    if (digest(package) != expected_digest or expected_digest != INPUT_DIGEST
            or package.get('schema') != SCHEMA
            or package.get('authority') != AUTHORITY or package.get('source_digest') != SOURCE
            or package.get('run_id') != RUN or package.get('dataset_manifest_sha256') != MANIFEST
            or package.get('configuration') != configurations()):
        raise ValueError('Exact approved target input envelope required')
    with connection.cursor() as c:
        c.execute('SELECT current_database()')
        if c.fetchone()[0] != DATABASE:
            raise ValueError('Target MDM database differs')
    run = selected_run()
    if not fixture.enabled() or str(run.pk) != RUN:
        raise ValueError('Target MDM selected fixture differs')
    source = MdmSource.objects.select_for_update().get(digest=SOURCE, dll_digest=DLL)
    lock_transaction(source.pk)
    if (MdmTargetFixture.objects.filter(source=source).exists()
            or MdmSourceIntegration.objects.filter(source=source).exists()
            or MdmDailyInputCapture.objects.filter(source=source).exists()
            or set(MdmFamilySource.objects.filter(source=source).values_list('master_id', flat=True)) != {2, 3}):
        raise ValueError('Target onboarding requires unchanged unsealed three-family fixture')
    tables = package['tables']
    counts = {'Importer/SOBDataRaw': 97, 'Importer/MOQDataRaw1': 1791,
        'Importer/MOQDataRaw2': 1496, 'Importer/PhaseOutStop': 0, 'Importer/PhaseOut': 0,
        'Importer/PhaseInNorms': 0, 'Importer/Seasonality': 0, 'Importer/ForceNormChange': 0,
        'DBM/PhaseOutTbl': 77, 'DBM/PhaseInTbl': 0, 'DBM/PhaseInPhaseOutMap': 77,
        'DBM/Seasonality': 83, 'DBM/SeasonalityStatus': 11}
    if set(tables) != set(counts) or any(len(tables[n]) != count for n, count in counts.items()):
        raise ValueError('Exact retained target population roster differs')
    # File/source hashes are frozen by the extraction receipt; do not admit a
    # bare count-only envelope, a substituted test catalogue or inferred empties.
    provenance = package.get('provenance', {})
    if (provenance.get('dataset_manifest_sha256') != MANIFEST
            or set(provenance.get('tables', {})) != set(counts)
            or any(provenance['tables'][n].get('digest') != digest(tables[n]) for n in counts)):
        raise ValueError('Complete retained table provenance required')
    family = MdmFamilySource.objects.get(source=source, master_id=3)
    if (family.digest != SKULOC_DIGEST or family.receipt != {
            name: dict(sha256=PINS[name], rows=COUNTS[name]) for name in PINS}):
        raise ValueError('Exact installed target SKU-location receipt required')
    eligibility = list(MdmSkuLocCurrent.objects.filter(source=source, owner='Importer')
                       .order_by('ordinal').values('SKUCode', 'WhCode', 'Norm'))
    if len(eligibility) != 97097 or digest(storage(eligibility)) != ELIGIBILITY_DIGEST:
        raise ValueError('Target NMS current eligibility roster differs')
    receipt = {k: package[k] for k in ('schema', 'authority', 'source_digest',
        'run_id', 'dataset_manifest_sha256', 'configuration')}
    receipt.update(input_digest=expected_digest, provenance_digest=digest(provenance),
        state_kind='native-consumer-fixture-not-calculated',
        tables={n: dict(rows=len(rows), digest=digest(rows)) for n, rows in tables.items()},
        eligibility=dict(rows=len(eligibility), digest=digest(storage(eligibility))))
    with connection.cursor() as c:
        c.execute("SELECT set_config('fresh.target_mdm_install',%s,true)", [str(source.pk)])
    fixture_digest = digest(receipt)
    install_supplier(source, {n: tables['Importer/' + n] for n in
        ('SOBDataRaw', 'MOQDataRaw1', 'MOQDataRaw2')}, moq_format='WithoutDestLoc',
        upload_log_active=True, provenance=dict(schema=SCHEMA, authority=AUTHORITY,
            target_fixture_digest=fixture_digest, input_digest=expected_digest))
    from mta.mdm.supplier_source import MODELS as supplier_models
    for name, model in supplier_models.items():
        actual = list(model.objects.filter(source=source).order_by('ordinal').values(*fields(model)))
        if digest(storage(actual)) != digest(tables['Importer/' + name]):
            raise ValueError('Target supplier typed readback differs: ' + name)
    for name, model in PROJECTIONS.values():
        rows = tables[name]
        if any(set(r) != set(fields(model)) for r in rows):
            raise ValueError('Target projection columns differ: ' + name)
        model.objects.bulk_create([model(source=source, ordinal=i, **r)
            for i, r in enumerate(rows, 1)], batch_size=500)
        actual = list(model.objects.filter(source=source).order_by('ordinal').values(*fields(model)))
        if digest(storage(actual)) != digest(rows):
            raise ValueError('Target projection typed readback differs: ' + name)
    owners = {'force': MdmForceOwner, 'season': MdmSeasonOwner,
              'stop_pipo': MdmStopPipoOwner, 'phase_controls': MdmPhaseControlsOwner}
    for group, model in owners.items():
        p = dict(schema=SCHEMA, authority=AUTHORITY, fixture_digest=fixture_digest,
                 source_digest=SOURCE, group=group)
        values = dict(source=source, last_run=run, provenance=p, receipt_digest=digest(p))
        if group == 'force':
            values.update(opening_digest=digest([]), closing_digest=digest([]),
                          root_state_digest=fixture_digest, closing_log_digest=digest([]))
        elif group == 'season':
            values.update(root_state_digest=fixture_digest, closing_queue_digest=digest([]),
                          closing_current_digest=digest(tables['DBM/Seasonality']))
        elif group == 'phase_controls':
            values['closing_queue_digest'] = digest(dict(phase_requests=[], phase_in_requests=[]))
        else:
            values['closing_queue_digest'] = digest([])
        model.objects.create(**values)
        for mid in GROUPS[group]:
            MdmFamilySource.objects.create(source=source, master_id=mid, receipt=p, digest=digest(p))
    season_rows = tables['DBM/Seasonality']
    if any(set(r) != set(fields(MdmSeasonCurrent)) for r in season_rows):
        raise ValueError('Target season current columns differ')
    MdmSeasonCurrent.objects.bulk_create([MdmSeasonCurrent(source=source, ordinal=i, **r)
        for i, r in enumerate(season_rows, 1)], batch_size=500)
    actual = list(MdmSeasonCurrent.objects.filter(source=source).order_by('ordinal')
                  .values(*fields(MdmSeasonCurrent)))
    if digest(storage(actual)) != digest(season_rows):
        raise ValueError('Target seasonal current typed readback differs')
    with connection.cursor() as c:
        c.execute("SELECT set_config('fresh.season_eligibility_source',%s,true)", [str(source.pk)])
    MdmSeasonEligibility.objects.bulk_create([MdmSeasonEligibility(source=source, ordinal=i, **r)
        for i, r in enumerate(eligibility, 1)], batch_size=1000)
    actual = list(MdmSeasonEligibility.objects.filter(source=source).order_by('ordinal')
                  .values('SKUCode', 'WhCode', 'Norm'))
    if digest(storage(actual)) != ELIGIBILITY_DIGEST:
        raise ValueError('Target seasonal eligibility typed readback differs')
    # Receipt insertion is the irreversible end of bootstrap, under the same
    # source lock. Even a stale/replayed installation GUC cannot append later.
    installed = MdmTargetFixture.objects.create(source=source, run=run,
                                               receipt=receipt, digest=fixture_digest)
    with connection.cursor() as c:
        c.execute("SELECT set_config('fresh.season_eligibility_source','',true)")
        c.execute("SELECT set_config('fresh.target_mdm_install','',true)")
    require(source)
    for group, model in owners.items():
        require_family(source, model.objects.get(source=source), group)
    return installed
