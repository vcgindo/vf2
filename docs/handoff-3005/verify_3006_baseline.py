"""Verify pinned baseline source Git blobs without changing the worktree."""
import hashlib
import json
import subprocess
import sys


def git(*args):
    return subprocess.check_output(['git', *args])


revision = sys.argv[1] if len(sys.argv) > 1 else 'HEAD'
manifest_path = 'docs/handoff-3005/BASELINE_SOURCE_MANIFEST_3006.json'
manifest = json.loads(git('show', f'{revision}:{manifest_path}'))
entries = git('ls-tree', '-r', '-z', revision).split(b'\0')
objects = {}
for entry in entries:
    if entry:
        meta, name = entry.split(b'\t', 1)
        objects[name.decode('utf-8')] = meta.decode().split()[2]
expected = manifest['source_hashes']
missing = sorted(set(expected) - set(objects))
if missing:
    raise SystemExit(f'Missing pinned files: {missing}')
process = subprocess.Popen(['git', 'cat-file', '--batch'], stdin=subprocess.PIPE,
                           stdout=subprocess.PIPE)
failures = []
for name, checksum in expected.items():
    process.stdin.write((objects[name] + '\n').encode('ascii'))
    process.stdin.flush()
    header = process.stdout.readline().decode('ascii').strip().split()
    size = int(header[2])
    data = process.stdout.read(size)
    assert process.stdout.read(1) == b'\n'
    if hashlib.sha256(data).hexdigest() != checksum:
        failures.append(name)
process.stdin.close()
assert process.wait() == 0
if failures:
    raise SystemExit(f'Hash mismatches: {failures}')
print(json.dumps({'status': 'PASS', 'revision': revision,
                  'source_files': len(expected),
                  'backend_files': manifest['backend_source_files'],
                  'frontend_source_files': manifest['frontend_source_files']}))
