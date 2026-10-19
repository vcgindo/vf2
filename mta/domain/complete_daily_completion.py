"""Explicit-population canonical completion and BPR retention operations.

These pure producers do not certify execution of another producer. Flag updates
must be called at the actual native statement position by the complete-day owner.
Native collation and datetime conversion are explicit adapters. No missing row
is inserted to make a completion gate pass. SQL error/CATCH durability is owned
by the invoking engine; these functions expose conversion failures.
"""
from copy import deepcopy
from datetime import date, datetime, time, timedelta
from mta.row_sequences import history_rows


def _eq(left, right, equal):
    return left is not None and right is not None and equal(left, right)


def _mark(rows, script_name, equal):
    for row in rows:
        if _eq(row['ScriptName'], script_name, equal):
            row['IsScriptExecuted'] = True


def mark_script_executed(flags, script_name, *, equal):
    """The pinned ScriptExecutionFlagQuery UPDATE; does not add missing flags."""
    result = deepcopy(flags)
    _mark(result, script_name, equal)
    return result


def reset_batch_flags(flags, settings, run_datetime, *, equal, format_datetime):
    """ResetBatchExecutionFlag.sql, including its final literal flag marker."""
    flags, settings = deepcopy(flags), deepcopy(settings)
    for row in flags:
        row['IsScriptExecuted'] = False
    for row in settings:
        if any(_eq(row['Parameter'], name, equal) for name in
               ('IsBatchFileExecuted', 'IsBPRBatchFileExecuted')):
            row['Value'] = '0'
        elif _eq(row['Parameter'], 'BatchFileExecutionDate', equal):
            row['Value'] = format_datetime(run_datetime)
    _mark(flags, 'ResetBatchExecutionFlag.sql', equal)
    return {'ScriptExecutedFlag': flags, 'ImporterSettingsTbl': settings}


def validate_batch_flags(flags, settings, run_datetime, *, kind, equal, parse_datetime):
    """Native EXISTS logic; optional/NULL flags and duplicate rows stay native.

    The BPR script really marks 'ValidateBPRBatchExecutionFlags' without '.sql'.
    Preserve that spelling, even if it matches no seeded row.
    """
    if kind not in ('BPR', 'ALL'):
        raise ValueError('Explicit BPR or ALL completion boundary required')
    flags, settings = deepcopy(flags), deepcopy(settings)
    marker = 'ValidateBPRBatchExecutionFlags' if kind == 'BPR' else 'ValidateBatchExecutionFlags.sql'
    parameter = 'IsBPRBatchFileExecuted' if kind == 'BPR' else 'IsBatchFileExecuted'
    _mark(flags, marker, equal)
    current = any(row['Value'] is not None and parse_datetime(row['Value']) == run_datetime
                  for row in settings if _eq(row['Parameter'], 'BatchFileExecutionDate', equal))
    missing = any(row['IsScriptCritical'] == 1 and row['IsScriptExecuted'] == 0
                  and (kind == 'ALL' or _eq(row['ModuleName'], 'BPR', equal)) for row in flags)
    for row in settings:
        if _eq(row['Parameter'], parameter, equal):
            row['Value'] = '1' if current and not missing else '0'
    return {'ScriptExecutedFlag': flags, 'ImporterSettingsTbl': settings}


def clear_failed_bpr_reports(populations):
    """Canonical four-table failure effects, for legacy compatibility proof only.

    Modern failed-candidate admission uses its approved rollback disposition;
    this function is not permission to clear previously published modern data.
    """
    result = deepcopy(populations)
    for name in ('BPR_Table', 'SupplierDispatchReq', 'vf_PickListReport', 'vf_RationedReqReport'):
        if name not in result:
            raise ValueError('Required BPR failure population absent: ' + name)
        result[name] = []
    return result


def sanitation_failure_count(rows, *, equal):
    """BAT predicate only. An explicitly empty table is not sanitizer success."""
    return sum(any(_eq(row[field], value, equal)
                   for field in ('Critical_Flag', 'Non_Critical_Flag')
                   for value in ('Partial', 'False')) for row in rows)


def _typed_datetime(value):
    if isinstance(value, datetime):
        if value.tzinfo is not None:
            raise ValueError('SQL datetime is timezone-naive')
        return value
    if isinstance(value, date):
        return datetime.combine(value, time())
    if isinstance(value, str):
        return _typed_datetime(datetime.fromisoformat(value))
    raise ValueError('Typed SQL date/datetime value required')


def prune_bpr_history(populations, last_batch_run, *, consumption_days, remark_days):
    """ClearHistoryData_BPR.sql inclusive midnight cutoff, with SQL NULL rules.

    SQL's scalar SELECT rejects multiple rows, even when their dates are equal.
    An empty or NULL scalar produces no deletion. Remarks later on the cutoff
    date survive because datetime > the date converted to midnight.
    """
    if len(last_batch_run) > 1:
        raise ValueError('SCALAR_SUBQUERY_MULTIPLE_ROWS: LastBatchRunTbl')
    for value in (consumption_days, remark_days):
        if type(value) is not int or not -2147483648 <= value <= 2147483647:
            raise ValueError('Typed SQL int horizon required')
    spec = (('DailyConsumption', 'ReportDate', consumption_days),
            ('BPRReport_RemarkDetails', 'RemarkDate', remark_days),
            ('OpenExpeditRequestRemarksHistory', 'RemarkDate', remark_days),
            ('InTransitWhereAboutsRemarks', 'RemarksDate', remark_days))
    if any(name not in populations for name, _, _ in spec):
        raise ValueError('Complete BPR history populations required; missing is not empty')
    result = deepcopy(populations)
    today = last_batch_run[0]['LastRunDate'] if last_batch_run else None
    if today is None:
        return result
    today = _typed_datetime(today).date()
    for name, field, horizon in spec:
        cutoff = datetime.combine(today - timedelta(days=horizon), time())
        result[name] = history_rows((row for row in result[name]
                        if row[field] is None or _typed_datetime(row[field]) > cutoff),
                        like=populations[name])
    return result
