"""Compose the DBM stop with its retained BPR dependencies and inherited BTR.

The DBM acceptance is the selected business boundary. The existing BPR read
reference remains a BPR owner and is never relabelled as a DBM publication.
"""
from dataclasses import dataclass
from django.db import connection, transaction
from mta.presentation.context import PublicationUnavailable
from mta.presentation import scoped_view, scoped_dbm_stop
from mta.presentation.scoped_dbm_stop import _accepted
from mta.serialization import digest
from release.phase_selection import DBM_SCHEMA, validate


@dataclass(frozen=True)
class DbmViewBinding(scoped_view.ViewBinding):
    dbm_phase: object
    dbm_context: object

    @property
    def read_identity(self):
        return dict(super().read_identity, dbm_phase_id=str(self.dbm_phase.pk),
            dbm_phase_digest=self.dbm_phase.digest, dbm_snapshot_digest=self.dbm_phase.snapshot.state_digest)


def compose(view, phase_id, *, expected_digest):
    from mta.runtime.input_reader import read_input
    from mta.runtime.production_upto_dbm import SCHEMA as REQUEST_SCHEMA
    phase = _accepted(phase_id,expected_digest)
    request = read_input(phase.run,components=('scope_request',)).get('scope_request')
    if (phase.phase!='DBM' or phase.run_id!=view.run_id
            or type(request) is not dict or request.get('scope')!='UptoDBM'
            or request.get('schema')!=REQUEST_SCHEMA
            or phase.snapshot.parent.acceptance_id!=view.bpr.sources.acceptance_id
            or phase.metadata['effects']['parent_acceptance_digest']!=view.bpr.sources.acceptance_digest):
        raise PublicationUnavailable('pre_btr_bpr_dependency_differs')
    with connection.cursor() as cursor:
        cursor.execute('SELECT mta.actionable_scope_phase(%s,%s)',[phase.run_id,phase.pk])
        if cursor.fetchone()[0] is not True:
            raise PublicationUnavailable('pre_btr_released_scope_required')
    context = scoped_dbm_stop.bind(phase.pk,expected_digest=phase.digest,
        action_revision=view.action_revision)
    return DbmViewBinding(view.reference,view.bpr,view.planning,view.git,view.expedite,phase,context)


@transaction.atomic
def prepare(phase_id, *, expected_digest, action_revision):
    from mta.runtime.models import CalculationRun
    from mta.runtime.scope_execution import _source_lock
    phase = _accepted(phase_id,expected_digest)
    _source_lock(phase.run_id)
    CalculationRun.objects.select_for_update().get(pk=phase.run_id)
    if phase.phase!='DBM':
        raise PublicationUnavailable('pre_btr_dbm_acceptance_required')
    from mta.runtime.models import RemarkOwner
    highwater=RemarkOwner.objects.get(pk='BPRReport_RemarkDetails').next_ordinal
    existing=_references(phase,(action_revision,highwater))
    if len(existing)>1:
        raise PublicationUnavailable('pre_btr_current_reference_missing_or_ambiguous')
    if existing:
        return compose(scoped_view.bind(existing[0].pk,expected_digest=existing[0].digest),
            phase.pk,expected_digest=phase.digest)
    parent = phase.snapshot.parent.acceptance
    view = scoped_view.prepare(parent.pk,expected_digest=parent.digest,action_revision=action_revision)
    return compose(view,phase.pk,expected_digest=phase.digest)


def candidate(view):
    from django.conf import settings
    from mta.presentation.context import permission_catalogue
    from mta.presentation.scoped_selection import native_identity,recipe_digest
    permission_catalogue()
    phase = view.dbm_phase
    value = {key:view.reference.metadata[key] for key in (
        'run_id','input_digest','input_manifest_digest','configuration_digest')}
    value.update(schema=DBM_SCHEMA,phase_id=str(phase.pk),phase_digest=phase.digest,
        snapshot_digest=phase.snapshot.state_digest,native_digest=digest(native_identity(view)),
        capture_digest=phase.capture_digest,permissions_sha256=settings.VF_MTA_PERMISSIONS_SHA256,
        recipe_digest=recipe_digest(),business_date=view.run.business_date.isoformat())
    value['selection_digest'] = digest(value)
    return validate(value)


def selected(anchor, cut):
    phase = _accepted(anchor['phase_id'],anchor['phase_digest'])
    if phase.phase!='DBM' or str(phase.run_id)!=anchor['run_id']:
        raise PublicationUnavailable('pre_btr_selected_phase_differs')
    rows = _references(phase,cut)
    if len(rows)!=1:
        raise PublicationUnavailable('pre_btr_current_reference_missing_or_ambiguous')
    return compose(scoped_view.bind(rows[0].pk,expected_digest=rows[0].digest),
        phase.pk,expected_digest=phase.digest)


def _references(phase,cut):
    from django.db.models import Q
    from mta.runtime.models import ScopeReadReference
    return list(ScopeReadReference.objects.filter(
        Q(action_command_id=cut[0])|Q(action_command__isnull=True,report_generation__action_revision=cut[0]),
        report_generation__run_id=phase.run_id,
        report_generation__phase_id=phase.snapshot.parent.acceptance_id,
        recipe_digest=scoped_view.recipe_digest(),
        metadata__bpr__remarks__live_highwater=cut[1])[:2])
