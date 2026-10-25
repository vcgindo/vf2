"""Transaction-local producer handoffs, not serving or cached read admission.

The orchestrator admits frozen accepted sources once under its run lock. Each
stage keeps its own SQL guards, persisted row checks and receipt validation.
The completed graph is independently rebound before the transaction can commit.
"""
from django.db import connection
from mta.presentation.context import PublicationUnavailable
from mta.serialization import digest


def require_sources(phase,sources):
    from mta.presentation.scoped_sources import BprSources
    from mta.runtime.scoped_actions import revision
    if (not connection.in_atomic_block or type(sources) is not BprSources
            or phase.phase!='BPR' or not phase.state_sealed
            or phase.run_id!=sources.run.pk or phase.pk!=sources.acceptance_id
            or phase.digest!=sources.acceptance_digest
            or phase.input_digest!=sources.run.input_digest
            or phase.snapshot.run_id!=sources.run.pk
            or phase.snapshot.acceptance_id!=phase.pk
            or phase.snapshot.state_digest!=sources.snapshot_digest
            or phase.snapshot.input_digest!=sources.run.input_digest
            or type(sources.action_revision) is not int or sources.action_revision<0
            or revision(sources.run)!=sources.action_revision):
        raise PublicationUnavailable('bpr_preparation_source_handoff_differs')
    return sources


def require_reports(reports,sources):
    from mta.presentation.scoped_report_storage import ReportBinding
    if type(reports) is not ReportBinding:
        raise PublicationUnavailable('bpr_preparation_report_handoff_differs')
    row=reports.generation
    require_sources(row.phase,sources)
    if (not row.sealed or row.sealed_at is None or row.digest!=digest(row.metadata)
            or row.run_id!=sources.run.pk or row.phase_id!=sources.acceptance_id
            or row.action_revision!=sources.action_revision
            or row.source_digest!=sources.source_digest
            or row.configuration_digest!=row.phase.snapshot.manifest['references']['profile']):
        raise PublicationUnavailable('bpr_preparation_report_handoff_differs')
    return reports


def require_prepared(prepared):
    from mta.presentation.scoped_prepared import PreparedBinding
    if type(prepared) is not PreparedBinding:
        raise PublicationUnavailable('bpr_preparation_projection_handoff_differs')
    require_reports(prepared.reports,prepared.sources)
    row=prepared.projection;report=prepared.reports.generation
    if (not row.sealed or row.sealed_at is None or row.digest!=digest(row.metadata)
            or row.generation_id!=report.pk or row.report_generation_digest!=report.digest):
        raise PublicationUnavailable('bpr_preparation_projection_handoff_differs')
    return prepared


def _same_owner(report,row):
    return all(getattr(report,name)==getattr(row,name) for name in
               ('run_id','phase_id','action_revision','source_digest','configuration_digest'))


def require_pick(prepared,pick):
    from mta.presentation.scoped_pick_storage import PickBinding
    require_prepared(prepared)
    if type(pick) is not PickBinding:
        raise PublicationUnavailable('bpr_preparation_pick_handoff_differs')
    row=pick.generation;report=prepared.reports.generation
    if (not row.sealed or row.sealed_at is None or row.digest!=digest(row.metadata)
            or not _same_owner(report,row) or pick.sources.run.pk!=prepared.run_id
            or pick.sources.acceptance_id!=prepared.sources.acceptance_id
            or pick.sources.snapshot_digest!=prepared.sources.snapshot_digest
            or pick.sources.source_digest!=prepared.sources.source_digest
            or pick.sources.action_revision!=prepared.sources.action_revision):
        raise PublicationUnavailable('bpr_preparation_pick_handoff_differs')
    return pick


def require_transit(prepared):
    from mta.presentation.scoped_transit_storage import TransitBinding
    require_prepared(prepared)
    if type(prepared.transit) is not TransitBinding:
        raise PublicationUnavailable('bpr_preparation_transit_handoff_differs')
    row=prepared.transit.generation
    if (not row.sealed or row.sealed_at is None or row.digest!=digest(row.metadata)
            or not _same_owner(prepared.reports.generation,row)):
        raise PublicationUnavailable('bpr_preparation_transit_handoff_differs')
    return prepared.transit
