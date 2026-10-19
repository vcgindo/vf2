"""Selected DBM daily observation retention, after configured reports."""
from copy import deepcopy
from datetime import date, datetime, timedelta
from mta.row_sequences import history_rows


def daily_cleanup(today, state, horizon):
    today = date.fromisoformat(today) if isinstance(today, str) else today
    if isinstance(today, datetime):
        today = today.date()
    if horizon != 370 or state['LastBatchRunTbl'] != [
        {'LastRunDate': today.isoformat() + 'T00:00:00'}
    ]:
        raise ValueError('Selected cleanup requires horizon370 and singleton midnight date')
    cutoff = today - timedelta(days=horizon)
    output = deepcopy(state)
    output['DailyConsumption'] = history_rows((
        row for row in output['DailyConsumption']
        if (date.fromisoformat(row['ReportDate'])
            if isinstance(row['ReportDate'], str) else row['ReportDate']) > cutoff
    ), like=state['DailyConsumption'])
    return output
