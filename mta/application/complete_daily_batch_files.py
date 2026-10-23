"""Generic Pick batch files using the retained sqlcmd -s , -h-1 -W contract.

These are literal sqlcmd resultset files, not RFC CSV: delimiters/newlines in
values are not escaped. Current encoding qualification is direct CP1252 text;
Windows best-fit/replacement conversions are not silently approximated.
"""
from decimal import Decimal
from pathlib import Path
import re
import shutil


PICK_NAMES = dict(logistic='LogisticPickListReport.csv',
    remaining_summary='LogisticRemainingQtySummary.csv',
    remaining_details='LogisticRemainingQtyDetails.csv',
    transport_summary='TransportReqSummaryRpt.csv')


class UnqualifiedBatchValue(ValueError):
    pass


def _cell(value, kind):
    if not isinstance(kind, str) or not re.fullmatch(r'n?varchar\(\d+\)|int|decimal\(\d+,\d+\)', kind):
        raise UnqualifiedBatchValue('Unqualified sqlcmd field type: ' + str(kind))
    if value is None:
        return 'NULL'
    if re.fullmatch(r'n?varchar\(\d+\)', kind):
        if not isinstance(value, str):
            raise UnqualifiedBatchValue('Exact native text cell required')
        width = int(kind[kind.index('(')+1:-1])
        if '\0' in value or len(value) > min(width, 256):
            raise UnqualifiedBatchValue('Native text width/display truncation requires qualification')
        return value
    if kind == 'int':
        if type(value) is not int or not -2**31 <= value < 2**31:
            raise UnqualifiedBatchValue('Exact native SQL int cell required')
        return str(value)
    match = re.fullmatch(r'decimal\((\d+),(\d+)\)', kind)
    if match:
        precision, scale = map(int, match.groups())
        if not isinstance(value, Decimal) or not value.is_finite():
            raise UnqualifiedBatchValue('Exact native decimal cell required')
        if value.as_tuple().exponent != -scale or abs(value) >= Decimal(10)**(precision-scale):
            raise UnqualifiedBatchValue('Native decimal precision/scale differs')
        text = format(abs(value) if value == 0 else value, 'f')
        if text.startswith('0.'):
            return text[1:]
        if text.startswith('-0.'):
            return '-' + text[2:]
        return text
    raise UnqualifiedBatchValue('Unqualified sqlcmd field type: ' + kind)


def _sqlcmd_lines(resultsets):
    """Exact header/data resultsets with explicit native CRLF and CP1252.

    Callers supply the header SELECT as a resultset. No headings, quoting,
    trimming, ordering or value substitution is performed here.
    """
    for resultset in resultsets:
        types = resultset['types']
        if len(resultset['fields']) != len(types):
            raise UnqualifiedBatchValue('Resultset column roster differs')
        for row in resultset['rows']:
            if len(row) != len(types):
                raise UnqualifiedBatchValue('Resultset row width differs')
            yield ','.join(_cell(value, kind) for value, kind in zip(row, types, strict=True)) + '\r\n'


def sqlcmd_chunks(resultsets):
    """Exact CP1252 lines for bounded complete-file validation before delivery."""
    try:
        for line in _sqlcmd_lines(resultsets):
            yield line.encode('cp1252')
    except UnicodeEncodeError as error:
        raise UnqualifiedBatchValue('Native Windows best-fit/replacement encoding requires separate qualification') from error


def sqlcmd_bytes(resultsets):
    # Keep the writer's original validate-all-cells, then encode ordering.
    try:
        return ''.join(_sqlcmd_lines(resultsets)).encode('cp1252')
    except UnicodeEncodeError as error:
        raise UnqualifiedBatchValue('Native Windows best-fit/replacement encoding requires separate qualification') from error


def write_pick_reports(reports, *, owned_root, output_folder, download_folder):
    """Retained delete-output/delete-download/write/copy lifecycle per file.

    Caller must bind owned_root to the operational attempt's authorized resource.
    This function neither selects serving output nor turns failure into success.
    """
    if list(reports) != list(PICK_NAMES):
        raise ValueError('Exact ordered four-report roster required')
    root = Path(owned_root).resolve(strict=True)
    folders = [Path(path).resolve(strict=True) for path in (output_folder, download_folder)]
    if not root.is_dir() or any(not p.is_dir() or not p.is_relative_to(root) for p in folders) or folders[0] == folders[1]:
        raise ValueError('Distinct existing output/download folders within owned root required')
    targets = {}
    for kind, name in PICK_NAMES.items():
        pair = [(folder / name) for folder in folders]
        if any(p.is_symlink() or p.resolve().parent != folder for p, folder in zip(pair, folders)):
            raise ValueError('Batch output link or path escapes its owned folder')
        targets[kind] = pair
    completed = []
    for kind, report in reports.items():
        output, download = targets[kind]
        output.unlink(missing_ok=True)
        download.unlink(missing_ok=True)
        payload = sqlcmd_bytes(report['resultsets'])
        with output.open('xb') as stream:
            stream.write(payload)
        shutil.copyfile(output, download)
        completed.append(dict(report=kind, output=str(output), download=str(download)))
    return completed


def reports_from_pick_state(state):
    """Reconstruct file projections from exact native or persisted typed rows.

    Persistence retains Decimal wire values as strings. Restore only declared
    decimal columns; do not coerce NULLs, numeric text fields or integer values.
    No source table may be absent or replaced with an empty population.
    """
    from mta.runtime.complete_daily_state import TABLES
    from mta.application.complete_daily_pick_files import project_reports
    from mta.row_sequences import is_record_rows
    restored = {}
    for name in ('LogisticPickList', 'PickListDataForTruckFormation'):
        fields = TABLES['complete/BPR/' + name]
        rows = state[name]
        if not is_record_rows(rows):
            raise ValueError('Explicit native Pick row population required')
        restored[name] = []
        for row in rows:
            if set(row) != {field for field, _ in fields}:
                raise ValueError('Complete native Pick column roster required: ' + name)
            copy = dict(row)
            for field, kind in fields:
                value = row[field]
                if kind == 'decimal' and value is not None:
                    if not isinstance(value, (str, Decimal)):
                        raise ValueError('Exact persisted decimal wire value required')
                    copy[field] = Decimal(value)
                    if not copy[field].is_finite():
                        raise ValueError('Exact finite persisted decimal wire value required: ' + name + '.' + field)
            restored[name].append(copy)
    return project_reports(logistic_pick_list=restored['LogisticPickList'],
        pick_list_data_for_truck_formation=restored['PickListDataForTruckFormation'])


def write_pick_state(state, **paths):
    """Write the four files from the run's own complete operational state."""
    return write_pick_reports(reports_from_pick_state(state), **paths)


def write_run_pick_files(run_id, state, owned_root):
    """A run owns its directories; failed attempts never replace another run."""
    from uuid import UUID
    identity = str(UUID(str(run_id)))
    root = Path(owned_root).resolve(strict=True)
    if not root.is_dir():
        raise ValueError('Existing owned Pick output root required')
    attempt = root / identity
    if attempt.is_symlink() or attempt.resolve().parent != root:
        raise ValueError('Pick attempt directory escapes its owned root')
    attempt.mkdir(exist_ok=True)
    folders = [attempt / name for name in ('output', 'download')]
    for folder in folders:
        if folder.is_symlink() or folder.resolve().parent != attempt:
            raise ValueError('Pick file directory escapes its attempt')
        folder.mkdir(exist_ok=True)
    return write_pick_state(state, owned_root=attempt, output_folder=folders[0], download_folder=folders[1])
