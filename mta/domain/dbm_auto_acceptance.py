"""Computed end-of-day acceptance queue; master changes belong to the next date."""
from copy import deepcopy
from datetime import date
from mta.domain.complete_daily_scalars import ascii_equal


def automatic_acceptance(today, state):
    today = date.fromisoformat(today) if type(today) is str else today
    if type(today) is not date or state['LastBatchRunTbl'] != [{'LastRunDate': today.isoformat()+'T00:00:00'}]:
        raise ValueError('Automatic acceptance requires singleton midnight business date')
    rows = []
    for suggestion in state['Suggestions']:
        # NULL is excluded by the source NOT IN predicate. Other integer types
        # are permitted; this is deliberately not a whitelist of types 1–6.
        if suggestion['Type'] is None or suggestion['Type'] in (7, 8, 9, 10, 11, 12):
            continue
        for master in state['DBMMaster']:
            if (ascii_equal(suggestion['SKUCode'], master['SKUCode'])
                    and ascii_equal(suggestion['WhCode'], master['WhCode'])):
                row = dict(SKUCode=suggestion['SKUCode'], WhCode=suggestion['WhCode'],
                    AcceptanceDate=today.isoformat(), OldNorm=master['Norm'], NewNorm=suggestion['NewNorm'])
                # The complete INSERT targets NOT NULL signed32 Norms and
                # NVARCHAR(50) identifiers. Deny the entire computation rather
                # than filter a row or publish a partially insertable queue.
                if any(type(row[name]) is not int or not -(2**31) <= row[name] < 2**31
                       for name in ('OldNorm', 'NewNorm')):
                    raise ValueError('Automatic acceptance requires NOT NULL signed32 Norms')
                if any('\0' in row[name] or len(row[name].encode('utf-16-le')) > 100
                       for name in ('SKUCode', 'WhCode')):
                    raise ValueError('Automatic acceptance identifier target width differs')
                rows.append(row)
    result = deepcopy(state)
    result['NormAcceptanceTbl'] = rows
    return result
