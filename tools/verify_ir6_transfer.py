"""Verify the pinned, private IR6 Apr 10 transfer bundle without using Docker."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat


MANIFEST_SHA256 = 'f917f19ca88e1df870f56cb6415c4fa5da59b62d84b590fdd31a5583286f86b4'


def sha256(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def verify(directory):
    root = directory.resolve(strict=True)
    if os.name == 'nt' and root.drive.endswith(':'):
        root = Path('\\\\?\\' + str(root))
    manifest = root / 'manifest.json'
    if sha256(manifest) != MANIFEST_SHA256:
        raise ValueError('IR6 transfer manifest checksum differs')
    value = json.loads(manifest.read_bytes())
    files = value['files']
    actual = {}
    for path in root.rglob('*'):
        entry = path.lstat()
        if (stat.S_ISLNK(entry.st_mode) or os.name == 'nt'
                and entry.st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT):
            raise ValueError(f'Unexpected link in transfer bundle: {path.name}')
        if path.is_file() and path != manifest:
            actual[path.relative_to(root).as_posix()] = path
    if actual.keys() != files.keys():
        raise ValueError('IR6 transfer file roster differs')
    for name, pin in files.items():
        path = actual[name]
        if path.stat().st_size != pin['bytes'] or sha256(path) != pin['sha256']:
            raise ValueError(f'IR6 transfer file differs: {name}')
    return {'status': 'VERIFIED', 'files': len(files), 'manifest_sha256': MANIFEST_SHA256,
            'images': value['images'], 'starting_selection': value['starting_selection']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('bundle', type=Path)
    print(json.dumps(verify(parser.parse_args().bundle), indent=2))
