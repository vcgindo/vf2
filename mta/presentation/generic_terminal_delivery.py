"""Terminal downloads from an ordinary generic split capture's accepted owners.

Historical exceptional BOR/archive dispositions remain separate. No producer,
file copy, receipt rewrite or fixture identity grants access here.
"""
from types import SimpleNamespace
from pathlib import Path

from mta.presentation.context import PublicationUnavailable
from mta.presentation.request_scope import once_per_request
from mta.runtime.input_reader import read_input


def applicable(run, captured=None):
    from mta.runtime.generic_capture_compatibility import applicable as generic
    value = (read_input(run, components=('scope_request',)) if captured is None else captured).get('scope_request')
    return generic(value)


@once_per_request
def binding(run):
    from mta.runtime import runtime_report_request, production_scope
    from mta.runtime.production_report_placement import _continued
    from mta.runtime.scoped_actions import revision
    from mta.runtime.scoped_pick_files import _accepted, read
    if not applicable(run) or run.status != 'SUCCEEDED':
        raise PublicationUnavailable('generic_terminal_completed_owner_required')
    value = runtime_report_request.validate_read_request(
        read_input(run, components=('scope_request',))['scope_request'])
    production_scope.captured_run(run, value)
    final = run.phase_acceptances.select_related('attempt').get(phase='DAY_FINAL', state_sealed=True)
    scope = {'UptoBPR': 'PostBPR', 'UptoDBM': 'PostDBM'}[value['scope']]
    _continued(run, value, scope=scope, command_key=final.attempt.command_key,
               expected_revision=revision(run))
    dbm = run.phase_acceptances.select_related('snapshot').get(phase='DBM', state_sealed=True)
    expected = final.attempt.expected_phase
    if expected not in (('BPR', 'DBM') if scope == 'PostBPR' else ('DBM',)):
        raise PublicationUnavailable('generic_terminal_phase_owner_differs')
    production_scope._phase(run, expected, final.attempt.expected_receipt_digest)
    phase = _accepted(dbm.snapshot.parent.acceptance_id,
                      dbm.metadata['effects']['parent_acceptance_digest'])
    if phase.run_id != run.pk or phase.phase != 'BPR':
        raise PublicationUnavailable('generic_terminal_bpr_owner_differs')
    files = read(phase.pk, expected_digest=phase.digest)
    return SimpleNamespace(run=run, phase=phase, files=files)


def archive_path(run, captured, *, create=False):
    """Separate run-owned storage; never add a fifth file to ScopePickFiles."""
    from mta.application.operational_io import owned_path
    binding(run)
    root = Path(captured['pick_output_root'])
    directory = owned_path(root, str(run.pk) + '/native-input')
    if create:
        directory.mkdir(mode=0o700, exist_ok=True)
    target = owned_path(root, str(run.pk) + '/native-input/InputData.zip')
    if not directory.is_dir() or directory.is_symlink() or (target.exists() and not target.is_file()):
        raise ValueError('generic_terminal_archive_path_denied')
    return target


def open_report(run, payload, report_name):
    from mta.presentation import pick_downloads as pick
    from mta.runtime.scoped_pick_files import open_file
    if report_name not in pick.REPORTS:
        raise pick.PickDownloadDenied('unknown_pick_report')
    view = binding(run)
    state = pick._complete_state(run)
    if not pick._fully_scoped(run, payload, state, report_name):
        raise pick.PickDownloadDenied('selected_run_pick_scope_denied')
    stream = open_file(view.phase.pk, pick.REPORTS[report_name], expected_digest=view.phase.digest)
    try:
        for chunk in pick._expected_chunks(state, report_name):
            if stream.read(len(chunk)) != chunk:
                raise pick.PickDownloadDenied('generic_terminal_pick_population_differs')
        if stream.read(1):
            raise pick.PickDownloadDenied('generic_terminal_pick_population_differs')
        stream.seek(0)
        return stream, pick.REPORTS[report_name]
    except BaseException:
        stream.close()
        raise
