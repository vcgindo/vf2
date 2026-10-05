"""Evidence-only April7 Expedite ordering exception approved 5 October 2026."""
from collections import Counter
import json

RUN = 'bfd75b4b-a9df-4a08-82d3-852e3324b623'
SOURCE = '4cbef69cbe8d75d64e5e9cdfc5b023d31770c318214c01c1d29912b6509a3f73'
KEYS = {('parent','critical'):(), ('child','critical'):(),
        ('parent','receiving'):('ParentwiseCount','MaxPipelineInv'),
        ('child','receiving'):('ParentwiseCount','MaxPipelineInv'),
        ('parent','nil_stock'):('counts',), ('parent','chronic'):('counts',)}


def compare(legacy, fresh, *, run_id, source_digest, business_date, kind, family):
    """Preserve all fields/types/duplicates and every explicit descending key.

    Never used by serving readers. Original arrays belong in retained evidence.
    This does not authorize sorting responses or transfer to another fixture.
    """
    if (run_id, source_digest, business_date) != (RUN, SOURCE, '2026-04-07') or (kind,family) not in KEYS:
        raise ValueError('Expedite order exception does not cover this boundary')
    keys = KEYS[kind,family]
    encode = lambda row: json.dumps(row, sort_keys=True, ensure_ascii=False, allow_nan=False)
    key = lambda row: tuple(row[name] for name in keys)
    for rows in (legacy,fresh):
        if keys and [key(row) for row in rows] != sorted([key(row) for row in rows],reverse=True):
            return dict(status='FAIL',reason='explicit_order')
    if Counter(map(encode,legacy)) != Counter(map(encode,fresh)):
        return dict(status='FAIL',reason='values_types_or_multiplicity')
    # Equal full-row bags plus ordered key sequences guarantee equal bags within
    # each key group; no row can cross an explicit key boundary unnoticed.
    strict = [encode(row) for row in legacy] == [encode(row) for row in fresh]
    return dict(status='PASS_STRICT' if strict else 'PASS_APPROVED_ORDER_EXCEPTION',
                explicit_order_keys=list(keys),rows=len(legacy),strict_equal=strict)
