"""Read-only ancestry for the exact reviewed Step Four export, never a new seal.

Inactive on fresh installations. The separately mounted declaration is pinned by
the operator, like the older ancestry declarations. Historical bytes are hashed
and inverse-checked as data; no historical module is imported or executed.
"""
import os
from pathlib import Path

from mta.serialization import digest

PIN_ENV = 'VF_MDM_SEALED_EXPORT_SHA256'
DECLARATION = Path('/proof/s4-20261016/sealed-export-compatibility.json')
SCHEMA = 'vectorflow-reviewed-sealed-export-v1'
REVIEWED_COMMIT = '9e353ff85ce20155ada6316024ce7ce4e52affa2'
LOGISTICS_SHA256 = 'b8b1a68ef5f97065e5d24ea6403932febe488e5664a67a92e03466e2c6601304'
REVIEWED_DIGEST = '40ef6dbc1d5668511b12a8e4bfa05125f96ec1a8cd472b583e0f8dc0bb4c2085'
OMITTED_DIGEST = '2d329aa12169078102ee738cdaa93a2970bbb93cad9cf5f144a40bb713f6fc06'
INSTALLATION_FILES = frozenset(('mta/mdm/application_registration.py', 'mta/mdm/owned_namespace.py'))
VERIFIER = 'mta/mdm/native_report_compatibility.py'
LAYOUT_VERIFIER = 'mta/mdm/owned_namespace.py'
OMITTED_NEW_TEST = 'mta/runtime/test_logistics.py'


def validate(raw, pin, logistics_raw, root, files, identity):
    from mta.mdm.native_report_compatibility import (
        _deny, _sha, _read_json, _files, apply_inverse, VERSION)
    if (not isinstance(pin, str) or len(pin) != 64
            or any(c not in '0123456789abcdef' for c in pin) or _sha(raw) != pin):
        _deny('sealed export declaration is not pinned')
    value = _read_json(raw)
    if (set(value) != {'schema', 'reviewed_commit', 'reviewed_files', 'omitted_files',
                      'installation_inverse', 'descendant_inverse', 'current_files', 'current_identity'}
            or value['schema'] != SCHEMA or value['reviewed_commit'] != REVIEWED_COMMIT
            or _sha(logistics_raw) != LOGISTICS_SHA256):
        _deny('sealed export declaration or original lineage differs')
    original = _read_json(logistics_raw)
    reviewed, omitted = value['reviewed_files'], value['omitted_files']
    if (len(original['current_files']) != 908 or len(reviewed) != 721 or len(omitted) != 187
            or digest(reviewed) != REVIEWED_DIGEST or digest(omitted) != OMITTED_DIGEST
            or set(reviewed) & set(omitted)
            or set(reviewed) | set(omitted) != set(original['current_files'])
            or any(original['current_files'].get(n) != h for n, h in omitted.items())):
        _deny('sealed export fixed omission or reviewed roster differs')
    if (files != value['current_files'] or files != _files(Path(root))
            or set(files) != set(reviewed) or identity != value['current_identity']
            or identity.get('source_manifest_digest') != digest(files)
            or identity.get('closing_projection_version') != VERSION):
        _deny('sealed export actual source or identity differs')
    for name in files:
        path = Path(root) / name
        if path.is_symlink() or any(p.is_symlink() for p in path.parents if p != Path(root).parent):
            _deny('sealed export symbolic source is not admitted')
    descendants = {n for n in files if files[n] != reviewed[n]}
    if (descendants not in ({VERIFIER}, {VERIFIER, LAYOUT_VERIFIER})
            or set(value['descendant_inverse']) != descendants
            or set(value['installation_inverse']) != INSTALLATION_FILES
            or {n for n in reviewed if reviewed[n] != original['current_files'][n]} != INSTALLATION_FILES):
        _deny('sealed export changed production file boundary differs')
    overrides = {}
    for name in INSTALLATION_FILES | descendants:
        current = (Path(root) / name).read_bytes()
        if _sha(current) != files[name]:
            _deny('sealed export current bytes differ')
        reviewed_bytes = (apply_inverse(current, value['descendant_inverse'][name])
                          if name in descendants else current)
        if _sha(reviewed_bytes) != reviewed[name]:
            _deny('sealed export reviewed inverse differs')
        prior = (apply_inverse(reviewed_bytes, value['installation_inverse'][name])
                 if name in INSTALLATION_FILES else reviewed_bytes)
        if _sha(prior) != original['current_files'][name]:
            _deny('sealed export original inverse differs')
        overrides[name] = prior
    # This omitted test was an added file in the PINNED logistics declaration.
    # Authenticate its existing inverse data and prove its predecessor is empty;
    # never restore a test file to the production tree or execute these bytes.
    import base64
    edits = original['inverse'][OMITTED_NEW_TEST]
    if len(edits) != 1 or edits[0]['offset'] != 0 or edits[0]['prior'] != '':
        _deny('sealed export omitted test ancestry differs')
    missing = base64.b64decode(edits[0]['current'], validate=True)
    if (_sha(missing) != omitted[OMITTED_NEW_TEST] or apply_inverse(missing, edits) != b''):
        _deny('sealed export omitted test hash differs')
    overrides[OMITTED_NEW_TEST] = missing
    return original['current_files'], overrides, original['current_identity']


def retained_source(root, files, identity, logistics_raw):
    """The only runtime entry: opt-in, immutable mount and exact pinned proof."""
    pin = os.environ.get(PIN_ENV)
    if not pin:
        return files, None, identity
    from mta.mdm.native_report_compatibility import _readonly
    _readonly(DECLARATION)
    return validate(DECLARATION.read_bytes(), pin, logistics_raw, root, files, identity)
