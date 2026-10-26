"""Serve an explicitly selected accepted BPR without a completed-day fiction."""
import hashlib
from pathlib import Path

from django.conf import settings

from mta.presentation.context import PublicationUnavailable, permission_catalogue
from mta.presentation import scoped_selection
from mta.presentation.request_scope import metadata_operation
from mta.runtime.models import RunPhaseAcceptance
from mta.runtime.mdm_daily_models import MdmDailyInputCapture
from mta.runtime.ingestion_admission import certified_source
from mta.serialization import digest


def binding(expected_run=None):
    from mta.presentation.admission import CONFIG_SETTINGS
    if not scoped_selection.enabled():
        raise PublicationUnavailable('phase_selection_required')
    anchor = scoped_selection.read(settings.VF_MTA_PHASE_SELECTION_FILE)
    if anchor != settings.VF_MTA_PHASE_SELECTION:
        raise PublicationUnavailable('phase_selection_changed_restart_required')
    if any(getattr(settings, field, '') for field in (
            'VF_MTA_SELECTION_FILE', 'VF_MTA_PUBLISHED_RUN', 'VF_MTA_PUBLISHED_DIGEST',
            'VF_MTA_HIERARCHY_FILE', 'VF_MTA_HIERARCHY_SHA256')):
        raise PublicationUnavailable('phase_publication_configuration_conflict')
    phase = RunPhaseAcceptance.objects.select_related('run').get(pk=anchor['phase_id'])
    run = phase.run
    capture = MdmDailyInputCapture.objects.select_related('source').get(run=run)
    source_digest = getattr(settings, 'VF_MDM_SOURCE_DIGEST', '')
    expected_phase = 'DBM' if anchor['schema']==scoped_selection.DBM_SCHEMA else 'BPR'
    if (phase.phase != expected_phase or not phase.state_sealed or str(run.pk) != anchor['run_id']
            or expected_run is not None and expected_run.pk != run.pk
            or run.kind != 'DAILY_CHAIN' or run.evidence_mode != 'production'
            or run.status not in ('RUNNING', 'SUCCEEDED')
            or phase.digest != anchor['phase_digest']
            or phase.snapshot.state_digest != anchor['snapshot_digest']
            or run.input_digest != anchor['input_digest']
            or run.input_manifest_digest != anchor['input_manifest_digest']
            or run.business_date.isoformat() != anchor['business_date']
            or capture.source_id != phase.source_id or capture.revision_digest != anchor['capture_digest']
            or capture.status != ('CONSUMED' if run.status == 'SUCCEEDED' else 'CAPTURED')
            or not source_digest or source_digest != capture.source.digest):
        raise PublicationUnavailable('phase_native_source_binding_differs')
    source = certified_source(source_digest)
    if source is None or source.pk != capture.source_id:
        raise PublicationUnavailable('phase_certified_source_required')
    permission_catalogue()
    if (settings.VF_MTA_PERMISSIONS_SHA256 != anchor['permissions_sha256']
            or scoped_selection.recipe_for_run(run) != anchor['recipe_digest']):
        raise PublicationUnavailable('phase_admission_recipe_or_permissions_changed')
    configuration = {name: getattr(settings, name) for name in CONFIG_SETTINGS}
    configuration.update(VF_MTA_PHASE_SELECTION_FILE=settings.VF_MTA_PHASE_SELECTION_FILE,
        VF_MTA_PHASE_SELECTION=settings.VF_MTA_PHASE_SELECTION, VF_MDM_SOURCE_DIGEST=source_digest)
    configuration['VF_MTA_SCOPED_BOR_OUTPUT_POLICY'] = getattr(settings, 'VF_MTA_SCOPED_BOR_OUTPUT_POLICY', None)
    from mta.presentation import scoped_batch_downloads
    file_phase = phase.snapshot.parent.acceptance if expected_phase=='DBM' else phase
    batch = scoped_batch_downloads.configured()
    if batch is not None:
        configuration['batch_files'] = scoped_batch_downloads.verify(file_phase.pk,
            expected_digest=file_phase.digest, expected_run_id=run.pk,
            expected_snapshot_digest=file_phase.snapshot.state_digest,
            manifest_file=batch[0], manifest_sha256=batch[1])
        configuration['batch_manifest'] = batch
    from mta.presentation import scoped_artifacts
    artifacts = scoped_artifacts.configured()
    if artifacts:
        from types import SimpleNamespace
        view = SimpleNamespace(bpr=SimpleNamespace(sources=SimpleNamespace(
            acceptance_id=file_phase.pk, acceptance_digest=file_phase.digest)))
        artifact = scoped_artifacts.selected(view)
        configuration.update(scope_delivery=artifacts, artifact_file_identity=artifact['file_identity'])
    paths = list((Path(__file__).resolve().parents[1] / 'config').glob('*.json'))
    paths += [Path(settings.VF_MTA_PERMISSIONS_FILE), Path(settings.VF_MTA_PHASE_SELECTION_FILE)]
    files = {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
    # Read-reference/action/remark revisions are admitted afresh by their actual
    # endpoints. They do not change this selected logical BPR's identity.
    return run, digest(dict(schema=('fresh-selected-dbm-admission-v1' if expected_phase=='DBM'
                                   else 'fresh-selected-bpr-admission-v1'), anchor=anchor,
                            source_id=source.pk, configuration=configuration, files=files))


def startup():
    with metadata_operation():
        run, before = binding()
        view = scoped_selection.selected()
        current, after = binding(run)
        from mta.presentation import scoped_artifacts
        scoped_artifacts.selected(view, verify_bytes=True)
    if current.pk != view.run_id or before != after:
        raise PublicationUnavailable('phase_changed_during_admission')
    return current, after, view.read_identity
