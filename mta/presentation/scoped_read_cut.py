"""The live command cut is distinct from a report's immutable build cut.

Only an exact persisted read reference can authorize binding a retained report
cut. This is an explicit argument, never a context flag or a cross-write cache.
The database guards own publication; this module rechecks the reader contract.
"""
from mta.presentation.context import PublicationUnavailable
from mta.serialization import digest

SCHEMA = 'fresh-bpr-read-reference-v2'


def revision(reference):
    return (reference.action_command_id if reference.action_command_id is not None
            else reference.report_generation.action_revision)


def transition(command, previous, kind):
    if previous is None:
        if command is not None or kind is not None:
            raise PublicationUnavailable('phase_read_base_transition_differs')
        return None
    if kind not in ('ACTION', 'REMARK'):
        raise PublicationUnavailable('phase_read_transition_kind_differs')
    return dict(kind=kind,command_id=None if command is None else command.pk,
        previous_reference_id=str(previous.pk),previous_reference_digest=previous.digest)


def require(reference, phase, *, build_revision, current_revision):
    """Check the exact stored graph and immediate transition, without replay.

    The caller reads the current revision freshly and subsequently binds every
    graph component and the canonical command chain. An old reference is not a
    current read merely because its report contents remain unchanged.
    """
    from mta.runtime.models import ScopeReadReference
    if (not isinstance(reference, ScopeReadReference) or reference._state.adding
            or reference._state.db!='default'):
        raise PublicationUnavailable('phase_read_reference_required')
    report=reference.report_generation
    live=revision(reference)
    if (type(build_revision) is not int or type(current_revision) is not int
            or type(live) is not int or build_revision<0 or live<build_revision
            or live!=current_revision or report.action_revision!=build_revision
            or report.phase_id!=phase.pk or report.run_id!=phase.run_id
            or not report.sealed or report.sealed_at is None
            or reference.digest!=digest(reference.metadata)
            or reference.metadata.get('schema')!=SCHEMA
            or type(reference.metadata.get('action_revision')) is not int
            or reference.metadata.get('action_revision')!=live
            or reference.metadata.get('run_id')!=str(phase.run_id)
            or reference.metadata.get('phase_id')!=str(phase.pk)
            or reference.metadata.get('phase_digest')!=phase.digest
            or reference.metadata.get('snapshot_digest')!=phase.snapshot.state_digest
            or reference.metadata.get('input_digest')!=phase.run.input_digest
            or reference.metadata.get('input_manifest_digest')!=phase.run.input_manifest_digest):
        raise PublicationUnavailable('phase_read_current_owner_differs')
    command=reference.action_command
    if command is not None:
        accepted=command.phase_acceptance
        if (not command.state_sealed or command.run_id!=phase.run_id
                or command.payload.get('operation') not in ('APPLY','SLEEP')
                or not command.payload.get('actor') or accepted is None
                or accepted.phase!='DBM' or not accepted.state_sealed
                or accepted.run_id!=phase.run_id or accepted.source_id!=phase.source_id
                or accepted.snapshot.parent_id!=phase.snapshot_id
                or accepted.snapshot.manifest.get('references',{}).get('profile')!=report.configuration_digest
                or accepted.metadata.get('effects',{}).get('parent_acceptance_digest')!=phase.digest):
            raise PublicationUnavailable('phase_read_command_owner_differs')
    previous=reference.previous_reference
    node=reference.metadata.get('transition')
    if previous is None:
        if command is not None or node is not None or live!=build_revision:
            raise PublicationUnavailable('phase_read_base_transition_differs')
        return live
    if (previous.pk==reference.pk or previous.digest!=digest(previous.metadata)
            or type(node) is not dict
            or node!=transition(command,previous,node.get('kind'))
            or previous.report_generation_id!=report.pk
            or previous.git_generation_id!=reference.git_generation_id
            or previous.pick_files_id!=reference.pick_files_id
            or previous.recipe_digest!=reference.recipe_digest
            or previous.runtime_reports_digest!=reference.runtime_reports_digest):
        raise PublicationUnavailable('phase_read_previous_owner_differs')
    before=previous.metadata['bpr']['remarks']['live_highwater']
    after=reference.metadata['bpr']['remarks']['live_highwater']
    if type(before) is not int or type(after) is not int or before<0:
        raise PublicationUnavailable('phase_read_remark_cut_differs')
    if node['kind']=='ACTION':
        if (command is None or command.pk==previous.action_command_id
                or command.scope_parent_revision!=revision(previous)
                or command.pk<=command.scope_parent_revision or before!=after
                or previous.expedite_parent_generation_id!=reference.expedite_parent_generation_id
                or {k:v for k,v in previous.metadata.items() if k not in ('action_revision','transition')}
                !={k:v for k,v in reference.metadata.items() if k not in ('action_revision','transition')}):
            raise PublicationUnavailable('phase_read_action_transition_differs')
    else:
        from copy import deepcopy
        def independent(metadata):
            values=deepcopy(metadata)
            for key in ('action_revision','transition'):values.pop(key,None)
            values['bpr'].pop('remarks',None)
            for key in ('parent_generation_id','parent_digest'):values.get('expedite',{}).pop(key,None)
            return values
        if (previous.action_command_id!=reference.action_command_id
                or revision(previous)!=live or after<=before
                or independent(previous.metadata)!=independent(reference.metadata)):
            raise PublicationUnavailable('phase_read_remark_transition_differs')
    return live
