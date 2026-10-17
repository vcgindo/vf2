"""Exact committed-export identity; no database, historical bytes or Git at runtime.

**DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.**

The deployment authority must supply both pins independently of this directory.
A manifest alongside its files is not, by itself, an authority to admit them.
"""
import ast
import hashlib
import json
import os
import re
from pathlib import Path, PurePosixPath


SCHEMA = 'vectorflow-native-release-source-v1'
MANIFEST = 'release-native-source.json'
AREAS = ('mta', 'vectorflow', 'baseline', 'release')
ROOT_FILES = frozenset(('manage.py', 'requirements.txt'))
# Finite MTA image dependencies. The complete operator/source archive has its
# own independently pinned descriptor; build/inspection tools never enter /app.
MTA_RELEASE_FILES = frozenset('release/' + name for name in (
    '__init__.py', 'configuration.py', 'metadata_access.py', 'mta_settings.py',
    'native_identity.py', 'native_schema.py', 'provision.py', 'register_mta.py',
    'service.py', 'owned-namespace.sql', 'requirements-mta.lock',
    'mta-wheels.lock.json', 'images.lock.json', 'mta.Dockerfile'))
HISTORICAL_SETTINGS = ('VF_MDM_SELECTIVE_COMPATIBILITY_SHA256',
    'VF_MDM_REPORT_COMPATIBILITY_SHA256', 'VF_MDM_READ_COMPATIBILITY_SHA256',
    'VF_MDM_LOGISTICS_COMPATIBILITY_SHA256', 'VF_MDM_SEALED_EXPORT_SHA256',
    'VF_MDM_SEALED_EXPORT_LAYOUTS')


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _pin(value, length):
    return isinstance(value, str) and re.fullmatch('[0-9a-f]{' + str(length) + '}', value) is not None


def _native(name):
    return (name in ROOT_FILES or name in MTA_RELEASE_FILES
        or bool(PurePosixPath(name).parts) and PurePosixPath(name).parts[0] in AREAS[:3])


def _implementation(files, root):
    # Read the committed literal roster without importing Django or any code
    # from an as-yet unauthenticated export.
    raw = (root / 'mta/mdm/initialization.py').read_bytes()
    if _sha(raw) != files.get('mta/mdm/initialization.py'):
        raise ValueError('Native implementation roster bytes differ')
    tree = ast.parse(raw)
    assignments = [node for node in tree.body if isinstance(node, ast.Assign)
                   and any(isinstance(t, ast.Name) and t.id == 'IMPLEMENTATION_FILES' for t in node.targets)]
    if len(assignments) != 1:
        raise ValueError('Native implementation roster is absent or ambiguous')
    names = ast.literal_eval(assignments[0].value)
    if (not isinstance(names, tuple) or not names or len(set(names)) != len(names)
            or any(not isinstance(n, str) or 'mta/' + n not in files for n in names)):
        raise ValueError('Native implementation roster differs')
    from mta.serialization import digest
    return digest({name: files['mta/' + name] for name in names})


def declaration(root, commit, exported_files):
    """Called only by the committed Git exporter, after copying its exact bytes."""
    if not _pin(commit, 40):
        raise ValueError('Full committed native source identity required')
    files = dict(sorted((n, h) for n, h in exported_files.items() if _native(n)))
    if not ROOT_FILES <= files.keys():
        raise ValueError('Native root entry and dependency metadata required')
    migrations = {n: h for n, h in files.items() if n.startswith('mta/runtime/migrations/')}
    if not migrations or not files:
        raise ValueError('Native migration and source rosters required')
    return dict(schema=SCHEMA, source_commit=commit, files=files, migrations=migrations,
                implementation_sha256=_implementation(files, Path(root)))


def _unique(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError('Duplicate native release manifest key')
        value[key] = item
    return value


def verify(root, *, expected_commit, expected_sha256):
    """Authenticate a complete export against separately supplied exact pins.

    Returns only metadata suitable for an immutable capability. Does not connect
    to a database, infer an input hash, accept an arbitrary manifest path, read
    historical proofs, reconstruct bytes, change files or import archived code.
    """
    if not _pin(expected_commit, 40) or not _pin(expected_sha256, 64):
        raise ValueError('Independent native release commit and SHA256 pins required')
    root = Path(root).absolute()
    if root.is_symlink() or any(p.is_symlink() for p in root.parents):
        raise ValueError('Native release symbolic root is forbidden')
    manifest = root / MANIFEST
    if manifest.is_symlink():
        raise ValueError('Native release symbolic manifest is forbidden')
    raw = manifest.read_bytes()
    if _sha(raw) != expected_sha256:
        raise ValueError('Native release manifest SHA256 differs')
    value = json.loads(raw, object_pairs_hook=_unique)
    if (not isinstance(value, dict)
            or set(value) != {'schema', 'source_commit', 'files', 'migrations', 'implementation_sha256'}
            or value['schema'] != SCHEMA or value['source_commit'] != expected_commit
            or not isinstance(value['files'], dict) or not value['files']):
        raise ValueError('Native release declaration differs')
    files = value['files']
    for name, pin in files.items():
        path = PurePosixPath(name)
        if (not name or path.is_absolute() or '..' in path.parts or '\\' in name
                or str(path) != name or not _native(name) or not _pin(pin, 64)):
            raise ValueError('Native release file identity is invalid')
    actual = {}
    for path in sorted(root.iterdir()):
        if path.name in ROOT_FILES or path.suffix in ('.py', '.pyc', '.pyo') or path.name == '__pycache__':
            if path.is_symlink() or path.name not in ROOT_FILES or not path.is_file():
                raise ValueError('Native root entry or undeclared executable differs')
            actual[path.name] = _sha(path.read_bytes())
    for area in AREAS:
        directory = root / area
        if not directory.is_dir() or directory.is_symlink():
            raise ValueError('Native release area is absent or symbolic')
        for path in sorted(directory.rglob('*')):
            if path.is_symlink():
                raise ValueError('Native release symbolic source is forbidden')
            if path.is_file():
                actual[path.relative_to(root).as_posix()] = _sha(path.read_bytes())
    if actual != files:
        raise ValueError('Native release complete file roster or bytes differ')
    expected = declaration(root, expected_commit, actual)
    if value != expected:
        raise ValueError('Native release migration or implementation identity differs')
    from mta.serialization import digest
    return dict(schema=SCHEMA, source_commit=expected_commit, manifest_sha256=expected_sha256,
                source_files_digest=digest(files), migrations_digest=digest(value['migrations']),
                implementation_sha256=value['implementation_sha256'])


def require_current():
    """Deployment pins are mandatory; historical compatibility is never a fallback."""
    if any(os.environ.get(name) for name in HISTORICAL_SETTINGS):
        raise ValueError('Historical compatibility requires the pinned original release')
    return verify(Path(__file__).resolve().parents[1],
        expected_commit=os.environ.get('VF_NATIVE_RELEASE_COMMIT'),
        expected_sha256=os.environ.get('VF_NATIVE_RELEASE_SHA256'))
