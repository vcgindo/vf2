"""Explicit trial actions, not a replacement DBM algorithm or production mode.

Each engine calls this policy with its OWN persisted computed suggestions.
The retained Sleep events take precedence on their declared day. All other
suggestions are accepted through the real deployed Apply workflow. There is no
threshold, Norm calculation, invented cooling rule or generated external fact.
"""
from datetime import date, datetime

from mta.temporal.action_policy_identity import (
    POLICY, ELIGIBLE_SLEEP_POLICY, POLICIES, require_policy_identity)


def policy_for_case(case):
    return require_policy_identity(case.get('profile', {}))


def commands_for_day(case, index, own_suggestions):
    policy = policy_for_case(case)
    today = case['days'][index]['business_date']
    date.fromisoformat(today)
    keys = [(r['SKUCode'], r.get('WhCode', r.get('WHCode'))) for r in own_suggestions]
    if any(not all(key) for key in keys) or len(keys) != len(set(keys)):
        raise ValueError('Automatic trial requires exactly one own suggestion per identity')
    available = set(keys)
    sleeping = set()
    commands = []
    for event in case['commands']:
        if event['after_day'] != index or event['operation'] != 'SLEEP':
            continue
        if datetime.fromisoformat(event['timestamp']).date().isoformat()!=today:
            raise ValueError('Retained Sleep SQL DATE must equal its declared trial day')
        selected = {tuple(key) for key in event['selected']}
        if policy == ELIGIBLE_SLEEP_POLICY:
            # Approved new-scenario variant. The retained strict policy above
            # still fails on absent targets. Never import the other engine's
            # eligible identities or manufacture a suggestion to enable Sleep.
            selected &= available
            if not selected:
                continue
        if not selected <= available or selected & sleeping:
            raise ValueError('Retained Sleep event lacks unique own suggestions')
        sleeping |= selected
        commands.append({**event, 'selected': [list(key) for key in sorted(selected)]})
    apply = sorted(available - sleeping)
    if apply:
        commands.append(dict(after_day=index, cohort='automatic-own-suggestions',
                             operation='APPLY', selected=[list(key) for key in apply],
                             timestamp=today+'T12:00:00+05:30'))
    return commands
