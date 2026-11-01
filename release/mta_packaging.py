"""Finite authenticated MTA build context; external to the production image.

**DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.**
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shutil


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def unique(pairs):
    value = {}
    for name, item in pairs:
        if name in value:
            raise ValueError('Duplicate export descriptor key')
        value[name] = item
    return value


def files(root):
    root = Path(root)
    if root.is_symlink() or any(p.is_symlink() for p in root.parents):
        raise ValueError('Symbolic build source is forbidden')
    result = {}
    for path in sorted(root.rglob('*')):
        if path.is_symlink():
            raise ValueError('Symbolic build source is forbidden')
        if path.is_file():
            result[path.relative_to(root).as_posix()] = sha(path)
    return result


def source(root, *, commit, source_sha256, native_sha256):
    """Complete source archive descriptor plus finite native image declaration."""
    from release.native_identity import declaration, MANIFEST, _pin
    root = Path(root)
    if not _pin(commit, 40) or not _pin(source_sha256, 64) or not _pin(native_sha256, 64):
        raise ValueError('Independent full source/native/commit pins required')
    descriptor = root / 'release-source.json'
    if sha(descriptor) != source_sha256 or sha(root / MANIFEST) != native_sha256:
        raise ValueError('Independent exported descriptor pin differs')
    value = json.loads(descriptor.read_bytes(), object_pairs_hook=unique)
    if (value.get('schema') != 'vectorflow-release-source-v1' or value.get('source_commit') != commit
            or value.get('default_data_import') is not False or not isinstance(value.get('files'), dict)):
        raise ValueError('Committed export descriptor differs')
    expected = dict(value['files'])
    for name, pin in expected.items():
        path = PurePosixPath(name)
        if (path.is_absolute() or '..' in path.parts or '\\' in name or str(path) != name
                or not _pin(pin, 64)):
            raise ValueError('Invalid committed export file identity')
    expected.update({'release-source.json':source_sha256, MANIFEST:native_sha256})
    if files(root) != expected:
        raise ValueError('Committed export complete roster or bytes differ')
    native = json.loads((root / MANIFEST).read_bytes(), object_pairs_hook=unique)
    if native != declaration(root, commit, value['files']):
        raise ValueError('Native source declaration differs from committed export')
    return value, native


def verify_wheels(root, wheelhouse):
    root, wheelhouse = Path(root), Path(wheelhouse)
    value = json.loads((root/'release/mta-wheels.lock.json').read_bytes(), object_pairs_hook=unique)
    if (value.get('schema') != 'vectorflow-mta-wheel-pins-v1' or value.get('platform') != 'linux/amd64'
            or value.get('python') != '3.11' or not isinstance(value.get('files'), list)):
        raise ValueError('Pinned Linux wheel descriptor differs')
    records = value['files']
    if len(records) != 8 or len({r['filename'] for r in records}) != 8:
        raise ValueError('Finite eight-wheel roster required')
    if files(wheelhouse) != {r['filename']:r['sha256'] for r in records}:
        raise ValueError('Wheel bytes or complete roster differ')
    normalize = lambda s: re.sub('[-_.]+', '-', s).lower()
    pins = {normalize(r['name']):r['version'] for r in records}
    required = dict(line.strip().split('==') for line in
        (root/'release/requirements-mta.lock').read_text().splitlines() if line.strip())
    if pins != {normalize(n):v for n,v in required.items()}:
        raise ValueError('Wheel dependencies differ from supported version pins')
    return records


def prepare(root, destination, wheelhouse, *, commit, source_sha256, native_sha256):
    """No Docker call until every source and dependency byte has been admitted."""
    from release.native_identity import MANIFEST, MTA_RELEASE_FILES, verify
    root, destination = Path(root).absolute(), Path(destination).resolve()
    if destination.exists() or root == destination or root in destination.parents:
        raise ValueError('Choose a new external build context; never overwrite')
    full, native = source(root, commit=commit, source_sha256=source_sha256, native_sha256=native_sha256)
    if 'release/image_entrypoint.py' not in full['files']:
        raise ValueError('Authenticated image entrypoint is absent from committed export')
    if not MTA_RELEASE_FILES <= native['files'].keys():
        raise ValueError('Required finite native release dependency is absent')
    wheels = verify_wheels(root, wheelhouse)
    application = destination/'application'
    for name in (*native['files'], MANIFEST):
        target=application/name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root/name, target)
    identity = verify(application, expected_commit=commit, expected_sha256=native_sha256)
    (destination/'tools').mkdir()
    shutil.copyfile(root/'release/mta_packaging.py', destination/'tools/mta_packaging.py')
    shutil.copyfile(root/'release/image_entrypoint.py', destination/'tools/image_entrypoint.py')
    image_identity = dict(source_commit=commit, source_sha256=source_sha256, native_sha256=native_sha256,
        packaging_tool_sha256=full['files']['release/mta_packaging.py'])
    identity_bytes = (json.dumps(image_identity, sort_keys=True, indent=2)+'\n').encode('utf-8')
    (destination/'identity.json').write_bytes(identity_bytes)
    shutil.copyfile(root/'release/mta.Dockerfile', destination/'Dockerfile')
    (destination/'wheels').mkdir()
    for row in wheels:
        shutil.copyfile(Path(wheelhouse)/row['filename'], destination/'wheels'/row['filename'])
    expected = {'application/'+n:h for n,h in native['files'].items()}
    expected.update({'application/'+MANIFEST:native_sha256,
        'Dockerfile':full['files']['release/mta.Dockerfile'],
        'tools/mta_packaging.py':full['files']['release/mta_packaging.py'],
        'tools/image_entrypoint.py':full['files']['release/image_entrypoint.py'],
        'identity.json':hashlib.sha256(identity_bytes).hexdigest()})
    expected.update({'wheels/'+r['filename']:r['sha256'] for r in wheels})
    if files(destination) != expected:
        raise ValueError('Complete MTA build context differs')
    return dict(native_identity=identity, files=expected,
        packaging_tool_sha256=expected['tools/mta_packaging.py'], wheels=wheels)


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--application',type=Path,required=True)
    parser.add_argument('--commit',required=True)
    parser.add_argument('--native-sha256',required=True)
    parser.add_argument('--wheelhouse',type=Path)
    args=parser.parse_args()
    import sys
    sys.path.insert(0,str(args.application))
    from release.native_identity import verify
    verify(args.application, expected_commit=args.commit, expected_sha256=args.native_sha256)
    if args.wheelhouse:
        verify_wheels(args.application,args.wheelhouse)
    print('Exact committed native build admission PASS')
