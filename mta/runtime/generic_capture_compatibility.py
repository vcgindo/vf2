"""Preserve accepted scoped execution custody across compatible storage changes.

Normal continuation uses original capture/phase/attempt custody and current
schema admission. Historical source-reconstruction helpers below remain for
their finite legacy recipe checks; they are not a new-release allowlist.
"""
from functools import lru_cache
import json
from pathlib import Path
from mta.serialization import digest

ORIGIN_RELEASE = {'implementation_sha256': 'c4ca2033c2a0ec295373f000c8acc2f0716376eae455549b5181eb8f0ebb086d',
 'manifest_sha256': '9bbb4f0c482563f66d898508c433752cfc6aba9b450b46fc380306c5a352ec2d',
 'migrations_digest': 'd8f7d5e8276a25f079a8fb617e40c073ffce8dbb09a5edbb028eb064e151886e',
 'schema': 'vectorflow-native-release-source-v1',
 'source_commit': '70554bd1dfa4d909194b873ebd98daaea470c715',
 'source_files_digest': 'a089b36ccb61d0cc36085526b7d3dde3326e15cb22e586df2fd7367021c6b60d'}
ORIGIN_OVERRIDES = {'mta/application/native_input_archive.py': 'c14821803124acfb9945c2d63e38c8a1c4e7229340dbba7af5efbe4e136229c1',
 'mta/mdm/daily_current.py': '80ab33ef51e49f043b7fb5f395119217e73ec1b8a1645fad194004caec0e313a',
 'mta/presentation/legacy_scope_read_compatibility.py': '6e5a4e8516344b28cff42d67f8d2047b188ce524b6ba30db9abc85cbf698220e',
 'mta/presentation/registered_read_compatibility.py': '1c07517299478c95c559bbd0b2623e0b243100c58ba61fed4c936df159bb434d',
 'mta/presentation/scoped_transit.py': '24cd6966f52f27c52ef4afc6006f50a50f703bce481e539b695afed4073e3370',
 'mta/presentation/scoped_transit_storage.py': 'afe545c33f2416e6986fd48e9104c1e8232fabba2005775018c2dae024b22729',
 'mta/presentation/scoped_view.py': '5b71b0d6c513ed458f6e08bff9dd42c46a5c847f9ff3096eade1aac21c55b4e3',
 'mta/presentation/views.py': 'b53981c460cfeaadcf6b85cea78aab1c970aea7e5cfc57c929472a0f3ff7c87a',
 'mta/runtime/capture_preparation.py': '0c52fbcb53a1eb3b13cada52065f86980eb7bde4240453b6c96bd960238a3bbd',
 'mta/runtime/csv_scope_operator.py': '4e256c845ada2da72bd054b6907720b923d1299ebbd25b328fedbc7d6d5c6c00',
 'mta/runtime/ingestion_admission.py': '3b0549692691bd885060ac24df50769d3d3fdc94a75b982715e16f99b30fdae8',
 'mta/runtime/ingestion_authority.py': 'e36857686acd4c00292580cc4c6f7b409a9347643c0b43ceab9b6ac39a3df378',
 'mta/runtime/placement_master_publication.py': 'd545c9d84c6aa7ff7f85bab4bbae26e8fcb4eadc5951674f33dc2a520729a0d5',
 'mta/runtime/retained_registered_execution_compatibility.py': '1c137b550b89d6ec51ee1f97f8d03e5bb6540ac6fa0253e67a0725d4e2383d83',
 'mta/runtime/runtime_report_request.py': '8e2f3186a5e6874aed9c3fe3facd131660e49f81445132a3a9006d8cfad702ff',
 'mta/runtime/services.py': '49462c8dc171928c3069f54cb8d78983761f09dcd7597473c396298653c24688',
 'release/advance_ingestion.py': '3eb155dce8b035a3f5aa04a2de2582e66559fc31b3740fd1d3afb0bb8530e838'}
ADDED_FILES = frozenset(['mta/presentation/generic_terminal_delivery.py',
 'mta/runtime/placement_current_master.py',
 'mta/runtime/generic_capture_compatibility.py',
 'mta/runtime/generic_read_alias_transition.py',
 'mta/runtime/migrations/0241_scope_transit_settings_owners.py',
 'mta/runtime/migrations/0242_generic_read_sql_aliases.py',
 'mta/runtime/transit_settings_schema_transition.py'])


# Exact qualified candidate11 factory; this is not arbitrary future upgrade authority.
PREVIOUS_RELEASE = {'implementation_sha256': '9a95264d656ae25493196318b336b8c4aa75faeaff4128150948747f5214ef87',
 'manifest_sha256': '9f54aa557f523d7a4f744774111301210844d304928e63aeb62448809bf28f9b',
 'migrations_digest': '27a26cab2725c56accb46b1e622ac790495279cbfeb68ee593bc863d69014778',
 'schema': 'vectorflow-native-release-source-v1',
 'source_commit': 'eae6c927972c8f31f22f65e0946bf021d7d67110',
 'source_files_digest': 'd056777b19701d4f7f4e02d17cc903c9394df4de588547c25b51001f219deee1'}
PREVIOUS_OVERRIDES = {'mta/runtime/csv_scope_operator.py': 'ec7ec0dde884604cac12cc7b242ba4d44f59fb664c1d5fca88c38dfc4a64a197',
 'mta/runtime/generic_capture_compatibility.py': '2e43f4d9740cab36d0e04d06d4b9260e1795b296c89df8a2020b2cc3edc72a5f',
 'mta/runtime/retained_registered_execution_compatibility.py': '80460e74f6d6c638433b56f5199cc690f70b6156de9a807548c576173338737b'}

# Filled from the exact reviewed original and corrected source recipes. Native
# source identity remains truthful and separate from compatible metadata recipes.
ORIGINAL_PRODUCTION_PUBLICATION_RECIPE = '6a38e8bfeca016b5780bb8f802e5994150a9d51d1e2bccd6c085331783dd7e80'
OBSERVED_PRODUCTION_PUBLICATION_RECIPE = 'cb83106e56b333a4844d43a95cb32461150d27c3bf491a0896e62802e7c7765c'


def production_publication_recipe(observed):
    from mta.runtime.retained_registered_execution_compatibility import _recipe_sources
    _recipe_sources()
    if observed != OBSERVED_PRODUCTION_PUBLICATION_RECIPE:
        raise ValueError('Generic production publication metadata recipe differs')
    return ORIGINAL_PRODUCTION_PUBLICATION_RECIPE


def applicable(value):
    from mta.runtime.production_scope_policy import SCHEMA
    return (type(value) is dict and value.get('scope') in ('UptoBPR','UptoDBM')
        and type(value.get('dispositions')) is dict
        and value['dispositions'].get('schema') == SCHEMA)


def require_original_sources(files, *, factory_release=None):
    """Reconstruct the signed origin map, never import historical producers."""
    factory = ORIGIN_RELEASE if factory_release is None else factory_release
    if factory == ORIGIN_RELEASE:
        overrides, added = ORIGIN_OVERRIDES, ADDED_FILES
    elif factory == PREVIOUS_RELEASE:
        overrides, added = PREVIOUS_OVERRIDES, ()
    else:
        raise ValueError('Generic continuation factory is not source qualified')
    if not overrides.keys() <= files.keys():
        raise ValueError('Generic continuation lost a retained native source')
    original = dict(files)
    for name in added:
        original.pop(name, None)
    original.update(overrides)
    if digest(original) != factory['source_files_digest']:
        raise ValueError('Generic continuation producer sources differ from the certified origin')


@lru_cache(maxsize=2)
def _source_release(commit, manifest_sha256, factory_manifest):
    from release import native_identity
    actual = native_identity.require_current()
    if (actual['source_commit'],actual['manifest_sha256']) != (commit,manifest_sha256):
        raise ValueError('Generic continuation independent process pins differ')
    root = Path(native_identity.__file__).resolve().parents[1]
    manifest = json.loads((root/native_identity.MANIFEST).read_bytes())
    factory = next((release for release in (ORIGIN_RELEASE, PREVIOUS_RELEASE)
                    if release['manifest_sha256'] == factory_manifest), None)
    if factory is None:
        raise ValueError('Generic continuation factory is not source qualified')
    require_original_sources(manifest['files'], factory_release=factory)
    return actual


def require_factory(value, expected, phase_recipe):
    if (not applicable(value) or set(value) != set(expected)
            or any(value[key] != expected[key] for key in expected if key != 'compatibility_digest')):
        raise ValueError('Generic continuation changed the captured factory contract')
    body = {key:item for key,item in value.items() if key != 'compatibility_digest'}
    for release in (ORIGIN_RELEASE, PREVIOUS_RELEASE):
        if value['compatibility_digest'] == digest(dict(request=body, release=release, phase_recipe=phase_recipe)):
            return release
    raise ValueError('Generic continuation original factory or phase recipe differs')


def require_captured_fields(value, expected):
    """Compare behavior, preserving the opaque ORIGINAL execution identity.

This pure check grants no execution authority. validate() must join the value
to its immutable capture and accepted phase before it can be reused.
"""
    from mta.runtime.ingestion_context import sha
    if (not applicable(value) or type(expected) is not dict or set(value) != set(expected)
            or any(value[key] != expected[key] for key in expected if key != 'compatibility_digest')):
        raise ValueError('Generic continuation changed the captured factory contract')
    sha(value['compatibility_digest'])


def _recovery_owner(run, phase):
    """Follow the existing failed-attempt ancestry, without granting a claim."""
    producer = phase.attempt
    latest = run.scope_attempts.filter(command_key=producer.command_key).order_by('-attempt_no').first()
    fields = ('run_id','scope','command_key','compatibility_digest','input_digest',
              'input_manifest_digest','action_revision')
    if latest is None or latest.status not in ('ACTIVE','FAILED','RELEASED'):
        raise ValueError('Generic recovery has no supported current attempt')
    if latest.pk != producer.pk and (latest.expected_phase, latest.expected_receipt_digest) != (phase.phase, phase.digest):
        raise ValueError('Generic recovery child is not bound to its accepted prefix')
    current = latest; seen = set()
    while True:
        if current.pk in seen or any(getattr(current,k) != getattr(producer,k) for k in fields):
            raise ValueError('Generic recovery attempt ancestry differs')
        seen.add(current.pk)
        if current.pk == producer.pk:
            return latest
        parent = current.recovery_of
        if (parent is None or parent.status != 'FAILED' or parent.attempt_no != current.attempt_no-1
                or (parent.created_at,parent.pk) >= (current.created_at,current.pk)):
            raise ValueError('Generic recovery requires its exact failed predecessor')
        current = parent


def validate(run, value, expected):
    """Authenticate unchanged original execution custody at the current cut.

    This does not claim a worker, change a pin or authorize accepted replay.
    The native continuation rechecks its phase/action/head and lease under lock.
    """
    from django.db import connection,transaction
    from release.native_identity import require_current
    from mta.runtime import phase_state
    from mta.runtime.input_reader import read_input
    from mta.runtime.runtime_report_registered_request import read_captured
    from mta.runtime.ingestion_admission import registration,_admit
    from mta.runtime.ingestion_upgrade import _origin
    from mta.runtime.models import ProductionInitialization,RunPhaseAcceptance
    from mta.runtime.scope_execution import receipt_digest, head
    from mta.runtime.runtime_report_placement_publication import read as publication
    from mta.runtime.scoped_pick_files import read as pick_files
    if (run.kind != 'DAILY_CHAIN' or run.evidence_mode != 'production'
            or run.status not in ('RUNNING','SUCCEEDED')
            or run.input_payload.get('content_digest') != run.input_digest
            or digest(run.input_payload) != run.input_manifest_digest):
        raise ValueError('Generic continuation requires its intact production capture')
    require_captured_fields(value,expected)
    actual = require_current()
    raw = read_input(run,components=('scope_request','report_registration_request','initialization_binding'))
    outer = read_captured(run)
    binding = raw.get('initialization_binding') or {}
    if raw.get('scope_request') != value or outer != raw.get('report_registration_request') or not outer:
        raise ValueError('Generic continuation captured registration differs')
    owner = ProductionInitialization.objects.select_related('source').get(pk=binding.get('id'))
    if (owner.source_id != run.mdm_input_capture.source_id
            or run.mdm_input_capture.status not in ('CAPTURED','CONSUMED')
            or binding != dict(id=str(owner.pk),source_digest=owner.source.digest,
                input_sha256=owner.input_sha256,content_digest=owner.input_digest,
                configuration_digest=owner.configuration_digest)
            or outer['registration']['initialization_id'] != str(owner.pk)
            or outer['registration']['source_digest'] != owner.source.digest):
        raise ValueError('Generic continuation original initialization/source differs')
    with transaction.atomic(),connection.cursor() as cursor:
        _original,capability = registration(cursor)
        admitted = _admit(cursor,owner.pk,actual,pending=True)
        # The initialization producer need not be the request factory. Existing
        # source admission authenticates that producer without inventing a
        # release identity from the request's opaque compatibility digest.
        _origin(owner.source)
        if outer['registration']['certificate_digest'] != admitted.certification_digest:
            raise ValueError('Generic continuation original certificate differs')
        phase = RunPhaseAcceptance.objects.select_related('snapshot','attempt').filter(
            run=run,phase={'UptoBPR':'BPR','UptoDBM':'DBM'}[value['scope']],state_sealed=True).first()
        partial = phase is None or phase.attempt.status != 'RELEASED'
        if partial:
            # A code correction can recover a failed initial scope before its
            # terminal phase exists. Authenticate the actual accepted prefix;
            # claiming/releasing the worker remains scope_execution's job.
            if value['scope'] != 'UptoDBM':
                raise ValueError('Generic recovery requires an accepted initial UptoDBM prefix')
            from mta.runtime.production_scope import _phase
            if phase is None:
                phase_name, phase_digest = head(run.pk)
                if phase_name not in ('PRE_BPR','BPR','DBM'):
                    raise ValueError('Generic recovery requires a sealed phase')
                phase = _phase(run,phase_name,phase_digest)
            else:
                phase = _phase(run,phase.phase,phase.digest)
            recovered = _recovery_owner(run,phase)
            partial = recovered.status != 'RELEASED'
            if partial and (run.status != 'RUNNING' or run.output_digest
                    or run.mdm_input_capture.status != 'CAPTURED'
                    or head(run.pk) != (phase.phase,phase.digest)
                    or run.scope_attempts.order_by('-created_at','-id').first().pk != recovered.pk):
                raise ValueError('Generic recovery requires its current unfinished prefix')
            if not partial and phase.phase != 'DBM':
                raise ValueError('Generic recovered release requires its terminal DBM phase')
        if (phase.source_id != owner.source_id or phase.input_digest != run.input_digest
                or phase.digest != receipt_digest(phase)
                or not phase_state.contract.compatible(phase.snapshot)
                or phase.snapshot.state_digest != digest(phase.snapshot.manifest)
                or phase.snapshot.run_id != run.pk or phase.snapshot.acceptance_id != phase.pk
                or phase.attempt.run_id != run.pk
                or phase.attempt.status not in (('ACTIVE','FAILED') if partial else ('RELEASED','FAILED'))
                or phase.attempt.scope != value['scope']
                or phase.attempt.command_key != value['command_key']
                or phase.attempt.compatibility_digest != value['compatibility_digest']
                or phase.attempt.input_digest != run.input_digest
                or phase.attempt.input_manifest_digest != run.input_manifest_digest):
            raise ValueError('Generic continuation accepted phase/attempt custody differs')
        if partial:
            # An accepted phase can precede its publication after interruption.
            # Validate existing artifacts; normal publish/release still demands
            # every required artifact before claiming a completed scope.
            from mta.runtime.models import RuntimeReportPublication
            placements = tuple(RuntimeReportPublication.objects.filter(run=run).values_list('placement',flat=True))
            allowed = ('PostImporter','PostBPR','PostDBM')[:('PRE_BPR','BPR','DBM').index(phase.phase)+1]
            if set(placements) != set(allowed[:len(placements)]):
                raise ValueError('Generic recovery publications exceed or skip the accepted prefix')
        else:
            placements = ('PostImporter','PostBPR')
        for placement in placements:
            row = publication(run.pk,placement=placement,verify_bytes=True)
            if row.run_id != run.pk:
                raise ValueError('Generic continuation original publication owner differs')
        if not partial:
            pick_files(phase.pk,expected_digest=phase.digest)
    return dict(run_id=str(run.pk),source_release=capability['release_identity']['manifest_sha256'],
        actual_release=actual['manifest_sha256'],compatibility_digest=value['compatibility_digest'],
        phase_id=str(phase.pk),phase_digest=phase.digest)
