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
ADAPTED_FILES = {'mta/presentation/scoped_transit.py': '2457e1f7471b0f10c37d231c6e98d36f00de29d8787e0995ad38df9a130bf36d',
 'mta/runtime/migrations/0240_framework_metadata_writer_guards.py': 'f3049a4f6e0e8b195565bb97fb441aa4247b9fdb3771906d532e060bdee0b2c1',
 'mta/application/operational_input_archive.py': '3ceb9a2d429a9fc121f1c83133bf25ec10a96e023e585dc8e917f6dd6678f4fa',
 'mta/application/runtime_report_hooks.py': '2d1054ac705b43c159fb12618ef5f4ff6c02451a214a407e6fb5dbe5f1611102',
 'mta/config/production_scope_profile.json': 'cf6bc4b10854ee966ad4eea2af43b03cb34b1d9a5b6e2dc2e8bed55e40c33421',
 'mta/presentation/legacy_scope_read_compatibility.py': '6e5a4e8516344b28cff42d67f8d2047b188ce524b6ba30db9abc85cbf698220e',
 'mta/presentation/registered_read_compatibility.py': '1c07517299478c95c559bbd0b2623e0b243100c58ba61fed4c936df159bb434d',
 'mta/presentation/registered_report_view.py': '01ae33ab88694414a7f45c816439965ad52e939f87d67bff9dba1fc4027cb144',
 'mta/presentation/scoped_artifacts.py': '4f1a61db37335940b1ce6911eff464cf99284053f57ca1fa7c8a764f852b4821',
 'mta/presentation/scoped_batch_downloads.py': '6d9c48ed037902564217055005e167782b6a4fffb822660efe60d830d27efb9e',
 'mta/presentation/scoped_batch_files.py': '8cfc8221749c47e8646e3689256682890348ba2456dcd75728ff82d1f52188f8',
 'mta/presentation/scoped_bor.py': '6f0f61572e1ead503b90d7193f6442c8b93f95e520975660d354f9bc0cade727',
 'mta/presentation/scoped_selection.py': '69e8fbb4a5c168ad30dcba47a1ab640394d04dc25c6f917ae8f781687aad802a',
 'mta/presentation/scoped_view.py': '5b71b0d6c513ed458f6e08bff9dd42c46a5c847f9ff3096eade1aac21c55b4e3',
 'mta/presentation/terminal_read_mode.py': '5ddc0218330c6ecf211f189ed5ab9c914034f0725ba74d05abd6a5ca594df3db',
 'mta/runtime/csv_scope_operator.py': '4e256c845ada2da72bd054b6907720b923d1299ebbd25b328fedbc7d6d5c6c00',
 'mta/runtime/ingestion_admission.py': '3b0549692691bd885060ac24df50769d3d3fdc94a75b982715e16f99b30fdae8',
 'mta/runtime/ingestion_authority.py': 'e36857686acd4c00292580cc4c6f7b409a9347643c0b43ceab9b6ac39a3df378',
 'mta/runtime/migrations/0238_registered_read_action_cut.py': '572d225c31d4b707da9f22e273b1669274afd46c9334355c73c067cbcea4110b',
 'mta/runtime/migrations/0239_production_generic_scope_read.py': '44e28f4a8b34912540ee56767e26c22ab1565870f583cc88a993936f5a522297',
 'mta/runtime/placement_master_publication.py': 'd545c9d84c6aa7ff7f85bab4bbae26e8fcb4eadc5951674f33dc2a520729a0d5',
 'mta/runtime/production_report_placement.py': 'd061425d85d9a75b149c62c7409a9c14322895777143e8d2290e968638b52544',
 'mta/runtime/production_scope.py': '032b122392ee2c4ff5c32ea8af0929233d7bf6e0b23c535a9045b865299aed1b',
 'mta/runtime/production_scope_policy.py': '88ab6efa6f77958d874fbcaecb049a32dc7bee2368b7ad61f28dacc52612ff0f',
 'mta/runtime/production_upto_dbm.py': '37f6f384e255193578e9a89d627d940c643a5ffd8812944b3ababca7d2442643',
 'mta/runtime/registered_read_action_transition.py': 'e18412674f29ccbf0fe0dcd6ec0845e98d4f0966516c1376790ab10b69057125',
 'mta/runtime/report_definition_registration.py': 'cab2b8c7f8403f610e4f8627615537eb6212877dd54b148d9a3f4bdaa1b27816',
 'mta/runtime/runtime_report_bpr_sources.py': 'a3b2bd56af4e44e3865b98ed518c6ba644608068eaf855793e07eb6c44234c8d',
 'mta/runtime/runtime_report_execution.py': '9ccfe45c6aefc4b8217740d8e7f3b7a66883b520da8a1f08f32e870b02f54c35',
 'mta/runtime/runtime_report_placement_publication.py': '6c384fabad01c3ea7f6cbed2c8d236f86caf2c9bcd0efabb2b4134d3b3352775',
 'mta/runtime/runtime_report_registered_request.py': 'fe94595e3241bcdf96ab7704b5a7fd7eae4c975049d905887b885e67956aa468',
 'mta/runtime/runtime_report_request.py': '8e2f3186a5e6874aed9c3fe3facd131660e49f81445132a3a9006d8cfad702ff',
 'mta/runtime/scope_execution.py': '1812f2e986db6b8b1fd91688ab0c3cd2183a0714c8007c5992d646a17d5b6d78',
 'mta/runtime/scope_runtime_reports.py': '20d5e22ee8eb1cc1287082ed4028fd04d94074b97e54b387244f8b15eab93797',
 'release/advance_ingestion.py': '3eb155dce8b035a3f5aa04a2de2582e66559fc31b3740fd1d3afb0bb8530e838',
 'release/configuration.py': '4a5294eeb3d965e96c9fea798a3a1d490c6d8e4585ca4c60f617fd021e9aa162'}
ADAPTED_PYTHON_TEXT = {'mta/presentation/scoped_transit.py': '2457e1f7471b0f10c37d231c6e98d36f00de29d8787e0995ad38df9a130bf36d',
 'mta/runtime/migrations/0240_framework_metadata_writer_guards.py': 'f3049a4f6e0e8b195565bb97fb441aa4247b9fdb3771906d532e060bdee0b2c1',
 'mta/application/operational_input_archive.py': '3ceb9a2d429a9fc121f1c83133bf25ec10a96e023e585dc8e917f6dd6678f4fa',
 'mta/application/runtime_report_hooks.py': '2d1054ac705b43c159fb12618ef5f4ff6c02451a214a407e6fb5dbe5f1611102',
 'mta/presentation/legacy_scope_read_compatibility.py': '6e5a4e8516344b28cff42d67f8d2047b188ce524b6ba30db9abc85cbf698220e',
 'mta/presentation/registered_read_compatibility.py': '1c07517299478c95c559bbd0b2623e0b243100c58ba61fed4c936df159bb434d',
 'mta/presentation/registered_report_view.py': '01ae33ab88694414a7f45c816439965ad52e939f87d67bff9dba1fc4027cb144',
 'mta/presentation/scoped_artifacts.py': '4f1a61db37335940b1ce6911eff464cf99284053f57ca1fa7c8a764f852b4821',
 'mta/presentation/scoped_batch_downloads.py': '6d9c48ed037902564217055005e167782b6a4fffb822660efe60d830d27efb9e',
 'mta/presentation/scoped_batch_files.py': '8cfc8221749c47e8646e3689256682890348ba2456dcd75728ff82d1f52188f8',
 'mta/presentation/scoped_bor.py': '6f0f61572e1ead503b90d7193f6442c8b93f95e520975660d354f9bc0cade727',
 'mta/presentation/scoped_selection.py': '69e8fbb4a5c168ad30dcba47a1ab640394d04dc25c6f917ae8f781687aad802a',
 'mta/presentation/scoped_view.py': '5b71b0d6c513ed458f6e08bff9dd42c46a5c847f9ff3096eade1aac21c55b4e3',
 'mta/presentation/terminal_read_mode.py': '5ddc0218330c6ecf211f189ed5ab9c914034f0725ba74d05abd6a5ca594df3db',
 'mta/runtime/csv_scope_operator.py': '4e256c845ada2da72bd054b6907720b923d1299ebbd25b328fedbc7d6d5c6c00',
 'mta/runtime/ingestion_admission.py': '3b0549692691bd885060ac24df50769d3d3fdc94a75b982715e16f99b30fdae8',
 'mta/runtime/ingestion_authority.py': 'e36857686acd4c00292580cc4c6f7b409a9347643c0b43ceab9b6ac39a3df378',
 'mta/runtime/migrations/0238_registered_read_action_cut.py': '572d225c31d4b707da9f22e273b1669274afd46c9334355c73c067cbcea4110b',
 'mta/runtime/migrations/0239_production_generic_scope_read.py': '44e28f4a8b34912540ee56767e26c22ab1565870f583cc88a993936f5a522297',
 'mta/runtime/placement_master_publication.py': 'd545c9d84c6aa7ff7f85bab4bbae26e8fcb4eadc5951674f33dc2a520729a0d5',
 'mta/runtime/production_report_placement.py': 'd061425d85d9a75b149c62c7409a9c14322895777143e8d2290e968638b52544',
 'mta/runtime/production_scope.py': '032b122392ee2c4ff5c32ea8af0929233d7bf6e0b23c535a9045b865299aed1b',
 'mta/runtime/production_scope_policy.py': '88ab6efa6f77958d874fbcaecb049a32dc7bee2368b7ad61f28dacc52612ff0f',
 'mta/runtime/production_upto_dbm.py': '37f6f384e255193578e9a89d627d940c643a5ffd8812944b3ababca7d2442643',
 'mta/runtime/registered_read_action_transition.py': 'e18412674f29ccbf0fe0dcd6ec0845e98d4f0966516c1376790ab10b69057125',
 'mta/runtime/report_definition_registration.py': 'cab2b8c7f8403f610e4f8627615537eb6212877dd54b148d9a3f4bdaa1b27816',
 'mta/runtime/runtime_report_bpr_sources.py': 'a3b2bd56af4e44e3865b98ed518c6ba644608068eaf855793e07eb6c44234c8d',
 'mta/runtime/runtime_report_execution.py': '9ccfe45c6aefc4b8217740d8e7f3b7a66883b520da8a1f08f32e870b02f54c35',
 'mta/runtime/runtime_report_placement_publication.py': '6c384fabad01c3ea7f6cbed2c8d236f86caf2c9bcd0efabb2b4134d3b3352775',
 'mta/runtime/runtime_report_registered_request.py': 'fe94595e3241bcdf96ab7704b5a7fd7eae4c975049d905887b885e67956aa468',
 'mta/runtime/runtime_report_request.py': '8e2f3186a5e6874aed9c3fe3facd131660e49f81445132a3a9006d8cfad702ff',
 'mta/runtime/scope_execution.py': '1812f2e986db6b8b1fd91688ab0c3cd2183a0714c8007c5992d646a17d5b6d78',
 'mta/runtime/scope_runtime_reports.py': '20d5e22ee8eb1cc1287082ed4028fd04d94074b97e54b387244f8b15eab93797',
 'release/advance_ingestion.py': '3eb155dce8b035a3f5aa04a2de2582e66559fc31b3740fd1d3afb0bb8530e838',
 'release/configuration.py': '4a5294eeb3d965e96c9fea798a3a1d490c6d8e4585ca4c60f617fd021e9aa162'}
NEW_FILES = {'mta/runtime/migrations/0240_framework_metadata_writer_guards.py',
 'mta/config/production_scope_profile.json',
 'mta/presentation/registered_read_compatibility.py',
 'mta/runtime/_retained_execution_source_pins.py',
 'mta/runtime/csv_scope_operator.py',
 'mta/runtime/migrations/0238_registered_read_action_cut.py',
 'mta/runtime/migrations/0239_production_generic_scope_read.py',
 'mta/runtime/production_scope_policy.py',
 'mta/runtime/registered_read_action_transition.py',
 'mta/runtime/retained_registered_execution_compatibility.py'}
PROFILE_FILES = {
    'mta/runtime/_retained_execution_source_pins.py',
    'mta/runtime/retained_registered_execution_compatibility.py',
}
OBSERVED_PUBLICATION_RECIPE = '4c1eba2cbf7e0cbe45acbebc9e540bf9956a669665c44905aa5301ccb0f76147'
OBSERVED_ATTACHMENT_RECIPE = '1ca267426afca271cfb0141bfd6c52d64a0d0254765bb5413dc0e336e846dfaf'


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


def artifact_recipe(observed):
    _recipe_sources()
    if observed != OBSERVED_ARTIFACT_RECIPE:
        raise ValueError('Retained InputData reader adaptation differs')
    return ARTIFACT_RECIPE


def batch_recipe(observed):
    _recipe_sources()
    if observed != OBSERVED_BATCH_RECIPE:
        raise ValueError('Retained BPR batch reader adaptation differs')
    return BATCH_RECIPE


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

ARTIFACT_RECIPE = 'b7047ad865d00062f29575c07e70ce95834a3cc9871ab9dfd0f4a03f546e2f46'
OBSERVED_ARTIFACT_RECIPE = 'd2080ffadf99f9cafe71dcf3c7a06b0d6c2a2eaf95989dd17eef0dd8a6478f48'
BATCH_RECIPE = '1a244a5376c43b7791ba88b3923e461adc6d9e48d9c3ca6e5deaa32bff46abee'
OBSERVED_BATCH_RECIPE = 'ad4d23e6d2e491fab475a9556ff3c0ed07fe3af5a2515139efa332e3af1f9090'
