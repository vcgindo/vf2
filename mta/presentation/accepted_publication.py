"""Bounded startup admission for qualified, protected native publications.

Full row audits remain publication/upgrade operations. This path is eligible
only when the existing certified schema authority covers accepted-state guards.
It retains no rows, authority cache, permissions or independent readiness seal.
"""
import os

from django.conf import settings
from django.db import connection

from mta.presentation.context import PublicationUnavailable


def _qualified_ownership(run):
    from mta.runtime.accepted_state_ownership import verify_guards
    from mta.runtime import accepted_state_transition as ownership
    from mta.runtime import ingestion_admission as ingestion
    from mta.runtime import ingestion_authority as authority
    from mta.runtime.initialization_models import ProductionInitialization
    from mta.runtime.mdm_daily_models import MdmDailyInputCapture

    with connection.cursor() as cursor:
        if not verify_guards(cursor, required=False):
            return False
        cursor.execute("SELECT name FROM mta.django_migrations WHERE app='fresh_mta' "
                       "AND name=ANY(%s) ORDER BY name", [[name for name, _ in ownership.PINS]])
        if cursor.fetchall() != [(name,) for name, _ in ownership.PINS]:
            return False
        source = MdmDailyInputCapture.objects.values_list('source_id', flat=True).get(run=run)
        owner = ProductionInitialization.objects.values_list('id', flat=True).get(source_id=source)
        release = ingestion._process_release(os.environ.get('VF_NATIVE_RELEASE_COMMIT'),
                                             os.environ.get('VF_NATIVE_RELEASE_SHA256'))
        body = authority.read(cursor, owner, release['manifest_sha256'])
        cert, anchor, schema, guard, _ = ingestion.effective_schema(cursor, body)
        extension = authority.read_schema_transition(cursor, anchor)
        if extension is not None:
            return ownership.approved_receipt(extension)
        # A fresh original certification may already cover these guards. An
        # old certification with a later, unqualified extension cannot qualify.
        return (anchor['target_release'] == cert['release_digest']
                and schema == cert['schema_digest'] and guard == cert['guard_digest'])


def _summary_ready(run):
    # Do not modify the sealed producer's recipe or call its population COUNT.
    from mta.presentation.planning_summary_daily import binding
    from mta.runtime.planning_summary_models import METRICS, PlanningSummaryReceipt
    from mta.runtime.planning_summary_schema import verify_guards
    identities, _, _ = binding(run)
    receipt = PlanningSummaryReceipt.objects.filter(run=run, **identities).first()
    if (receipt is None or receipt.status != 'READY' or receipt.metrics != list(METRICS)
            or any(getattr(receipt, key) != value for key, value in identities.items())):
        raise PublicationUnavailable('planning_summary_generation_unavailable')
    verify_guards(connection)
    return receipt


def _btr_ready(run):
    from mta.presentation.btr_reporting import selected_generation
    generation = selected_generation(run)
    if generation is not None and generation.version == 2:
        from mta.presentation.btr_snapshot import reference_generation
        reference_generation(run, generation)


def _external_artifacts(run):
    from mta.presentation.context import permission_catalogue
    from mta.presentation.hierarchy import selected_manifest
    permission_catalogue()
    selected_manifest(run)
    if settings.VF_MTA_TERMINAL_FILE or settings.VF_MTA_TERMINAL_SHA256:
        from mta.presentation.terminal_supplement import terminal_ancillary
        terminal_ancillary(run)


def _checked_selection(run):
    from mta.presentation import native_publication, native_selection
    from mta.presentation.daily_publication import require_ready
    _external_artifacts(run)
    publication = require_ready(run, verify_rows=False)
    summary = _summary_ready(run)
    native = native_publication.identity(run)
    if getattr(settings, 'VF_BTR_REPORTING_GENERATION', ''):
        _btr_ready(run)
    native_selection.require_candidate(native_selection.candidate(run, publication, summary, native))


def startup(binding):
    """Admit the actual entry path, including selection, with fresh pass lifetimes."""
    from mta.presentation import native_publication
    if (not native_publication.enabled()
            or not getattr(settings, 'VF_MTA_DAILY_PUBLICATION', False)):
        return None
    native_publication.require_mode()
    from mta.presentation.context import configured_run
    from mta.presentation.report_verification import verification_scope
    from mta.presentation.request_scope import metadata_operation
    run = configured_run()
    with metadata_operation(), verification_scope(run):
        if not _qualified_ownership(run):
            return None
        identities = []
        for _ in range(2):
            with metadata_operation():
                current = configured_run()
                if current.pk != run.pk:
                    raise PublicationUnavailable('publication_changed_during_admission')
                _checked_selection(current)
                _, identity = binding(current)
                identities.append(identity)
        if identities[0] != identities[1]:
            raise PublicationUnavailable('publication_changed_during_admission')
    return current, identities[1]
