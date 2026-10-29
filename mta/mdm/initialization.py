"""Atomic native instance initialization from supplied masters and opening facts."""
from collections import Counter
import hashlib
from itertools import zip_longest
import json
from pathlib import Path
import uuid

from django.db import connection, transaction
from mta.serialization import digest, storage
from mta.application.stage_observation import observed, stage, observe_exit
from mta.runtime.models import CalculationRun, MdmSource, ProductionInitialization
from mta.runtime.mdm_models import MdmFamilySource, MdmTask, MdmSubTask
from mta.runtime.mdm_daily_models import MdmDailyInputCapture
from mta.mdm.initialization_contract import decode, SOURCE_SCHEMA, SCHEMA, CURRENT_LIST_PATHS
from mta.mdm.master_owners import business_fields, owner_batches
from mta.mdm.owned_namespace import authorize_install, verify_binding
from mta.runtime.input_storage import save_input, read_input
from mta.runtime import opening_storage
from mta.runtime.opening_scope import immutable, opening_operation
from mta.mdm.initialization_rows import select as initialization_table


IMPLEMENTATION_FILES = ('mdm/initialization.py', 'mdm/initialization_preparation.py', 'mdm/initialization_transport.py', 'runtime/input_v3.py', 'runtime/input_reader.py', 'mdm/initialization_contract.py', 'mdm/initialization_rows.py', 'mdm/master_owners.py',
        'mdm/owned_namespace.py', 'runtime/initialization_models.py', 'runtime/opening_storage.py',
        'runtime/input_storage.py', 'runtime/relational_state.py',
        'runtime/mdm_models.py', 'runtime/mdm_skuloc_models.py', 'serialization.py',
        'row_sequences.py','application/streamed_input.py','runtime/opening_scope.py',
        'mdm/skuloc_tasks.py', 'mdm/skuloc_audit.py',
        'mdm/native_audit.py', 'mdm/native_audit_policy.py',
        'runtime/native_audit_models.py', 'runtime/operational_opening.py',
        'runtime/migrations/0136_native_upload_audit.py',
        'runtime/migrations/0137_native_audit_guards.py',
        'runtime/migrations/0128_native_skuloc_upload_audit.py',
        'runtime/migrations/0129_skuloc_modify_audit_nullable_parent.py',
        'application/daily_finalization.py', 'application/r1_daily_input.py', 'domain/complete_daily_scalars.py',
        'application/r1_importer_master.py', 'config/daily_finalization_flags.json',
        'domain/dbm_norm012.py', 'domain/btr_finalization.py', 'domain/dbm_conditional.py',
        'domain/dbm_auto_acceptance.py',
        'domain/btr_rationing_history.py','runtime/btr_history_storage.py',
        'config/btr_rationing_history_v1.json','runtime/migrations/0123_btr_rationing_history.py',
        'domain/order_identity.py','domain/order_closing.py','domain/elephant_orders.py','application/r1_order_input.py',
        'application/r1_input.py','application/r1_calculation.py','application/r1_daily_entry.py','planning/engine.py','runtime/temporal.py','runtime/services.py',
        'application/r1_master_state.py','application/r1_norm_updates.py','application/r1_control_diagnostics.py',
        'mdm/phase_controls_capture.py',
        'domain/dbm_phase_recommendation.py', 'runtime/dbm_phase_storage.py',
        'config/dbm_phase_recommendation_v1.json',
        'runtime/migrations/0122_phase_recommendation_storage.py',
        'domain/dbm_selected_chain.py', 'temporal/chain.py',
        'runtime/production_preflight.py',
        'runtime/migrations/0117_production_initialization.py',
        'runtime/migrations/0118_initialization_typed_storage.py', 'runtime/migrations/0119_initialization_guards.py',
        'runtime/management/commands/initialize_production.py',
        'config/initialization_storage_v1.json', 'config/production_state_schema_v1.json',
        'runtime/daily_preparation.py', 'runtime/accepted_daily.py', 'runtime/batch_storage.py',
        'runtime/daily_feed.py', 'runtime/daily_feed_models.py', 'runtime/production_daily.py',
        'mdm/daily_current.py', 'config/daily_batch_storage_v1.json',
        'application/master_compatibility.py','application/master_preparation.py',
        'application/persistent_master.py','temporal/entry_preparation.py',
        'runtime/capture_preparation.py','runtime/master_revisions.py',
        'runtime/run_input_references.py','runtime/ingestion_admission.py','runtime/ingestion_upgrade.py',
        'runtime/captured_input.py','runtime/captured_recovery.py')


def current_implementation_digest():
    root = Path(__file__).resolve().parents[1]
    return digest({name: hashlib.sha256((root/name).read_bytes()).hexdigest()
                   for name in IMPLEMENTATION_FILES})


def implementation_digest():
    from release.native_identity import require_current
    identity = require_current()
    current = current_implementation_digest()
    if identity['implementation_sha256'] != current:
        raise ValueError('Native release implementation differs')
    return current


def families_for(batches):
    families = {str(i): dict(owners=[]) for i in (1, 2, 3)}
    for family, model, scope, rows, path in batches:
        families[str(family)]['owners'].append(dict(model=model.__name__, scope=scope,
            path=path, count=len(rows), digest=digest(storage(rows)),
            fields=[field.name for field in business_fields(model)]))
    return families


def verified_origin_implementation(source):
    current=implementation_digest()
    if source.implementation_digest==current:
        return current
    from mta.runtime.ingestion_upgrade import implementation_for
    return implementation_for(source)


def verify_current_masters(source, batches):
    counts = Counter()
    models = {}
    for _, model, scope, rows, path in batches:
        fields = [field.name for field in business_fields(model)]
        actual = model.objects.filter(source=source, **scope).order_by('ordinal').values(*fields).iterator(chunk_size=500)
        missing = object()
        for observed, expected in zip_longest(actual, rows, fillvalue=missing):
            if observed is missing or expected is missing or storage(observed) != storage(expected):
                raise ValueError('Native master typed readback differs: '+path)
        counts[model] += len(rows)
        models[model] = model
    for model in models:
        if model.objects.filter(source=source).count() != counts[model]:
            raise ValueError('Native master has unknown owners/occurrences: '+model.__name__)


@stage('opening_reconstruction')
def read_initialized_input(owner):
    # These are the initializer's explicit current-list contracts. Operational
    # histories outside these roots remain streamed and fully checksum-checked.
    return immutable(owner, 'frame', lambda: read_input(owner, image_reader=opening_storage.load_image,
        materialized_roots=(*CURRENT_LIST_PATHS, 'input/profile', 'input/pair_exclusions')))


def opening_digests(owner, frame):
    return immutable(owner, 'digests', lambda: dict(content=digest(frame),
        profile=digest(frame['profile']), recipe=digest(frame['recipe']),
        state=digest(frame['opening']['state'])))


def validated_master_batches(owner, frame):
    """Reuse only successful strict projections of this sealed opening.

    Fresh certification clears opening_scope before reconstructing persisted
    input, so prepared input cannot supply that evidence. Live master rows are
    still read and compared independently on every verification.
    """
    return immutable(owner, 'validated-master-batches',
        lambda: owner_batches(frame['opening']['state'], strict=True))


def verify(owner, *, expected_frame=None, current_masters=False):
    source = owner.source
    p = source.receipt
    if (p.get('schema') != SOURCE_SCHEMA or source.dll_digest != ''
            or source.implementation_digest != verified_origin_implementation(source)
            or owner.implementation_digest != source.implementation_digest
            or digest(p) != source.digest or p.get('initialization_id') != str(owner.pk)
            or p.get('input_sha256') != owner.input_sha256
            or p.get('configuration_digest') != owner.configuration_digest
            or p.get('recipe_sha256') != owner.recipe_sha256
            or p.get('opening_identity') != owner.opening_identity
            or p.get('opening_date') != owner.opening_date.isoformat()
            or p.get('content_digest') != owner.input_digest
            or digest(owner.receipt) != owner.receipt_digest
            or owner.receipt != dict(schema='native-initialization-seal-v1', source_digest=source.digest,
                manifest_digest=owner.input_manifest_digest, content_digest=owner.input_digest)):
        raise ValueError('Native initialization/source identity drift')
    verify_binding(p)
    frame = read_initialized_input(owner)
    hashes = opening_digests(owner, frame)
    if (hashes['content'] != owner.input_digest or hashes['profile'] != owner.configuration_digest
            or hashes['recipe'] != owner.recipe_sha256
            or frame['opening']['identity'] != owner.opening_identity
            or frame['opening']['opening_date'] != owner.opening_date.isoformat()
            or expected_frame is not None and hashes['content'] != digest(expected_frame)):
        raise ValueError('Native opening/configuration full readback drift')
    batches = owner_batches(frame['opening']['state'], strict=True)
    families = immutable(owner, 'families', lambda: families_for(batches))
    if p.get('families') != families:
        raise ValueError('Native master projection identity drift')
    actual = {str(row.master_id): (row.digest, row.receipt)
        for row in MdmFamilySource.objects.filter(source=source)}
    if actual != {key: (digest(families[key]), families[key]) for key in ('2', '3')}:
        raise ValueError('Native base family roster/receipt drift')
    if current_masters:
        verify_current_masters(source, batches)
        from mta.mdm.daily_input import _capture_pair_exclusions
        if _capture_pair_exclusions(source)['rows'] != frame['pair_exclusions']:
            raise ValueError('Native pair exclusion readback drift')
    return owner


def bind_source(source, *, input_sha256, input_schema):
    if input_schema != SCHEMA:
        raise ValueError('Native initialization schema binding differs')
    owner = ProductionInitialization.objects.select_related('source').get(source=source)
    if owner.input_sha256 != input_sha256:
        raise ValueError('Native operator input identity differs')
    verify(owner)
    return source


@opening_operation
def initialize(raw, expected_sha256, *, expected_configuration, expected_recipe):
    return _initialize(raw, expected_sha256, expected_configuration=expected_configuration,
        expected_recipe=expected_recipe, complete=False)


@opening_operation
def initialize_complete(raw, expected_sha256, *, expected_configuration, expected_recipe):
    """One prepared opening, atomic all-family write and final full certification."""
    return _initialize(raw, expected_sha256, expected_configuration=expected_configuration,
        expected_recipe=expected_recipe, complete=True)


@observed('native_initialization', owner_parameter='expected_sha256')
def _initialize(raw, expected_sha256, *, expected_configuration, expected_recipe, complete):
    from mta.mdm.initialization_preparation import PreparedInitialization, prepare
    prepared = raw if type(raw) is PreparedInitialization else prepare(raw, expected_sha256,
        expected_configuration=expected_configuration, expected_recipe=expected_recipe)
    _, frame, batches = prepared.claim(expected_sha256, expected_configuration, expected_recipe)
    implementation = implementation_digest()
    # Full immutable CPU work precedes the atomic writer; all database guards,
    # current-master readback and sealing stay in the transaction.
    content_digest, families = prepared.content_digest, prepared.families
    own_transaction = not connection.in_atomic_block
    with observe_exit(transaction.atomic(), 'initialization_transaction_exit'):
        if own_transaction:
            with connection.cursor() as cursor:
                cursor.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ')
        namespace = authorize_install(expected_sha256, implementation)
        if namespace['registration'] is None:
            raise ValueError('Native initialization requires registered namespace ownership')
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_xact_lock(hashtextextended('fresh.production.initialization',0))")
        existing = ProductionInitialization.objects.select_for_update().select_related('source').first()
        if existing:
            if (existing.input_sha256 != expected_sha256 or existing.configuration_digest != expected_configuration
                    or existing.recipe_sha256 != expected_recipe or existing.implementation_digest != implementation):
                raise ValueError('Instance already initialized; overwrite/reset is prohibited')
            if MdmDailyInputCapture.objects.filter(source=existing.source).exists():
                raise ValueError('Initialization consumed; H3 continuation must use its persisted predecessor')
            if complete:
                _complete(existing, frame)
                return existing, False
            return verify(existing, expected_frame=frame, current_masters=True), False
        if (MdmSource.objects.exists() or CalculationRun.objects.exists()
                or MdmTask.objects.exists() or MdmSubTask.objects.exists()):
            raise ValueError('Native initialization requires a fresh instance; existing ownership cannot be replaced')
        identity = uuid.uuid4()
        receipt = dict(schema=SOURCE_SCHEMA, initialization_id=str(identity),
            input_schema=SCHEMA, input_sha256=expected_sha256,
            recipe_sha256=expected_recipe, configuration_digest=expected_configuration,
            implementation_digest=implementation, database=namespace['database_name'],
            owned_namespace=namespace['registration'], families=families,
            opening_identity=frame['opening']['identity'], opening_date=frame['opening']['opening_date'],
            content_digest=content_digest, qualification='INITIALIZATION_ONLY_NO_ACCEPTED_DAY')
        source = MdmSource.objects.create(digest=digest(receipt), dll_digest='',
            implementation_digest=implementation, database_name=namespace['database_name'], receipt=receipt)
        with connection.cursor() as cursor:
            cursor.execute("SELECT set_config('fresh.production_initialization',%s,true)", [str(identity)])
        owner = ProductionInitialization.objects.create(id=identity, source=source,
            opening_identity=frame['opening']['identity'], opening_date=frame['opening']['opening_date'],
            input_sha256=expected_sha256, recipe_sha256=expected_recipe,
            configuration_digest=expected_configuration, implementation_digest=implementation,
            input_digest=content_digest)
        with connection.cursor() as cursor:
            cursor.execute("SELECT set_config('fresh.production_initialization',%s,true), "
                "set_config('fresh.mdm_current_bootstrap',%s,true)", [str(owner.pk), str(source.pk)])
        for _, model, scope, rows, _ in batches:
            from mta.mdm.initialization_transport import create_rows
            create_rows(model, (dict(source_id=source.pk, ordinal=i, **scope, **row)
                               for i, row in enumerate(rows, 1)), count=len(rows))
        for key in ('2', '3'):
            MdmFamilySource.objects.create(source=source, master_id=int(key),
                digest=digest(families[key]), receipt=families[key])
        from mta.mdm.daily_input import install_pair_exclusions
        install_pair_exclusions(source, frame['pair_exclusions'], provenance=dict(
            schema=SOURCE_SCHEMA, input_sha256=expected_sha256, configuration_digest=expected_configuration,
            initialization_id=str(owner.pk)))
        from mta.runtime.input_v3 import opening_aliases
        owner.input_payload = save_input(owner, frame, version=3, aliases=opening_aliases(frame),
            image_writer=opening_storage.save_image, table_selector=initialization_table)
        owner.input_manifest_digest = digest(owner.input_payload)
        owner.receipt = dict(schema='native-initialization-seal-v1', source_digest=source.digest,
            manifest_digest=owner.input_manifest_digest, content_digest=owner.input_digest)
        owner.receipt_digest = digest(owner.receipt)
        owner.save(update_fields=('input_payload', 'input_manifest_digest', 'receipt', 'receipt_digest'))
        owner.opening_date = owner._meta.get_field('opening_date').to_python(owner.opening_date)
        if complete:
            _complete(owner, frame)
        else:
            verify(owner, expected_frame=frame, current_masters=True)
        with connection.cursor() as cursor:
            cursor.execute("SELECT set_config('fresh.production_initialization','',true), "
                "set_config('fresh.mdm_current_bootstrap','',true)")
        return owner, True


def _complete(owner, frame):
    from mta.mdm import production_families as families
    from mta.runtime.ingestion_certification import certify_locked
    from mta.runtime.ingestion_models import InitializationCertification
    if InitializationCertification.objects.filter(initialization=owner).exists():
        # Re-entry is not permission to certify again or bypass admission.
        from mta.runtime.ingestion_admission import _admit
        from release.native_identity import require_current
        with connection.cursor() as cursor:
            _admit(cursor, owner.pk, require_current())
        return
    _, bags = families._expected(owner, frame=frame)
    families._write_family_roster(owner, frame, bags)
    from release.native_identity import require_current
    with connection.cursor() as cursor:
        certify_locked(owner.pk, require_current(), cursor)
