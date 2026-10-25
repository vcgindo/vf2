"""New scoped runs accept allocation histories with their BPR snapshot.

This adapter has no independent writer or late-completion owner. Its result is
passed to the existing atomic BPR acceptance and inherited unchanged by DBM.
The retained PostBPR run's separately approved completion stays separate.
"""
from dataclasses import replace

from mta.application import operational_bor, production_output_policy
from mta.application.stage_calculation_sources import CalculationSources

NAMES = ('BOR_OrderAllocationHistory', 'RRR_OrderAllocationHistory')


def project(values, history, *, business_date, policy, source_schema):
    from mta.application.production_source_inputs import SCHEMA
    if source_schema not in (SCHEMA, production_output_policy.SOURCE_SCHEMA):
        raise ValueError('Explicit scoped allocation-history source schema required')
    if not isinstance(history, dict) or set(history) != set(NAMES):
        raise ValueError('Complete owned allocation-history opening required')
    if not isinstance(values, dict) or set(NAMES) & set(values):
        raise ValueError('BPR history must be produced once with its current populations')
    if not isinstance(policy, dict) or not {'bor_history_horizon', 'rrr_history_horizon'} <= set(policy):
        raise ValueError('Explicit allocation-history horizons required')
    if source_schema == production_output_policy.SOURCE_SCHEMA:
        bor = production_output_policy.bor_oa_history(
            opening=history[NAMES[0]], current=values['BORWithOrderAllocation'],
            business_date=business_date, horizon=policy['bor_history_horizon'],
            policy=policy['output_contract'])
    else:
        bor = operational_bor.collect_bor_order_allocation_history(
            opening_history=history[NAMES[0]], current_bor=values['BORWithOrderAllocation'],
            business_date=business_date, horizon=policy['bor_history_horizon'])
    rrr = operational_bor.collect_rrr_order_allocation_history(
        opening_history=history[NAMES[1]], current_rrr=values['RRR_OrderAllocation'],
        business_date=business_date, horizon=policy['rrr_history_horizon'])
    return dict(values, **{NAMES[0]: bor, NAMES[1]: rrr})


def complete_sources(run, sources, opening):
    """Read only this run's declared opening; persist via BPR acceptance later."""
    if type(sources) is not CalculationSources or sources.production_reports is None:
        raise ValueError('Scoped BPR allocation populations are required')
    initial = opening['production_report_opening']
    if run.predecessor_id is None:
        if initial != {name: [] for name in NAMES}:
            raise ValueError('Explicit fresh allocation-history opening required')
        history = initial
    else:
        if initial is not None:
            raise ValueError('Scoped history must use its own persisted predecessor')
        parent = run.predecessor
        if parent.status != 'SUCCEEDED' or parent.business_date >= run.business_date:
            raise ValueError('Scoped history requires its completed prior day')
        from mta.runtime.production_report_storage import read
        # read() verifies the predecessor root and exact published image owner;
        # unavailable history is not an empty opening.
        history = {name: read(parent, name) for name in NAMES}
    values = project(sources.production_reports, history,
        business_date=run.business_date.isoformat(),
        policy=opening['production_report_policy'],
        source_schema=opening['production_report_schema'])
    return replace(sources, production_reports=values)
