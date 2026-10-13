"""Typed configurable DBM report cutoffs; no fixture horizon defaults."""
from datetime import date, timedelta


def horizon_days(horizon):
    if type(horizon) is not int or not -(2 ** 31) <= horizon < 2 ** 31:
        raise ValueError('DBM report horizon must be a signed32-bit integer')
    # The date expression negates the parameter in a signed integer domain.
    if horizon == -(2 ** 31):
        raise ValueError('DBM report horizon date expression overflows')
    return horizon


def report_cutoff(today, state, horizon, *, inclusive):
    today = date.fromisoformat(today) if isinstance(today, str) else today
    if type(today) is not date or state['LastBatchRunTbl'] != [
            {'LastRunDate': today.isoformat() + 'T00:00:00'}]:
        raise ValueError('DBM report requires singleton midnight business date')
    return horizon_cutoff(today, horizon, inclusive=inclusive)


def horizon_cutoff(today, horizon, *, inclusive):
    today = date.fromisoformat(today) if isinstance(today, str) else today
    if type(today) is not date:
        raise ValueError('DBM report business date required')
    horizon_days(horizon)
    try:
        cutoff = today + timedelta(days=-horizon + (1 if inclusive else 0))
    except OverflowError:
        raise ValueError('DBM report cutoff exceeds the date range') from None
    if not inclusive and cutoff < date(1753, 1, 1):
        raise ValueError('DBM history cutoff exceeds the timestamp range')
    return cutoff


def row_date(value):
    return date.fromisoformat(value) if isinstance(value, str) else value
