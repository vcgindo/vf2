"""One pure input-to-output current-day MTA calculation; no ORM or oracle reads."""
from copy import deepcopy
from dataclasses import dataclass, replace
from decimal import Decimal

from mta.application.r1_input import (
    _consume_r1_operation_context,
    prepare_r1_current_day,
    prepare_owned_order_current_day,
)
from mta.application.stage_observation import stage
from mta.application.r1_calculation import calculate_r1_requirements
from mta.application.r1_supplier_input import sorted_rows
from mta.application.r1_importer_master import _sql_key
from mta.application.rrr import calculate_rrr_groups
from mta.domain.r1_current_day import allocate_spike_pso
from mta.serialization import storage, digest
from mta.planning.projections import (
    _as_json, _pso_inputs, _bifurcation_rows, _bpp_order_rows,
    _requirement_band_rows, _source_bor_rows, _pick_rows,
)

CURRENT_DAY_OUTPUTS = (
    'r1_additional_master', 'r1_stock_balance', 'r1_order_route', 'r1_order_bpp',
    'r1_advance_stock_allocation', 'r1_git_advance_allocation', 'r1_requirement_band',
    'r1_pso_ration', 'r1_requirement', 'r1_normal_ration', 'r1_ration_bifurcation',
    'r1_bor', 'r1_bor_oa', 'r1_pick_list', 'r1_pick_remaining',
)
MASTER_OUTPUTS = tuple('r1_' + n for n in (
    'dbm_master', 'importer_master', 'norm_change_export', 'norm_change_export_remaining', 'bpr_master'))


@dataclass(frozen=True)
class NormalAllocation:
    sku_id: str
    location_code: str
    parent_location_id: str
    final_quantity: Decimal
    requirement_quantity: Decimal
    remaining_parent_stock: Decimal
    is_virtual: bool

    @classmethod
    def from_row(cls, row):
        return cls(row['sku_code'], row['location_code'], row['parent_location_code'],
                   Decimal(row['final_quantity']), Decimal(row['requirement']),
                   Decimal(row['remaining_parent_stock']), row['virtual'])


def calculate_current_day(raw, *, defer_pick=False, _owned_order_closing=None,
                          _owned_daily_stock=None, _production_sources=False,
                          _owned_r1_context=None):
    """Consume validated external facts and return every produced checkpoint.

Caller cannot supply bands, calculated stock, ration or current-day answers.
Raw producer/control checkpoints remain visible, not silently flattened into
processed-input coverage. Legacy undefined branches retain their guards.
"""
    adapter = None
    if raw.get('schema') == 'r1-gulfoil-file-input-v1':
        from mta.application.r1_gulfoil_input import prepare_gulfoil_standard_input
        raw, adapter = prepare_gulfoil_standard_input(raw)
    if _owned_r1_context is not None and _owned_order_closing is None:
        raise ValueError('Owned R1 preparation context requires its connected order owner')
    with stage('r1_dependency_order_routing'):
        if _owned_r1_context is not None:
            prepared = _consume_r1_operation_context(_owned_r1_context, raw, _owned_order_closing)
        else:
            prepared = (prepare_r1_current_day(raw) if _owned_order_closing is None else
                        prepare_owned_order_current_day(raw, _owned_order_closing))
    if _owned_daily_stock is not None:
        if _owned_order_closing is None:
            raise ValueError('Native daily stock requires its connected order/day owner')
        from mta.application.r1_daily_entry import native_auxiliary_stock_balances
        owned = _owned_daily_stock
        auxiliary = native_auxiliary_stock_balances(owned['daily_consumption'], prepared.stock_balances,
            owned['attributes'], raw['foundation']['snapshot']['business_date'],
            raw['stock_configuration']['reservation_type'])
        prepared = replace(prepared, stock_balances=prepared.stock_balances + auxiliary)
    if adapter is not None:
        # Canonical selected site hook follows validation and Norm controls.
        # It is not a default common-engine behavior or an active NMS snapshot.
        from mta.application.r1_gulfoil_input import convert_non_nms
        validation = deepcopy(prepared.importer_validation)
        validation['tables']['SkuLocAttributeData'] = convert_non_nms(
            validation['tables']['SkuLocAttributeData'], profile='GulfOil')
        prepared = replace(prepared, importer_validation=validation)
    payload = prepared.calculation_payload or raw
    with stage('r1_two_pass_requirements'):
        track, requirements, stock_advances, git_advances, trace = calculate_r1_requirements(prepared, payload)
    with stage('r1_rrr_pso'):
        normal = calculate_rrr_groups(
            track, requirements,
            parent_stock_for_rationing={(r['sku_code'], r['location_code']): Decimal(r['stock_for_rationing'])
                                       for r in prepared.stock_balances},
            replenishment_exclusions=prepared.replenishment_exclusions,
            allow_negative_stock_for_requirement=True,
        )
        normal_values = [NormalAllocation.from_row(row) for row in normal]
        pso = allocate_spike_pso(_pso_inputs(prepared, requirements, normal_values))
    with stage('r1_band_bor_projections'):
        bpp = _bpp_order_rows(prepared, payload)
        source_bands = {} if _production_sources else None
        bands = _requirement_band_rows(prepared, payload, requirements, bpp, stock_advances + git_advances,
                                      source_rows=source_bands)
        bifurcation = _bifurcation_rows(prepared, requirements, normal_values, pso)
        bor, bor_oa = _source_bor_rows(prepared, payload, requirements, bands)

    def consumer_orders(rows):
        if prepared.order_part_identity is None:
            return list(rows)
        return [{**row, **prepared.order_part_identity[row['order_id']]} for row in rows]

    output = {
        'r1_additional_master': list(prepared.additional_master),
        'r1_stock_balance': list(prepared.stock_balances),
        'r1_order_route': consumer_orders(prepared.routes),
        'r1_order_bpp': consumer_orders(bpp),
        'r1_advance_stock_allocation': consumer_orders(stock_advances),
        'r1_git_advance_allocation': consumer_orders(git_advances),
        'r1_requirement_band': bands,
        'r1_pso_ration': [_as_json(row) for row in pso],
        'r1_requirement': requirements,
        'r1_normal_ration': normal,
        'r1_ration_bifurcation': bifurcation,
        'r1_bor': bor,
        'r1_bor_oa': bor_oa,
    }
    if source_bands is not None:
        output['r1_order_allocation_bands'] = [source_bands[key] for key in sorted(source_bands)]
    if not defer_pick:
        output.update(r1_pick_list=_pick_rows(bifurcation, payload['logistics']),
            r1_pick_remaining=_pick_rows(bifurcation, payload['logistics'], remaining=True))
    if prepared.master_state is not None:
        output.update({'r1_' + name: rows for name, rows in prepared.master_state.items()})
    if prepared.order_part_identity is not None:
        output['r1_order_remaining'] = consumer_orders(trace['order_remainders'])
    if prepared.order_import_state is not None:
        output['r1_order_import_state'] = [dict(table=n, rows=rows)
            for n, rows in prepared.order_import_state.items() if n in ('orders', 'new_spikes', 'closure_history')]
    if prepared.importer_validation is not None:
        output['r1_importer_validation'] = [{'stage': 'master_validation', **prepared.importer_validation}]
    if prepared.supplier_validation is not None:
        output['r1_supplier_validation'] = [{'stage': s, **v} for s, v in prepared.supplier_validation.items()]
        output['r1_supplier_state'] = [{'table': n, 'rows': rows} for n, rows in prepared.supplier_state.items()]
    if prepared.supplier_state is not None:
        master = prepared.master_state['bpr_master']
        physical = {(_sql_key(r['sku_code']), _sql_key(r['location_code'])) for r in master}
        topmost = {(_sql_key(r['sku_code']), _sql_key(r['location_code'])) for r in master
                   if (_sql_key(r['sku_code']), _sql_key(r['parent_location_code'])) not in physical}
        vendors = {_sql_key(v) for v in prepared.vendor_codes}
        output['r1_vendor_bor'] = [r for r in bor if _sql_key(r['supplier']) in vendors]
        output['r1_bor'] = [r for r in bor if (_sql_key(r['sku']), _sql_key(r['location'])) in topmost]
    if prepared.daily_validation is not None:
        output['r1_daily_validation'] = [{'stage': s, **v} for s, v in prepared.daily_validation.items()]
        output['r1_daily_consumption'] = [{'table': 'DailyConsumption', 'rows': sorted_rows(prepared.daily_consumption)}]
    if adapter is not None:
        output['r1_gulfoil_adapter'] = [dict(stage='files_to_standard',
            source_checksum=digest(storage(adapter['source'])), standard_checksum=digest(storage(raw)),
            **storage(adapter))]
    return output
