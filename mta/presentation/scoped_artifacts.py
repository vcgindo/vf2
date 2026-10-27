"""Explicit owned-test InputData over already accepted producer cells.

The declaration is a delivery disposition, never a new calculation/input seal.
Original captures, phase receipts and dedicated input-capture policy stay intact.
"""
from copy import deepcopy
import hashlib
import inspect
import json
import os
from pathlib import Path
from uuid import uuid4
import zipfile

from mta.serialization import digest

SCHEMA = 'fresh-scoped-test-delivery-v1'
PRODUCTION_SCHEMA = 'vectorflow-production-generic-scope-delivery-v1'
RECEIPT = 'fresh-scoped-input-artifact-v1'
TABLES = ('MasterDataRaw', 'DailyDataRaw', 'SOBDataRaw', 'MOQDataRaw1')
PHYSICAL = tuple(name + '.csv' for name in (*TABLES, 'InTransitRaw'))
FIELDS = frozenset(('schema', 'purpose', 'run_id', 'phase_id', 'phase_digest',
    'input_digest', 'input_manifest_digest', 'site_code', 'post_bpr_hook',
    'input_download', 'importer_database', 'physical_files', 'input_tables',
    'archive_clock', 'authority'))


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def declaration(path, expected_sha256):
    from mta.mdm.initialization_contract import object_pairs
    from mta.runtime.ingestion_context import sha
    from uuid import UUID
    sha(expected_sha256)
    with Path(path).open('rb') as stream:
        raw = stream.read(8193)
    if len(raw) > 8192 or _sha(raw) != expected_sha256:
        raise ValueError('Scoped delivery declaration file differs')
    value = json.loads(raw, object_pairs_hook=object_pairs)
    production = isinstance(value, dict) and value.get('schema') == PRODUCTION_SCHEMA
    from mta.runtime import production_scope_policy as generic
    if (type(value) is not dict or set(value) != FIELDS
            or value['schema'] not in (SCHEMA, PRODUCTION_SCHEMA)
            or value['purpose'] != (generic.PURPOSE if production else 'owned-scoped-test')
            or value['input_download'] is not True
            or value['physical_files'] != list(PHYSICAL) or value['input_tables'] != list(TABLES)
            or value['archive_clock'] != 'business-midnight-Asia-Kolkata'
            or (not production and value['site_code'] != 'SUPPLIED-INSTANCE')
            or value['post_bpr_hook'] != (generic.MODE if production else 'explicit-test-no-op')
            or type(value['authority']) is not str or not 1 <= len(value['authority']) <= 1000):
        raise ValueError('Explicit enabled owned-test InputData and hook disposition required')
    if production:
        generic.text(value['site_code'], 100, 'configured site')
        generic.archive_label(value['importer_database'])
    for name in ('run_id', 'phase_id'):
        UUID(value[name])
    for name in ('phase_digest', 'input_digest', 'input_manifest_digest'):
        sha(value[name])
    if type(value['importer_database']) is not str:
        raise ValueError('Explicit owned input database label required')
    return value


def _bind(phase_id, expected_digest, value):
    from django.db import connection
    from mta.runtime.scoped_pick_files import _accepted
    from mta.runtime.input_reader import read_input
    phase = _accepted(phase_id, expected_digest)
    run = phase.run
    with connection.cursor() as cursor:
        cursor.execute('SELECT current_database()')
        database = cursor.fetchone()[0]
    production = value['schema'] == PRODUCTION_SCHEMA
    if production:
        from mta.runtime.scope_runtime_reports import require_test_database
        require_test_database(run=run)
        raw = read_input(run, components=('scope_request',))['scope_request']
        from mta.runtime.production_scope_policy import SCHEMA as POLICY_SCHEMA
        if raw['dispositions']['schema'] != POLICY_SCHEMA:
            raise ValueError('Production archive requires its captured generic policy')
        if (value['site_code'] != raw['dispositions']['site_code']
                or value['authority'] != raw['dispositions']['authority']):
            raise ValueError('Production archive differs from captured policy authority')
    if ((not production and not database.lower().startswith('vftest_fresh_'))
            or (production and value['importer_database'] != database)
            or value['importer_database'].casefold() != database.casefold()
            or phase.phase != 'BPR' or value['run_id'] != str(run.pk)
            or value['phase_id'] != str(phase.pk) or value['phase_digest'] != phase.digest
            or value['input_digest'] != run.input_digest
            or value['input_manifest_digest'] != run.input_manifest_digest):
        raise ValueError('Scoped delivery declaration owner differs')
    profile = read_input(run, components=('profile',))['profile']
    if profile['delivery']['site_code'] != value['site_code']:
        raise ValueError('Scoped test site disposition differs from captured site')
    return phase


def producer_tables(phase):
    """Project original accepted bags, without fabricating an opt-in capture.

    These are the exact arguments of capture_input_tables in produce_bpr.
    Dedicated operational_input_tables/export policy is not relabelled or changed.
    """
    from mta.runtime import phase_state, relational_state as typed
    from mta.application.operational_input_capture import capture_input_tables
    manifest = phase.snapshot.manifest
    locations = dict(MasterDataRaw=('control_final', 'raw_master'),
        DailyDataRaw=('daily_final', 'DailyDataRaw'),
        SOBDataRaw=('complete', 'SOBDataRaw'), MOQDataRaw1=('complete', 'MOQDataRaw1'))
    bags, owners = {}, {}
    for name, (group, field) in locations.items():
        node = manifest['state'][group][field]
        if type(node) is not dict or set(node) != {'image'}:
            raise ValueError('Accepted InputData producer reference missing: ' + name)
        metadata = manifest['images'][node['image']]
        bags[name] = typed.load_image(phase.run, metadata, table_registry=phase_state.REGISTRY)
        owners[name] = deepcopy(metadata)
    checked = capture_input_tables(controls={'raw_master': bags['MasterDataRaw']},
        daily={'DailyDataRaw': bags['DailyDataRaw']}, supplier=bags)
    return checked, owners


def payloads(phase, value):
    from mta.runtime.input_reader import read_input
    from mta.application.operational_inputs import physical_files
    from mta.application.operational_upload_logs import _schema
    from mta.application.operational_sqlcmd import input_table_bytes
    from mta.runtime.operational_archive import TRANSIT_COLUMNS
    day = read_input(phase.run, components=('day',))['day']
    shipment = day['shipment_input']
    if shipment['business_date'] != phase.run.business_date.isoformat():
        raise ValueError('Captured shipment date differs')
    # The retained physical interface reproduces typed intake; it is not an
    # assertion that original external CSV bytes were supplied to this JSON run.
    raw = dict(MasterDataRaw=list(day['raw_master']), DailyDataRaw=list(day['raw_daily']),
        SOBDataRaw=list(day['supplier_feeds']['SOBDataRaw']),
        MOQDataRaw1=list(day['supplier_feeds']['MOQDataRaw1']), InTransitRaw=list(shipment['rows']))
    physical = physical_files(_schema, raw, TRANSIT_COLUMNS)
    processed, owners = producer_tables(phase)
    exports = {value['importer_database'] + '_' + name + '.CSV':
        input_table_bytes(_schema['tables']['Importer/' + name], processed[name]) for name in TABLES}
    return physical, exports, owners


def _root(phase, value):
    from mta.runtime.input_reader import read_input
    from mta.application.operational_io import owned_path
    root = Path(read_input(phase.run, components=('pick_output_root',))['pick_output_root'])
    relative = str(phase.run_id) + '/scope-input/' + str(phase.pk) + '/' + digest(value)
    return owned_path(root, relative)


def _recipe():
    from mta.runtime.retained_registered_execution_compatibility import artifact_recipe
    return artifact_recipe(digest(inspect.getsource(inspect.getmodule(_recipe))))


def _members(phase, physical, exports):
    from mta.application.operational_input_archive import archive_clock, MARKER_BYTES
    return {**physical, **exports, archive_clock(phase.run.business_date)['marker']: MARKER_BYTES}


def prepare(phase_id, *, expected_digest, declaration_file, declaration_sha256):
    """Offline file producer only; never sets whole-scope or serving status."""
    from mta.application.operational_input_archive import write_input_archive
    from mta.application.operational_io import inspect_file
    value = declaration(declaration_file, declaration_sha256)
    phase = _bind(phase_id, expected_digest, value)
    final_root = _root(phase, value)
    if (final_root / 'artifact.json').exists():
        return verify(phase_id, expected_digest=expected_digest,
            declaration_file=declaration_file, declaration_sha256=declaration_sha256)
    # Only publish a complete directory. Failed private candidates remain for
    # inspection; a later retry starts a new candidate and keeps the same owner.
    root = final_root.with_name(final_root.name + '.' + uuid4().hex)
    root.mkdir(parents=True, exist_ok=False)
    physical, exports, owners = payloads(phase, value)
    members = _members(phase, physical, exports)
    if sum(len(raw) for raw in members.values()) > 256 * 1024**2:
        raise ValueError('Scoped InputData expanded size exceeds bound')
    def archive_writer(*, root, staging, members, destination):
        from mta.application.operational_io import owned_path
        target = owned_path(root, destination)
        with zipfile.ZipFile(target, 'x', compression=zipfile.ZIP_DEFLATED) as archive:
            for name in members:
                archive.write(owned_path(root, staging + '/' + name), arcname=name)
        return dict(inspect_file(root, destination), members=members)
    result = write_input_archive(root, physical=physical, table_exports=exports,
        importer_database=value['importer_database'], business_date=phase.run.business_date,
        archive_writer=archive_writer,
        database_policy=('vectorflow-production-generic-scope-policy-v1'
                         if value['schema'] == PRODUCTION_SCHEMA else None))
    receipt = dict(schema=RECEIPT, declaration=value, declaration_sha256=declaration_sha256,
        recipe_digest=_recipe(), phase_snapshot_digest=phase.snapshot.state_digest,
        producer_images=owners, members={name: dict(size=len(raw), sha256=_sha(raw))
            for name, raw in members.items()}, download=result['download'])
    if len(json.dumps(receipt)) > 32768:
        raise ValueError('Scoped InputData receipt exceeds bound')
    # Exclusive root and exclusive final receipt; partial failures stay visible
    # for explicit recovery, never overwrite a previously prepared archive.
    with (root / 'artifact.json').open('x', encoding='utf-8') as stream:
        json.dump(receipt, stream, sort_keys=True)
        stream.flush()
        os.fsync(stream.fileno())
    os.rename(root, final_root)
    return verify(phase_id, expected_digest=expected_digest,
        declaration_file=declaration_file, declaration_sha256=declaration_sha256)


def verify(phase_id, *, expected_digest, declaration_file, declaration_sha256,
           receipt_sha256=None, verify_bytes=True):
    from mta.application.operational_io import owned_path, inspect_file
    value = declaration(declaration_file, declaration_sha256)
    phase = _bind(phase_id, expected_digest, value)
    root = _root(phase, value)
    path = owned_path(root, 'artifact.json')
    with path.open('rb') as stream:
        raw = stream.read(32769)
    if len(raw) > 32768:
        raise ValueError('Scoped InputData receipt exceeds bound')
    if receipt_sha256 is not None:
        from mta.runtime.ingestion_context import sha
        sha(receipt_sha256)
        if _sha(raw) != receipt_sha256:
            raise ValueError('Scoped InputData independently pinned receipt differs')
    from mta.mdm.initialization_contract import object_pairs
    receipt = json.loads(raw, object_pairs_hook=object_pairs)
    if (receipt['schema'] != RECEIPT or receipt['declaration'] != value
            or receipt['declaration_sha256'] != declaration_sha256
            or receipt['recipe_digest'] != _recipe()
            or receipt['phase_snapshot_digest'] != phase.snapshot.state_digest):
        raise ValueError('Scoped InputData receipt owner differs')
    if receipt_sha256 is None:
        # Offline idempotent prepare independently rederives member identities.
        # Runtime uses its separately deployed receipt SHA and never runs this.
        physical, exports, owners = payloads(phase, value)
        members = _members(phase, physical, exports)
        if (receipt['producer_images'] != owners or receipt['members'] != {
                name: dict(size=len(raw), sha256=_sha(raw)) for name, raw in members.items()}):
            raise ValueError('Scoped InputData accepted producer bytes differ')
    target = owned_path(root, 'download/InputData.zip')
    stat = target.stat()
    if not target.is_file() or stat.st_size != receipt['download']['size_bytes']:
        raise ValueError('Scoped InputData archive size differs')
    if not verify_bytes:
        if receipt_sha256 is None:
            raise ValueError('Runtime artifact metadata requires independent receipt pin')
        return dict(receipt, receipt_sha256=_sha(raw), file_identity=(
            stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns))
    download = inspect_file(root, 'download/InputData.zip')
    if download != receipt['download']:
        raise ValueError('Scoped InputData archive bytes differ')
    with zipfile.ZipFile(owned_path(root, 'download/InputData.zip')) as archive:
        infos = archive.infolist()
        if (len(infos) != len(receipt['members']) or len(infos) != 10
                or {item.filename for item in infos} != set(receipt['members'])):
            raise ValueError('Scoped InputData member roster differs')
        if sum(item.file_size for item in infos) > 256 * 1024**2:
            raise ValueError('Scoped InputData expanded size exceeds bound')
        for item in infos:
            expected = receipt['members'][item.filename]
            checksum = hashlib.sha256()
            with archive.open(item) as stream:
                while block := stream.read(1024 * 1024):
                    checksum.update(block)
            if item.file_size != expected['size'] or checksum.hexdigest() != expected['sha256']:
                raise ValueError('Scoped InputData member bytes differ')
    return dict(receipt, receipt_sha256=_sha(raw))


def open_archive(view, declaration_file, declaration_sha256, receipt_sha256):
    value = verify(view.bpr.sources.acceptance_id, expected_digest=view.bpr.sources.acceptance_digest,
        declaration_file=declaration_file, declaration_sha256=declaration_sha256,
        receipt_sha256=receipt_sha256)
    phase = _bind(view.bpr.sources.acceptance_id, view.bpr.sources.acceptance_digest, value['declaration'])
    from contextlib import ExitStack
    from mta.runtime.scoped_pick_files import _folder, _open, _stream_metadata
    if os.name != 'posix' or not hasattr(os, 'O_NOFOLLOW'):
        raise ValueError('Safe directory-relative InputData IO is unavailable')
    root = _root(phase, value['declaration'])
    with ExitStack() as stack:
        descriptor = os.open(root.anchor, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        stack.callback(os.close, descriptor)
        for name in (*root.parts[1:], 'download'):
            descriptor = stack.enter_context(_folder(descriptor, name))
        stream = _open(descriptor, 'InputData.zip')
    try:
        actual = _stream_metadata(stream)
        expected = value['download']
        if actual != dict(size=expected['size_bytes'], sha256=expected['sha256']):
            raise ValueError('Scoped InputData changed before opening')
        stream.seek(0)
        return stream
    except BaseException:
        stream.close()
        raise


def configured():
    from django.conf import settings
    values = tuple(getattr(settings, name, '') for name in (
        'VF_MTA_SCOPE_DELIVERY_FILE', 'VF_MTA_SCOPE_DELIVERY_SHA256',
        'VF_MTA_SCOPE_ARTIFACT_SHA256'))
    if any(values) and not all(values):
        raise ValueError('Complete scoped delivery and artifact receipt pins required')
    return values if all(values) else None


def selected(view, *, verify_bytes=False):
    values = configured()
    if values is None:
        return None
    path, sha, receipt = values
    return verify(view.bpr.sources.acceptance_id,
        expected_digest=view.bpr.sources.acceptance_digest, declaration_file=path,
        declaration_sha256=sha, receipt_sha256=receipt, verify_bytes=verify_bytes)
