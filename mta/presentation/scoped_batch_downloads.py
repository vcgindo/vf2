"""Read-only verification and finite download admission for prepared BPR files."""
from contextlib import ExitStack
from datetime import date
import hashlib
import json
import os
from pathlib import Path

from mta.application import operational_io
from mta.presentation import scoped_batch_files as producer, scoped_sources
from mta.presentation.context import PublicationUnavailable
from mta.serialization import digest

DOWNLOAD = 'download/BOR_OrderAllocation.csv'
FIELDS = frozenset(('schema','run_id','phase_id','phase_digest','snapshot_digest','business_date',
    'declaration','recipe_digest','sources','colour_reference','producer_sources','counts','payloads',
    'payload_digest','wrappers','files','digest'))
SOURCE_TABLES = {
    'state/importer/SKUDescriptionTbl':'Importer/SKUDescriptionTbl',
    'state/importer/SiteDescriptionTbl':'Importer/SiteDescriptionTbl',
    'consumers/production_reports/BORWithOrderAllocation':'production/BORWithOrderAllocation',
    'consumers/production_reports/BOROARequirement':'production/BOROARequirement',
    'state/diagnostics/failed_force':'Projection/FailedForce',
    'state/importer/MasterData':'Importer/MasterData',
    'state/control_final/phase_out':'DBM/PhaseOutTbl',
    'state/bpr_master':'BPR/BPRMaster',
    'state/late/BPRDailyConsumption':'BPR/DailyConsumption',
}


def _fail(reason):
    raise PublicationUnavailable('bpr_batch_download_' + reason)


def configured():
    from django.conf import settings
    values = tuple(getattr(settings, name, '') for name in
        ('VF_MTA_SCOPE_BATCH_MANIFEST_FILE','VF_MTA_SCOPE_BATCH_MANIFEST_SHA256'))
    if any(values) and not all(values):
        _fail('complete_pins_required')
    return values if all(values) else None


def _manifest(path, expected_sha256):
    from mta.runtime.ingestion_context import sha
    from mta.mdm.initialization_contract import object_pairs
    sha(expected_sha256)
    path = Path(path)
    if not path.is_absolute() or path.name != 'scoped-batch-files.json':
        _fail('manifest_path_differs')
    checked = operational_io.owned_path(path.parent, path.name)
    with checked.open('rb') as stream:
        raw = stream.read(262145)
    if len(raw) > 262144 or hashlib.sha256(raw).hexdigest() != expected_sha256:
        _fail('manifest_pin_differs')
    value = json.loads(raw, object_pairs_hook=object_pairs)
    if (type(value) is not dict or set(value) != FIELDS or value['schema'] != producer.SCHEMA
            or value['digest'] != digest({k:v for k,v in value.items() if k != 'digest'})
            or value['recipe_digest'] != producer.recipe_digest()
            or value['declaration'] != producer.TEST_DECLARATION
            or type(value['declaration']['IsMTOEnvironment']) is not int):
        _fail('manifest_identity_differs')
    original = {k:v for k,v in value.items() if k not in ('digest','payload_digest','files','wrappers')}
    if value['payload_digest'] != digest(original):
        _fail('payload_identity_differs')
    expected_producers = dict(bor=producer.bor.SOURCES['report'],failed_force=producer.alerts.SOURCES['force'],
        exceptions=producer.exceptions.SOURCES,wrappers={key: producer.files.SOURCES[key]
            for key in ('bor','force_norm','parent_norm','bpr_exceptions')})
    if (value['colour_reference'] != producer.native_report_colours.reference()
            or digest(value['producer_sources']) != digest(expected_producers)):
        _fail('producer_sources_differ')
    return path.parent, value


def _sources(phase, value):
    manifest = phase.snapshot.manifest
    if set(value['sources']) != set(SOURCE_TABLES):
        _fail('source_roster_differs')
    for node, table in SOURCE_TABLES.items():
        logical = scoped_sources._image(manifest, tuple(node.split('/')))
        if logical is None:
            _fail('source_missing')
        item = scoped_sources._checked(manifest['images'].get(logical))
        if (not logical.startswith('phase/BPR/') or item['table'] != table
                or item['image'] not in (logical,logical.replace('phase/BPR/','phase/PRE_BPR/',1))
                or value['sources'][node] != dict(logical_image=logical,physical_image=item['image'],
                    table=table,count=item['count'],rows_digest=item['digest'],fields=item['fields'])):
            _fail('source_owner_differs')


def _files(root, value):
    from mta.runtime.ingestion_context import sha
    names = ('BOR_OrderAllocation','FailedForceNormChanges','NoNormParentReport','BPRExceptionReport')
    counts, payloads = value['counts'], value['payloads']
    if set(counts) != set(names) or set(payloads) != set(names):
        _fail('report_roster_differs')
    for name in names:
        if type(counts[name]) is not int or counts[name] < 0:
            _fail('report_count_differs')
        item = payloads[name]
        if item is None:
            if name != 'BPRExceptionReport' or counts[name] != 0:
                _fail('payload_missing')
        else:
            if (type(item) is not dict or set(item) != {'sha256','size_bytes'}
                    or type(item['size_bytes']) is not int or item['size_bytes'] < 0):
                _fail('payload_metadata_differs')
            sha(item['sha256'])
    if (payloads['BPRExceptionReport'] is None) != (counts['BPRExceptionReport'] == 0):
        _fail('exception_branch_differs')
    parent = payloads['NoNormParentReport']
    if (parent['size_bytes'] == 0) != (counts['NoNormParentReport'] == 0):
        _fail('parent_branch_differs')
    if parent['size_bytes'] == 0 and parent['sha256'] != hashlib.sha256(b'').hexdigest():
        _fail('empty_parent_bytes_differ')
    direct = {'output/BOR_OrderAllocation.csv':payloads['BOR_OrderAllocation'],
        DOWNLOAD:payloads['BOR_OrderAllocation'],
        f"output/{date.fromisoformat(value['business_date']).day:02d}-FailedForceNormChanges.csv":payloads['FailedForceNormChanges']}
    zipped = {}
    if parent['size_bytes'] == 0:
        direct['output/NoNormParentReport.csv'] = parent
    else:
        for location in ('output','download'):
            zipped[location+'/NoNormParentReport.zip'] = ('NoNormParentReport.csv',parent)
    if payloads['BPRExceptionReport'] is not None:
        direct['output/BPRExceptionReport.csv'] = payloads['BPRExceptionReport']
        zipped['download/BPRExceptionReport.zip'] = ('BPRExceptionReport.csv',payloads['BPRExceptionReport'])
    roster = value['files']
    if type(roster) is not list or len(roster) != len(direct) + len(zipped):
        _fail('file_roster_differs')
    actual = {}
    for item in roster:
        if type(item) is not dict or set(item) != {'relative_path','sha256','size_bytes'}:
            _fail('file_metadata_differs')
        if type(item['size_bytes']) is not int or item['size_bytes'] < 0:
            _fail('file_metadata_differs')
        sha(item['sha256'])
        path = item['relative_path']
        if type(path) is not str or path not in direct.keys() | zipped.keys() or path in actual:
            _fail('file_path_denied')
        if operational_io.inspect_file(root, path) != item:
            _fail('file_bytes_differ')
        if path in direct and {k:item[k] for k in ('sha256','size_bytes')} != direct[path]:
            _fail('file_payload_differs')
        if path in zipped:
            member, expected = zipped[path]
            rows = operational_io.zip_members(root,path)
            if rows != [dict(ordinal=0,name=member,sha256=expected['sha256'],size_bytes=expected['size_bytes'])]:
                _fail('archive_members_differ')
        actual[path] = item
    found = {path.relative_to(root).as_posix() for path in root.rglob('*') if path.is_file()}
    if found != set(actual) | {'scoped-batch-files.json'}:
        _fail('unexpected_retained_file')
    return actual


def verify(phase_id, *, expected_digest, expected_run_id, expected_snapshot_digest,
           manifest_file, manifest_sha256):
    """Verify pinned files against a lightweight admitted phase identity.

    Never selects a view or invokes a producer. This can run during admission.
    """
    from mta.runtime.scope_runtime_reports import require_test_database
    try:
        require_test_database()
        root, value = _manifest(manifest_file, manifest_sha256)
        phase = scoped_sources._accepted_phase(phase_id, expected_digest)
        if (phase.phase != 'BPR' or value['run_id'] != str(expected_run_id)
                or value['run_id'] != str(phase.run_id) or value['phase_id'] != str(phase_id)
                or value['phase_id'] != str(phase.pk) or value['phase_digest'] != expected_digest
                or value['phase_digest'] != phase.digest or value['snapshot_digest'] != expected_snapshot_digest
                or value['snapshot_digest'] != phase.snapshot.state_digest
                or value['business_date'] != phase.run.business_date.isoformat()):
            _fail('phase_owner_differs')
        _sources(phase, value)
        files = _files(root, value)
        return dict(schema='fresh-scoped-batch-downloads-v1',manifest_sha256=manifest_sha256,
            metadata_digest=value['digest'],payload_digest=value['payload_digest'],recipe_digest=value['recipe_digest'],
            run_id=value['run_id'],phase_id=value['phase_id'],phase_digest=value['phase_digest'],
            snapshot_digest=value['snapshot_digest'],counts=value['counts'],files=files)
    except (OSError,ValueError,KeyError,TypeError,AttributeError) as error:
        if isinstance(error,PublicationUnavailable):
            raise
        raise PublicationUnavailable('bpr_batch_download_unavailable') from error


def _selected(view, values):
    path, sha = values
    sources = view.bpr.sources
    return verify(sources.acceptance_id,expected_digest=sources.acceptance_digest,
        expected_run_id=view.run_id,expected_snapshot_digest=sources.snapshot_digest,
        manifest_file=path,manifest_sha256=sha)


def selected(view):
    """Return None when unsupported; otherwise fully verify the finite files."""
    values = configured()
    return None if values is None else _selected(view, values)


def _open_download(root, expected):
    from mta.runtime.scoped_pick_files import _folder, _open, _stream_metadata
    if os.name != 'posix' or not hasattr(os,'O_NOFOLLOW'):
        _fail('safe_open_unavailable')
    root = Path(root)
    with ExitStack() as stack:
        descriptor = os.open(root.anchor,os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        stack.callback(os.close,descriptor)
        for name in (*root.parts[1:],'download'):
            descriptor = stack.enter_context(_folder(descriptor,name))
        stream = _open(descriptor,'BOR_OrderAllocation.csv')
    try:
        if _stream_metadata(stream) != dict(size=expected['size_bytes'],sha256=expected['sha256']):
            _fail('changed_before_opening')
        stream.seek(0)
        return stream
    except BaseException:
        stream.close()
        raise


def open_file(view, relative_path=DOWNLOAD):
    """Only the BOR download is public; diagnostics remain output-only."""
    if relative_path != DOWNLOAD:
        _fail('file_path_denied')
    values = configured()
    if values is None:
        _fail('not_configured')
    verified = _selected(view, values)
    try:
        return _open_download(Path(values[0]).parent,verified['files'][DOWNLOAD])
    except (OSError,ValueError) as error:
        if isinstance(error,PublicationUnavailable):
            raise
        raise PublicationUnavailable('bpr_batch_download_safe_open_failed') from error
