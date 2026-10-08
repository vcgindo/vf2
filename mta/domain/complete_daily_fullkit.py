"""Source-shaped fullkit/date gates; external checks remain explicit inputs.

Authority: CheckRunStartCriteria.bat, CheckForFilesAvailability.bat and
FullkitCheckForPostRun.bat. This module never claims that a filesystem check,
site hook, or sanitizer ran. Their ordered actual results belong to the caller.
Missing settings stay missing; the post-run COUNT=2 quirk is preserved.
"""
from copy import deepcopy
from datetime import date


def _same(left, right, equal):
    return left is not None and right is not None and equal(left, right)


def _day(value):
    if type(value) is not str or date.fromisoformat(value).isoformat() != value:
        raise ValueError('Explicit canonical ISO run date required')
    return value


def initialise_fullkit(settings, critical_files, run_date, *, equal):
    """Initial UPDATEs precede site checks and physical file resolution."""
    run_date = _day(run_date)
    settings, files = deepcopy(settings), deepcopy(critical_files)
    for row in settings:
        if _same(row['Parameter'], 'FullkitAvailable', equal):
            row['Value'] = '1'
        elif _same(row['Parameter'], 'FullkitCheckdate', equal):
            row['Value'] = run_date
    for row in files:
        row.update(Exists=False, ResolvedPath=None, ResolvedFileName=None)
    return dict(ImporterSettingsTbl=settings, CriticalFiles=files)


def file_availability(critical_files, file_type, *, previous, equal):
    """Native count after real resolver/existence writes, preserving NULLs.

    The BAT only changes its cumulative flag to zero. A later successful type
    must not erase an earlier missing GoAheadFiles result.
    """
    if file_type not in ('GoAheadFiles', 'DataFiles') or type(previous) is not bool:
        raise ValueError('Explicit supported file check and prior flag required')
    missing = sum(_same(row['Type'], file_type, equal) and row['Exists'] == 0
                  for row in critical_files)
    return dict(missing_count=missing, files_available=previous and missing == 0)


def unavailable_file_reasons(opening, critical_files, file_type, run_datetime, *, equal):
    """GetUnavailableFiles.sql INSERT from explicitly resolved file rows.

    This does not resolve paths or run a client hook. Preserve existing history,
    duplicate occurrences and SQL NULL-concatenation failure; no default opening.
    A failed INSERT contributes no partial rows.
    """
    from mta.domain.complete_daily_scalars import parse_datetime
    if not isinstance(opening, list) or not isinstance(critical_files, list):
        raise ValueError('Explicit abort-reason opening and resolved files required')
    if file_type not in ('GoAheadFiles', 'DataFiles'):
        raise ValueError('Explicit supported file check required')
    clock = parse_datetime(run_datetime).isoformat(timespec='milliseconds')
    added = []
    for row in critical_files:
        if not (_same(row['Type'], file_type, equal) and row['Exists'] == 0):
            continue
        name, path = row['ResolvedFileName'], row['ResolvedPath']
        if name is None or path is None:
            raise ValueError('Native RunAbortReasons.Reason NOT NULL violation')
        reason = f'File "{name}" is not present at Location "{path}".'
        if len(reason.encode('utf-16-le')) // 2 > 512:
            raise ValueError('Native RunAbortReasons.Reason truncation')
        file_id = row['Id']
        if type(file_id) is not int or not -(2**31) <= file_id < 2**31:
            raise ValueError('Native RunAbortReasons.FileId requires SQL int')
        added.append(dict(FileId=file_id, RunDateTime=clock, Reason=reason))
    return deepcopy(opening) + added


def fullkit_outcome(settings, *, go_ahead, files_available,
                    daily_data_available, equal):
    """Final BAT outcome from actual explicit hook/file/database checks."""
    checks = (go_ahead, files_available, daily_data_available)
    if any(type(value) is not bool for value in checks):
        raise ValueError('Actual fullkit boolean check results required')
    settings = deepcopy(settings)
    abort = not all(checks)
    if abort:
        for row in settings:
            if _same(row['Parameter'], 'FullkitAvailable', equal):
                row['Value'] = '0'
    return dict(ImporterSettingsTbl=settings, AbortRun=abort,
                daily_unavailability_alert_required=abort)


def post_run_fullkit(settings, run_date, *, scope, equal):
    """Exact retained post-run COUNT, not an invented two-key EXISTS check."""
    run_date = _day(run_date)
    if not isinstance(scope, str):
        raise ValueError('Explicit BAT scope required')
    if scope in ('UptoBPR', 'UptoDBM', ''):
        return dict(checked=False, matching_count=None, AbortPostRun=False)
    count = sum((_same(row['Parameter'], 'FullkitAvailable', equal)
                 and _same(row['Value'], '1', equal))
                or (_same(row['Parameter'], 'FullkitCheckdate', equal)
                    and _same(row['Value'], run_date, equal)) for row in settings)
    return dict(checked=True, matching_count=count, AbortPostRun=count != 2)
