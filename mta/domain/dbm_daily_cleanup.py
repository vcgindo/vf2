"""Selected DBM daily observation retention, after configured reports."""
from copy import deepcopy
from datetime import date, datetime
from mta.row_sequences import history_rows
from mta.domain.dbm_report_dates import horizon_cutoff


def daily_cleanup(today, state, horizon):
    today = date.fromisoformat(today) if isinstance(today, str) else today
    if isinstance(today, datetime):
        today = today.date()
    if state['LastBatchRunTbl'] != [
        {'LastRunDate': today.isoformat() + 'T00:00:00'}
    ]:
        raise ValueError('DBM cleanup requires singleton midnight date')
    cutoff = horizon_cutoff(today, horizon, inclusive=False)
    output = deepcopy(state)
    output['DailyConsumption'] = history_rows((
        row for row in output['DailyConsumption']
        # SQL DELETE WHERE ReportDate <= cutoff does not delete NULL dates.
        if row['ReportDate'] is None or (date.fromisoformat(row['ReportDate'])
            if isinstance(row['ReportDate'], str) else row['ReportDate']) > cutoff
    ), like=state['DailyConsumption'])
    return output
