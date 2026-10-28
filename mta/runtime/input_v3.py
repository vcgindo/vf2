"""Version-three typed input manifests with same-owner logical aliases.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.

This module is deliberately restricted to input storage.  It does not change
calculation, SQL selection, action policy, frontend, MTO, authentication, or
daily ownership. Aliases are explicit one-hop references between exactly equal
collections owned by the same initialization or run. Daily facts may instead
use the finite M3 BATCH reference contract bound to the run's sealed CSV attempt.
"""
from collections.abc import Sequence
from copy import deepcopy
from uuid import UUID

from django.db import connection

from mta.row_sequences import RecordRows
from mta.serialization import canonical_parts, digest, rows_digest, storage
from mta.application.stage_observation import stage


V3 = 'fresh-daily-input-manifest-v3'
IDENTITY_FIELDS = frozenset(('database_name', 'database_oid', 'source_digest',
                             'owner_kind', 'owner_id'))
BATCH_REFERENCE_FIELDS = frozenset(('attempt_id', 'filename', 'manifest_digest',
                                    'population_digest', 'count'))
OWNER_REFERENCE_FIELDS = frozenset(('kind', 'owner_id', 'path',
                                    'manifest_digest', 'content_digest'))
MASTER_REFERENCE_FIELDS = frozenset(('contract', 'run_id', 'output_digest',
    'initialization_id', 'source_digest', 'master_revision_id'))
MASTER_CONTRACT = 'native-nms-master-compatibility-v1'
MASTER_PATH = 'input/day/raw_master'
MASTER_IMAGE = 'closing/consumer_context/NMSAllItems'
CONTENT_KIND = 'native-prepared-input-v1'
CONTENT_IDENTITY_FIELDS = frozenset(('database_name', 'database_oid', 'source_digest',
                                     'initialization_id'))
BATCH_PATHS = {
    'input/day/raw_daily': 'DailyDataRaw.csv',
    'input/day/raw_non_nms': 'MasterDataRawNonNMS.csv',
    'input/day/raw_no_norm': 'NoNormMasterRaw.csv',
    'input/day/accepted_feed': 'AcceptedNorms.csv',
    'input/day/order_raw': 'OrderData.csv',
    'input/day/order_feed': 'OrderFeed.csv',
    'input/day/distributor_transactions': 'DistributorTransactions.csv',
    'input/day/vendor_transactions': 'VendorTransactions.csv',
    'input/day/shipment_input/rows': 'InTransitRaw.csv',
    'input/day/transporter_input/rows': 'Transporters.csv',
    'input/day/requirement_stock': 'AdditionalDataStockForReqCalc.csv',
}
OWNER_PATHS = {
    'input/profile': 'INITIALIZATION', 'input/opening': 'INITIALIZATION',
    **{f'input/mdm_input/rows/{family}/{part}': 'RUN'
       for family in ('sku', 'location', 'skuloc')
       for part in ('attributes', 'descriptions')},
}


def _database_identity():
    with connection.cursor() as cursor:
        cursor.execute('SELECT current_database(),oid::bigint FROM pg_database '
                       'WHERE datname=current_database()')
        row = cursor.fetchone()
    if not row:
        raise ValueError('Typed input database identity unavailable')
    return row


from mta.presentation.request_scope import once_per_metadata_operation


@once_per_metadata_operation
def _live_identity(owner, *, reading):
    """Resolve production identity from the database, never caller metadata."""
    meta = getattr(owner, '_meta', None)
    model_name = getattr(meta, 'model_name', None)
    if model_name == 'productioninitialization':
        current = type(owner).objects.select_related('source').only('id','source__digest','input_manifest_digest').get(pk=owner.pk)
        if reading and not current.input_manifest_digest:
            raise ValueError('Typed input initialization owner is mutable')
        owner_kind = 'initialization'
        source_digest = current.source.digest
    elif model_name == 'calculationrun':
        current = type(owner).objects.get(pk=owner.pk)
        if (reading and (current.status not in ('RUNNING', 'SUCCEEDED', 'FAILED')
                         or not current.input_manifest_digest)
                or not reading and current.status != 'RUNNING'):
            raise ValueError('Typed input run owner is mutable')
        owner_kind = 'run'
        try:
            source_digest = current.mdm_input_capture.source.digest
        except (AttributeError, ObjectDoesNotExist):
            try:
                source_digest = current.csv_attempt.initialization.source.digest
            except (AttributeError, ObjectDoesNotExist) as error:
                raise ValueError('Typed input run source identity unavailable') from error
    else:
        raise ValueError('Typed input owner kind is unsupported')
    database_name, database_oid = _database_identity()
    return dict(database_name=database_name, database_oid=database_oid,
                source_digest=source_digest, owner_kind=owner_kind,
                owner_id=str(current.pk))


# Importing ObjectDoesNotExist after the function keeps the storage-only module
# cheap for pure tests while retaining a precise related-owner failure boundary.
from django.core.exceptions import ObjectDoesNotExist


def _identity(owner, resolver, *, reading):
    value = resolver(owner) if resolver is not None else _live_identity(owner, reading=reading)
    if not isinstance(value, dict) or set(value) != IDENTITY_FIELDS:
        raise ValueError('Typed input owner identity fields differ')
    if (not isinstance(value['database_name'], str) or not value['database_name']
            or type(value['database_oid']) is not int or value['database_oid'] <= 0
            or value['owner_kind'] not in ('initialization', 'run')
            or not isinstance(value['source_digest'], str)
            or len(value['source_digest']) != 64
            or any(c not in '0123456789abcdef' for c in value['source_digest'])):
        raise ValueError('Typed input owner identity value differs')
    try:
        owner_id = str(UUID(str(value['owner_id'])))
    except (TypeError, ValueError, AttributeError) as error:
        raise ValueError('Typed input owner UUID differs') from error
    if owner_id != str(value['owner_id']).lower() or owner_id != str(owner.pk).lower():
        raise ValueError('Typed input owner UUID differs')
    return {**value, 'owner_id': owner_id}


def _normal_path(value):
    if (not isinstance(value, str) or not value.startswith('input/')
            or value.endswith('/') or '//' in value or any(part in ('', '.', '..') for part in value.split('/'))):
        raise ValueError('Typed input alias path differs')
    return value


def _at(raw, path):
    value = raw
    for key in path.split('/')[1:]:
        if not isinstance(value, dict) or key not in value:
            raise ValueError('Typed input alias target is dangling: '+path)
        value = value[key]
    return value


def _collection(value):
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray, dict))


def _typed_equal(left, right):
    if _collection(left) or _collection(right):
        if not _collection(left) or not _collection(right) or len(left) != len(right):
            return False
        return all(_typed_equal(a, b) for a, b in zip(left, right))
    if isinstance(left, dict) or isinstance(right, dict):
        if not isinstance(left, dict) or not isinstance(right, dict) or list(left) != list(right):
            return False
        return all(_typed_equal(left[key], right[key]) for key in left)
    return type(left) is type(right) and left == right


def _master_reference(value):
    if (not isinstance(value, dict) or set(value) != MASTER_REFERENCE_FIELDS
            or value.get('contract') != MASTER_CONTRACT):
        raise ValueError('Typed input derived master reference identity differs')
    result = dict(value)
    for name in ('run_id', 'initialization_id', 'master_revision_id'):
        try:
            result[name] = str(UUID(str(value[name])))
        except (TypeError, ValueError, AttributeError) as error:
            raise ValueError('Typed input derived master UUID differs') from error
        if result[name] != str(value[name]).lower():
            raise ValueError('Typed input derived master UUID differs')
    for name in ('output_digest', 'source_digest'):
        if (not isinstance(value[name], str) or len(value[name]) != 64
                or any(c not in '0123456789abcdef' for c in value[name])):
            raise ValueError('Typed input derived master digest differs')
    return result


def _content_identity(value):
    if (not isinstance(value, dict) or set(value) != CONTENT_IDENTITY_FIELDS
            or not isinstance(value['database_name'], str) or not value['database_name']
            or type(value['database_oid']) is not int or value['database_oid'] <= 0
            or not isinstance(value['source_digest'], str) or len(value['source_digest']) != 64
            or any(c not in '0123456789abcdef' for c in value['source_digest'])):
        raise ValueError('Typed prepared input content identity differs')
    try:
        initialization_id = str(UUID(str(value['initialization_id'])))
    except (TypeError, ValueError, AttributeError) as error:
        raise ValueError('Typed prepared input initialization UUID differs') from error
    if initialization_id != str(value['initialization_id']).lower():
        raise ValueError('Typed prepared input initialization UUID differs')
    return {**value, 'initialization_id': initialization_id}


@stage('input_content_digest')
def content_root(raw, content_identity, *, owner_references={}, batch_references={}):
    """Return the bounded prepared-input root without retaining its raw graph."""
    identity = _content_identity(content_identity)
    if not isinstance(owner_references, dict) or not isinstance(batch_references, dict):
        raise ValueError('Typed prepared input references require mappings')
    owners = {_normal_path(path): _owner_reference(value, _normal_path(path))
              for path, value in owner_references.items()}
    batches = {_normal_path(path): _batch_reference(value, _normal_path(path))
               for path, value in batch_references.items()}
    if set(owners) & set(batches):
        raise ValueError('Typed prepared input path has multiple references')

    from mta.application.persistent_master import NmsMasterRows
    seen_owners, seen_batches = set(), set()
    def summarize(value, path):
        if path in owners:
            seen_owners.add(path)
            return {'owner_reference': owners[path]}
        if path in batches:
            seen_batches.add(path)
            return {'batch_reference': batches[path]}
        if isinstance(value, NmsMasterRows):
            if path != MASTER_PATH:
                raise ValueError('Typed input derived master path differs')
            return {'derived_master': _master_reference(value.reference)}
        if isinstance(value, dict):
            return {'object': [[key, summarize(item, path+'/'+key)]
                               for key, item in value.items()]}
        if _collection(value):
            if not value:
                return {'empty': True}
            return {'rows': len(value), 'digest': rows_digest(value)}
        return {'scalar': storage(value)}

    tree = summarize(raw, 'input')
    if seen_owners != set(owners) or seen_batches != set(batches):
        raise ValueError('Typed prepared input reference target is dangling')
    return digest(dict(schema=V3, content_kind=CONTENT_KIND, identity=identity, tree=tree))


def _aliases(raw, aliases):
    if aliases is None:
        return {}
    if not isinstance(aliases, dict):
        raise ValueError('Typed input aliases require an explicit mapping')
    result = {}
    for source, target in aliases.items():
        source, target = _normal_path(source), _normal_path(target)
        if source == target or source in result:
            raise ValueError('Typed input alias identity differs')
        result[source] = target
    if any(target in result for target in result.values()):
        raise ValueError('Typed input aliases must be one-hop')
    for source, target in result.items():
        source_value, target_value = _at(raw, source), _at(raw, target)
        if not _collection(source_value) or not _collection(target_value):
            raise ValueError('Typed input alias requires collection targets')
        if not _typed_equal(source_value, target_value):
            raise ValueError('Typed input alias population differs: '+source)
    return result


def _batch_reference(value, path):
    if path not in BATCH_PATHS or not isinstance(value, dict) or set(value) != BATCH_REFERENCE_FIELDS:
        raise ValueError('Typed input batch reference identity differs')
    try:
        attempt_id = str(UUID(str(value['attempt_id'])))
    except (TypeError, ValueError, AttributeError) as error:
        raise ValueError('Typed input batch attempt UUID differs') from error
    if (attempt_id != str(value['attempt_id']).lower()
            or value['filename'] != BATCH_PATHS[path]
            or any(not isinstance(value[name], str) or len(value[name]) != 64
                   or any(c not in '0123456789abcdef' for c in value[name])
                   for name in ('manifest_digest', 'population_digest'))
            or type(value['count']) is not int or value['count'] < 0):
        raise ValueError('Typed input batch reference identity differs')
    return {**value, 'attempt_id': attempt_id}


def _batch_attempt(owner, attempt_id, resolver):
    if resolver is not None:
        attempt = resolver(owner, attempt_id)
        if (str(getattr(attempt, 'attempt_id', '')).lower() != attempt_id
                or str(getattr(attempt, 'run_id', '')).lower() != str(owner.pk).lower()):
            raise ValueError('Typed input run batch owner differs')
        return attempt
    current = type(owner).objects.select_related(
        'csv_attempt__initialization__source').get(pk=owner.pk)
    try:
        attempt = current.csv_attempt
    except (AttributeError, ObjectDoesNotExist) as error:
        raise ValueError('Typed input run has no bound daily batch') from error
    if str(attempt.attempt_id) != attempt_id or attempt.run_id != current.pk:
        raise ValueError('Typed input run batch owner differs')
    return attempt


def _resolve_batch(owner, path, reference, owner_identity, resolver, *,
                   allow_owned_failed=False):
    reference = _batch_reference(reference, path)
    if owner_identity['owner_kind'] != 'run':
        raise ValueError('Typed input batch references require a run owner')
    attempt = _batch_attempt(owner, reference['attempt_id'], resolver)
    manifest = getattr(attempt, 'accepted_facts', None)
    if not isinstance(manifest, dict) or digest(manifest) != reference['manifest_digest']:
        raise ValueError('Typed input batch manifest identity differs')
    from mta.runtime import batch_storage
    batch_identity = batch_storage._live_identity(attempt, reading=True, manifest=manifest,
        allow_owned_failed=allow_owned_failed)
    if (batch_identity['database_name'] != owner_identity['database_name']
            or batch_identity['database_oid'] != owner_identity['database_oid']
            or batch_identity['source_digest'] != owner_identity['source_digest']):
        raise ValueError('Typed input batch database/source identity differs')
    try:
        entry = next(item for item in manifest['feeds'] if item['filename'] == reference['filename'])
    except (KeyError, TypeError, StopIteration) as error:
        raise ValueError('Typed input batch population is unavailable') from error
    if (entry.get('digest') != reference['population_digest']
            or entry.get('count') != reference['count']):
        raise ValueError('Typed input batch population identity differs')
    factory = lambda: batch_storage.iter_population(attempt, reference['filename'], manifest,
        _allow_owned_failed=allow_owned_failed)
    return (RecordRows(reference['count'], factory)
            if reference['count'] > 10000 else list(factory()))


def _batch_references(raw, references, owner, owner_identity, resolver):
    if references is None:
        return {}
    if not isinstance(references, dict):
        raise ValueError('Typed input batch references require an explicit mapping')
    result = {}
    for path, value in references.items():
        path = _normal_path(path)
        reference = _batch_reference(value, path)
        target = _at(raw, path)
        if not _collection(target):
            raise ValueError('Typed input batch reference requires a collection target')
        rows = _resolve_batch(owner, path, reference, owner_identity, resolver)
        with stage('batch_reference_compare', path=path):
            if not _typed_equal(target, rows):
                raise ValueError('Typed input batch population differs: ' + path)
        result[path] = reference
    return result


def _owner_reference(value, source_path):
    if (source_path not in OWNER_PATHS or not isinstance(value, dict)
            or set(value) != OWNER_REFERENCE_FIELDS or value['kind'] != OWNER_PATHS[source_path]
            or value['path'] != source_path):
        raise ValueError('Typed input owner reference identity differs')
    try:
        owner_id = str(UUID(str(value['owner_id'])))
    except (TypeError, ValueError, AttributeError) as error:
        raise ValueError('Typed input referenced owner UUID differs') from error
    if (owner_id != str(value['owner_id']).lower()
            or any(not isinstance(value[name], str) or len(value[name]) != 64
                   or any(c not in '0123456789abcdef' for c in value[name])
                   for name in ('manifest_digest', 'content_digest'))):
        raise ValueError('Typed input owner reference identity differs')
    return {**value, 'owner_id': owner_id}


def _node_at(manifest, path):
    node = manifest['tree']
    for key in _normal_path(path).split('/')[1:]:
        if 'object' not in node:
            raise ValueError('Typed input owner reference target is dangling')
        matches = [child for name, child in node['object'] if name == key]
        if len(matches) != 1:
            raise ValueError('Typed input owner reference target is dangling')
        node = matches[0]
    return node


def _physical(node):
    if any(name in node for name in ('reference', 'batch_reference', 'owner_reference', 'derived_master')):
        return False
    return (all(_physical(child) for _, child in node.get('object', []))
            and all(_physical(child) for _, child, _ in node.get('children', [])))


def _initialization_component_is_physical(manifest, path):
    """Admit only the frozen M2 same-initialization opening aliases."""
    aliases = manifest.get('aliases')
    if not isinstance(aliases, dict):
        return False

    def inspect(node, source):
        if any(name in node for name in ('batch_reference', 'owner_reference')):
            return False
        if 'reference' in node:
            target = node.get('reference')
            if (set(node) != {'reference'} or source not in OPENING_ALIASES
                    or aliases.get(source) != target or OPENING_ALIASES[source] != target):
                return False
            try:
                target_node = _node_at(manifest, target)
            except ValueError:
                return False
            return _physical(target_node)
        return (all(inspect(child, source+'/'+name)
                    for name, child in node.get('object', []))
                and all(inspect(child, source+'/children/'+'/'.join(field))
                        for field, child, _ in node.get('children', [])))

    return inspect(_node_at(manifest, path), path)


def _owner_target(owner, reference, resolver):
    if resolver is not None:
        return resolver(owner, reference)
    current = type(owner).objects.select_related('predecessor').get(pk=owner.pk)
    initialization_id = _run_initialization_id(current, None)
    from mta.runtime.initialization_models import ProductionInitialization
    initialization = ProductionInitialization.objects.get(pk=initialization_id)
    if reference['kind'] == 'INITIALIZATION':
        if reference['owner_id'] != str(initialization.pk):
            raise ValueError('Typed input initialization reference is foreign')
        return initialization
    target = type(owner).objects.get(pk=reference['owner_id'])
    if target.status != 'SUCCEEDED':
        raise ValueError('Typed input referenced run is mutable')
    master = getattr(target, 'production_manifest', {}).get('master_preparation')
    if (not isinstance(master, dict) or type(master.get('qualified')) is not bool
            or not isinstance(master.get('master_cut'), list)
            or len(master['master_cut']) != 2
            or any(type(value) is not int or value < 0 for value in master['master_cut'])
            or _run_initialization_id(target, None) != initialization_id):
        raise ValueError('Typed input referenced run final master identity differs')
    predecessor = str(current.predecessor_id) if current.predecessor_id else None
    if reference['owner_id'] != predecessor:
        from mta.runtime.ingestion_models import MasterInputRevision
        if not MasterInputRevision.objects.filter(initialization_id=initialization.pk,
                run_id=target.pk, status='ACCEPTED').exists():
            raise ValueError('Typed input referenced run is outside accepted lineage')
    return target


def _owner_manifest(owner, source_path, reference, owner_identity, resolver):
    reference = _owner_reference(reference, source_path)
    if owner_identity['owner_kind'] != 'run' or reference['owner_id'] == owner_identity['owner_id']:
        raise ValueError('Typed input owner reference requires a distinct run target')
    target = _owner_target(owner, reference, resolver)
    if str(target.pk).lower() != reference['owner_id']:
        raise ValueError('Typed input referenced owner differs')
    if reference['kind'] == 'RUN' and getattr(target, 'status', None) != 'SUCCEEDED':
        raise ValueError('Typed input referenced run is mutable')
    if resolver is not None and (getattr(target, '_reference_initialization_id', None)
            != getattr(owner, '_reference_initialization_id', None)
            or not getattr(target, '_reference_accepted', False)):
        raise ValueError('Typed input referenced owner is foreign or unaccepted')
    target_identity = _identity(target, None if resolver is None else
        lambda value: getattr(value, '_reference_identity'), reading=True)
    if target_identity['owner_kind'] != reference['kind'].lower():
        raise ValueError('Typed input referenced owner kind differs')
    if (target_identity['database_name'] != owner_identity['database_name']
            or target_identity['database_oid'] != owner_identity['database_oid']
            or target_identity['source_digest'] != owner_identity['source_digest']):
        raise ValueError('Typed input referenced database/source differs')
    manifest = target.input_payload
    from mta.runtime import input_storage
    legacy_initialization = (reference['kind'] == 'INITIALIZATION'
        and isinstance(manifest, dict) and manifest.get('schema') == input_storage.SCHEMA)
    if (not isinstance(manifest, dict) or not (manifest.get('schema') == V3 or legacy_initialization)
            or digest(manifest) != reference['manifest_digest']
            or target.input_manifest_digest != reference['manifest_digest']
            or target.input_digest != reference['content_digest']
            or manifest.get('content_digest') != reference['content_digest']):
        raise ValueError('Typed input referenced manifest/content differs')
    physical = (_initialization_component_is_physical(manifest, reference['path'])
                if reference['kind'] == 'INITIALIZATION' and not legacy_initialization else
                _physical(_node_at(manifest, reference['path'])))
    if not physical:
        raise ValueError('Typed input owner references must target physical one-hop subtrees')
    return target, manifest, legacy_initialization


@stage('owner_reference_read')
def _resolve_owner(owner, source_path, reference, owner_identity, resolver):
    from mta.runtime import input_storage
    reference = _owner_reference(reference, source_path)
    target, manifest, legacy_initialization = _owner_manifest(
        owner, source_path, reference, owner_identity, resolver)
    component = reference['path'].removeprefix('input/')
    reader = (__import__('mta.runtime.opening_storage', fromlist=['load_image']).load_image
              if reference['kind'] == 'INITIALIZATION' else
              __import__('mta.runtime.relational_state', fromlist=['load_image']).load_image)
    # Original v2 openings remain sealed as v2. Identity is checked against the
    # live owner above; v2 has no embedded v3 identity or reference contract.
    value = input_storage.read_input(target, components=(component,), image_reader=reader,
        identity_resolver=(None if resolver is None or legacy_initialization
                          else lambda value: value._reference_identity))
    return _at(value, reference['path'])


def component_absent(owner, path):
    """Prove optional-member absence using authenticated physical metadata only.

    A present or unsupported representation always falls back to a value read.
    Reference ownership checks are identical to the ordinary component reader.
    """
    from mta.runtime import input_storage
    path = _normal_path(path)
    input_storage.read_input(owner, components=())
    manifest = owner.input_payload
    if manifest.get('schema') not in (V3, input_storage.SCHEMA):
        return False
    node = manifest['tree']
    current = 'input'
    for part in path.split('/')[1:]:
        if 'owner_reference' in node:
            if manifest.get('schema') != V3:
                return False
            target, target_manifest, _ = _owner_manifest(owner, current,
                manifest['owner_references'][current], _identity(owner, None, reading=True), None)
            input_storage.read_input(target, components=())
            node = _node_at(target_manifest, current)
            owner, manifest = target, target_manifest
        if set(node) != {'object'}:
            return False
        if (not isinstance(node['object'], list) or any(
                not isinstance(child, list) or len(child) != 2
                or not isinstance(child[0], str) or not isinstance(child[1], dict)
                for child in node['object'])):
            raise ValueError('Typed input optional component object differs')
        matches = [child for name, child in node['object'] if name == part]
        if not matches:
            return True
        if len(matches) != 1:
            raise ValueError('Typed input optional component is ambiguous')
        node = matches[0]
        current += '/' + part
    return False


def _owner_references(raw, references, owner, owner_identity, resolver):
    if references is None:
        return {}
    if not isinstance(references, dict):
        raise ValueError('Typed input owner references require an explicit mapping')
    result = {}
    for path, value in references.items():
        path = _normal_path(path)
        reference = _owner_reference(value, path)
        target = _at(raw, path)
        resolved = _resolve_owner(owner, path, reference, owner_identity, resolver)
        with stage('owner_reference_compare', path=path):
            if not _typed_equal(target, resolved):
                raise ValueError('Typed input referenced population differs: ' + path)
        result[path] = reference
    return result


def _run_initialization_id(owner, resolver):
    preparation = getattr(owner, 'production_manifest', {}).get('ingestion_preparation', {})
    value = preparation.get('initialization_id') if isinstance(preparation, dict) else None
    try:
        initialization_id = str(UUID(str(value)))
    except (TypeError, ValueError, AttributeError) as error:
        raise ValueError('Typed input run initialization is unavailable') from error
    if initialization_id != str(value).lower():
        raise ValueError('Typed input run initialization is unavailable')
    if resolver is not None:
        if (str(getattr(owner, '_reference_initialization_id', '')).lower() != initialization_id
                or str(getattr(owner, '_reference_capture_initialization_id', '')).lower()
                   != initialization_id
                or (getattr(owner, '_reference_csv_initialization_id', None) is not None
                    and str(owner._reference_csv_initialization_id).lower() != initialization_id)
                or getattr(owner, '_reference_capture_source_digest', None)
                   != getattr(owner, '_reference_identity', {}).get('source_digest')
                or getattr(owner, '_reference_certified', False) is not True):
            raise ValueError('Typed input run initialization seed is uncorroborated')
        return initialization_id
    current = type(owner).objects.select_related(
        'mdm_input_capture__source__production_initialization',
        'csv_attempt__initialization').get(pk=owner.pk)
    try:
        capture_initialization = current.mdm_input_capture.source.production_initialization
    except (AttributeError, ObjectDoesNotExist) as error:
        raise ValueError('Typed input run MDM capture initialization is unavailable') from error
    if str(capture_initialization.pk) != initialization_id:
        raise ValueError('Typed input run initialization seed differs from MDM capture')
    csv_initialization_id = getattr(getattr(current, 'csv_attempt', None), 'initialization_id', None)
    if csv_initialization_id is not None and str(csv_initialization_id) != initialization_id:
        raise ValueError('Typed input CSV and native initialization differ')
    from mta.runtime.ingestion_models import InitializationCertification
    if not InitializationCertification.objects.filter(initialization_id=initialization_id,
            source_digest=current.mdm_input_capture.source.digest, status='CERTIFIED').exists():
        raise ValueError('Typed input run initialization is not currently certified')
    return initialization_id


def _validate_content_owner(owner, owner_identity, value, resolver):
    content_identity = _content_identity(value)
    if owner_identity['owner_kind'] != 'run':
        raise ValueError('Prepared content identity requires a run owner')
    actual = dict(database_name=owner_identity['database_name'],
        database_oid=owner_identity['database_oid'], source_digest=owner_identity['source_digest'],
        initialization_id=_run_initialization_id(owner, resolver))
    if content_identity != actual:
        raise ValueError('Typed prepared input live identity differs')
    return content_identity


def _derived_parent(owner, reference, resolver):
    if resolver is not None:
        return resolver(owner, reference)
    current = type(owner).objects.select_related('predecessor').get(pk=owner.pk)
    if str(current.predecessor_id or '') != reference['run_id']:
        raise ValueError('Typed input derived master requires the direct predecessor')
    return current.predecessor


def _resolve_derived_master(owner, reference, owner_identity, resolver, *, projection=None):
    reference = _master_reference(reference)
    if owner_identity['owner_kind'] != 'run':
        raise ValueError('Typed input derived master requires a run owner')
    if str(getattr(owner, 'predecessor_id', '') or '').lower() != reference['run_id']:
        if resolver is not None:
            raise ValueError('Typed input derived master requires the direct predecessor')
    preparation = getattr(owner, 'production_manifest', {}).get('ingestion_preparation', {})
    if (not isinstance(preparation, dict)
            or preparation.get('qualified_master_reuse') is not True
            or str(preparation.get('base_revision_id', '')).lower()
               != reference['master_revision_id']):
        raise ValueError('Typed input derived master is not qualified by preparation')
    parent = _derived_parent(owner, reference, resolver)
    if (str(getattr(parent, 'pk', '')).lower() != reference['run_id']
            or getattr(parent, 'status', None) != 'SUCCEEDED'
            or getattr(parent, 'output_digest', None) != reference['output_digest']):
        raise ValueError('Typed input derived master predecessor identity differs')
    parent_master = getattr(parent, 'production_manifest', {}).get('master_preparation', {})
    if (not isinstance(parent_master, dict) or parent_master.get('qualified') is not True
            or not isinstance(parent_master.get('master_cut'), list)
            or len(parent_master['master_cut']) != 2
            or any(type(value) is not int or value < 0 for value in parent_master['master_cut'])):
        raise ValueError('Typed input derived master predecessor is unqualified')
    parent_identity = _identity(parent, None if resolver is None else
        lambda value: value._reference_identity, reading=True)
    if (parent_identity['source_digest'] != owner_identity['source_digest']
            or reference['source_digest'] != owner_identity['source_digest']
            or reference['initialization_id'] != _run_initialization_id(owner, resolver)
            or _run_initialization_id(parent, resolver) != reference['initialization_id']):
        raise ValueError('Typed input derived master source/initialization differs')
    if resolver is not None:
        if (str(getattr(parent, '_reference_accepted_revision_id', '')).lower()
                != reference['master_revision_id']
                or list(getattr(parent, '_reference_accepted_revision_cut', ()))
                   != parent_master['master_cut']
                or not getattr(parent, '_reference_accepted', False)):
            raise ValueError('Typed input derived master revision is unaccepted')
    else:
        from mta.runtime.ingestion_models import MasterInputRevision
        revision = MasterInputRevision.objects.filter(pk=reference['master_revision_id'],
            initialization_id=reference['initialization_id'], status='ACCEPTED').values_list(
                'master_epoch', 'configuration_epoch').first()
        if revision is None or list(revision) != parent_master['master_cut']:
            raise ValueError('Typed input derived master revision is unaccepted')
    from mta.runtime.receipt_integrity import verify_root
    verify_root(parent)
    try:
        image = parent.production_manifest['images'][MASTER_IMAGE]
    except (KeyError, TypeError) as error:
        raise ValueError('Typed input derived master image is unavailable') from error
    from mta.runtime.relational_state import load_image
    rows = load_image(parent, image)
    from mta.application.persistent_master import NmsMasterRows
    if resolver is not None:
        return NmsMasterRows(rows, canonical=False, reference=reference)
    if projection is None:
        from mta.runtime.input_storage import read_input as read_owned
        captured=read_owned(owner,components=('mdm_input','input/day/business_date'))
        projection=(captured['mdm_input'],captured['day']['business_date'])
    return NmsMasterRows(rows,canonical=False,reference=reference,
        snapshot=projection[0],business_date=projection[1])


@stage('typed_input_write')
def save_input(owner, raw, *, image_writer, table_selector, aliases=None,
               identity_resolver=None, explicit_table_selector=False,
               batch_references=None, batch_resolver=None,
               owner_references=None, owner_resolver=None, master_resolver=None,
               content_identity=None):
    """Write an opt-in v3 manifest; callers must persist its digest separately."""
    from mta.runtime import input_storage as common
    identity = _identity(owner, identity_resolver, reading=False)
    aliases = _aliases(raw, aliases)
    batch_references = _batch_references(raw, batch_references, owner, identity, batch_resolver)
    owner_references = _owner_references(raw, owner_references, owner, identity, owner_resolver)
    if len(set(aliases) | set(batch_references) | set(owner_references)) != (
            len(aliases) + len(batch_references) + len(owner_references)):
        raise ValueError('Typed input path cannot have multiple reference owners')
    from mta.application.persistent_master import NmsMasterRows
    try:
        raw_master = _at(raw, MASTER_PATH)
    except ValueError:
        raw_master = None
    derived_references = {}
    if isinstance(raw_master, NmsMasterRows):
        reference = _master_reference(raw_master.reference)
        resolved = _resolve_derived_master(owner, reference, identity, master_resolver,
            projection=((raw['mdm_input'],raw['day']['business_date']) if master_resolver is None else None))
        if not _typed_equal(raw_master, resolved):
            raise ValueError('Typed input derived master population differs')
        derived_references[MASTER_PATH] = reference
    prepared_identity = None
    if content_identity is not None:
        prepared_identity = _validate_content_owner(owner, identity, content_identity,
                                                     identity_resolver)
        expected = content_root(raw, prepared_identity, owner_references=owner_references,
                                batch_references=batch_references)
        if owner.input_digest != expected:
            raise ValueError('Typed prepared input content root differs')
    images = {}

    def image(path, rows, table=None):
        table = table or table_selector(rows[0] if rows else (), path, rows)
        images[path] = image_writer(owner, path, None, rows, table=table)
        return path

    def pack(value, path):
        if path in derived_references:
            return {'derived_master': path}
        if path in owner_references:
            return {'owner_reference': path}
        if path in batch_references:
            return {'batch_reference': path}
        if path in aliases:
            return {'reference': aliases[path]}
        if isinstance(value, dict):
            return {'object': [[key, pack(item, path+'/'+key)]
                               for key, item in value.items()]}
        if not _collection(value):
            return {'scalar': storage(value)}
        if not value:
            if explicit_table_selector:
                table = table_selector((), path+'/values', [])
            else:
                from mta.runtime.complete_daily_state import input_table
                table = input_table(path+'/values')
            if table is None:
                return {'empty': True}
            return {'records': image(path+'/values', [], table), 'shape': None,
                    'count': 0, 'children': []}
        if all(not isinstance(item, dict) and not _collection(item) for item in value):
            rows = common.Rows(len(value), lambda: ({'value': item} for item in value))
            kinds = {type(item) for item in value if item is not None}
            if kinds <= {int}:
                table = 'input/integer_values'
            elif kinds <= {str}:
                table = 'input/string_values'
            else:
                raise ValueError('Unsupported scalar input collection: '+path)
            return {'scalars': image(path, rows, table)}
        if not all(isinstance(row, dict) for row in value):
            raise ValueError('Input collection requires one declared record family: '+path)
        shapes, fields, children = [], [], []
        for row in value:
            item = common.shape(row)
            if item not in shapes:
                shapes.append(item)
                if len(shapes) > 128:
                    raise ValueError('Input record schema exceeds bounded shape contract')
                for leaf in common.leaves(item, 'value'):
                    if leaf not in fields:
                        fields.append(leaf)
                for child in common.leaves(item, 'list'):
                    if child not in children:
                        children.append(child)
        projected = common.Rows(len(value), lambda: ({'/'.join(field): common.get(row, field)
            for field in fields} for row in value))
        scalar_image = image(path+'/values', projected) if fields else None
        if len(shapes) == 1:
            result = {'records': scalar_image, 'shape': shapes[0],
                      'count': len(value), 'children': []}
        else:
            variants = common.Rows(len(value), lambda: ({'shape_id': shapes.index(common.shape(row))}
                                                         for row in value))
            result = {'records': scalar_image,
                      'shape_image': image(path+'/shape', variants, 'input/row_shape'),
                      'shapes': shapes, 'children': []}
        for field in children:
            length = sum(len(common.get(row, field, [])) for row in value)
            childrows = common.Rows(length, lambda field=field:
                (child for row in value for child in common.get(row, field, [])))
            links = common.Rows(length, lambda field=field:
                ({'parent_ordinal': index, 'child_ordinal': ordinal}
                 for index, row in enumerate(value)
                 for ordinal, _ in enumerate(common.get(row, field, []))))
            childpath = path+'/children/'+'/'.join(field)
            result['children'].append([list(field), pack(childrows, childpath),
                                       image(childpath+'/links', links, 'input/child_link')])
        return result

    tree = pack(raw, 'input')
    manifest = dict(schema=V3, tree=tree, images=images,
                    content_digest=owner.input_digest, identity=identity,
                    aliases=aliases,
                    batch_references=batch_references,
                    owner_references=owner_references,
                    profile={'delivery': {'site_code': raw['profile']['delivery']['site_code']}})
    if derived_references:
        manifest['derived_references'] = derived_references
    if prepared_identity is not None:
        manifest['content_kind'] = CONTENT_KIND
        manifest['content_identity'] = prepared_identity
    if sum(len(part) for part in canonical_parts(manifest)) > 1024*1024:
        raise ValueError('Typed input metadata exceeds bounded manifest size')
    return manifest


def read_input(owner, *, components=None, image_reader, materialized_roots=(),
               identity_resolver=None, batch_resolver=None, owner_resolver=None,
               master_resolver=None):
    value = owner.input_payload
    if (value.get('schema') != V3 or value.get('content_digest') != owner.input_digest
            or digest(value) != owner.input_manifest_digest):
        raise ValueError('Typed daily input manifest identity drift')
    owner_identity = _identity(owner, identity_resolver, reading=True)
    if value.get('identity') != owner_identity:
        raise ValueError('Typed input live owner identity drift')
    has_content = 'content_identity' in value or 'content_kind' in value
    if has_content:
        if value.get('content_kind') != CONTENT_KIND:
            raise ValueError('Typed prepared input content kind differs')
        if _validate_content_owner(owner, owner_identity, value.get('content_identity'),
                                   identity_resolver) != value.get('content_identity'):
            raise ValueError('Typed prepared input content identity differs')
    aliases = value.get('aliases')
    if not isinstance(aliases, dict):
        raise ValueError('Typed input alias manifest differs')
    batch_references = value.get('batch_references', {})
    if not isinstance(batch_references, dict):
        raise ValueError('Typed input batch reference manifest differs')
    owner_references = value.get('owner_references', {})
    if not isinstance(owner_references, dict):
        raise ValueError('Typed input owner reference manifest differs')
    derived_references = value.get('derived_references', {})
    if not isinstance(derived_references, dict):
        raise ValueError('Typed input derived reference manifest differs')
    def node_at(path):
        node = value['tree']
        for key in _normal_path(path).split('/')[1:]:
            if 'object' not in node:
                raise ValueError('Typed input alias target is dangling: '+path)
            matches = [child for name, child in node['object'] if name == key]
            if len(matches) != 1:
                raise ValueError('Typed input alias target is dangling: '+path)
            node = matches[0]
        return node

    references = {}
    batch_nodes = {}
    owner_nodes = {}
    derived_nodes = {}
    def inspect(node, path):
        if 'derived_master' in node:
            if (set(node) != {'derived_master'} or node['derived_master'] != path
                    or path != MASTER_PATH):
                raise ValueError('Typed input derived master node differs')
            derived_nodes[path] = path
            return
        if 'owner_reference' in node:
            if set(node) != {'owner_reference'} or node['owner_reference'] != path:
                raise ValueError('Typed input owner reference node differs')
            owner_nodes[path] = path
            return
        if 'batch_reference' in node:
            if set(node) != {'batch_reference'} or node['batch_reference'] != path:
                raise ValueError('Typed input batch reference node differs')
            batch_nodes[path] = path
            return
        if 'reference' in node:
            if set(node) != {'reference'} or aliases.get(path) != node['reference']:
                raise ValueError('Typed input alias reference differs')
            references[path] = node['reference']
            return
        if 'object' in node:
            for key, child in node['object']:
                inspect(child, path+'/'+key)
        for field, child, _ in node.get('children', []):
            inspect(child, path+'/children/'+'/'.join(field))
    inspect(value['tree'], 'input')
    if references != aliases or any(target in aliases for target in aliases.values()):
        raise ValueError('Typed input aliases must be explicit one-hop references')
    if set(batch_nodes) != set(batch_references) or set(batch_references) & set(aliases):
        raise ValueError('Typed input batch references must be explicit')
    if (set(owner_nodes) != set(owner_references)
            or set(owner_references) & (set(aliases) | set(batch_references))):
        raise ValueError('Typed input owner references must be explicit')
    if (set(derived_nodes) != set(derived_references)
            or set(derived_references) & (set(aliases) | set(batch_references)
                                          | set(owner_references))):
        raise ValueError('Typed input derived master references must be explicit')
    for path, reference in batch_references.items():
        _batch_reference(reference, path)
    for path, reference in owner_references.items():
        _owner_reference(reference, path)
    for path, reference in derived_references.items():
        if path != MASTER_PATH:
            raise ValueError('Typed input derived master path differs')
        _master_reference(reference)
    for source, target in aliases.items():
        _normal_path(source); _normal_path(target)
        target_node = node_at(target)
        if 'reference' in target_node or not any(key in target_node for key in
                ('empty', 'scalars', 'records', 'shape_image')):
            raise ValueError('Typed input alias target differs')

    def read(path):
        return image_reader(owner, value['images'][path])

    cache = {}
    resolving = set()
    def unpack(node, path):
        if path in cache:
            return cache[path]
        if 'derived_master' in node:
            resolved = _resolve_derived_master(owner, derived_references[path], owner_identity,
                                               master_resolver)
            cache[path] = resolved
            return resolved
        if 'owner_reference' in node:
            resolved = _resolve_owner(owner, path, owner_references[path], owner_identity,
                                      owner_resolver)
            cache[path] = resolved
            return resolved
        if 'batch_reference' in node:
            rows = _resolve_batch(owner, path, batch_references[path], owner_identity, batch_resolver,
                allow_owned_failed=True)
            cache[path] = rows
            return rows
        if 'reference' in node:
            target = node['reference']
            if target in resolving:
                raise ValueError('Typed input alias cycle')
            if target not in cache:
                resolving.add(target)
                cache[target] = unpack(node_at(target), target)
                resolving.remove(target)
            return deepcopy(cache[target])
        if 'scalar' in node:
            return node['scalar']
        if 'empty' in node:
            return []
        if 'object' in node:
            return {key: unpack(child, path+'/'+key) for key, child in node['object']}
        if 'scalars' in node:
            return [row['value'] for row in read(node['scalars'])]
        if 'shape' in node:
            count = node.get('count')
            if type(count) is not int or count < 0 or (node['shape'] is None) != (count == 0):
                raise ValueError('Typed input uniform shape identity drift')
            from itertools import repeat
            templates = None
            scalars = read(node['records']) if node['records'] else RecordRows(count, lambda: ({} for _ in range(count)))
        else:
            types = read(node['shape_image'])
            templates = []
            for item in types:
                shape_id = item['shape_id']
                if type(shape_id) is not int or not 0 <= shape_id < len(node['shapes']):
                    raise ValueError('Typed input shape identity drift')
                templates.append(node['shapes'][shape_id])
            scalars = read(node['records']) if node['records'] else [{} for _ in types]
        count = count if 'shape' in node else len(templates)
        if count != len(scalars):
            raise ValueError('Typed input shape population drift')

        def rebuild(template, row):
            if template[0] == 'dict':
                return {key: rebuild(child, row) for key, child in template[1]}
            if template[0] == 'list':
                return []
            return row['/'.join(template[1])]
        def records():
            for template, row in zip(repeat(node['shape'], count) if templates is None else templates, scalars):
                yield rebuild(template, row)
        materialized = any(path == root or path.startswith(root+'/')
                           for root in materialized_roots)
        rows = (RecordRows(count, records)
                if not materialized and not node['children'] and count > 10000
                else list(records()))
        for field, child, link in node['children']:
            child_path = path+'/children/'+'/'.join(field)
            values, links = unpack(child, child_path), read(link)
            if len(values) != len(links):
                raise ValueError('Typed input child population drift')
            for item, childvalue in zip(links, values):
                if (type(item.get('parent_ordinal')) is not int
                        or type(item.get('child_ordinal')) is not int
                        or not 0 <= item['parent_ordinal'] < len(rows)):
                    raise ValueError('Typed input child ownership/order drift')
                target = common_get(rows[item['parent_ordinal']], field)
                if not isinstance(target, list) or len(target) != item['child_ordinal']:
                    raise ValueError('Typed input child ownership/order drift')
                target.append(childvalue)
        cache[path] = rows
        return rows

    from mta.runtime.input_storage import get as common_get
    tree = value['tree']
    if components is not None:
        requested = [component if component.startswith('input/') else 'input/' + component
                     for component in components]
        def prune(node, path):
            if path in requested:
                return node
            children = [[key, selected] for key, child in node.get('object', [])
                        if (selected := prune(child, path + '/' + key)) is not None]
            return {'object': children} if children else None
        tree = prune(tree, 'input') or {'object': []}
    return unpack(tree, 'input')


def audit_references(owner, *, identity_resolver=None, batch_resolver=None,
                     owner_resolver=None, master_resolver=None):
    """Validate and return bounded external references for receipt integration."""
    value = owner.input_payload
    if (value.get('schema') != V3 or value.get('content_digest') != owner.input_digest
            or digest(value) != owner.input_manifest_digest):
        raise ValueError('Typed daily input manifest identity drift')
    owner_identity = _identity(owner, identity_resolver, reading=True)
    if value.get('identity') != owner_identity:
        raise ValueError('Typed input live owner identity drift')
    has_content = 'content_identity' in value or 'content_kind' in value
    if has_content:
        if (value.get('content_kind') != CONTENT_KIND
                or _validate_content_owner(owner, owner_identity,
                    value.get('content_identity'), identity_resolver)
                   != value.get('content_identity')):
            raise ValueError('Typed prepared input content identity differs')
    references = value.get('batch_references', {})
    if not isinstance(references, dict):
        raise ValueError('Typed input batch reference manifest differs')
    owner_references = value.get('owner_references', {})
    if not isinstance(owner_references, dict):
        raise ValueError('Typed input owner reference manifest differs')
    derived_references = value.get('derived_references', {})
    if not isinstance(derived_references, dict):
        raise ValueError('Typed input derived reference manifest differs')
    aliases = value.get('aliases', {})
    if not isinstance(aliases, dict):
        raise ValueError('Typed input alias manifest differs')
    nodes, owner_nodes, derived_nodes = set(), set(), set()
    def inspect(node, path):
        if 'derived_master' in node:
            if set(node) != {'derived_master'} or node['derived_master'] != path:
                raise ValueError('Typed input derived master node differs')
            derived_nodes.add(path)
            return
        if 'owner_reference' in node:
            if set(node) != {'owner_reference'} or node['owner_reference'] != path:
                raise ValueError('Typed input owner reference node differs')
            owner_nodes.add(path)
            return
        if 'batch_reference' in node:
            if set(node) != {'batch_reference'} or node['batch_reference'] != path:
                raise ValueError('Typed input batch reference node differs')
            nodes.add(path)
            return
        for key, child in node.get('object', []):
            inspect(child, path + '/' + key)
        for field, child, _ in node.get('children', []):
            inspect(child, path + '/children/' + '/'.join(field))
    inspect(value.get('tree', {}), 'input')
    if nodes != set(references):
        raise ValueError('Typed input batch references must be explicit')
    if (owner_nodes != set(owner_references) or owner_nodes & nodes
            or owner_nodes & set(aliases) or nodes & set(aliases)):
        raise ValueError('Typed input owner references must be explicit')
    if (derived_nodes != set(derived_references) or derived_nodes != ({MASTER_PATH}
            if derived_references else set()) or derived_nodes & (nodes | owner_nodes | set(aliases))):
        raise ValueError('Typed input derived master references must be explicit')
    result = {}
    for path, reference in references.items():
        rows = _resolve_batch(owner, path, reference, owner_identity, batch_resolver,
                              allow_owned_failed=True)
        for _ in rows:
            pass
        result[path] = _batch_reference(reference, path)
    for path, reference in owner_references.items():
        resolved = _resolve_owner(owner, path, reference, owner_identity, owner_resolver)
        if _collection(resolved):
            for _ in resolved: pass
        result[path] = _owner_reference(reference, path)
    for path, reference in derived_references.items():
        resolved = _resolve_derived_master(owner, reference, owner_identity, master_resolver)
        for _ in resolved:
            pass
        result[path] = _master_reference(reference)
    return result


# Finite lossless same-opening aliases. Distinct producer populations remain
# separate whenever any typed value, key order, duplicate or ordinal differs.
OPENING_ALIASES = {
    'input/opening/state/controls/importer_settings': 'input/opening/state/importer_settings',
    'input/opening/state/btr/SKUDescriptionTbl': 'input/opening/state/importer/SKUDescriptionTbl',
    'input/opening/state/dbm/SKUDescriptionTbl': 'input/opening/state/importer/SKUDescriptionTbl',
    'input/opening/state/btr/SiteDescriptionTbl': 'input/opening/state/importer/SiteDescriptionTbl',
    'input/opening/state/dbm/SiteDescriptionTbl': 'input/opening/state/importer/SiteDescriptionTbl',
}


def opening_aliases(frame):
    aliases = {}
    for source, target in OPENING_ALIASES.items():
        try:
            left, right = _at(frame, source), _at(frame, target)
        except ValueError:
            continue
        if _collection(left) and _collection(right) and _typed_equal(left, right):
            aliases[source] = target
    return aliases
