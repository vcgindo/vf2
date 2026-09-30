"""Complete-row temporal comparisons; never normalize business values.

Structural/bag fingerprint semantics retained from 66a7773,
parity/block3_sizeable_evidence.py. No old execution/runtime is imported.
"""
from collections import Counter
from copy import deepcopy
import hashlib
import json

BOUNDARIES = ('controls', 'final-bpr-bluezone', 'dbm-imported', 'final-suspensions',
              'final-suggestions', 'post-rule-reports', 'btr-insights', 'closing-state')


def fingerprint(value, path=''):
    if path.endswith('/IntermediateTables'):
        value = {r['table']: r['rows'] for r in value} if isinstance(value, list) else value
    if isinstance(value, dict):
        encoded = ['dict', [[name, fingerprint(value[name], path + '/' + name)] for name in sorted(value)]]
    elif isinstance(value, list) and all(isinstance(row, dict) for row in value):
        rows = Counter(json.dumps(row, sort_keys=True, separators=(',', ':')) for row in value)
        encoded = ['dict-bag', sorted(rows.items())]
    else:
        encoded = [type(value).__name__, value]
    return hashlib.sha256(json.dumps(encoded, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def differences(expected, actual, path=''):
    if path.endswith('/IntermediateTables'):
        expected = {r['table']: r['rows'] for r in expected} if isinstance(expected, list) else expected
        actual = {r['table']: r['rows'] for r in actual} if isinstance(actual, list) else actual
    if isinstance(expected, dict) and isinstance(actual, dict):
        result = []
        for name in sorted(set(expected) | set(actual)):
            where = path + '/' + name
            if name not in expected or name not in actual:
                result.append(dict(path=where, missing_side='legacy' if name not in expected else 'modern'))
            else:
                result.extend(differences(expected[name], actual[name], where))
        return result
    if isinstance(expected, list) and isinstance(actual, list) and all(isinstance(r, dict) for r in expected + actual):
        encode = lambda rows: Counter(json.dumps(r, sort_keys=True, separators=(',', ':')) for r in rows)
        left, right = encode(expected), encode(actual)
        return [] if left == right else [dict(path=path, missing=list((left-right).items()), extra=list((right-left).items()))]
    return [] if type(expected) is type(actual) and expected == actual else [dict(path=path, legacy=expected, modern=actual)]


def legacy_states(result):
    native = deepcopy(result['delivery']['boundaries'])
    late = result['output']['BPRStages'][-1]['state']
    native['final-bpr-bluezone'] = dict(BPR_Table=late['BPR_Table'],
        BPRDailyConsumption=late['BPRDailyConsumption'], BPRLastBatchRunTbl=late['LastBatchRunTbl'],
        vf_RationedReqReport=late['vf_RationedReqReport'])
    return {name: native[name] for name in BOUNDARIES}


def command_membership(state, selected):
    """Exact retained SQL action receipt projection, not raw Suggestions shape.

    block3_one_pass.replay_commands selects Suggestions joined to latest log
    and ReasonCodes. Refuse an ambiguous TOP1 rather than invent its ordering.
    """
    result = []
    for suggestion in state['Suggestions']:
        identity = suggestion['SKUCode'], suggestion['WhCode']
        if identity not in selected:
            continue
        logs = [r for r in state['SuggestionsLog'] if
                (r['SKUCode'], r['WhCode']) == identity and r['Type']==suggestion['Type']
                and r['NewNorm']==suggestion['NewNorm']]
        latest = max((r['SuggestionDate'] for r in logs), default=None)
        values = {(r['OldNorm'], r['SuggestionDate']) for r in logs if r['SuggestionDate']==latest}
        if len(values)>1:
            raise ValueError('Legacy TOP1 action receipt has ambiguous latest logs')
        old_norm, suggestion_date = next(iter(values)) if values else (None, None)
        reasons = [r['Reason'] for r in state['ReasonCodes'] if r['Id']==suggestion['Type']] or [None]
        result.extend(dict(suggestion, OldNorm=old_norm, SuggestionDate=suggestion_date, Reason=reason)
                      for reason in reasons)
    return result
