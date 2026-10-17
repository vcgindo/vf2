"""Exact pinned source ancestry for the two approved report dispositions."""
import base64
import difflib
import hashlib
import json
import os
from pathlib import Path

from django.db import connection

from mta.serialization import digest

SCHEMA = 'fresh-native-report-source-compatibility-v6'
CASE = 'handoff3005-day05-report-disposition-source-v1'
DECLARATION = Path('/proof/s3-20261015-001/mdm-finite-continuation-20261016-v1/'
                   'day05-report-disposition-v1/source-seal-compatibility-v6.json')
SOURCE_BEFORE = DECLARATION.with_name('source-before.json')
V6_DECLARATION = DECLARATION
V6_SHA256 = 'e6b377b330868b661c129fe3df88fe9f72856bea768f90a9208a81ad32c0f06e'
DECLARATION = Path('/proof/s3-20261015-001/mdm-finite-continuation-20261016-v1/'
                   'day06-report-disposition-v1/source-seal-compatibility-v7.json')
DAY6_FILES = {'mta/application/native_report_disposition.py',
              'mta/runtime/temporal.py', 'mta/runtime/production_daily.py',
              'mta/mdm/native_report_compatibility.py'}
DAY6_SCHEMA = 'fresh-native-report-source-compatibility-v7'
DAY6_CASE = 'handoff3005-day06-report-disposition-source-v1'
READ_DECLARATION = Path('/proof/s3-20261015-001/g3-three-gap-closure-20261016-v1/'
                        'source-seal-compatibility-v8.json')
READ_PIN_ENV = 'VF_MDM_READ_COMPATIBILITY_SHA256'
READ_SCHEMA = 'fresh-native-read-source-compatibility-v8'
READ_CASE = 'handoff3005-getstate-request-scope-v1'
READ_FILES = {'mta/presentation/request_scope.py', 'mta/mdm/native_report_compatibility.py'}

LOGISTICS_PIN_ENV = 'VF_MDM_LOGISTICS_COMPATIBILITY_SHA256'
LOGISTICS_DECLARATION = Path('/proof/s3-20261015-001/logistics-reintegration-20261016/source-ancestry.json')
LOGISTICS_V8_SHA256 = '6967d5b762f1062cfc47f91403a0eddf9f569af3731ba091bb0e7b8e06d42841'
LOGISTICS_SCHEMA = 'fresh-native-logistics-read-source-v1'
LOGISTICS_FILES = {
    'mta/mdm/owned_namespace.py',
    'mta/mdm/native_report_compatibility.py',
    'mta/presentation/views.py', 'mta/presentation/urls.py',
    'mta/presentation/daily_publication.py',
    'mta/presentation/bpr_read.py', 'mta/presentation/bpr_prepared.py',
    'mta/presentation/planning_git_sql.py', 'mta/presentation/planning_expedite_sql.py',
    'mta/presentation/expedite_read.py',
    'mta/presentation/logistics_live.py', 'mta/presentation/logistics_read.py',
    'mta/presentation/logistics_commands.py', 'mta/presentation/logistics_views.py',
    'mta/runtime/models.py', 'mta/runtime/logistics_models.py',
    'mta/runtime/migrations/0140_logistics_live.py',
    'mta/runtime/migrations/0141_logistics_guards.py', 'mta/runtime/test_logistics.py',
    'mta/config/logistics/ui_columns_v1.json', 'vectorflow/settings.py',
}


def validate_logistics_ancestry(raw, pin, v8_raw, root, files, identity, *, byte_overrides=None):
    """Exact native source extension, preserving the original DB and seal checks."""
    if not isinstance(pin, str) or _sha(raw) != pin:
        _deny('logistics deployment source is not pinned')
    value = _read_json(raw)
    if (set(value) != {'schema', 'v8_sha256', 'current_files', 'current_identity', 'inverse'}
            or value['schema'] != LOGISTICS_SCHEMA
            or value['v8_sha256'] != LOGISTICS_V8_SHA256 or _sha(v8_raw) != LOGISTICS_V8_SHA256):
        _deny('logistics source declaration or retained v8 differs')
    previous = _read_json(v8_raw)
    if files != value['current_files'] or identity != value['current_identity']:
        _deny('logistics running source identity differs')
    if identity.get('closing_projection_version') != previous['current_identity']['closing_projection_version']:
        _deny('logistics closing projection version differs')
    changed = {name for name in set(files) | set(previous['current_files'])
               if files.get(name) != previous['current_files'].get(name)}
    if changed != LOGISTICS_FILES or set(value['inverse']) != LOGISTICS_FILES:
        _deny('logistics changed file boundary differs')
    reconstructed, overrides = dict(files), {}
    for name in sorted(LOGISTICS_FILES):
        after = _source_bytes(root, name, byte_overrides)
        if _sha(after) != files.get(name):
            _deny('logistics current bytes differ')
        before = apply_inverse(after, value['inverse'][name])
        if name in previous['current_files']:
            reconstructed[name] = _sha(before)
            overrides[name] = before
        else:
            if before != b'':
                _deny('logistics added file inverse differs')
            reconstructed.pop(name)
    if reconstructed != previous['current_files']:
        _deny('logistics exact inverse source differs')
    return reconstructed, overrides, previous['current_identity']


def logistics_producer_sources():
    """Prior producer module text only after complete pinned source validation."""
    pin = os.environ.get(LOGISTICS_PIN_ENV)
    if not pin:
        return None
    from mta.mdm.location_transition import ROOT, source_files
    from mta.mdm.production_families import adapter_digest
    _readonly(LOGISTICS_DECLARATION)
    _readonly(READ_DECLARATION)
    files = source_files()
    identity = dict(adapter_digest=adapter_digest(), closing_projection_version=VERSION,
                    source_manifest_digest=digest(files))
    from release.sealed_export import retained_source
    files, export_overrides, identity = retained_source(
        ROOT, files, identity, LOGISTICS_DECLARATION.read_bytes())
    _, overrides, _ = validate_logistics_ancestry(LOGISTICS_DECLARATION.read_bytes(),
        pin, READ_DECLARATION.read_bytes(), ROOT, files, identity, byte_overrides=export_overrides)
    return {name: raw.decode('utf-8') for name, raw in overrides.items()}

V7_SHA256 = 'f3fc560e33c4e48761d494814e07404e90f2885d94a5da3a9941b85e1009922d'
PRIOR_DECLARATION = Path('/proof/s3-20261015-001/g3-hierarchy-execution/'
                         'source-seal-compatibility-v5.json')
PIN_ENV = 'VF_MDM_REPORT_COMPATIBILITY_SHA256'
PRIOR_DECLARATION_SHA256 = '2f1d0defde259f607835294f6177a03a865c4af031ff87173955dfa2de3add70'
PRIOR_FILES_SHA256 = 'd14c1f4ee136cd521843537a3effc28116a4ad6abb340ccd58a6f1a5177368a8'
PRIOR_FILES_DIGEST = '1a91a832e127dc35d3d7be4188f85125f2e680fe287a4a4057ebe5ec4b696e1a'
PRIOR_FILE_COUNT = 897
SOURCE = '2e22cdb6866c3e43587aa26612abd8201865e903243919add92fffc2c454fa5f'
INITIALIZATION = '25cceb52-e68f-446b-b2d2-5e212ceec173'
IMPLEMENTATION = '372c8ead5e10c72796b6318ce9eae531fb068182d9445ff727ab531e280d7ee5'
INITIALIZATION_RECEIPT = '05b91fed615aeaa5e54616ea17c4df49d5ae62235375c61e5949038cc0034263'
SEAL = 'a5e269cbaa8b59994c0eeeb882d5d18d0b853c9457ace9232360e08f88053255'
SEALED_ADAPTER = 'f31be0e859c6c0b8a7d8cc6eebc9bff70a9823534f1c6b7c4c0ca021962f4409'
SEALED_MANIFEST = '8f80ec0e250df83240aa459365319d22d1a5b53684284659d9579db6011fac37'
DATABASE = ('handoff3005_g3_workflow_20261015_003', 296160)
VERSION = 'native-closing-locations-v2'
NEW_FILES = {'mta/application/native_report_disposition.py',
             'mta/mdm/native_report_compatibility.py'}
CHANGED_FILES = NEW_FILES | {
    'mta/mdm/presentation_compatibility.py', 'mta/mdm/initialization.py',
    'mta/runtime/temporal.py', 'mta/runtime/production_daily.py',
    'mta/runtime/services.py', 'mta/domain/dbm_selected_chain.py',
    'mta/application/norm0_reports.py', 'mta/runtime/norm0_reports.py',
    'mta/runtime/management/commands/run_production_day.py'}


def _deny(reason):
    raise ValueError('Exact native report source compatibility ' + reason)


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            _deny('declaration contains duplicate keys')
        result[key] = value
    return result


def inverse_delta(before, after):
    """Return byte-exact edits which reconstruct *before* from *after*."""
    before_lines, after_lines = before.splitlines(keepends=True), after.splitlines(keepends=True)
    before_offsets, after_offsets = [0], [0]
    for line in before_lines:
        before_offsets.append(before_offsets[-1] + len(line))
    for line in after_lines:
        after_offsets.append(after_offsets[-1] + len(line))
    result = []
    for tag, a0, a1, b0, b1 in difflib.SequenceMatcher(
            None, before_lines, after_lines, autojunk=False).get_opcodes():
        if tag != 'equal':
            start, end = after_offsets[b0], after_offsets[b1]
            prior_start, prior_end = before_offsets[a0], before_offsets[a1]
            result.append(dict(offset=start,
                current=base64.b64encode(after[start:end]).decode('ascii'),
                prior=base64.b64encode(before[prior_start:prior_end]).decode('ascii')))
    return result


def apply_inverse(raw, edits):
    value = raw
    previous = len(raw) + 1
    for edit in reversed(edits):
        if set(edit) != {'offset', 'current', 'prior'} or type(edit['offset']) is not int:
            _deny('inverse delta shape differs')
        offset = edit['offset']
        try:
            current = base64.b64decode(edit['current'], validate=True)
            prior = base64.b64decode(edit['prior'], validate=True)
        except (TypeError, ValueError) as exc:
            raise ValueError('Exact native report source compatibility inverse delta differs') from exc
        if offset < 0 or offset + len(current) > len(value) or offset >= previous:
            _deny('inverse delta offsets differ')
        if value[offset:offset + len(current)] != current:
            _deny('inverse delta current bytes differ')
        value = value[:offset] + prior + value[offset + len(current):]
        previous = offset
    return value


def _files(root):
    return {path.relative_to(root).as_posix(): _sha(path.read_bytes())
            for parent in ('mta', 'vectorflow') for path in (root / parent).rglob('*')
            if path.is_file() and path.suffix in ('.py', '.json')
            and '__pycache__' not in path.parts}


def _read_json(raw):
    value = json.loads(raw, object_pairs_hook=_unique)
    if not isinstance(value, dict):
        _deny('declaration is not an object')
    return value


def _source_bytes(root, name, overrides=None):
    return overrides[name] if overrides and name in overrides else (Path(root) / name).read_bytes()


def build_declaration(*, root, before_root, prior_raw, implementation_paths,
                      current_adapter_digest):
    """Build the sole v6 declaration; callers serialize it with sorted keys."""
    root, before_root = Path(root), Path(before_root)
    prior_files = _read_json(prior_raw)
    if (_sha(prior_raw) != PRIOR_FILES_SHA256 or digest(prior_files) != PRIOR_FILES_DIGEST
            or len(prior_files) != PRIOR_FILE_COUNT):
        _deny('source-before identity differs')
    current = _files(root)
    changed = {name for name in set(current) | set(prior_files)
               if current.get(name) != prior_files.get(name)}
    if changed != CHANGED_FILES or NEW_FILES & set(prior_files):
        _deny('changed file boundary differs')
    patches = {}
    for name in sorted(CHANGED_FILES):
        after = (root / name).read_bytes()
        if name in NEW_FILES:
            patches[name] = dict(kind='new', before_sha256=None,
                                 after_sha256=_sha(after), inverse=[])
        else:
            before = (before_root / name).read_bytes()
            if _sha(before) != prior_files[name]:
                _deny('before artifact differs for ' + name)
            patches[name] = dict(kind='modified', before_sha256=_sha(before),
                                 after_sha256=_sha(after), inverse=inverse_delta(before, after))
    names = ['mta/' + name for name in implementation_paths]
    current_implementation = digest({name[4:]: current[name] for name in names})
    prior_implementation = digest({name[4:]: prior_files[name] for name in names})
    if prior_implementation != IMPLEMENTATION:
        _deny('prior implementation identity differs')
    return dict(schema=SCHEMA, case=CASE,
        binding=dict(database_name=DATABASE[0], database_oid=DATABASE[1], source_id=1,
            source_digest=SOURCE, initialization_id=INITIALIZATION,
            initialization_receipt_digest=INITIALIZATION_RECEIPT, seal_digest=SEAL,
            retained_implementation_digest=IMPLEMENTATION),
        prior=dict(declaration_sha256=PRIOR_DECLARATION_SHA256,
            files_sha256=PRIOR_FILES_SHA256, files_digest=PRIOR_FILES_DIGEST,
            file_count=PRIOR_FILE_COUNT), current_files=current, patches=patches,
        current_identity=dict(adapter_digest=current_adapter_digest,
            closing_projection_version=VERSION, source_manifest_digest=digest(current)),
        implementation=dict(paths=names, current_digest=current_implementation,
                            retained_digest=IMPLEMENTATION))


def _validate(source, initialization, seal, identity, database, raw, pin, root,
              files, prior_raw, prior_declaration_raw, current_implementation,
              implementation_paths, *, byte_overrides=None):
    if (not isinstance(pin, str) or len(pin) != 64
            or any(c not in '0123456789abcdef' for c in pin) or _sha(raw) != pin):
        _deny('deployment declaration is not pinned')
    declaration = _read_json(raw)
    if set(declaration) != {'schema', 'case', 'binding', 'prior', 'current_files',
                            'patches', 'current_identity', 'implementation'}:
        _deny('declaration shape differs')
    if declaration['schema'] != SCHEMA or declaration['case'] != CASE:
        _deny('declaration schema or case differs')
    prior_files = _read_json(prior_raw)
    prior_declaration = _read_json(prior_declaration_raw)
    expected_binding = dict(database_name=DATABASE[0], database_oid=DATABASE[1], source_id=1,
        source_digest=SOURCE, initialization_id=INITIALIZATION,
        initialization_receipt_digest=INITIALIZATION_RECEIPT, seal_digest=SEAL,
        retained_implementation_digest=IMPLEMENTATION)
    expected_prior = dict(declaration_sha256=PRIOR_DECLARATION_SHA256,
        files_sha256=PRIOR_FILES_SHA256, files_digest=PRIOR_FILES_DIGEST,
        file_count=PRIOR_FILE_COUNT)
    if declaration['binding'] != expected_binding or declaration['prior'] != expected_prior:
        _deny('frozen binding differs')
    if (_sha(prior_raw) != PRIOR_FILES_SHA256 or digest(prior_files) != PRIOR_FILES_DIGEST
            or len(prior_files) != PRIOR_FILE_COUNT
            or _sha(prior_declaration_raw) != PRIOR_DECLARATION_SHA256
            or prior_declaration.get('current_files') != prior_files):
        _deny('prior v5 identity differs')
    if (database != DATABASE or source.pk != 1 or source.digest != SOURCE
            or source.implementation_digest != IMPLEMENTATION
            or str(initialization.pk) != INITIALIZATION or initialization.source_id != source.pk
            or initialization.implementation_digest != IMPLEMENTATION
            or initialization.receipt_digest != INITIALIZATION_RECEIPT
            or seal.source_id != source.pk or seal.digest != SEAL or digest(seal.receipt) != SEAL
            or seal.receipt.get('source_digest') != SOURCE
            or seal.receipt.get('initialization_id') != INITIALIZATION
            or seal.receipt.get('adapter_digest') != SEALED_ADAPTER
            or seal.receipt.get('source_manifest_digest') != SEALED_MANIFEST
            or seal.receipt.get('closing_projection_version') != VERSION):
        _deny('database/source/initialization/seal differs')
    current = declaration['current_files']
    if files != current or identity != declaration['current_identity']:
        _deny('running source identity differs')
    patches = declaration['patches']
    changed = {name for name in set(current) | set(prior_files)
               if current.get(name) != prior_files.get(name)}
    if changed != CHANGED_FILES or set(patches) != CHANGED_FILES:
        _deny('changed file boundary differs')
    reconstructed = dict(current)
    for name in sorted(CHANGED_FILES):
        patch = patches[name]
        after = _source_bytes(root, name, byte_overrides)
        if _sha(after) != current.get(name) or patch.get('after_sha256') != current.get(name):
            _deny('current bytes differ for ' + name)
        if name in NEW_FILES:
            if patch != dict(kind='new', before_sha256=None,
                             after_sha256=current[name], inverse=[]):
                _deny('new-file declaration differs')
            reconstructed.pop(name)
        else:
            if (set(patch) != {'kind', 'before_sha256', 'after_sha256', 'inverse'}
                    or patch['kind'] != 'modified'
                    or patch['before_sha256'] != prior_files[name]
                    or _sha(apply_inverse(after, patch['inverse'])) != prior_files[name]):
                _deny('inverse proof differs for ' + name)
            reconstructed[name] = prior_files[name]
    if reconstructed != prior_files:
        _deny('reconstructed v5 roster differs')
    implementation = declaration['implementation']
    expected_paths = ['mta/' + name for name in implementation_paths]
    expected_current = digest({name[4:]: current[name] for name in expected_paths})
    expected_prior_implementation = digest(
        {name[4:]: prior_files[name] for name in expected_paths})
    if (set(implementation) != {'paths', 'current_digest', 'retained_digest'}
            or implementation['paths'] != expected_paths
            or implementation['current_digest'] != expected_current
            or implementation['retained_digest'] != IMPLEMENTATION
            or expected_prior_implementation != IMPLEMENTATION
            or current_implementation != implementation['current_digest']):
        _deny('implementation identity differs')
    return dict(prior_files=prior_files,
        prior_identity=dict(adapter_digest=prior_declaration['current_adapter_digest'],
            closing_projection_version=VERSION, source_manifest_digest=PRIOR_FILES_DIGEST),
        prior_declaration_raw=prior_declaration_raw,
        retained_implementation_digest=IMPLEMENTATION)


def _readonly(path):
    if not os.statvfs(path).f_flag & os.ST_RDONLY:
        _deny('evidence mount is writable')


def build_day6_declaration(*, root, before_v6, v6_raw, source):
    """Add the exact four-file v6 ancestry, including this verifier's bytes."""
    if _sha(v6_raw) != V6_SHA256:
        _deny('retained v6 declaration differs')
    previous = _read_json(v6_raw)['current_files']
    current = _files(Path(root))
    if current != source['current_files'] or {
            name for name in set(previous) | set(current)
            if previous.get(name) != current.get(name)} != DAY6_FILES:
        _deny('day6 changed file boundary differs')
    patches = {}
    for name in sorted(DAY6_FILES):
        before, after = (Path(before_v6) / name).read_bytes(), (Path(root) / name).read_bytes()
        if _sha(before) != previous[name]:
            _deny('day6 prior bytes differ')
        patches[name] = inverse_delta(before, after)
    return dict(schema=DAY6_SCHEMA, case=DAY6_CASE, v6_sha256=V6_SHA256,
                v6_inverse=patches, source=source)


def validate_day6_ancestry(raw, pin, v6_raw, root, files, *, byte_overrides=None):
    if not isinstance(pin, str) or _sha(raw) != pin:
        _deny('day6 deployment declaration is not pinned')
    value = _read_json(raw)
    if (set(value) != {'schema','case','v6_sha256','v6_inverse','source'}
            or value['schema'] != DAY6_SCHEMA or value['case'] != DAY6_CASE
            or value['v6_sha256'] != V6_SHA256 or _sha(v6_raw) != V6_SHA256):
        _deny('day6 declaration or retained v6 differs')
    source = value['source']
    previous = _read_json(v6_raw)['current_files']
    if files != source['current_files']:
        _deny('day6 running source identity differs')
    changed = {name for name in set(previous) | set(files) if previous.get(name) != files.get(name)}
    if changed != DAY6_FILES or set(value['v6_inverse']) != DAY6_FILES:
        _deny('day6 changed file boundary differs')
    reconstructed = dict(files)
    for name in sorted(DAY6_FILES):
        after = _source_bytes(root, name, byte_overrides)
        if _sha(after) != files[name]:
            _deny('day6 current bytes differ')
        reconstructed[name] = _sha(apply_inverse(after, value['v6_inverse'][name]))
    if reconstructed != previous:
        _deny('day6 inverse proof differs')
    return source


def validate_read_ancestry(raw, pin, v7_raw, root, files, identity, *, byte_overrides=None):
    """Authenticate the two exact reader changes before using retained v7 bytes."""
    if not isinstance(pin, str) or _sha(raw) != pin:
        _deny('read deployment declaration is not pinned')
    value = _read_json(raw)
    if (set(value) != {'schema', 'case', 'v7_sha256', 'current_files',
                       'current_identity', 'v7_inverse'}
            or value['schema'] != READ_SCHEMA or value['case'] != READ_CASE
            or value['v7_sha256'] != V7_SHA256 or _sha(v7_raw) != V7_SHA256):
        _deny('read declaration or retained v7 differs')
    previous = _read_json(v7_raw)['source']
    if files != value['current_files'] or identity != value['current_identity']:
        _deny('read running source identity differs')
    if identity != {**previous['current_identity'], 'source_manifest_digest': digest(files)}:
        _deny('read adapter or manifest differs')
    changed = {name for name in set(files) | set(previous['current_files'])
               if files.get(name) != previous['current_files'].get(name)}
    if changed != READ_FILES or set(value['v7_inverse']) != READ_FILES:
        _deny('read changed file boundary differs')
    reconstructed, overrides = dict(files), {}
    for name in sorted(READ_FILES):
        after = _source_bytes(root, name, byte_overrides)
        if _sha(after) != files[name]:
            _deny('read current bytes differ')
        overrides[name] = apply_inverse(after, value['v7_inverse'][name])
        reconstructed[name] = _sha(overrides[name])
    if reconstructed != previous['current_files']:
        _deny('read inverse proof differs')
    return reconstructed, overrides, previous['current_identity']


def require_exact_source_delta(source, initialization, seal, identity, database, root, files):
    from mta.mdm.initialization import IMPLEMENTATION_FILES, current_implementation_digest
    try:
        overrides = None
        implementation = current_implementation_digest()
        if os.environ.get(LOGISTICS_PIN_ENV) and implementation != digest({
                name: files['mta/'+name] for name in IMPLEMENTATION_FILES}):
            _deny('logistics implementation source differs')
        for path in (DECLARATION, V6_DECLARATION, SOURCE_BEFORE, PRIOR_DECLARATION):
            _readonly(path)
        if os.environ.get(LOGISTICS_PIN_ENV):
            _readonly(LOGISTICS_DECLARATION)
            _readonly(READ_DECLARATION)
            from release.sealed_export import retained_source
            files, export_overrides, identity = retained_source(
                root, files, identity, LOGISTICS_DECLARATION.read_bytes())
            files, overrides, identity = validate_logistics_ancestry(
                LOGISTICS_DECLARATION.read_bytes(), os.environ.get(LOGISTICS_PIN_ENV),
                READ_DECLARATION.read_bytes(), root, files, identity, byte_overrides=export_overrides)
            implementation = digest({name: files['mta/'+name] for name in IMPLEMENTATION_FILES})
        if os.environ.get(READ_PIN_ENV):
            _readonly(READ_DECLARATION)
            prior_overrides = overrides or {}
            files, read_overrides, identity = validate_read_ancestry(
                READ_DECLARATION.read_bytes(), os.environ.get(READ_PIN_ENV),
                DECLARATION.read_bytes(), root, files, identity, byte_overrides=prior_overrides)
            overrides = {**prior_overrides, **read_overrides}
        source_declaration = validate_day6_ancestry(DECLARATION.read_bytes(),
            os.environ.get(PIN_ENV), V6_DECLARATION.read_bytes(), root, files,
            byte_overrides=overrides)
        raw = json.dumps(source_declaration, sort_keys=True, separators=(',', ':')).encode()
        return _validate(source, initialization, seal, identity, database,
            raw, _sha(raw), root, files,
            SOURCE_BEFORE.read_bytes(), PRIOR_DECLARATION.read_bytes(),
            implementation, IMPLEMENTATION_FILES, byte_overrides=overrides)
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise ValueError('Exact native report source compatibility declaration unavailable or invalid') from exc


def require_exact_implementation_delta(current):
    if not os.environ.get(PIN_ENV):
        return current
    from mta.mdm.location_transition import ROOT, source_files
    from mta.mdm.production_families import adapter_digest
    from mta.mdm.initialization import IMPLEMENTATION_FILES
    from mta.runtime.models import MdmSource, ProductionInitialization
    from mta.runtime.mdm_integration_models import MdmSourceIntegration
    source = MdmSource.objects.get(pk=1)
    initialization = ProductionInitialization.objects.get(pk=INITIALIZATION)
    seal = MdmSourceIntegration.objects.get(source=source)
    with connection.cursor() as cursor:
        cursor.execute('SELECT current_database(), oid::bigint FROM pg_database '
                       'WHERE datname=current_database()')
        database = cursor.fetchone()
    files = source_files()
    identity = dict(adapter_digest=adapter_digest(), closing_projection_version=VERSION,
                    source_manifest_digest=digest(files))
    result = require_exact_source_delta(source, initialization, seal, identity,
                                        database, ROOT, files)
    expected_implementation = (digest({name: files['mta/'+name] for name in IMPLEMENTATION_FILES})
        if os.environ.get(LOGISTICS_PIN_ENV) else
        _read_json(DECLARATION.read_bytes())['source']['implementation']['current_digest'])
    if current != expected_implementation:
        _deny('implementation digest differs')
    # The v6 proof only reconstructs the prior installed source. The unchanged
    # v5 verifier remains the authority that admits that prior bridge.
    from mta.mdm.presentation_compatibility import _validate as validate_v5
    validate_v5(source, initialization, seal, result['prior_identity'], database,
        result['prior_declaration_raw'], PRIOR_DECLARATION_SHA256, ROOT,
        result['prior_files'])
    return result['retained_implementation_digest']
