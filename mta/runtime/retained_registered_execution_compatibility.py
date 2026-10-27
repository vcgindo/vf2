"""Finite execution authority for two preserved registered scoped captures.

This does not turn a read recipe into execution permission. Original producers
and captured identities are checked independently of the actual admitted build.
New captures and Full requests retain their ordinary strict validation.
"""
from functools import lru_cache
from pathlib import Path
import hashlib
import json

from mta.serialization import digest
from mta.runtime._retained_execution_source_pins import (
    ORIGINAL_RELEASE, ORIGINAL_FILES, ORIGINAL_PYTHON_TEXT_OVERRIDES, RETAINED_RUNS)

PUBLICATION_RECIPE = '6fb2894f2165fcd087bece0e580c1b5802923d5c83dbf16fab00025120f4007b'
ATTACHMENT_RECIPE = '798dd462a82d43272015c4c683a6bf58cf3b7c9f7c22d27e9e6b572c59e7e4a9'
PREVIOUS_RELEASE = '08703fa862fe22ffb2c23c7755a56872bfb3fe2aa07797ab64bca11d1749c8e3'
PREVIOUS_COMMIT = '36c33f66f825299a0b3796ba6d1496c13cc3d6c3'
READ_ROUTING_PREVIOUS_RELEASE = '39489103fddb29766949f6f8b5642904f6a1688ad397a4ea9b5278603d0ad7e6'
READ_ROUTING_PREVIOUS_COMMIT = '3ed8c93f3c0e3fa3ddf8da2d690af6e3b1bc5de5'

# Filled from the reviewed staged export, never from a caller or live database.
# Raw hashes qualify the native artifact; text hashes also support Python's
# universal-newline source recipes in a Windows development checkout.
ADAPTED_FILES = {'mta/presentation/legacy_scope_read_compatibility.py': '6e5a4e8516344b28cff42d67f8d2047b188ce524b6ba30db9abc85cbf698220e',
 'mta/presentation/terminal_read_mode.py': 'c4ac7a12220ac552788a9d09a16d0acf82cb5ba76d4bafdcc60408a51d4829bc',
 'release/configuration.py': '4a5294eeb3d965e96c9fea798a3a1d490c6d8e4585ca4c60f617fd021e9aa162',
 'mta/presentation/registered_read_compatibility.py': 'f8a2e56ef5c254b8a34672c0d70e2e45e9fe12eb337578a86746144ca9e7f585',
 'mta/presentation/registered_report_view.py': 'e8c7291d7f043261d3240577b2d669d1e6bd054da90e5519853a3f1436f27e4d',
 'mta/presentation/scoped_view.py': '501572cdc61bc1eebcb61ba2c6bd42d3ee571988290daf08d4eee16789c68306',
 'mta/runtime/ingestion_admission.py': '3b0549692691bd885060ac24df50769d3d3fdc94a75b982715e16f99b30fdae8',
 'mta/runtime/ingestion_authority.py': '2d701c9b3500c08400aba7e9345979d7bb3e8fff91eb7f8661ee08a9c35e8630',
 'mta/runtime/migrations/0238_registered_read_action_cut.py': '572d225c31d4b707da9f22e273b1669274afd46c9334355c73c067cbcea4110b',
 'mta/runtime/placement_master_publication.py': 'd545c9d84c6aa7ff7f85bab4bbae26e8fcb4eadc5951674f33dc2a520729a0d5',
 'mta/runtime/production_report_placement.py': 'd27e4eb15f830a977c2e72d48b02148de0a764b226b69bc7f6c62c2e986d483a',
 'mta/runtime/production_scope.py': '66cb6136186676fd0e110bae2ab2595c89d4837bd1ba2704e7db6103f9b5a44a',
 'mta/runtime/registered_read_action_transition.py': 'e18412674f29ccbf0fe0dcd6ec0845e98d4f0966516c1376790ab10b69057125',
 'mta/runtime/runtime_report_execution.py': '9ccfe45c6aefc4b8217740d8e7f3b7a66883b520da8a1f08f32e870b02f54c35',
 'mta/runtime/runtime_report_registered_request.py': '0e3059f95a13ec3165105d1d2130426c2d389ccf9db08b533396d9151e42176b',
 'mta/runtime/runtime_report_request.py': 'd99147a7a6b79483a422897faa0b7087511d6dd449a3b14ee722fea0679cc140',
 'mta/runtime/scope_execution.py': '1812f2e986db6b8b1fd91688ab0c3cd2183a0714c8007c5992d646a17d5b6d78',
 'release/advance_ingestion.py': '3eb155dce8b035a3f5aa04a2de2582e66559fc31b3740fd1d3afb0bb8530e838'}
ADAPTED_PYTHON_TEXT = {'mta/presentation/legacy_scope_read_compatibility.py': '6e5a4e8516344b28cff42d67f8d2047b188ce524b6ba30db9abc85cbf698220e',
 'mta/presentation/terminal_read_mode.py': 'c4ac7a12220ac552788a9d09a16d0acf82cb5ba76d4bafdcc60408a51d4829bc',
 'release/configuration.py': '4a5294eeb3d965e96c9fea798a3a1d490c6d8e4585ca4c60f617fd021e9aa162',
 'mta/presentation/registered_read_compatibility.py': 'f8a2e56ef5c254b8a34672c0d70e2e45e9fe12eb337578a86746144ca9e7f585',
 'mta/presentation/registered_report_view.py': 'e8c7291d7f043261d3240577b2d669d1e6bd054da90e5519853a3f1436f27e4d',
 'mta/presentation/scoped_view.py': '501572cdc61bc1eebcb61ba2c6bd42d3ee571988290daf08d4eee16789c68306',
 'mta/runtime/ingestion_admission.py': '3b0549692691bd885060ac24df50769d3d3fdc94a75b982715e16f99b30fdae8',
 'mta/runtime/ingestion_authority.py': '2d701c9b3500c08400aba7e9345979d7bb3e8fff91eb7f8661ee08a9c35e8630',
 'mta/runtime/migrations/0238_registered_read_action_cut.py': '572d225c31d4b707da9f22e273b1669274afd46c9334355c73c067cbcea4110b',
 'mta/runtime/placement_master_publication.py': 'd545c9d84c6aa7ff7f85bab4bbae26e8fcb4eadc5951674f33dc2a520729a0d5',
 'mta/runtime/production_report_placement.py': 'd27e4eb15f830a977c2e72d48b02148de0a764b226b69bc7f6c62c2e986d483a',
 'mta/runtime/production_scope.py': '66cb6136186676fd0e110bae2ab2595c89d4837bd1ba2704e7db6103f9b5a44a',
 'mta/runtime/registered_read_action_transition.py': 'e18412674f29ccbf0fe0dcd6ec0845e98d4f0966516c1376790ab10b69057125',
 'mta/runtime/runtime_report_execution.py': '9ccfe45c6aefc4b8217740d8e7f3b7a66883b520da8a1f08f32e870b02f54c35',
 'mta/runtime/runtime_report_registered_request.py': '0e3059f95a13ec3165105d1d2130426c2d389ccf9db08b533396d9151e42176b',
 'mta/runtime/runtime_report_request.py': 'd99147a7a6b79483a422897faa0b7087511d6dd449a3b14ee722fea0679cc140',
 'mta/runtime/scope_execution.py': '1812f2e986db6b8b1fd91688ab0c3cd2183a0714c8007c5992d646a17d5b6d78',
 'release/advance_ingestion.py': '3eb155dce8b035a3f5aa04a2de2582e66559fc31b3740fd1d3afb0bb8530e838'}
NEW_FILES = {
    'mta/presentation/registered_read_compatibility.py',
    'mta/runtime/registered_read_action_transition.py',
    'mta/runtime/migrations/0238_registered_read_action_cut.py',
    'mta/runtime/_retained_execution_source_pins.py',
    'mta/runtime/retained_registered_execution_compatibility.py',
}
PROFILE_FILES = {
    'mta/runtime/_retained_execution_source_pins.py',
    'mta/runtime/retained_registered_execution_compatibility.py',
}
OBSERVED_PUBLICATION_RECIPE = '7d5c4dc8a7c1a623c96e9e48f36779a7fd51f954ed5277063376927ddd1a9ead'
OBSERVED_ATTACHMENT_RECIPE = 'ae393a0d612497af702f650b7cdc2cd824b6ff50fa360f2857ac5ba2d02f7fab'


def check_source_manifest(files):
    """Every original native byte remains pinned except reviewed adapters."""
    expected = dict(ORIGINAL_FILES, **ADAPTED_FILES)
    if (set(files) != set(ORIGINAL_FILES) | NEW_FILES
            or not NEW_FILES-PROFILE_FILES <= ADAPTED_FILES.keys()
            or any(files.get(name) != checksum for name, checksum in expected.items())):
        raise ValueError('Retained execution native source closure differs')


@lru_cache(maxsize=1)
def _recipe_sources():
    # Source files are immutable for this process. No database or business cut
    # is cached; every retained execution call validates live authority below.
    root = Path(__file__).resolve().parents[2]
    expected = {**ORIGINAL_FILES, **ORIGINAL_PYTHON_TEXT_OVERRIDES,
                **ADAPTED_PYTHON_TEXT}
    if not ADAPTED_FILES or set(ADAPTED_PYTHON_TEXT) != {p for p in ADAPTED_FILES if p.endswith('.py')}:
        raise ValueError('Retained execution adapter roster is incomplete')
    for name, checksum in expected.items():
        if name.endswith('.py'):
            actual = hashlib.sha256((root/name).read_text(encoding='utf-8').encode()).hexdigest()
            if actual != checksum:
                raise ValueError('Retained execution producer source differs: '+name)


def publication_recipe(observed):
    _recipe_sources()
    if observed != OBSERVED_PUBLICATION_RECIPE:
        raise ValueError('Retained execution publication adaptation differs')
    return PUBLICATION_RECIPE


def attachment_recipe(observed):
    _recipe_sources()
    if observed != OBSERVED_ATTACHMENT_RECIPE:
        raise ValueError('Retained execution registration adaptation differs')
    return ATTACHMENT_RECIPE


@lru_cache(maxsize=1)
def process_release():
    from release.native_identity import require_current, MANIFEST
    actual = require_current()  # Always truthful; never return the origin here.
    root = Path(__file__).resolve().parents[2]
    manifest = json.loads((root/MANIFEST).read_bytes())
    check_source_manifest(manifest['files'])
    _recipe_sources()
    return actual


def retained_facts(run, value, expected):
    """Pure identity check shared by source tests and the native validator."""
    from mta.runtime.phase_state import recipe_digest
    pin = RETAINED_RUNS.get(str(run.pk))
    if (pin is None or run.kind != 'DAILY_CHAIN' or run.evidence_mode != 'production'
            or run.status not in ('RUNNING', 'SUCCEEDED')
            or value.get('scope') != pin['scope'] or pin['scope'] not in ('UptoBPR','UptoDBM')
            or run.input_digest != pin['input_digest']
            or run.input_manifest_digest != pin['input_manifest_digest']
            or digest(run.input_payload) != run.input_manifest_digest
            or run.input_payload.get('content_digest') != run.input_digest
            or digest(value) != pin['scope_request_digest']
            or value.get('compatibility_digest') != pin['compatibility_digest']
            or recipe_digest() != pin['phase_recipe']
            or any(value.get(k) != v for k,v in expected.items() if k != 'compatibility_digest')):
        raise ValueError('Exact retained registered execution capture required')
    body = {k:v for k,v in value.items() if k != 'compatibility_digest'}
    original = digest(dict(request=body,release=ORIGINAL_RELEASE,phase_recipe=pin['phase_recipe']))
    if original != value['compatibility_digest']:
        raise ValueError('Retained execution origin or phase recipe differs')
    return pin


def validate_retained(run, value, expected):
    from django.db import connection
    from mta.runtime.input_reader import read_input
    from mta.runtime.runtime_report_registered_request import read_captured
    from mta.runtime.models import RunPhaseAcceptance
    from mta.runtime.scope_execution import receipt_digest
    from mta.runtime import ingestion_authority as authority
    from mta.runtime.ingestion_admission import validate_activation
    from mta.runtime.runtime_report_placement_publication import read as publication

    pin = retained_facts(run,value,expected)
    release = process_release()
    raw = read_input(run,components=('scope_request','report_registration_request','initialization_binding'))
    outer = read_captured(run)  # Independently verifies persisted registration custody.
    binding = raw.get('initialization_binding',{})
    if (raw.get('scope_request') != value or outer != raw.get('report_registration_request')
            or digest(outer) != pin['outer_digest']
            or binding.get('id') != pin['initialization_id']
            or binding.get('source_digest') != pin['source_digest']
            or outer['registration']['registration_digest'] != pin['registration_digest']):
        raise ValueError('Retained execution registered source binding differs')
    phase = RunPhaseAcceptance.objects.get(pk=pin['phase_id'],run=run,state_sealed=True)
    if (phase.phase != {'UptoBPR':'BPR','UptoDBM':'DBM'}[pin['scope']]
            or phase.digest != pin['phase_digest'] or receipt_digest(phase) != phase.digest
            or phase.attempt.compatibility_digest != value['compatibility_digest']
            or phase.attempt.input_digest != run.input_digest
            or phase.attempt.input_manifest_digest != run.input_manifest_digest):
        raise ValueError('Retained execution accepted source phase differs')
    for placement, locator in pin['publications'].items():
        row = publication(run.pk,placement=placement,verify_bytes=True)
        if str(row.pk) != locator['id'] or row.digest != locator['digest']:
            raise ValueError('Retained execution accepted publication differs')
    with connection.cursor() as cursor:
        cursor.execute('SELECT current_database()')
        if cursor.fetchone() != (pin['database'],):
            raise ValueError('Retained execution database differs')
        body = authority.read(cursor,pin['initialization_id'],release['manifest_sha256'])
        if body['target_commit'] != release['source_commit']:
            raise ValueError('Retained execution actual release authority differs')
        certificate = validate_activation(cursor,body)
        if (certificate['source_digest'] != pin['source_digest']
                or certificate['receipt_digest'] != pin['original_certification_digest']):
            raise ValueError('Retained execution original certification differs')
        cursor.execute("SELECT max(name) FROM mta.django_migrations WHERE app='fresh_mta'")
        if cursor.fetchone() != ('0238_registered_read_action_cut',):
            raise ValueError('Retained execution requires its admitted0238 catalogue')
    # Existing claim, phase-publication and final-master owners still validate
    # their exact live head, action revision and current transaction lease.
    # The captured compatibility digest is returned unchanged by the caller.


def transition_profile(initialization_id, previous, target):
    """Exact qualified predecessors for code-only adaptation, with no DDL."""
    if (previous.get('source_commit'), previous.get('manifest_sha256')) not in (
            (PREVIOUS_COMMIT, PREVIOUS_RELEASE),
            (READ_ROUTING_PREVIOUS_COMMIT, READ_ROUTING_PREVIOUS_RELEASE)):
        return False
    if str(initialization_id) not in {p['initialization_id'] for p in RETAINED_RUNS.values()}:
        raise ValueError('Retained execution transition requires its owned initialization')
    if process_release() != target:
        raise ValueError('Retained execution transition release differs')
    return True
