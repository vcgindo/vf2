"""Owned file/7-Zip effects, with exact member verification and no shell calls."""
from pathlib import Path, PurePosixPath
import hashlib
import os
import shutil
import subprocess
import zipfile


def sha256_file(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def owned_path(root, relative):
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        raise ValueError('Existing owned directory required')
    root = root.resolve(strict=True)
    if not isinstance(relative, str) or not relative or '\\' in relative or ':' in relative:
        raise ValueError('Canonical relative file path required')
    parts = PurePosixPath(relative)
    if parts.is_absolute() or '..' in parts.parts or str(parts) != relative:
        raise ValueError('File path escapes owned directory')
    path = root.joinpath(*parts.parts)
    cursor = root
    for part in parts.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise ValueError('Operational file links are forbidden')
    if not path.resolve().is_relative_to(root):
        raise ValueError('File path escapes owned directory')
    return path


def remove_file(root, relative):
    path = owned_path(root, relative)
    if path.exists() and not path.is_file():
        raise ValueError('Operational deletion requires a file')
    path.unlink(missing_ok=True)


def write_file(root, relative, payload):
    if not isinstance(payload, bytes):
        raise ValueError('Exact file bytes required')
    return write_chunks(root, relative, (payload,))


def write_chunks(root, relative, chunks):
    """Write an owned file incrementally; no receipt is returned on late failure."""
    if isinstance(chunks, (str, bytes, bytearray)):
        raise ValueError('Explicit iterable of file byte chunks required')
    try:
        chunks = iter(chunks)
    except TypeError as error:
        raise ValueError('Explicit iterable of file byte chunks required') from error
    path = owned_path(root, relative)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        for chunk in chunks:
            if not isinstance(chunk, bytes):
                raise ValueError('Exact file byte chunks required')
            stream.write(chunk)
        stream.flush()
        os.fsync(stream.fileno())
    return inspect_file(root, relative)


def copy_file(root, source, destination):
    origin, target = owned_path(root, source), owned_path(root, destination)
    if not origin.is_file() or target.exists():
        raise ValueError('Existing source and absent copy target required')
    target.parent.mkdir(parents=True, exist_ok=True)
    with origin.open('rb') as source_stream, target.open('xb') as target_stream:
        shutil.copyfileobj(source_stream, target_stream, length=1024 * 1024)
        target_stream.flush()
        os.fsync(target_stream.fileno())
    result = inspect_file(root, destination)
    if result['sha256'] != sha256_file(origin):
        raise ValueError('Operational copy bytes differ')
    return result


def inspect_file(root, relative):
    path = owned_path(root, relative)
    if not path.is_file():
        raise ValueError('Required operational file absent: ' + relative)
    return dict(relative_path=relative, sha256=sha256_file(path), size_bytes=path.stat().st_size)


def verify_file(root, receipt):
    actual = inspect_file(root, receipt['relative_path'])
    if actual != {key: receipt[key] for key in actual}:
        raise ValueError('Operational file bytes differ: ' + receipt['relative_path'])
    return actual


def tool_identity(executable, expected_sha256):
    path = Path(executable).resolve(strict=True)
    if not path.is_file() or sha256_file(path) != expected_sha256:
        raise ValueError('Pinned operational tool identity differs')
    return path


def zip_members(root, relative):
    path = owned_path(root, relative)
    members = []
    with zipfile.ZipFile(path) as archive:
        for ordinal, info in enumerate(archive.infolist()):
            if info.is_dir() or info.flag_bits & 1:
                raise ValueError('Unexpected ZIP directory/encrypted member')
            # Same portable path safety rule as standalone files.
            owned_path(root, info.filename)
            checksum = hashlib.sha256()
            with archive.open(info) as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b''):
                    checksum.update(block)
            members.append(dict(ordinal=ordinal, name=info.filename,
                sha256=checksum.hexdigest(), size_bytes=info.file_size))
    if len({row['name'] for row in members}) != len(members):
        raise ValueError('Unexpected duplicate ZIP member')
    return members


def archive_files(root, *, staging, members, destination, executable, tool_sha256):
    """Run the approved real ZIP utility and read every decompressed member."""
    tool = tool_identity(executable, tool_sha256)
    stage = owned_path(root, staging)
    target = owned_path(root, destination)
    if not stage.is_dir() or target.exists() or not members:
        raise ValueError('Existing staging, absent archive and explicit members required')
    if len(members) != len(set(members)):
        raise ValueError('Archive input roster contains duplicate names')
    wanted = {}
    for member in members:
        if (not isinstance(member, str) or member.startswith(('-', '@'))
                or any(character in member for character in '*?')
                or len(PurePosixPath(member).parts) != 1):
            raise ValueError('Canonical batch archive uses flat members')
        source = owned_path(stage, member)
        if not source.is_file():
            raise ValueError('Required archive member absent: ' + member)
        wanted[member] = (sha256_file(source), source.stat().st_size)
    target.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run([str(tool), 'a', '-tzip', '-y', str(target), *members],
                            cwd=stage, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            check=False, timeout=180)
    if result.returncode != 0:
        raise RuntimeError('7-Zip failed with exit ' + str(result.returncode))
    actual = zip_members(root, destination)
    if {row['name']: (row['sha256'], row['size_bytes']) for row in actual} != wanted:
        raise ValueError('Decompressed archive member roster/content differs')
    return dict(file=inspect_file(root, destination), members=actual,
                tool_sha256=tool_sha256, returncode=result.returncode)


def clear_staging(root, relative, expected_members):
    folder = owned_path(root, relative)
    if not folder.is_dir() or sorted(p.name for p in folder.iterdir()) != sorted(expected_members):
        raise ValueError('Staging cleanup roster differs')
    for name in expected_members:
        remove_file(root, relative + '/' + name)
    folder.rmdir()
