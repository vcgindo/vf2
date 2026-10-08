"""Selected-run, fully scoped access to the four complete Pick batch files."""
from pathlib import Path

from mta.application.complete_daily_batch_files import PICK_NAMES
from mta.presentation.context import scope
from mta.presentation.permissions import _sql_equal
from mta.presentation.selective import image_rows
from mta.runtime.validation_storage import read_input


REPORTS = {
    'LogisticPickListReport': PICK_NAMES['logistic'],
    'LogisticRemainingQtySummary': PICK_NAMES['remaining_summary'],
    'LogisticRemainingQtyDetails': PICK_NAMES['remaining_details'],
    'TransportReqSummaryRpt': PICK_NAMES['transport_summary'],
}
FORMED_REPORTS = frozenset(('LogisticPickListReport', 'TransportReqSummaryRpt'))


class PickDownloadDenied(ValueError):
    pass


def _complete_state(run):
    state = {}
    for name in ('LogisticPickList', 'PickListDataForTruckFormation'):
        state[name] = image_rows(run, 'closing/complete/' + name)
    return state


def _attributes(run):
    return {
        'SkuAttributeData': image_rows(run, 'closing/importer/SkuAttributeData'),
        'LocationAttributeData': image_rows(run, 'closing/importer/LocationAttributeData'),
    }


def _fully_scoped(run, payload, state, report_name):
    rows = state['LogisticPickList'] if report_name in FORMED_REPORTS else \
        state['PickListDataForTruckFormation']
    products, locations = scope(payload, attributes=_attributes(run))
    required_products = [row.get('SKUCode') for row in rows]
    required_locations = [row.get(field) for row in rows
                          for field in ('WHCode', 'ParentWHCode', 'LogisticLocation')]
    return (all(any(_sql_equal(required, granted) for granted in products)
                for required in required_products)
            and all(any(_sql_equal(required, granted) for granted in locations)
                    for required in required_locations))


def _expected_bytes(state, report_name):
    from mta.application.complete_daily_batch_files import reports_from_pick_state, sqlcmd_bytes
    kind = next(kind for kind, filename in PICK_NAMES.items()
                if filename == REPORTS[report_name])
    return sqlcmd_bytes(reports_from_pick_state(state)[kind]['resultsets'])


def _owned_file(run, filename):
    raw = read_input(run, components=('pick_output_root',))
    root_value = raw.get('pick_output_root')
    if not isinstance(root_value, str) or not root_value:
        raise PickDownloadDenied('selected_run_pick_output_root_unavailable')
    try:
        root = Path(root_value)
        if root.is_symlink():
            raise PickDownloadDenied('selected_run_pick_path_denied')
        root = root.resolve(strict=True)
        attempt = root / str(run.pk)
        download = attempt / 'download'
        target = download / filename
        if any(path.is_symlink() for path in (attempt, download, target)):
            raise PickDownloadDenied('selected_run_pick_path_denied')
        attempt_resolved = attempt.resolve(strict=True)
        download_resolved = download.resolve(strict=True)
        target_resolved = target.resolve(strict=True)
    except PickDownloadDenied:
        raise
    except (OSError, RuntimeError) as error:
        raise PickDownloadDenied('selected_run_pick_file_unavailable') from error
    if (attempt_resolved.parent != root or download_resolved.parent != attempt_resolved
            or target_resolved.parent != download_resolved or not target_resolved.is_file()):
        raise PickDownloadDenied('selected_run_pick_path_denied')
    return target_resolved


def open_report(run, payload, report_name):
    filename = REPORTS.get(report_name)
    if filename is None:
        raise PickDownloadDenied('unknown_pick_report')
    if getattr(run, 'kind', None) != 'DAILY_CHAIN' or getattr(run, 'status', None) != 'SUCCEEDED':
        raise PickDownloadDenied('selected_run_pick_status_denied')
    state = _complete_state(run)
    if not _fully_scoped(run, payload, state, report_name):
        raise PickDownloadDenied('selected_run_pick_scope_denied')
    path = _owned_file(run, filename)
    stream = path.open('rb')
    if stream.read() != _expected_bytes(state, report_name):
        stream.close()
        raise PickDownloadDenied('selected_run_pick_file_drift')
    stream.seek(0)
    return stream, filename
