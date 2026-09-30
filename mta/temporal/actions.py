from copy import deepcopy
from datetime import datetime

def key(row):
    return row['SKUCode'], row.get('WhCode', row.get('WHCode', row.get('LocCode')))

def apply_command(state, operation, selected, timestamp):
    """Exact deployed DBMProcessor writes; both target columns are SQL date."""
    if operation not in ('APPLY', 'SLEEP'):
        raise ValueError('Unsupported DBM command')
    action_date = datetime.fromisoformat(timestamp).date().isoformat()
    selected = set(selected)
    out = deepcopy(state)
    suggestions = [r for r in out['Suggestions'] if key(r) in selected]
    selected_keys = {key(r) for r in suggestions}
    if operation == 'APPLY':
        out['NormAcceptanceTbl'] = [r for r in out['NormAcceptanceTbl'] if key(r) not in selected_keys]
        out['NormAcceptanceTbl'].extend({'SKUCode': s['SKUCode'], 'WhCode': key(s)[1],
            'AcceptanceDate': action_date, 'OldNorm': m['Norm'], 'NewNorm': s['NewNorm']}
            for s in suggestions for m in out['DBMMaster'] if key(s) == key(m))
    else:
        out['NormsInSleepModeTbl'].extend({'SKUCode': r['SKUCode'], 'WhCode': key(r)[1],
                                         'StartDate': action_date} for r in suggestions)
        out['Suggestions'] = [r for r in out['Suggestions'] if key(r) not in selected]
    return out
