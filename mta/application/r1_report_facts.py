from decimal import Decimal

def rationed_leftovers(rows, stock, normal_leftovers, pso_leftovers):
    """GenerateRationReqReport's ordered parent/self leftover updates.

    Ambiguous UPDATE-FROM matches are a legacy flaw, not permission to choose
    a min/max or sum. Surface the affected key explicitly.
    """
    parent_values = {}
    candidates = {}
    for row in rows:
        key = (row['SKUCode'], row['WhCode'])
        parent = (row['SKUCode'], row['PWh'])
        value = stock.get(parent, Decimal(0))
        value = normal_leftovers.get(key, value)
        value = pso_leftovers.get(key, value)
        parent_values[key] = value
        candidates.setdefault(parent, set()).add(value)
    result = {}
    for key, parent_value in parent_values.items():
        matches = candidates.get(key, set())
        if len(matches) > 1:
            raise ValueError(f'Legacy ambiguous LeftoverStock UPDATE for {key}: {sorted(matches)}')
        result[key] = (parent_value, next(iter(matches)) if matches else stock.get(key, Decimal(0)))
    return result
