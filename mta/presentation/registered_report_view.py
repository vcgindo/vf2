"""Registered eight-report attachment to the existing intermediate read graph.

The BPR graph remains its original typed owner. This versioned configuration
binds captured registration and actual placement receipts, not copied results.
Live actions/remarks continue through the existing immutable-reference leases.
"""
from mta.serialization import digest
from mta.presentation.context import PublicationUnavailable
from mta.presentation.request_scope import once_per_request


SCHEMA = 'fresh-registered-placement-read-configuration-v1'
FIELDS = frozenset({'schema', 'configuration_digest', 'reference',
                   'registration_request', 'post_importer', 'post_bpr'})


def applicable_configuration(value):
    return type(value) is dict and value.get('schema') == SCHEMA


def applicable_reference(row):
    return applicable_configuration(row.metadata.get('runtime_reports'))


def applicable_run(run):
    from mta.runtime.input_reader import read_input
    return read_input(run, components=('report_registration_request',)).get('report_registration_request') is not None


@once_per_request
def recipe_digest():
    # Preserve the existing graph identity only under the exact compatible
    # reader profile. Native build/schema authority remains independent.
    from mta.presentation.registered_read_compatibility import recipe
    return recipe()


def _locator(row):
    return dict(id=str(row.pk), digest=row.digest)


def _phase_publication(run, placement, phase):
    from mta.runtime.runtime_report_placement_publication import read
    row = read(run.pk, placement=placement, verify_bytes=False)
    if (row.run_id != run.pk or row.owner_kind != 'SCOPED_PHASE' or row.phase_id != phase.pk
            or phase.run_id != run.pk or not phase.state_sealed
            or row.metadata['authority']['owner']['phase_digest'] != phase.digest):
        raise PublicationUnavailable('registered_placement_phase_owner_differs')
    return row


@once_per_request
def configuration(run):
    from mta.runtime import runtime_report_registered_request as registration
    from mta.runtime.input_reader import read_input
    from mta.runtime.scope_runtime_reports import require_test_database
    from mta.runtime.models import RunPhaseAcceptance
    outer = registration.read_captured(run)
    inner = read_input(run, components=('scope_request',)).get('scope_request')
    if outer is None or inner['scope'] not in ('UptoBPR', 'UptoDBM'):
        raise PublicationUnavailable('registered_intermediate_capture_required')
    require_test_database()
    bpr = RunPhaseAcceptance.objects.select_related('snapshot__parent').get(
        run=run, phase='BPR', state_sealed=True)
    pre = bpr.snapshot.parent.acceptance
    if pre.phase != 'PRE_BPR' or pre.run_id != run.pk:
        raise PublicationUnavailable('registered_bpr_parent_differs')
    importer = _phase_publication(run, 'PostImporter', pre)
    publication = _phase_publication(run, 'PostBPR', bpr)
    expected_configuration = inner['runtime_reports']['configuration_digest']
    expected_request = digest(inner)
    if (publication.catalogue_parent_id != importer.pk
            or any(row.configuration_digest != expected_configuration
                   or row.scope_request_digest != expected_request
                   or row.input_digest != run.input_digest
                   or row.input_manifest_digest != run.input_manifest_digest
                   for row in (importer, publication))):
        raise PublicationUnavailable('registered_read_publication_chain_differs')
    return dict(schema=SCHEMA, configuration_digest=expected_configuration,
        reference=inner['runtime_reports'], registration_request=outer,
        post_importer=_locator(importer), post_bpr=_locator(publication)), expected_request


def require_dbm(view, phase):
    """Current DBM joins its own BPR and actual PostDBM file-stage receipt."""
    from mta.runtime.input_reader import read_input
    inner = read_input(phase.run, components=('scope_request',)).get('scope_request')
    config, request_digest = configuration(phase.run)
    if (inner['scope'] != 'UptoDBM' or phase.phase != 'DBM' or phase.run_id != view.run_id
            or phase.snapshot.parent.acceptance_id != view.bpr.sources.acceptance_id
            or phase.metadata['effects']['parent_acceptance_digest'] != view.bpr.sources.acceptance_digest
            or view.reference.metadata['runtime_reports'] != config):
        raise PublicationUnavailable('registered_dbm_bpr_parent_differs')
    row = _phase_publication(phase.run, 'PostDBM', phase)
    if (str(row.catalogue_parent_id) != config['post_bpr']['id']
            or row.configuration_digest != config['configuration_digest']
            or row.scope_request_digest != request_digest):
        raise PublicationUnavailable('registered_dbm_publication_chain_differs')
    return row


def bind(row, expected_digest, *, retained_parent=False):
    from mta.presentation import scoped_view, scoped_read_graph
    scoped_view.verify_guards(registered=True)
    if (not applicable_reference(row) or row.digest != expected_digest
            or row.digest != digest(row.metadata) or row.recipe_digest != recipe_digest()):
        raise PublicationUnavailable('registered_read_reference_identity_differs')
    config, request_digest = configuration(row.report_generation.run)
    bpr, planning, git, expedition = scoped_read_graph.bind(row, retained_parent=retained_parent)
    files = scoped_view._files(row.report_generation.phase, row)
    actual = scoped_view._metadata(bpr, planning, git, expedition, files, config, request_digest,
        action_command=row.action_command, previous_reference=row.previous_reference,
        transition_kind=None if row.metadata['transition'] is None else row.metadata['transition']['kind'])
    if actual != row.metadata or row.runtime_reports_digest != config['configuration_digest']:
        raise PublicationUnavailable('registered_read_reference_dependencies_differ')
    return scoped_view.ViewBinding(row, bpr, planning, git, expedition)
