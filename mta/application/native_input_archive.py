"""Immutable native input export, prepared offline without an engine invocation.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import zipfile

from mta.runtime.input_reader import read_input
from mta.serialization import canonical_parts, digest

SCHEMA = 'fresh-native-input-download-v1'
FILENAME = 'InputData.zip'
MAX_COMPRESSED = 64 * 1024**2
MAX_UNCOMPRESSED = 256 * 1024**2
MEMBERS = frozenset(('manifest.json', 'NativeOpeningInput.json',
    'NativeDailyInput.json', 'NativeCapturedInput.json', 'NativeInputSchema.json'))
RESTRICTION = __doc__.splitlines()[2]


class ArchiveDenied(ValueError):
    pass


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _canonical(value):
    result = io.BytesIO()
    for part in canonical_parts(value):
        if result.tell() + len(part) > MAX_UNCOMPRESSED:
            raise ArchiveDenied('native_input_archive_size_limit')
        result.write(part)
    return result.getvalue()


def _inputs(run):
    from mta.presentation import native_publication
    native_publication.require_mode()
    identity = native_publication.identity(run)
    value = read_input(run)
    if (digest(value) != run.input_digest
            or digest(run.input_payload) != run.input_manifest_digest
            or value.get('initialization_binding') != identity['initialization']):
        raise ArchiveDenied('native_input_archive_identity_drift')
    return value


def _pins(run, captured):
    binding = captured['initialization_binding']
    return dict(schema=SCHEMA, restriction=RESTRICTION, run_id=str(run.pk),
        business_date=run.business_date.isoformat(),
        initialization_id=binding['id'], source_digest=binding['source_digest'],
        input_digest=run.input_digest, input_manifest_digest=run.input_manifest_digest,
        output_digest=run.output_digest)


def _original(path, expected):
    path = Path(path)
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ArchiveDenied('native_input_original_symlink_denied')
    try:
        with path.open('rb') as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                raise ArchiveDenied('native_input_original_not_file')
            raw = stream.read(MAX_UNCOMPRESSED + 1)
    except OSError as error:
        raise ArchiveDenied('native_input_original_unavailable') from error
    if len(raw) > MAX_UNCOMPRESSED or _sha(raw) != expected:
        raise ArchiveDenied('native_input_original_hash_or_size_drift')
    return raw


def prepare(run, opening_file, daily_file):
    captured = _inputs(run)
    payloads = {
        'NativeOpeningInput.json': _original(opening_file,
            captured['initialization_binding']['input_sha256']),
        'NativeDailyInput.json': _original(daily_file, captured['daily_input_sha256']),
        'NativeCapturedInput.json': _canonical(captured),
        'NativeInputSchema.json': _canonical(run.input_payload),
    }
    manifest = dict(_pins(run, captured), files={name: dict(bytes=len(raw),
        sha256=_sha(raw)) for name, raw in payloads.items()})
    payloads['manifest.json'] = _canonical(manifest)
    if sum(map(len, payloads.values())) > MAX_UNCOMPRESSED:
        raise ArchiveDenied('native_input_archive_size_limit')
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for name, raw in payloads.items():
            info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (stat.S_IFREG | 0o440) << 16
            archive.writestr(info, raw)
    if buffer.tell() > MAX_COMPRESSED:
        raise ArchiveDenied('native_input_archive_compressed_limit')
    # Pick owns the existing per-run download directory; never create another
    # root or overwrite a prior export, including a preserved partial file.
    from mta.presentation.pick_downloads import _owned_file, PickDownloadDenied
    try:
        sibling = _owned_file(run, 'LogisticPickListReport.csv')
    except PickDownloadDenied as error:
        raise ArchiveDenied(str(error)) from error
    target = sibling.parent / FILENAME
    if target.exists():
        stream, _ = open_archive(run)
        try:
            if stream.read(MAX_COMPRESSED + 1) != buffer.getvalue():
                raise ArchiveDenied('native_input_archive_existing_bytes_differ')
        finally:
            stream.close()
    else:
        with target.open('xb') as stream:
            stream.write(buffer.getvalue())
    return dict(path=str(target), bytes=target.stat().st_size,
        sha256=_sha(buffer.getvalue()), manifest=manifest)


def open_archive(run):
    captured = _inputs(run)
    from mta.presentation.pick_downloads import _owned_file, PickDownloadDenied
    try:
        path = _owned_file(run, FILENAME)
    except PickDownloadDenied as error:
        raise ArchiveDenied(str(error)) from error
    stream = path.open('rb')
    try:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise ArchiveDenied('native_input_archive_not_file')
        if os.fstat(stream.fileno()).st_size > MAX_COMPRESSED:
            raise ArchiveDenied('native_input_archive_compressed_limit')
        with zipfile.ZipFile(stream) as archive:
            infos = archive.infolist()
            if len(infos) != 5 or {item.filename for item in infos} != MEMBERS:
                raise ArchiveDenied('native_input_archive_member_drift')
            if (sum(item.file_size for item in infos) > MAX_UNCOMPRESSED
                    or any(item.flag_bits & 1 or item.is_dir()
                        or stat.S_ISLNK(item.external_attr >> 16)
                        or item.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED)
                        for item in infos)):
                raise ArchiveDenied('native_input_archive_member_denied')
            manifest = json.loads(archive.read('manifest.json'))
            expected = _pins(run, captured)
            if (not isinstance(manifest, dict) or set(manifest) != set(expected) | {'files'}
                    or any(manifest[k] != v for k, v in expected.items())
                    or not isinstance(manifest['files'], dict)
                    or set(manifest['files']) != MEMBERS - {'manifest.json'}):
                raise ArchiveDenied('native_input_archive_manifest_drift')
            hashes = {
                'NativeOpeningInput.json': captured['initialization_binding']['input_sha256'],
                'NativeDailyInput.json': captured['daily_input_sha256'],
                'NativeCapturedInput.json': run.input_digest,
                'NativeInputSchema.json': run.input_manifest_digest,
            }
            for name, expected_hash in hashes.items():
                raw = archive.read(name)
                if (_sha(raw) != expected_hash or manifest['files'][name] !=
                        dict(bytes=len(raw), sha256=expected_hash)):
                    raise ArchiveDenied('native_input_archive_file_drift')
        stream.seek(0)
        return stream, FILENAME
    except BaseException as error:
        stream.close()
        if isinstance(error, (OSError, zipfile.BadZipFile, KeyError, TypeError, ValueError)):
            raise ArchiveDenied('native_input_archive_invalid: ' + str(error)) from error
        raise
