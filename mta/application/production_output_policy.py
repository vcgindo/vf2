"""Explicit approved production output amendments; never legacy-parity defaults."""
from copy import deepcopy
from datetime import date, timedelta

from mta.application import operational_bor

SCHEMA = 'fresh-production-output-contract-v1'
# Source-only version: no Guided history or UI configuration admission.
SOURCE_SCHEMA = 'fresh-production-source-inputs-bor-v1'
from mta.application.production_bor_contract import POLICY as BOR_POLICY
TEXT_POLICY = 'boroa-supplier-text-null-availability-v1'
ATTRIBUTES = tuple(f'SKULocAtt{i:02}' for i in range(1, 16))


def contract():
    return {'schema': SCHEMA, 'normal_bor': BOR_POLICY,
            'boroa_text': {'policy': TEXT_POLICY, 'fields': list(ATTRIBUTES),
                          'type': 'nullable-nvarchar50',
                          'qualification': 'APPROVED_NULL_AVAILABILITY_NOT_LEGACY_PARITY'}}


def require(value):
    if value != contract():
        raise ValueError('Exact approved production output contract required')
    return value


def bor_oa(rows, policy):
    """Retain known text; only the explicitly allowed absent fields become NULL."""
    require(policy)
    core = tuple(c['name'] for c in operational_bor.NATIVE_SCHEMAS['BORWithOrderAllocation'])
    result = []
    for row in rows:
        if not isinstance(row, dict) or not set(core) <= set(row) or set(row) - set(core) - set(ATTRIBUTES):
            raise ValueError('BOROA core/source field roster differs')
        base = {name: deepcopy(row[name]) for name in core}
        operational_bor._validate_native([base], 'BORWithOrderAllocation')
        for name in ATTRIBUTES:
            value = row.get(name)
            if value is not None and (not isinstance(value, str) or len(value.encode('utf-16-le')) > 100):
                raise ValueError('BOROA supplier attribute must be nullable nvarchar50: ' + name)
            base[name] = value
        result.append(base)
    return result


def bor_oa_history(*, opening, current, business_date, horizon, policy):
    require(policy)
    core = tuple(c['name'] for c in operational_bor.NATIVE_SCHEMAS['BORWithOrderAllocation'])
    # Run the existing history contract on the core projection, then prove that
    # carrying the approved text columns preserves its exact ordered result.
    prior = []
    for row in opening:
        if 'ReportDate' not in row or set(row) != set(core) | set(ATTRIBUTES) | {'ReportDate'}:
            raise ValueError('Own predecessor full BOROA history required')
        value = bor_oa([{key: item for key, item in row.items() if key != 'ReportDate'}], policy)[0]
        prior.append(dict(value, ReportDate=row['ReportDate']))
    present = bor_oa(current, policy)
    projected = lambda rows, historical: [
        {name: row[name] for name in (*core, 'ReportDate') if historical or name != 'ReportDate'}
        for row in rows]
    expected = operational_bor.collect_bor_order_allocation_history(
        opening_history=projected(prior, True), current_bor=projected(present, False),
        business_date=business_date, horizon=horizon)
    today = date.fromisoformat(business_date)
    cutoff = today - timedelta(days=operational_bor._int(horizon))
    result = [deepcopy(row) for row in prior
              if date.fromisoformat(row['ReportDate']) != today and date.fromisoformat(row['ReportDate']) > cutoff]
    result.extend(dict(deepcopy(row), ReportDate=business_date) for row in present)
    if projected(result, True) != expected:
        raise ValueError('BOROA history core semantics changed')
    return result
