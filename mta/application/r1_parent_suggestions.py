"""R1-02/04 InsertParentOrderTypeSuggestions before UpdateAcceptedNorms.

The current accepted feed is imported later by UpdateAcceptedNorms; propagation
here starts from the existing NormAcceptanceTbl, exactly as the batch does.
"""
from copy import deepcopy
from decimal import Decimal, ROUND_CEILING
from mta.application.r1_norm_updates import key

ACCEPTED_FIELDS = {
    'accepted': ('SKUCode','WhCode'),
    'suggestions': ('SKUCode','WhCode','Type','NewNorm'),
    'acceptance': ('SKUCode','WhCode','AcceptanceDate','OldNorm','NewNorm'),
    'reason_codes': ('Id','Reason'),
    'suggestions_log': ('SKUCode','WhCode','Type','OldNorm','NewNorm','SuggestionDate'),
    'order_summary': ('SKUCode','WhCode','NodeOrderCount','CummOrderCount','NodeConsumption','ImportDate'),
    'suspend_order_type': ('SKUCode','WhCode','RedEnabled','GreenEnabled','RedResumeDate','GreenResumeDate','SuggestionStartDate'),
}
ACCEPTED_STATE_FIELDS = {**ACCEPTED_FIELDS,
    'log': ('SKUCode','WhCode','OldNorm','NewNorm','NormChangeDate','NormChangeReason')}


def accepted_checkpoint(state):
    import json
    return [dict(table=name, rows=sorted([{f:r[f] for f in fields} for r in state[name]],
                                        key=lambda r: json.dumps(r,sort_keys=True)))
            for name,fields in ACCEPTED_STATE_FIELDS.items()]


def validate_accepted_input(source, business_date):
    from datetime import date
    if not isinstance(source, dict) or set(source) != set(ACCEPTED_FIELDS) | {'opening_date'}:
        raise ValueError('Invalid accepted-Norm source contract')
    opening = date.fromisoformat(source['opening_date'])
    if opening >= date.fromisoformat(business_date):
        raise ValueError('Suggestion opening must precede business date')
    text = {'SKUCode','WhCode','Reason'}
    dates = {'AcceptanceDate','SuggestionDate','ImportDate','RedResumeDate','GreenResumeDate','SuggestionStartDate'}
    for name, fields in ACCEPTED_FIELDS.items():
        if not isinstance(source[name], list):
            raise ValueError('Accepted-Norm source tables must be lists')
        for row in source[name]:
            if not isinstance(row,dict) or set(row) != set(fields):
                raise ValueError('Invalid accepted-Norm row: ' + name)
            for field,value in row.items():
                if field in text:
                    if not isinstance(value,str) or not value.strip():
                        raise ValueError('Nonblank accepted-Norm identity/text required')
                elif field in dates:
                    if value is not None:
                        parsed = date.fromisoformat(value)
                        if field in {'AcceptanceDate','SuggestionDate','ImportDate'} and parsed > opening:
                            raise ValueError('Cannot seed current-day acceptance/suggestion history')
                elif type(value) is not int or not -2147483648 <= value <= 2147483647:
                    raise ValueError('Accepted-Norm numeric input must be SQL integer')


def insert_parent_suggestions(state, day):
    out = deepcopy(state)
    masters = {key(r): r for r in out['dbm_master']}
    if len(masters) != len(out['dbm_master']):
        raise ValueError('Ambiguous DBM master key')
    pending = [dict(SKUCode=a['SKUCode'], WhCode=a['WhCode'], NewNorm=a['NewNorm'])
               for a in out['acceptance'] for s in out['suggestions'] if key(a) == key(s) and s['Type'] == 7]
    hierarchy = dict(masters)
    count = 0
    while hierarchy and count < 100:
        parents = {key(dict(SKUCode=r['SKUCode'], WhCode=r['ParentWhCode']))
                   for r in hierarchy.values() if r['ParentWhCode'] is not None}
        leaves = set(hierarchy) - parents
        existing = {key(r) for r in pending}
        additions = {}
        for k in leaves & existing:
            row = hierarchy[k]
            if row['ParentWhCode'] is not None:
                parent = key(dict(SKUCode=row['SKUCode'], WhCode=row['ParentWhCode']))
                if parent in masters and parent not in existing and masters[parent]['Norm'] == 0:
                    additions[parent] = dict(SKUCode=masters[parent]['SKUCode'], WhCode=masters[parent]['WhCode'], NewNorm=1)
        pending.extend(additions.values())
        hierarchy = {k:r for k,r in hierarchy.items() if k not in leaves}
        count += 1
    if count >= 100:
        # Canonical early return: no generated suggestion/acceptance mutations.
        return out
    accepted_keys = {key(r) for r in out['acceptance']}
    pending_keys = {key(r) for r in pending}
    for suggestion in out['suggestions']:
        if key(suggestion) in pending_keys - accepted_keys and suggestion['Type'] == 7:
            suggestion['Type'] = 8
    existing = {key(r) for r in out['suggestions']}
    suspended = {key(r) for r in out['suspend_order_type'] if r['RedEnabled'] == 0}
    pending = [r for r in pending if key(r) not in existing | suspended]
    dates = [r['SuggestionDate'] for r in out['suggestions_log'] if r['SuggestionDate'] is not None]
    yesterday = max(dates) if dates else None
    for row in pending:
        summaries = [r for r in out['order_summary'] if key(r) == key(row)
                     and yesterday is not None and r['ImportDate'] == yesterday]
        if len(summaries) > 1:
            raise ValueError('Canonical duplicate order-summary UPDATE; no invented winner')
        if summaries:
            summary = summaries[0]
            row['NewNorm'] = int((Decimal(summary['NodeConsumption']) / Decimal(summary['NodeOrderCount'])).to_integral_value(rounding=ROUND_CEILING)) if summary['NodeConsumption'] and summary['NodeOrderCount'] else 1
    out['suggestions'].extend(dict(r, Type=9) for r in pending)
    out['acceptance'].extend(dict(SKUCode=r['SKUCode'], WhCode=r['WhCode'], AcceptanceDate=day,
                                 OldNorm=masters[key(r)]['Norm'], NewNorm=r['NewNorm'])
                             for r in out['suggestions'] if r['Type'] in (8,9) and key(r) in masters)
    return out
