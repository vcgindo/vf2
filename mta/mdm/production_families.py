"""Bootstrap optional MDM owners from the sealed native opening.

This module grants no day acceptance.  It projects only typed populations that
are already part of ``ProductionInitialization`` and seals the complete 1-13
owner roster before the first capture can be made.
"""
from datetime import datetime
import hashlib
from pathlib import Path
from zoneinfo import ZoneInfo

from django.conf import settings
from django.db import connection, transaction

from mta.serialization import digest, storage
from mta.presentation.request_scope import once_per_request
from mta.runtime.opening_scope import immutable, opening_operation
from mta.mdm.initialization_contract import SOURCE_SCHEMA
from mta.runtime.models import CalculationRun, ProductionInitialization
from mta.runtime.mdm_daily_models import MdmDailyInputCapture
from mta.runtime.mdm_models import MdmFamilySource, MdmSource
from mta.runtime.mdm_integration_models import MdmSourceIntegration

OWNER_SCHEMA = 'fresh-production-mdm-opening-owner-v1'
INTEGRATION_SCHEMA = 'fresh-production-mdm-integration-v1'
GROUPS = {'supplier': (4, 5), 'stop_pipo': (6,), 'phase_controls': (7, 8, 9),
          'season': (10, 11, 12), 'force': (13,)}


def legacy_adapter_paths():
    names = ['mdm/'+name+'.py' for name in ('production_families', 'daily_input',
        'daily_current', 'integration_source', 'owned_namespace', 'native_source', 'source', 'families')]
    names += ['mdm/'+family+'_'+suffix+'.py' for family in
        ('supplier', 'force', 'season', 'stop_pipo', 'phase_controls')
        for suffix in ('source', 'capture', 'revisions')]
    names += ['runtime/'+name+'.py' for name in ('production_daily', 'production_preflight', 'temporal',
        'services', 'input_storage', 'mdm_stop_pipo_models', 'mdm_phase_controls_models')]
    names += ['runtime/migrations/0120_native_mdm_openings.py',
        'runtime/migrations/0121_native_daily_transaction_input.py',
        'runtime/management/commands/run_production_day.py']
    return names


def adapter_digest():
    root = Path(__file__).resolve().parents[1]
    names = legacy_adapter_paths() + [
        'mdm/location_tasks.py', 'mdm/location_publication.py',
        'mdm/location_projection.py', 'mdm/location_transition.py',
        'runtime/mdm_projection_models.py', 'runtime/models.py',
        'runtime/receipt_integrity.py',
        'runtime/migrations/0132_native_synchronous_location_add.py',
        'runtime/migrations/0133_mdmclosingprojectionreceipt.py',
        'runtime/migrations/0134_native_closing_projection_guards.py',
        'runtime/migrations/0135_closing_projection_parent_guard.py']
    return digest({name: hashlib.sha256((root/name).read_bytes()).hexdigest() for name in names})


def _configuration():
    from mta.mdm.supplier_source import CONFIGURATION as supplier
    from mta.mdm.stop_pipo_source import configuration_sha as stop
    from mta.mdm.phase_controls_source import configuration_sha as phase
    from mta.mdm.season_source import configuration_sha as season
    from mta.mdm.force_source import configuration_sha as force
    return {'supplier': supplier, 'stop_pipo': stop(), 'phase_controls': phase(),
            'season': season(), 'force': force()}


@once_per_request
def _opening_input(initialization):
    from mta.mdm.initialization import read_initialized_input
    return read_initialized_input(initialization)


@once_per_request
def _verified_initialization(source, *, input_sha256=None, input_schema=None):
    """Verify the immutable H2 seal after optional family rows have been added."""
    from mta.mdm.initialization import implementation_digest, opening_digests
    from mta.mdm.initialization_contract import SCHEMA
    from mta.mdm.owned_namespace import verify_binding
    initialization = ProductionInitialization.objects.select_related('source').get(source=source)
    p = source.receipt
    if (input_schema is not None and input_schema != SCHEMA
            or input_sha256 is not None and input_sha256 != initialization.input_sha256
            or p.get('schema') != SOURCE_SCHEMA or source.dll_digest != ''
            or source.implementation_digest != implementation_digest()
            or initialization.implementation_digest != source.implementation_digest
            or digest(p) != source.digest or p.get('initialization_id') != str(initialization.pk)
            or p.get('input_sha256') != initialization.input_sha256
            or p.get('recipe_sha256') != initialization.recipe_sha256
            or p.get('configuration_digest') != initialization.configuration_digest
            or p.get('implementation_digest') != initialization.implementation_digest
            or p.get('opening_identity') != initialization.opening_identity
            or p.get('opening_date') != initialization.opening_date.isoformat()
            or p.get('content_digest') != initialization.input_digest
            or p.get('database') != source.database_name
            or digest(initialization.receipt) != initialization.receipt_digest
            or initialization.receipt != dict(schema='native-initialization-seal-v1',
                source_digest=source.digest, manifest_digest=initialization.input_manifest_digest,
                content_digest=initialization.input_digest)):
        raise ValueError('Native initialization/source identity drift')
    verify_binding(p)
    frame = _opening_input(initialization)
    hashes = opening_digests(initialization, frame)
    immutable(initialization, 'root-digest', lambda: hashes['state'])
    if (hashes['content'] != initialization.input_digest
            or hashes['profile'] != initialization.configuration_digest
            or hashes['recipe'] != initialization.recipe_sha256
            or frame['opening']['identity'] != initialization.opening_identity
            or frame['opening']['opening_date'] != initialization.opening_date.isoformat()):
        raise ValueError('Native opening/configuration full readback drift')
    from mta.mdm.initialization import families_for
    from mta.mdm.master_owners import owner_batches
    if p.get('families') != immutable(initialization, 'families',
            lambda: families_for(owner_batches(frame['opening']['state'], strict=True))):
        raise ValueError('Native initialization master projection identity drift')
    return initialization, frame


def require_initialization(source, *, input_sha256=None, input_schema=None):
    return _verified_initialization(source, input_sha256=input_sha256,
                                    input_schema=input_schema)[0]


def prepare_opening(source):
    """Precompute immutable family facts without opening a write transaction."""
    initialization, frame = _verified_initialization(source)
    _, bags = _expected(initialization, frame=frame)
    for family in GROUPS:
        _provenance(initialization, family, bags[family])
    return initialization


def _setting(rows, name):
    values = [row['Value'] for row in rows if row['Parameter'] == name]
    if len(values) != 1:
        raise ValueError('Native MDM opening requires one explicit '+name)
    return values[0]


def _fields(model, excluded=('id', 'source', 'ordinal', 'revision')):
    return [f.name for f in model._meta.fields if f.name not in excluded]


def _create_rows(model, source, rows, *, ordinal=False, mapping=None):
    names = _fields(model)
    expected = {(mapping or {}).get(name, name) for name in names}
    if any(set(row) != expected for row in rows):
        raise ValueError('Native MDM opening fields differ: '+model.__name__)
    records = []
    for index, row in enumerate(rows, 1):
        values = {name: row[(mapping or {}).get(name, name)] for name in names}
        if model.__name__ == 'MdmForceUploadLog':
            stamp = datetime.fromisoformat(values['ActionTimeStamp'])
            if stamp.tzinfo is None:
                stamp = stamp.replace(tzinfo=ZoneInfo(settings.VF_MTA_ACTION_TIME_ZONE))
            values['ActionTimeStamp'] = stamp
        records.append(model(source=source, **({'ordinal': index} if ordinal else {}), **values))
        if len(records) == 500:
            model.objects.bulk_create(records, batch_size=500)
            records.clear()
    if records:
        model.objects.bulk_create(records, batch_size=500)


def _read_rows(model, source, *, ordinal=False, mapping=None):
    names = _fields(model)
    ordering = 'ordinal' if ordinal else 'id'
    rows = model.objects.filter(source=source).order_by(ordering).values(*names)
    for row in rows.iterator(chunk_size=500):
        if model.__name__ == 'MdmForceUploadLog':
            from mta.mdm.force_capture import native_log
            row = native_log(row)
        if mapping:
            row = {mapping.get(name, name): row[name] for name in names}
        yield storage(row)


def _same_bags(actual, expected):
    """Compare every live value/occurrence in order without whole-table copies."""
    from itertools import zip_longest
    from mta.row_sequences import RecordRows
    if actual.keys() != expected.keys():
        return False
    missing = object()
    for name, value in expected.items():
        if isinstance(value, (list, tuple, RecordRows)):
            for observed, wanted in zip_longest(actual[name], value, fillvalue=missing):
                if observed is missing or wanted is missing or storage(observed) != storage(wanted):
                    return False
        elif storage(actual[name]) != storage(value):
            return False
    return True


def _provenance(initialization, family, bags):
    return dict(schema=OWNER_SCHEMA, family=family,
        source_digest=initialization.source.digest,
        initialization_id=str(initialization.pk),
        initialization_content_digest=initialization.input_digest,
        configuration_sha256=_configuration()[family],
        opening_bag_digests=immutable(initialization, 'bag-digests:'+family,
            lambda: {name: digest(storage(rows)) for name, rows in sorted(bags.items())}))


def _expected(initialization, *, frame=None):
    return immutable(initialization, 'family-bags', lambda: _build_expected(initialization, frame=frame))


def _build_expected(initialization, *, frame=None):
    if frame is None:
        frame = _opening_input(initialization)
    state = frame['opening']['state']
    settings = state['importer_settings']
    from mta.mdm.force_capture import FIELDS as force_fields, LOG_FIELDS
    from mta.application.r1_seasonality import REQUEST_FIELDS, SEASON_FIELDS
    supplier = {name: state['complete'][name]
                for name in ('SOBDataRaw', 'MOQDataRaw1', 'MOQDataRaw2')}
    supplier['NMSMOQInputDataFormat'] = _setting(settings, 'NMSMOQInputDataFormat')
    supplier['ActivateNMSUIUploadLogs'] = _setting(settings, 'ActivateNMSUIUploadLogs')
    return frame, {
        'supplier': supplier,
        'force': {'ForceNormChange': [{name: row[name] for name in force_fields}
                                      for row in state['importer']['ForceNormChange']],
                  'upload_log': state['controls']['upload_log']},
        'season': {'season_requests': [{name: row[name] for name in REQUEST_FIELDS}
                                       for row in state['control_aux']['season_requests']],
                   'Seasonality': [{name: row[name] for name in SEASON_FIELDS}
                                   for row in state['dbm']['Seasonality']],
                   'eligibility': [{name: row[name] for name in ('SKUCode', 'WhCode', 'Norm')}
                                   for row in state['importer']['MasterData']]},
        'stop_pipo': {'phase_stops': state['control_aux']['phase_stops']},
        'phase_controls': {name: state['control_aux'][name]
                           for name in ('phase_requests', 'phase_in_requests')},
    }


def _actual(source, family):
    if family == 'supplier':
        from mta.mdm.supplier_source import MODELS
        from mta.runtime.mdm_supplier_models import MdmSupplierConfiguration
        config = MdmSupplierConfiguration.objects.get(source=source)
        result = {name: _read_rows(model, source, ordinal=True) for name, model in MODELS.items()}
        result.update(NMSMOQInputDataFormat=config.moq_format,
                      ActivateNMSUIUploadLogs='1' if config.upload_log_active else '0')
        return result
    if family == 'force':
        from mta.runtime.mdm_force_models import MdmForceQueue, MdmForceUploadLog
        return {'ForceNormChange': _read_rows(MdmForceQueue, source),
                'upload_log': _read_rows(MdmForceUploadLog, source,
                    mapping={'WhCode': 'WHCode'})}
    if family == 'season':
        from mta.runtime.mdm_season_models import MdmSeasonQueue, MdmSeasonCurrent, MdmSeasonEligibility
        return {'season_requests': _read_rows(MdmSeasonQueue, source),
                'Seasonality': _read_rows(MdmSeasonCurrent, source, ordinal=True),
                'eligibility': _read_rows(MdmSeasonEligibility, source, ordinal=True)}
    if family == 'stop_pipo':
        from mta.runtime.mdm_stop_pipo_models import MdmStopPipoQueue
        return {'phase_stops': _read_rows(MdmStopPipoQueue, source)}
    from mta.mdm.phase_controls_source import QUEUES
    return {name: _read_rows(model, source) for name, model in QUEUES.items()}


def require_owner(source, owner, family):
    if family not in GROUPS or owner.source_id != source.pk:
        raise ValueError('Native MDM owner/source differs')
    initialization = ProductionInitialization.objects.get(source=source)
    frame, bags = _expected(initialization)
    unchanged_opening = not MdmDailyInputCapture.objects.filter(source=source).exists()
    return _verify_owner(source, owner, family, initialization, frame, bags, unchanged_opening)


def _verify_owner(source, owner, family, initialization, frame, bags, unchanged_opening):
    """Use one caller-owned verified frame, never a cache across operations."""
    if family not in GROUPS or owner.source_id != source.pk:
        raise ValueError('Native MDM owner/source differs')
    expected = _provenance(initialization, family, bags[family])
    if (source.receipt.get('schema') != SOURCE_SCHEMA or owner.provenance != expected
            or owner.receipt_digest != digest(expected)
            or hasattr(owner, 'root_state_digest')
            and owner.root_state_digest != immutable(initialization, 'root-digest', lambda: digest(frame['opening']['state']))
            or unchanged_opening and not _same_bags(_actual(source, family), bags[family])):
        raise ValueError('Native MDM '+family+' opening owner differs')
    rows = list(MdmFamilySource.objects.filter(source=source,
        master_id__in=GROUPS[family]).order_by('master_id'))
    if ([row.master_id for row in rows] != list(GROUPS[family])
            or any(row.receipt != expected or row.digest != digest(expected) for row in rows)):
        raise ValueError('Native MDM '+family+' family receipt differs')
    return owner


def _install(initialization, family, bags, root_digest):
    source = initialization.source
    provenance = _provenance(initialization, family, bags)
    receipt_digest = digest(provenance)
    if family == 'supplier':
        from mta.mdm.supplier_source import MODELS
        from mta.runtime.mdm_supplier_models import MdmSupplierConfiguration
        fmt, active = bags['NMSMOQInputDataFormat'], bags['ActivateNMSUIUploadLogs']
        if fmt not in ('WithDestLoc', 'WithoutDestLoc') or active not in ('0', '1'):
            raise ValueError('Native supplier configuration differs')
        owner = MdmSupplierConfiguration.objects.create(source=source, moq_format=fmt,
            upload_log_active=active == '1', provenance=provenance, receipt_digest=receipt_digest)
        for name, model in MODELS.items():
            _create_rows(model, source, bags[name], ordinal=True)
    elif family == 'force':
        from mta.runtime.mdm_force_models import MdmForceOwner, MdmForceQueue, MdmForceUploadLog
        queue, logs = bags['ForceNormChange'], bags['upload_log']
        owner = MdmForceOwner.objects.create(source=source, provenance=provenance,
            receipt_digest=receipt_digest, opening_digest=digest(queue), closing_digest=digest(queue),
            root_state_digest=root_digest, closing_log_digest=digest(logs))
        _create_rows(MdmForceQueue, source, queue)
        _create_rows(MdmForceUploadLog, source, logs, mapping={'WhCode': 'WHCode'})
    elif family == 'season':
        from mta.runtime.mdm_season_models import MdmSeasonOwner, MdmSeasonQueue, MdmSeasonCurrent, MdmSeasonEligibility
        queue, current, eligible = bags['season_requests'], bags['Seasonality'], bags['eligibility']
        owner = MdmSeasonOwner.objects.create(source=source, provenance=provenance,
            receipt_digest=receipt_digest, root_state_digest=root_digest,
            closing_queue_digest=digest(queue), closing_current_digest=digest(current))
        _create_rows(MdmSeasonQueue, source, queue)
        _create_rows(MdmSeasonCurrent, source, current, ordinal=True)
        _create_rows(MdmSeasonEligibility, source, eligible, ordinal=True)
    elif family == 'stop_pipo':
        from mta.runtime.mdm_stop_pipo_models import MdmStopPipoOwner, MdmStopPipoQueue
        queue = bags['phase_stops']
        owner = MdmStopPipoOwner.objects.create(source=source, provenance=provenance,
            receipt_digest=receipt_digest, root_state_digest=root_digest,
            closing_queue_digest=digest(queue))
        _create_rows(MdmStopPipoQueue, source, queue)
    else:
        from mta.runtime.mdm_phase_controls_models import MdmPhaseControlsOwner
        from mta.mdm.phase_controls_source import QUEUES
        owner = MdmPhaseControlsOwner.objects.create(source=source, provenance=provenance,
            receipt_digest=receipt_digest, root_state_digest=root_digest,
            closing_queue_digest=digest(bags))
        for name, model in QUEUES.items():
            _create_rows(model, source, bags[name])
    for master_id in GROUPS[family]:
        MdmFamilySource.objects.create(source=source, master_id=master_id,
            receipt=provenance, digest=receipt_digest)
    return owner


def _read_execution_identity(seal):
    """Read a sealed, supported projection without relabelling its producer code.

    The immutable execution hashes describe the producer of these rows, not the
    currently installed presentation code. Execution and mutation callers never
    use this admission path.
    """
    from mta.mdm.location_projection import VERSION
    p = seal.receipt
    if (not isinstance(p, dict) or seal.digest != digest(p)
            or p.get('closing_projection_version') != VERSION):
        raise ValueError('Native MDM read execution seal or schema differs')
    result = {key: p.get(key) for key in
              ('adapter_digest', 'source_manifest_digest', 'closing_projection_version')}
    for key in ('adapter_digest', 'source_manifest_digest'):
        value = result[key]
        if (not isinstance(value, str) or len(value) != 64
                or any(c not in '0123456789abcdef' for c in value)):
            raise ValueError('Native MDM read execution identity is absent or invalid')
    return result


@once_per_request
def require_binding(source, *, read_only=False):
    initialization, frame = _verified_initialization(source)
    _, bags = _expected(initialization, frame=frame)
    unchanged_opening = not MdmDailyInputCapture.objects.filter(source=source).exists()
    seal = MdmSourceIntegration.objects.get(source=source)
    families = {'1': digest(source.receipt['families']['1'])}
    families.update({str(row.master_id): row.digest for row in
                     MdmFamilySource.objects.filter(source=source).order_by('master_id')})
    from mta.mdm.location_transition import integration_identity
    code_identity = (_read_execution_identity(seal) if read_only
                     else integration_identity(source, initialization, seal))
    receipt = dict(schema=INTEGRATION_SCHEMA, source_digest=source.digest,
        initialization_id=str(initialization.pk),
        initialization_content_digest=initialization.input_digest,
        families=families, required_families=list(range(1, 14)),
        configuration=_configuration(), **code_identity)
    if (families.keys() != {str(i) for i in range(1, 14)}
            or seal.receipt != receipt or seal.digest != digest(receipt)):
        raise ValueError('Native complete MDM integration seal differs')
    owners = {
        'supplier': __import__('mta.runtime.mdm_supplier_models', fromlist=['MdmSupplierConfiguration']).MdmSupplierConfiguration.objects.get(source=source),
        'force': __import__('mta.runtime.mdm_force_models', fromlist=['MdmForceOwner']).MdmForceOwner.objects.get(source=source),
        'season': __import__('mta.runtime.mdm_season_models', fromlist=['MdmSeasonOwner']).MdmSeasonOwner.objects.get(source=source),
        'stop_pipo': __import__('mta.runtime.mdm_stop_pipo_models', fromlist=['MdmStopPipoOwner']).MdmStopPipoOwner.objects.get(source=source),
        'phase_controls': __import__('mta.runtime.mdm_phase_controls_models', fromlist=['MdmPhaseControlsOwner']).MdmPhaseControlsOwner.objects.get(source=source),
    }
    for family, owner in owners.items():
        _verify_owner(source, owner, family, initialization, frame, bags, unchanged_opening)
    return seal


@opening_operation
def bootstrap_native_families(initialization):
    # Decode/hash the sealed opening before opening a write transaction. Live
    # owners and receipts are still checked again under the source lock below.
    _verified_initialization(initialization.source)
    _expected(initialization)
    from mta.mdm.initialization import opening_digests
    root_digest = opening_digests(initialization, _opening_input(initialization))['state']
    immutable(initialization, 'root-digest', lambda: root_digest)
    for family in GROUPS:
        _provenance(initialization, family, _expected(initialization)[1][family])
    with transaction.atomic():
        return _bootstrap_native_families(initialization)


def _bootstrap_native_families(initialization):
    from mta.mdm.initialization import verify
    from mta.mdm.supplier_revisions import source_lock
    identity, source_id = initialization.pk, initialization.source_id
    with source_lock(source_id):
        initialization = ProductionInitialization.objects.select_for_update().select_related('source').get(pk=identity)
        source = MdmSource.objects.select_for_update().get(pk=source_id)
        initialization.source = source
        existing = MdmSourceIntegration.objects.filter(source=source).first()
        if existing is not None:
            return require_binding(source)
        if (CalculationRun.objects.exists() or MdmDailyInputCapture.objects.filter(source=source).exists()
                or MdmFamilySource.objects.filter(source=source).exclude(master_id__in=(2, 3)).exists()):
            raise ValueError('Native MDM bootstrap requires an untouched initialized opening')
        verify(initialization, current_masters=True)
        frame, bags = _expected(initialization)
        root_digest = immutable(initialization, 'root-digest', lambda: digest(frame['opening']['state']))
        with connection.cursor() as cursor:
            cursor.execute("SELECT set_config('fresh.native_mdm_families',%s,true), "
                "set_config('fresh.mdm_supplier_bootstrap',%s,true), "
                "set_config('fresh.stop_pipo_install',%s,true), "
                "set_config('fresh.phase_controls_install',%s,true), "
                "set_config('fresh.season_eligibility_source',%s,true)",
                [str(initialization.pk), str(source.pk), str(source.pk), str(source.pk), str(source.pk)])
        owners = {family: _install(initialization, family, bags[family], root_digest)
                  for family in ('supplier', 'force', 'season', 'stop_pipo', 'phase_controls')}
        families = {'1': digest(source.receipt['families']['1'])}
        families.update({str(row.master_id): row.digest for row in
                         MdmFamilySource.objects.filter(source=source).order_by('master_id')})
        from mta.mdm.location_transition import source_manifest_digest
        from mta.mdm.location_projection import VERSION
        receipt = dict(schema=INTEGRATION_SCHEMA, source_digest=source.digest,
            initialization_id=str(initialization.pk),
            initialization_content_digest=initialization.input_digest,
            families=families, required_families=list(range(1, 14)),
            configuration=_configuration(), adapter_digest=adapter_digest(),
            closing_projection_version=VERSION, source_manifest_digest=source_manifest_digest())
        MdmSourceIntegration.objects.create(source=source, receipt=receipt, digest=digest(receipt))
        for family, owner in owners.items():
            _verify_owner(source, owner, family, initialization, frame, bags, True)
        seal = require_binding(source)
        with connection.cursor() as cursor:
            cursor.execute("SELECT set_config('fresh.native_mdm_families','',true)")
        return seal
