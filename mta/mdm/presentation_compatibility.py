"""Exact deployment bridge for the approved reader, SKU reviewer response and MOQ Add destination.

The original source seal stays immutable. A read-only deployment declaration,
authenticated outside its own source roster, includes this verifier and its
call site. It is not a registry or an admission path for other source changes.
"""
import hashlib
import json
import os
from pathlib import Path

from django.db import connection

from mta.serialization import digest

CASE = 'handoff3005-g3-003-selective-sku-reviewer-moq-v1'
DECLARATION = Path('/proof/s3-20261015-001/g3-hierarchy-execution/'
                   'source-seal-compatibility-v5.json')
PIN_ENV = 'VF_MDM_SELECTIVE_COMPATIBILITY_SHA256'
SOURCE = '2e22cdb6866c3e43587aa26612abd8201865e903243919add92fffc2c454fa5f'
INITIALIZATION = '25cceb52-e68f-446b-b2d2-5e212ceec173'
IMPLEMENTATION = '372c8ead5e10c72796b6318ce9eae531fb068182d9445ff727ab531e280d7ee5'
INITIALIZATION_RECEIPT = '05b91fed615aeaa5e54616ea17c4df49d5ae62235375c61e5949038cc0034263'
SEAL = 'a5e269cbaa8b59994c0eeeb882d5d18d0b853c9457ace9232360e08f88053255'
ADAPTER = 'f31be0e859c6c0b8a7d8cc6eebc9bff70a9823534f1c6b7c4c0ca021962f4409'
MANIFEST = '8f80ec0e250df83240aa459365319d22d1a5b53684284659d9579db6011fac37'
SELECTIVE_OLD = '735b310c0baee24dbf98d6c286c43c34cc8c564673809571ec0c03b5873d4bbd'
SELECTIVE_NEW = 'e96e0f657b90b8468dce410ad08b2c495e5983bf1364b4d70ed1007c5e78b3d2'
SELECTIVE = 'mta/presentation/selective.py'
HOOK_FILE = 'mta/mdm/location_transition.py'
VERIFIER = 'mta/mdm/presentation_compatibility.py'
REVIEWER = 'mta/mdm/task_reads.py'
MOQ_DELTAS = {'mta/mdm/moq.py': ("def configuration(screen_type, *, source=None):\n    result = supplier.configuration(5, screen_type)\n    if screen_type == 'add' and source is not None and supplier.setting(source) == 'WithDestLoc':\n        for master in result:\n            for field in master['fields']:\n                if field['key'] == 'wc':\n                    field['isAdd'] = True\n    return result", 'def configuration(screen_type):\n    return supplier.configuration(5, screen_type)', '\n'), 'mta/presentation/mdm_views.py': ('for row in (families.module(master_id).configuration(screen, source=installed)\n                    if master_id == 5 else families.module(master_id).configuration(screen))])', 'for row in families.module(master_id).configuration(screen)])', '\r\n')}
DATABASE = ('handoff3005_g3_workflow_20261015_003', 296160)
VERSION = 'native-closing-locations-v2'

READER_DELTA = """    if path == 'closing/dbm/PhaseOutRecommendation':
        from mta.runtime.dbm_phase_storage import TABLES, BINDINGS
        tables = TABLES
        if item and item['table'] != BINDINGS[path]:
            raise PublicationUnavailable('selected_report_image_table_mismatch:' + path)
"""
REVIEWER_DELTA = """                        if not download:
                            import json
                            item = {key: json.dumps(value, ensure_ascii=False, separators=(',', ':'))
                                    for key, value in item.items()}
"""
OLD_HOOK = """        return dict(adapter_digest=adapter_digest(), closing_projection_version=VERSION,
                    source_manifest_digest=source_manifest_digest())
"""
NEW_HOOK = """        identity = dict(adapter_digest=adapter_digest(), closing_projection_version=VERSION,
                        source_manifest_digest=source_manifest_digest())
        if identity != {key: seal.receipt.get(key) for key in identity}:
            from mta.mdm.presentation_compatibility import require_exact_presentation_delta
            return require_exact_presentation_delta(source, initialization, seal, identity)
        return identity
"""


def _deny(reason):
    raise ValueError('Exact MDM presentation compatibility ' + reason)


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _unique_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            _deny('declaration contains duplicate keys')
        value[key] = item
    return value


def _undo(raw, new, old='', *, newline):
    # Reconstruct each retained file's exact bytes, including its line endings.
    # Neither normalization nor arbitrary replacement can create an admission.
    before = new.replace('\n', newline).encode()
    after = old.replace('\n', newline).encode()
    if raw.count(before) != 1:
        _deny('source delta differs')
    return raw.replace(before, after, 1)


def _validate(source, initialization, seal, identity, database, raw, pin, root, files):
    if (not isinstance(pin, str) or len(pin) != 64
            or any(c not in '0123456789abcdef' for c in pin) or _sha(raw) != pin):
        _deny('deployment declaration is not pinned')
    declaration = json.loads(raw, object_pairs_hook=_unique_object)
    if (not isinstance(declaration, dict) or set(declaration) != {
            'case', 'original_files', 'current_files', 'current_adapter_digest'}
            or declaration['case'] != CASE):
        _deny('declaration shape or case differs')
    if (database != DATABASE or source.pk != 1 or source.digest != SOURCE
            or source.implementation_digest != IMPLEMENTATION
            or str(initialization.pk) != INITIALIZATION
            or initialization.source_id != source.pk
            or initialization.implementation_digest != IMPLEMENTATION
            or initialization.receipt_digest != INITIALIZATION_RECEIPT
            or seal.source_id != source.pk or seal.digest != SEAL
            or digest(seal.receipt) != SEAL
            or seal.receipt.get('source_digest') != SOURCE
            or seal.receipt.get('initialization_id') != INITIALIZATION
            or seal.receipt.get('adapter_digest') != ADAPTER
            or seal.receipt.get('source_manifest_digest') != MANIFEST
            or seal.receipt.get('closing_projection_version') != VERSION):
        _deny('original database/source/initialization/seal differs')
    old, current = declaration['original_files'], declaration['current_files']
    if (not isinstance(old, dict) or not isinstance(current, dict)
            or digest(old) != MANIFEST or VERIFIER in old
            or set(current) != set(old) | {VERIFIER} or files != current):
        _deny('complete source roster differs')
    changed = {name for name in current if current[name] != old.get(name)}
    if changed != {SELECTIVE, HOOK_FILE, VERIFIER, REVIEWER} | set(MOQ_DELTAS):
        _deny('changed file boundary differs')
    if (old.get(SELECTIVE) != SELECTIVE_OLD or current.get(SELECTIVE) != SELECTIVE_NEW
            or _sha(_undo((root / SELECTIVE).read_bytes(), READER_DELTA, newline='\n')) != SELECTIVE_OLD
            or _sha(_undo((root / HOOK_FILE).read_bytes(), NEW_HOOK, OLD_HOOK,
                         newline='\r\n')) != old[HOOK_FILE]
            or _sha(_undo((root / REVIEWER).read_bytes(), REVIEWER_DELTA,
                         newline='\n')) != old[REVIEWER]):
        _deny('approved reader, reviewer response or admission hook differs')
    for name, (new, before, newline) in MOQ_DELTAS.items():
        after = (root / name).read_bytes()
        if name == 'mta/presentation/mdm_views.py' and _sha(after) != current[name]:
            from release.sealed_export import presentation_source_bytes
            after = presentation_source_bytes(root, name, current[name])
        if _sha(_undo(after, new, before, newline=newline)) != old[name]:
            _deny('approved MOQ destination delta differs')
    # current_files authenticates the entire verifier and hook as well as every
    # unchanged file. The pin lives in trusted deployment configuration, so it
    # does not form a recursive source checksum or exclude its own code.
    if identity != dict(adapter_digest=declaration['current_adapter_digest'],
                        closing_projection_version=VERSION,
                        source_manifest_digest=digest(current)):
        _deny('running code identity differs')
    return dict(adapter_digest=ADAPTER, closing_projection_version=VERSION,
                source_manifest_digest=MANIFEST)


def require_exact_presentation_delta(source, initialization, seal, identity):
    from mta.mdm.location_transition import ROOT, source_files
    with connection.cursor() as cursor:
        cursor.execute('SELECT current_database(), oid::bigint FROM pg_database '
                       'WHERE datname=current_database()')
        database = cursor.fetchone()
    try:
        files = source_files()
        prior_raw = DECLARATION.read_bytes()
        prior = json.loads(prior_raw, object_pairs_hook=_unique_object)
        if files != prior.get('current_files'):
            from mta.mdm.native_report_compatibility import require_exact_source_delta
            extension = require_exact_source_delta(source, initialization, seal, identity,
                                                   database, ROOT, files)
            return _validate(source, initialization, seal, extension['prior_identity'], database,
                extension['prior_declaration_raw'],
                hashlib.sha256(extension['prior_declaration_raw']).hexdigest(), ROOT,
                extension['prior_files'])
        if not os.statvfs(DECLARATION).f_flag & os.ST_RDONLY:
            _deny('declaration mount is writable')
        return _validate(source, initialization, seal, identity, database,
                         prior_raw, os.environ.get(PIN_ENV), ROOT, files)
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise ValueError('Exact MDM presentation compatibility declaration unavailable or invalid') from exc
