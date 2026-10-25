"""One-use sealed-component validation inside a locked DBM action transaction.

This is not a view cache. Sources, live authorities, DBM state and final native
selection are admitted again. Fresh component rows must exactly equal the rows
already validated in this transaction; bindings are reconstructed from those
fresh rows. Unqualified callers continue through the complete ordinary reader.
"""
from copy import deepcopy
from dataclasses import replace

from django.db import connection

from mta.presentation.context import PublicationUnavailable
from mta.presentation.report_verification import guard_stamp


def _fail():
    raise PublicationUnavailable('phase_action_validation_changed')


def _row(row):
    return deepcopy({field.attname: getattr(row, field.attname)
                     for field in row._meta.concrete_fields})


def _sources(sources):
    inherited = sources.inherited_btr
    return deepcopy((
        _row(sources.run), sources.acceptance_id, sources.acceptance_digest,
        sources.snapshot_digest, sources.action_revision, sources.display_date,
        sources.source_digest, sources._images,
        None if inherited is None else (_row(inherited.owner), inherited.provenance()),
    ))


def _identity():
    if (connection.vendor != 'postgresql' or not connection.in_atomic_block
            or connection.needs_rollback or connection.connection is None):
        return None
    with connection.cursor() as cursor:
        cursor.execute('SELECT current_database(),session_user,current_user,'
                       'pg_backend_pid(),pg_current_xact_id()::text,pg_postmaster_start_time()')
        value = cursor.fetchone()
    return (connection.connection, tuple(connection.atomic_blocks),
            tuple(connection.savepoint_ids), value)


def _runtime():
    from mta.presentation import admission, native_publication
    if admission._admitted is None or not native_publication.enabled():
        return False
    # An owner can replace a guard twice in one transaction without changing
    # its catalogue xmin. Reuse is forbidden for such sessions, including
    # sessions able to SET ROLE to a privileged/owning role.
    with connection.cursor() as cursor:
        cursor.execute("SELECT session_user=current_user AND NOT EXISTS ("
            "SELECT 1 FROM pg_roles r WHERE pg_has_role(current_user,r.oid,'MEMBER') "
            "AND (r.rolsuper OR r.rolcreatedb OR r.rolcreaterole OR r.rolreplication "
            "OR r.rolbypassrls OR r.rolname<>current_user)) "
            "AND NOT has_database_privilege(current_user,current_database(),'CREATE') "
            "AND NOT EXISTS (SELECT 1 FROM pg_namespace n WHERE "
            "n.nspname !~ '^pg_' AND (pg_has_role(current_user,n.nspowner,'MEMBER') "
            "OR has_schema_privilege(current_user,n.oid,'CREATE'))) "
            "AND NOT EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
            "WHERE n.nspname !~ '^pg_' AND pg_has_role(current_user,c.relowner,'MEMBER')) "
            "AND NOT EXISTS (SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace "
            "WHERE n.nspname !~ '^pg_' AND pg_has_role(current_user,p.proowner,'MEMBER'))")
        return cursor.fetchone() == (True,)


def _recipes():
    from mta.presentation import (scoped_report_storage, scoped_reports,
        scoped_prepared, scoped_planning, scoped_transit_storage,
        scoped_pick_storage, scoped_expedite_storage, scoped_git)
    return tuple(module.recipe_digest() for module in (
        scoped_report_storage, scoped_reports, scoped_prepared, scoped_planning,
        scoped_transit_storage, scoped_pick_storage, scoped_expedite_storage, scoped_git))


def begin():
    """Fence the full initial selection; a missing ticket means no optimization."""
    identity = _identity()
    if identity is None or not _runtime():
        return None
    return identity, guard_stamp(), _recipes()


def capture(ticket, view):
    from mta.presentation.scoped_dbm_view import DbmViewBinding
    if ticket is None or not isinstance(view, DbmViewBinding):
        return None
    if ticket != (_identity(), guard_stamp(), _recipes()):
        _fail()
    return ComponentProof(ticket, view)


class ComponentProof:
    def __init__(self, ticket, view):
        self._ticket = ticket
        self._used = False
        self._finished = False
        self._reference_id = view.reference.pk
        self._phase = (view.dbm_phase.pk, view.dbm_phase.digest)
        self._source = _sources(view.bpr.sources)
        self._requests = deepcopy(view.expedite.requests.provenance())
        self._remarks = deepcopy(view.bpr.remarks.provenance())
        self._rows = tuple(_row(row) for row in (
            view.bpr.reports.generation, view.bpr.projection, view.planning.projection,
            view.bpr.transit.generation, view.pick.generation, view.expedite.core.generation,
            view.expedite.parent.generation, view.git.generation, view.reference.pick_files))

    def selected(self, anchor, cut):
        if self._used or self._ticket[:2] != (_identity(), guard_stamp()):
            _fail()
        self._used = True  # A failed attempt consumes the proof as well.
        from mta.presentation import scoped_dbm_view, scoped_view
        from mta.runtime.models import ScopeReadReference
        phase = scoped_dbm_view._accepted(anchor['phase_id'], anchor['phase_digest'])
        if (phase.phase != 'DBM' or str(phase.run_id) != anchor['run_id']
                or (phase.pk, phase.digest) != self._phase):
            _fail()
        rows = scoped_dbm_view._references(phase, cut)
        if len(rows) != 1:
            _fail()
        row = ScopeReadReference.objects.select_related(
            'report_generation__phase__snapshot', 'report_generation__phase__run',
            'git_generation', 'expedite_parent_generation', 'pick_files',
            'action_command__phase_acceptance__snapshot',
            'previous_reference__report_generation').get(pk=rows[0].pk)
        if row.previous_reference_id != self._reference_id:
            _fail()
        scoped_view.verify_guards()
        from mta.serialization import digest
        if (row.digest != rows[0].digest or row.digest != digest(row.metadata)
                or row.recipe_digest != scoped_view.recipe_digest()):
            _fail()
        bpr, planning, git, expedition = self._graph(row)
        configuration, request_digest = scoped_view._configuration(bpr.sources.run)
        files = scoped_view._files(row.report_generation.phase, row)
        metadata = scoped_view._metadata(bpr, planning, git, expedition, files,
            configuration, request_digest, action_command=row.action_command,
            previous_reference=row.previous_reference,
            transition_kind=None if row.metadata['transition'] is None
                else row.metadata['transition']['kind'])
        if (metadata != row.metadata
                or row.runtime_reports_digest != configuration['configuration_digest']
                or row.expedite_parent_generation_id != expedition.parent.generation.pk):
            _fail()
        return scoped_dbm_view.compose(scoped_view.ViewBinding(row, bpr, planning, git, expedition),
            phase.pk, expected_digest=phase.digest)

    def _graph(self, row):
        from mta.presentation import (scoped_sources, scoped_report_storage, scoped_prepared,
            scoped_planning, scoped_transit_storage, scoped_pick_storage, scoped_expedite_storage,
            scoped_expedite_parent, scoped_expedite, scoped_git, scoped_requests, scoped_remarks)
        from mta.runtime import models
        report = row.report_generation
        build = report.action_revision
        # These are the original validators, including their transitive owners,
        # predecessor/receipt/absence predicates and current external file bytes.
        sources = scoped_sources.bind(report.phase_id, expected_digest=row.metadata['phase_digest'],
            action_revision=build, include_nms=True, include_inherited_btr=True, read_reference=row)
        if _sources(sources) != self._source:
            _fail()
        nms = replace(sources, inherited_btr=None)
        plain = replace(nms, _images={name: item for name, item in sources._images.items()
                                     if name != 'closing/consumer_context/NMSAllItems'})
        locator = row.metadata['expedite']
        projection = models.ScopeSourceProjection.objects.get(generation_id=report.pk)
        planning_row = models.ScopePlanningProjection.objects.get(generation_id=report.pk)
        transit_row = models.ScopeTransitGeneration.objects.select_related('phase__snapshot').get(
            pk=locator['transit_generation_id'])
        pick_row = models.ScopePickGeneration.objects.select_related('phase__snapshot').get(
            pk=row.metadata['pick']['generation_id'])
        core_row = models.ScopeExpediteGeneration.objects.get(pk=locator['core_generation_id'])
        fresh_rows = (report, projection, planning_row, transit_row, pick_row, core_row,
                      row.expedite_parent_generation, row.git_generation, row.pick_files)
        if tuple(_row(item) for item in fresh_rows) != self._rows:
            _fail()
        # Every concrete field and cross-link is unchanged. Only the successful
        # validation of these sealed components is reused, never their ORM objects.
        reports = scoped_report_storage.ReportBinding(report)
        prepared = scoped_prepared.PreparedBinding(projection, reports, plain)
        nms_prepared = replace(prepared, sources=nms)
        planning = scoped_planning.PlanningBinding(planning_row, nms_prepared)
        transit = scoped_transit_storage.TransitBinding(transit_row)
        pick = scoped_pick_storage.PickBinding(pick_row, plain)
        scoped_expedite_storage.pick_queries.bind(sources.run, read_binding=nms_prepared, pick_binding=pick)
        core = scoped_expedite_storage.ExpediteBinding(core_row, nms_prepared, pick)
        remarks = scoped_remarks.bind(sources, configuration_digest=report.configuration_digest)
        requests = scoped_requests.bind(nms)
        if (remarks.provenance() != self._remarks or requests.provenance() != self._requests):
            _fail()
        scoped_expedite_parent.verify_guards()
        parent = scoped_expedite_parent._admit(row.expedite_parent_generation, core, remarks,
            locator['parent_digest'], build)
        expedition = scoped_expedite.require_binding(sources.run,
            scoped_expedite.ExpediteBinding(core, parent, transit, requests))
        if expedition.read_identity != locator:
            _fail()
        git = scoped_git.GitBinding(row.git_generation, replace(prepared, transit=transit))
        return replace(prepared, sources=sources, remarks=remarks, transit=transit), planning, git, expedition

    def finish(self):
        """Called after final native identity, permissions and current-cut checks."""
        if (not self._used or self._finished
                or self._ticket != (_identity(), guard_stamp(), _recipes())):
            _fail()
        self._finished = True
