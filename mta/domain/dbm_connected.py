"""Fixed ingestion, suspension1–26 and currently available Rules1–6 chain."""
from copy import deepcopy
from mta.domain.dbm_ingestion import ingest_dbm
from mta.domain import dbm_suspensions as s, dbm_rules as r


def connected_stages(today, state, facts, *, _owned=False):
    """Yield actual complete predecessor state; never accept stage answers."""
    current = ingest_dbm(today, state, facts, _owned=_owned)
    yield 'ingestion', current
    current = s.prepare_suspensions(current, _owned=_owned)
    yield 'suspension1-5', current
    steps = (
        s.suspend_introductions, s.apply_accepted_norm_stock,
        s.apply_accepted_norm_consumption, s.apply_forced_norm_stock,
        s.apply_forced_norm_consumption, s.apply_sleep, s.apply_existing_disabled,
        s.apply_spike, s.apply_white, s.apply_supply,
        lambda _, v: s.apply_phaseout_suspension(v),
        lambda _, v: s.apply_phasein_suspension(v),
        lambda _, v: s.apply_seasonality_suspension(v),
        lambda _, v: s.aggregate_order_common(v),
        lambda _, v: s.aggregate_common(v),
        lambda _, v: s.aggregate_stock_family(v),
        lambda _, v: s.aggregate_consumption_family(v),
        lambda d, v: s.finalize_stock_suspensions(d, v, _owned=_owned),
        lambda d, v: s.finalize_consumption_suspensions(d, v, _owned=_owned),
        lambda d, v: s.finalize_order_suspensions(d, v, _owned=_owned),
        lambda d, v: s.suppress_insufficient_data(d, v, _owned=_owned),
    )
    for number, calculate in enumerate(steps, 6):
        current = calculate(today, current)
        yield f'suspension{number}', current
    for number, calculate in enumerate((r.stockout_type_a, r.virtual_stockout,
            r.stockout_type_b, r.too_much_in_red, r.too_much_in_green,
            r.spike_recommendation), 1):
        current = calculate(today, current)
        yield f'rule{number}', current


def calculate_connected(today, state, facts):
    for _, current in connected_stages(today, state, facts):
        pass
    return current
