"""Safe immutable CSV snapshots and explicit onboarding references; no database writes."""
from copy import deepcopy
from hashlib import sha256
import json
import os
from pathlib import Path
import stat

from mta.serialization import digest
from mta.application.production_csv_contract import SCHEMA_VERSION


def decode_json(raw):
    def unique(pairs):
        result = {}
        for name, value in pairs:
            if name in result:
                raise ValueError('Duplicate JSON field: ' + name)
            result[name] = value
        return result
    return json.loads(raw, object_pairs_hook=unique)


def contained(path, root):
    path, root = Path(path).absolute(), Path(root).absolute()
    # Check raw ancestors before normalizing '..': never hide a symlink hop.
    if any(p.is_symlink() for p in (path, *path.parents, root, *root.parents)):
        raise ValueError('Symlink inputs are forbidden')
    path, root = Path(os.path.abspath(path)), Path(os.path.abspath(root))
    if not path.is_relative_to(root):
        raise ValueError('Input path is outside its configured root')
    return path


def regular(path, root):
    path = contained(path, root)
    if not stat.S_ISREG(path.stat().st_mode):
        raise ValueError('A regular input file is required: ' + path.name)
    return path


def load_binding(path):
    path = Path(path).absolute()
    raw = regular(path, path.parent).read_bytes()
    value = decode_json(raw)
    required = {'schema', 'initialization_id', 'source_digest', 'configuration_digest',
        'opening_file', 'opening_sha256', 'intake_schema', 'producer_source_schema',
        'report_policy', 'report_opening', 'consumer_opening_file', 'consumer_opening_sha256', 'validation'}
    if not isinstance(value, dict) or set(value) != required or value['schema'] != 'vectorflow-daily-binding-v1':
        raise ValueError('Complete versioned daily onboarding binding required')
    result = deepcopy(value)
    for prefix in ('opening', 'consumer_opening'):
        filename = Path(value[prefix + '_file'])
        if filename.is_absolute():
            raise ValueError('Onboarding files must be relative to the binding directory')
        source = regular(path.parent / filename, path.parent)
        checksum=sha256()
        with source.open('rb') as stream:
            for block in iter(lambda:stream.read(1024*1024),b''):checksum.update(block)
        if checksum.hexdigest() != value[prefix + '_sha256']:
            raise ValueError('Onboarding original checksum differs: ' + prefix)
        result['_' + prefix + '_path'] = str(source)
        if prefix == 'consumer_opening':
            result['consumer_opening'] = decode_json(source.read_bytes())
    result['_binding_digest'] = digest(value)
    return result


def snapshot(source, destination, root):
    source, destination = contained(source, root), Path(destination)
    marker = regular(source / 'READY', root)
    control = regular(source / 'batch.json', root)
    manifest_bytes = control.read_bytes()
    batch = decode_json(manifest_bytes)
    if not isinstance(batch, dict) or batch.get('schema') != SCHEMA_VERSION or not isinstance(batch.get('feeds'), dict):
        raise ValueError('A versioned batch manifest is required')
    expected = {'READY', 'batch.json'} | {name for name, state in batch['feeds'].items() if state == 'PRESENT'}
    if any('/' in name or '\\' in name or name in ('.', '..') for name in expected):
        raise ValueError('Batch files must have simple names')
    if {p.name for p in source.iterdir()} != expected:
        raise ValueError('Completed directory file roster differs from manifest')
    destination.mkdir(parents=True, exist_ok=False)
    receipts = {}
    for name in sorted(expected):
        original = regular(source / name, root)
        before = original.stat()
        checksum = sha256()
        with original.open('rb') as incoming, (destination / name).open('xb') as out:
            while block := incoming.read(1024 * 1024):
                checksum.update(block)
                out.write(block)
        after = original.stat()
        if (before.st_size, before.st_mtime_ns, before.st_ino) != (after.st_size, after.st_mtime_ns, after.st_ino):
            raise ValueError('Batch file changed during capture: ' + name)
        receipts[name] = dict(sha256=checksum.hexdigest(), bytes=before.st_size)
    if control.read_bytes() != manifest_bytes or not marker.exists():
        raise ValueError('Batch completion declaration changed during capture')
    manifest = dict(schema='vectorflow-csv-snapshot-v1', files=receipts)
    manifest['digest'] = digest(manifest)
    (destination / 'snapshot.json').write_text(json.dumps(manifest, sort_keys=True) + '\n', encoding='utf-8')
    return batch, manifest
