"""Portable lossless validation files, read one checkpoint row at a time."""
import gzip
import hashlib
import io
import json
from pathlib import Path

from mta.serialization import canonical_parts


def file_sha(path):
    checksum = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            checksum.update(block)
    return checksum.hexdigest()


def write_rows(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    checksum = hashlib.sha256(b'[')
    count = 0
    with path.open('xb') as target:
        with gzip.GzipFile(fileobj=target, mode='wb', compresslevel=1, mtime=0) as compressed:
            with io.BufferedWriter(compressed, buffer_size=65536) as stream:
                for row in rows:
                    if count:
                        checksum.update(b',')
                    for part in canonical_parts(row):
                        checksum.update(part)
                        stream.write(part)
                    stream.write(b'\n')
                    count += 1
    checksum.update(b']')
    return dict(row_count=count, digest=checksum.hexdigest(), sha256=file_sha(path))


def iter_rows(path, metadata):
    if file_sha(path) != metadata['sha256']:
        raise ValueError('Validation evidence file drift')
    checksum = hashlib.sha256(b'[')
    count = 0
    with gzip.open(path, 'rb') as stream:
        for line in stream:
            row = json.loads(line)
            if count:
                checksum.update(b',')
            for part in canonical_parts(row):
                checksum.update(part)
            count += 1
            yield row
    checksum.update(b']')
    if count != metadata['row_count'] or checksum.hexdigest() != metadata['digest']:
        raise ValueError('Validation evidence logical rows/checksum drift')


def update_array(checksum, rows):
    checksum.update(b'[')
    for index, row in enumerate(rows):
        if index:
            checksum.update(b',')
        for part in canonical_parts(row):
            checksum.update(part)
    checksum.update(b']')


class OutputArchive:
    def __init__(self, manifest_path):
        self.path = Path(manifest_path)
        self.manifest = json.loads(self.path.read_text())
        if self.manifest['schema'] not in ('fresh-output-archive-v1','fresh-output-archive-v2'):
            raise ValueError('Unknown output archive')
        names = [item['name'] for item in self.manifest['checkpoints']]
        if names != sorted(set(names)):
            raise ValueError('Archive checkpoint roster/multiplicity differs')
        self.items = {item['name']: item for item in self.manifest['checkpoints']}

    def iter_rows(self, name):
        item = self.items[name]
        yield from iter_rows(self.path.parent / item['path'], item)

    def __getitem__(self, name):
        return list(self.iter_rows(name))

    def verify(self, expected_digest, expected_validation_digest=None):
        modern=self.manifest['schema']=='fresh-output-archive-v2'
        if modern and (not expected_validation_digest or
                       self.manifest.get('validation_digest')!=expected_validation_digest):
            raise ValueError('Explicit validation evidence identity required')
        checksum = hashlib.sha256(b'{')
        for index, name in enumerate(self.items):
            if index:
                checksum.update(b',')
            for part in canonical_parts(name):
                checksum.update(part)
            checksum.update(b':')
            update_array(checksum, self.iter_rows(name))
        checksum.update(b'}')
        if (checksum.hexdigest() != (expected_validation_digest if modern else expected_digest)
                or self.manifest['output_digest'] != expected_digest):
            raise ValueError('Complete output archive checksum differs')
