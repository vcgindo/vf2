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
# Exact source-only setup descendant of the reviewed export. The original
# 908-file seal, 721-file reviewed projection and 187 omissions stay fixed.
# These hashes are committed Linux export bytes, not operator-selected values.
SETUP_SCHEMA = 'vectorflow-reviewed-sealed-export-setup-v1'
SETUP_ADDED = frozenset(('mta/presentation/application_state.py',))
SETUP_FILES = {
    'mta/mdm/presentation_compatibility.py': '56f0b83c49be4cc79790783c4bce2dc25bc0906b9c4cde819fdfc869cde00cc7',
    'mta/mdm/source.py': 'ad49be81bd9b4d931622ddb12e3cc7becc55abe07e7b961b5547ee4fbadd84c3',
    'mta/presentation/application_state.py': '4c047861aa977b7c791d7b1c5045ddd0ec781def9f6649997292251bdca5b65a',
    'mta/presentation/admission.py': 'ba33a686b185c65fb6347bf5ed602ea2dc0a410fea86bdf0ceb68720cecd668d',
    'mta/presentation/mdm_views.py': '618f771e1284bccf5f131d90ec4475e4bb84a938fcad509a775e6cfd6fe08c35',
    'mta/presentation/views.py': 'c3550dc4d5ebe24d04af8a61c6cd4a08cbf9c5eb32ff897ae2906620c5ff70f6',
    'vectorflow/urls.py': '409b86050d2d8a38ce671db2424be9ba1df9d9f1ac63b5865719fe28be752f61',
}


def validate(raw, pin, logistics_raw, root, files, identity):
    from mta.mdm.native_report_compatibility import (
        _deny, _sha, _read_json, _files, apply_inverse, VERSION)
    if (not isinstance(pin, str) or len(pin) != 64
            or any(c not in '0123456789abcdef' for c in pin) or _sha(raw) != pin):
        _deny('sealed export declaration is not pinned')
    value = _read_json(raw)
    if (set(value) != {'schema', 'reviewed_commit', 'reviewed_files', 'omitted_files',
                      'installation_inverse', 'descendant_inverse', 'current_files', 'current_identity'}
            or value['schema'] not in (SCHEMA, SETUP_SCHEMA) or value['reviewed_commit'] != REVIEWED_COMMIT
            or _sha(logistics_raw) != LOGISTICS_SHA256):
        _deny('sealed export declaration or original lineage differs')
    original = _read_json(logistics_raw)
    setup = value['schema'] == SETUP_SCHEMA
    reviewed, omitted = value['reviewed_files'], value['omitted_files']
    if (len(original['current_files']) != 908 or len(reviewed) != 721 or len(omitted) != 187
            or digest(reviewed) != REVIEWED_DIGEST or digest(omitted) != OMITTED_DIGEST
            or set(reviewed) & set(omitted)
            or set(reviewed) | set(omitted) != set(original['current_files'])
            or any(original['current_files'].get(n) != h for n, h in omitted.items())):
        _deny('sealed export fixed omission or reviewed roster differs')
    if (files != value['current_files'] or files != _files(Path(root))
            or set(files) != set(reviewed) | (SETUP_ADDED if setup else set())
            or identity != value['current_identity']
            or identity.get('source_manifest_digest') != digest(files)
            or identity.get('closing_projection_version') != VERSION):
        _deny('sealed export actual source or identity differs')
    if setup and any(files.get(name) != checksum for name, checksum in SETUP_FILES.items()):
        _deny('sealed export setup descendant bytes differ')
    for name in files:
        path = Path(root) / name
        if path.is_symlink() or any(p.is_symlink() for p in path.parents if p != Path(root).parent):
            _deny('sealed export symbolic source is not admitted')
    descendants = {n for n in files if files[n] != reviewed.get(n)}
    setup_names = set(SETUP_FILES) if setup else set()
    if (descendants not in ({VERIFIER} | setup_names, {VERIFIER, LAYOUT_VERIFIER} | setup_names)
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
        if _sha(reviewed_bytes) != reviewed.get(name, _sha(b'')):
            _deny('sealed export reviewed inverse differs')
        prior = (apply_inverse(reviewed_bytes, value['installation_inverse'][name])
                 if name in INSTALLATION_FILES else reviewed_bytes)
        if _sha(prior) != original['current_files'].get(name, _sha(b'')):
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


def presentation_source_bytes(root, name, expected):
    """Supply authenticated historical bytes to the unchanged old MOQ assertion.

    The old assertion reads mdm_views directly. Only this exact setup descendant
    may project that file back through the already verified source inverse. No
    reconstructed code is executed and no other file/expected hash is accepted.
    """
    from mta.mdm.native_report_compatibility import _files, _sha, _deny, LOGISTICS_DECLARATION
    from mta.mdm.production_families import adapter_digest
    from mta.mdm.location_projection import VERSION
    if name != 'mta/presentation/mdm_views.py' or not os.environ.get(PIN_ENV):
        _deny('setup presentation projection is not authorized')
    files = _files(Path(root))
    identity = dict(adapter_digest=adapter_digest(), closing_projection_version=VERSION,
                    source_manifest_digest=digest(files))
    prior_files, overrides, _ = retained_source(root, files, identity, LOGISTICS_DECLARATION.read_bytes())
    if (overrides is None or prior_files.get(name) != expected or name not in overrides
            or _sha(overrides[name]) != expected):
        _deny('setup presentation projection differs from original source')
    return overrides[name]
