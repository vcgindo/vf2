from __future__ import annotations

import argparse

import dataclasses

import json

import hashlib

import subprocess

import sys

from collections import Counter

from decimal import Decimal, InvalidOperation

from pathlib import Path

from typing import Any

from parity.comparators.exact import compare_records

from parity.models import ComparisonClass, ComparisonStatus, OutputPolicy

from mta.application.r1_master_state import MASTER_SCHEMA

from mta.application.r1_raw_master_entry import RAW_MASTER_SCHEMA

from mta.application.r1_supplier_entry import RAW_SUPPLIER_SCHEMA, SUPPLIER_STATE_FIELDS

from mta.application.r1_supplier_input import STAGES as SUPPLIER_STAGES, CHECKPOINT_TABLES as SUPPLIER_TABLES

from mta.application.r1_daily_entry import RAW_DAILY_SCHEMA, DAILY_CONSUMPTION_FIELDS

from mta.application.r1_daily_input import STAGES as DAILY_STAGES, CHECKPOINT_TABLES as DAILY_TABLES

from mta.application.r1_importer_master import TABLE_COLUMNS

TECHNICAL_NORMALIZER = "R1-TECHNICAL-001"

_REQUIREMENT_EXTRA_NUMERIC = (
    "cnr", "routed_due_spike", "residual_children", "additional_demand", "netted_additional",
    "residual_additional", "normal_gap", "virtual_norm", "blue_requirement", "dispatch_pen",
)

_BAND_FIELDS = (
    "norm_black_band", "norm_red_band", "norm_yellow_band", "norm_green_band",
    "order_black_band", "order_red_band", "order_yellow_band", "order_green_band",
    "order_blue_band",
    "norm_req_black", "norm_req_red", "norm_req_yellow", "norm_req_green",
    "order_req_black", "order_req_red", "order_req_yellow", "order_req_green", "order_req_blue",
    "remaining_stock",
)

_NORMAL_RATION_FIELDS = (
    "virtual_norm", "stock_for_requirement", "goods_in_transit", "requirement",
    "pre_round_quantity", "step1_parent_leftover", "final_quantity", "remaining_parent_stock",
)

_PICK_REMAINING_FIELDS = ('sku', 'from_location', 'to_location', 'logistics_location',
                          'priority', 'remaining_quantity', 'vehicle')

_PICK_FIELDS = ('sku_code', 'location_code', 'parent_location_code', 'logistics_location',
                'priority', 'picked_quantity', 'vehicle', 'truck', 'total_weight', 'total_volume')

_PICK_NUMERIC = ('priority', 'picked_quantity', 'truck', 'total_weight', 'total_volume')

_ADDITIONAL_MASTER_NUMERIC = (
    "wh_level", "topmost_norm", "topmost_pack_size", "cumulative_rlt_days",
    "spike_threshold_percent", "pso_threshold_percent",
)

_CHECKPOINT_KEYS = {
    "pick_remaining": ("sku", "from_location", "to_location", "logistics_location", "priority"),
    "additional_master": ("sku_code", "location_code"),
    "stock": ("sku_code", "location_code"),
    "routes": ("order_id", "location_code", "child_location_code"),
    "order_bpp": ("order_id", "sku_code", "source_location_code", "destination_location_code"),
    "advance_stock": ("order_id", "source_location_code", "destination_location_code"),
    "git_advance": ("order_id", "source_location_code", "destination_location_code"),
    "requirements": ("sku_code", "location_code"),
    "bands": ("sku_code", "location_code"),
    "pso_ration": ("sku_code", "location_code", "parent_location_code"),
    "normal_ration": ("sku_code", "location_code", "parent_location_code"),
    "bifurcation": ("sku_code", "location_code", "parent_location_code"),
    "supplier_bor": ("sku_code", "location_code", "supplier"),
    "bor_oa": ("sku_code", "location_code", "supplier"),
    "logistic_pick": ("sku_code", "location_code", "parent_location_code", "logistics_location", "priority", "truck"),
}

_MASTER_CHECKPOINT_FIELDS = {
    "dbm_master": ("sku_code", "location_code", "norm", "min_norm", "rlt", "rcp", "gcp", "ocp", "min_order_count", "parent_location_code", "sku_intro_date"),
    "importer_master": ("sku_code", "location_code", "norm", "min_norm", "rlt", "rcp", "gcp", "ocp", "min_order_count", "parent_location_code", "sku_intro_date"),
    "norm_change_export": ("sku_code", "location_code", "new_norm", "reason"),
    "norm_change_export_remaining": ("sku_code", "location_code", "new_norm", "reason"),
    "bpr_master": ("sku_code", "location_code", "norm", "parent_location_code", "sku_intro_date"),
}

_MASTER_CHECKPOINT_KEYS = {name: ("sku_code", "location_code") for name in _MASTER_CHECKPOINT_FIELDS}

_IMPORTER_CHECKPOINT_NAMES = {"importer_validation_" + n for n in (*TABLE_COLUMNS, "outcome", "rejects_added", "retired_events_added")}

_SUPPLIER_CHECKPOINT_NAMES = {"supplier_validation_" + s + ":" + t for s in SUPPLIER_STAGES for t in (*SUPPLIER_TABLES, "outcome")} | {"supplier_state_" + t for t in SUPPLIER_STATE_FIELDS} | {"vendor_bor"}

_DAILY_CHECKPOINT_NAMES = {"daily_validation_" + s + ":" + t for s in DAILY_STAGES for t in (*DAILY_TABLES, "outcome")} | {"daily_consumption"}

def number(value: Any) -> str:
    """Normalize only decimal representation, never business rounding."""
    if value is None:
        raise ValueError("Expected a present numeric R1 checkpoint value, got null")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as error:
        raise ValueError(f"Expected a numeric R1 checkpoint value, got {value!r}") from error
    if result == 0:
        return "0"
    return format(result.normalize(), "f")

def colour(value: Any) -> str:
    return str(value).upper()

def _rows(rows: list[dict], fields: tuple[str, ...], *, numeric: tuple[str, ...] = (), colours: tuple[str, ...] = ()) -> list[dict]:
    normalized = []
    for row in rows:
        item = {field: row.get(field) for field in fields}
        for field in numeric:
            item[field] = number(item[field])
        for field in colours:
            item[field] = colour(item[field])
        normalized.append(item)
    return normalized

def normalize_legacy(checkpoints: dict) -> dict[str, list[dict]]:
    """Expose the common semantic projection of the SQL Server capture."""
    return {
        'pick_remaining': _rows(checkpoints['pick_remaining'], _PICK_REMAINING_FIELDS,
                                numeric=('priority', 'remaining_quantity')),
        "additional_master": _rows(checkpoints["additional_master"], ("sku_code", "location_code", "topmost_location_code", *_ADDITIONAL_MASTER_NUMERIC), numeric=_ADDITIONAL_MASTER_NUMERIC),
        "stock": _rows(checkpoints["stock"], ("sku_code", "location_code", "stock_for_requirement", "stock_for_rationing"), numeric=("stock_for_requirement", "stock_for_rationing")),
        "routes": _rows(checkpoints["routes"], ("order_id", "location_code", "child_location_code", "due_date")),
        # The leaf report record is a terminal White presentation row; the
        # modern persisted seam holds only upstream BPP route records.
        "order_bpp": _rows([row for row in checkpoints["order_bpp"] if row["source_location_code"] != row["destination_location_code"]], ("order_id", "sku_code", "source_location_code", "destination_location_code", "route_due_date", "due_date_at_destination", "bpp", "colour", "quantity"), numeric=("bpp", "quantity"), colours=("colour",)),
        "advance_stock": _rows(checkpoints["advance_stock"], ("order_id", "source_location_code", "destination_location_code", "allocated_quantity"), numeric=("allocated_quantity",)),
        "git_advance": _rows(checkpoints["git_advance"], ("order_id", "source_location_code", "destination_location_code", "allocated_quantity"), numeric=("allocated_quantity",)),
        "requirements": _rows(checkpoints["requirements"], ("sku_code", "location_code", "norm", "stock_for_requirement", "stock_for_rationing", "direct_spike_overdue", "pso", "relevant_pso_cnr", "requirement", *_REQUIREMENT_EXTRA_NUMERIC, "dispatch_colour"), numeric=("norm", "stock_for_requirement", "stock_for_rationing", "direct_spike_overdue", "pso", "relevant_pso_cnr", "requirement", *_REQUIREMENT_EXTRA_NUMERIC), colours=("dispatch_colour",)),
        "bands": _rows(checkpoints["bands"], ("sku_code", "location_code", *_BAND_FIELDS), numeric=_BAND_FIELDS),
        "normal_ration": _rows(checkpoints["normal_ration"], ("sku_code", "location_code", "parent_location_code", *_NORMAL_RATION_FIELDS), numeric=_NORMAL_RATION_FIELDS),
        "pso_ration": _rows(checkpoints["pso_ration"], ("sku_code", "location_code", "parent_location_code", "starting_requirement", "remaining_requirement", "total_allocation", "parent_leftover"), numeric=("starting_requirement", "remaining_requirement", "total_allocation", "parent_leftover")),
        "bifurcation": _rows(checkpoints["bifurcation"], ("sku_code", "location_code", "parent_location_code", "to_black", "to_red", "to_yellow", "to_green", "to_blue"), numeric=("to_black", "to_red", "to_yellow", "to_green", "to_blue")),
        "supplier_bor": _rows([{**row, "supplier": row["supplier_code"]} for row in checkpoints["supplier_bor"]], ("sku_code", "location_code", "supplier", "original_requirement", "dispatch_requirement", "to_red", "to_yellow", "to_green", "to_blue"), numeric=("original_requirement", "dispatch_requirement", "to_red", "to_yellow", "to_green", "to_blue")),
        "bor_oa": _rows([{**row, "supplier": row["supplier_code"]} for row in checkpoints["bor_oa"]], ("sku_code", "location_code", "supplier", "requirement", "dispatch_quantity", "req_black", "req_red", "req_yellow", "req_green", "req_blue", "dispatch_black", "dispatch_red", "dispatch_yellow", "dispatch_green", "dispatch_blue", "dispatch_colour"), numeric=("requirement", "dispatch_quantity", "req_black", "req_red", "req_yellow", "req_green", "req_blue", "dispatch_black", "dispatch_red", "dispatch_yellow", "dispatch_green", "dispatch_blue"), colours=("dispatch_colour",)),
        "logistic_pick": _rows(checkpoints["logistic_pick"], _PICK_FIELDS, numeric=_PICK_NUMERIC),
    }

def normalize_modern(outputs: dict) -> dict[str, list[dict]]:
    """Map the persisted R1 ledger onto the legacy adapter's common fields."""
    for row in outputs['r1_pick_remaining']:
        if row['truck'] is not None or number(row['picked_quantity']) != '0':
            raise ValueError('Unallocated Pick queue cannot contain a dispatched truck/quantity')
    balances = {(row["sku_code"], row["location_code"]): row for row in outputs["r1_stock_balance"]}
    requirements = []
    for row in outputs["r1_requirement"]:
        requirement = row["requirement"]
        balance = balances[(row["sku_code"], row["location_code"])]
        requirements.append({
            "sku_code": row["sku_code"], "location_code": row["location_code"],
            "norm": row["effective_norm"]["value"],
            "stock_for_requirement": requirement["stock_for_requirement"],
            "stock_for_rationing": balance["stock_for_rationing"],
            "direct_spike_overdue": requirement["due_spike"], "pso": requirement["pso"],
            "relevant_pso_cnr": requirement["relevant_pso_cnr"], "requirement": requirement["requirement"],
            **{field: requirement[field] for field in _REQUIREMENT_EXTRA_NUMERIC[:7]},
            "virtual_norm": row["virtual_norm"]["value"],
            "blue_requirement": row["virtual_norm"]["blue_requirement"],
            "dispatch_pen": row["colours"]["dispatch"]["penetration"],
            "dispatch_colour": row["colours"]["dispatch"]["band"],
        })
    bands = []
    for row in outputs["r1_requirement_band"]:
        bands.append({key: row[key] for key in ("sku_code", "location_code", *_BAND_FIELDS)})
    bor_oa = []
    for row in outputs["r1_bor_oa"]:
        required, dispatch = row["requirement_buckets"], row["dispatch_buckets"]
        bor_oa.append({
            "sku_code": row["sku"], "location_code": row["location"], "supplier": row["supplier"],
            "requirement": row["requirement"], "dispatch_quantity": row["dispatch_requirement"],
            "req_black": required["to_black"], "req_red": required["to_red"], "req_yellow": required["to_yellow"], "req_green": required["to_green"], "req_blue": required["to_blue"],
            "dispatch_black": dispatch["to_black"], "dispatch_red": dispatch["to_red"], "dispatch_yellow": dispatch["to_yellow"], "dispatch_green": dispatch["to_green"], "dispatch_blue": dispatch["to_blue"], "dispatch_colour": row["dispatch_colour"],
        })
    picks = [{
        "sku_code": row["sku"], "location_code": row["to_location"], "parent_location_code": row["from_location"],
        "priority": row["priority"], "picked_quantity": row["picked_quantity"], "vehicle": row["vehicle"], "truck": row["truck"],
        'logistics_location': row['logistics_location'], 'total_weight': row['total_weight'], 'total_volume': row['total_volume'],
    } for row in outputs["r1_pick_list"]]
    raw = {
        "additional_master": outputs["r1_additional_master"],
        "stock": outputs["r1_stock_balance"],
        "routes": outputs["r1_order_route"],
        "order_bpp": outputs["r1_order_bpp"],
        "advance_stock": outputs["r1_advance_stock_allocation"],
        "git_advance": outputs["r1_git_advance_allocation"],
        "requirements": requirements,
        "bands": bands,
        "normal_ration": outputs["r1_normal_ration"],
        "pso_ration": outputs["r1_pso_ration"],
        "bifurcation": outputs["r1_ration_bifurcation"],
        "supplier_bor": [{"sku_code": row["sku"], "location_code": row["location"], "supplier": row["supplier"], **{key: row[key] for key in ("original_requirement", "dispatch_requirement", "to_red", "to_yellow", "to_green", "to_blue")}} for row in outputs["r1_bor"]],
        "bor_oa": bor_oa,
        "logistic_pick": picks,
        "pick_remaining": outputs['r1_pick_remaining'],
    }
    return {
        'pick_remaining': _rows(raw['pick_remaining'], _PICK_REMAINING_FIELDS,
                                numeric=('priority', 'remaining_quantity')),
        "additional_master": _rows(raw["additional_master"], ("sku_code", "location_code", "topmost_location_code", *_ADDITIONAL_MASTER_NUMERIC), numeric=_ADDITIONAL_MASTER_NUMERIC),
        "stock": _rows(raw["stock"], ("sku_code", "location_code", "stock_for_requirement", "stock_for_rationing"), numeric=("stock_for_requirement", "stock_for_rationing")),
        "routes": _rows(raw["routes"], ("order_id", "location_code", "child_location_code", "due_date")),
        "order_bpp": _rows(raw["order_bpp"], ("order_id", "sku_code", "source_location_code", "destination_location_code", "route_due_date", "due_date_at_destination", "bpp", "colour", "quantity"), numeric=("bpp", "quantity"), colours=("colour",)),
        "advance_stock": _rows(raw["advance_stock"], ("order_id", "source_location_code", "destination_location_code", "allocated_quantity"), numeric=("allocated_quantity",)),
        "git_advance": _rows(raw["git_advance"], ("order_id", "source_location_code", "destination_location_code", "allocated_quantity"), numeric=("allocated_quantity",)),
        "requirements": _rows(raw["requirements"], ("sku_code", "location_code", "norm", "stock_for_requirement", "stock_for_rationing", "direct_spike_overdue", "pso", "relevant_pso_cnr", "requirement", *_REQUIREMENT_EXTRA_NUMERIC, "dispatch_colour"), numeric=("norm", "stock_for_requirement", "stock_for_rationing", "direct_spike_overdue", "pso", "relevant_pso_cnr", "requirement", *_REQUIREMENT_EXTRA_NUMERIC), colours=("dispatch_colour",)),
        "bands": _rows(raw["bands"], ("sku_code", "location_code", *_BAND_FIELDS), numeric=_BAND_FIELDS),
        "normal_ration": _rows(raw["normal_ration"], ("sku_code", "location_code", "parent_location_code", *_NORMAL_RATION_FIELDS), numeric=_NORMAL_RATION_FIELDS),
        "pso_ration": _rows(raw["pso_ration"], ("sku_code", "location_code", "parent_location_code", "starting_requirement", "remaining_requirement", "total_allocation", "parent_leftover"), numeric=("starting_requirement", "remaining_requirement", "total_allocation", "parent_leftover")),
        "bifurcation": _rows(raw["bifurcation"], ("sku_code", "location_code", "parent_location_code", "to_black", "to_red", "to_yellow", "to_green", "to_blue"), numeric=("to_black", "to_red", "to_yellow", "to_green", "to_blue")),
        "supplier_bor": _rows(raw["supplier_bor"], ("sku_code", "location_code", "supplier", "original_requirement", "dispatch_requirement", "to_red", "to_yellow", "to_green", "to_blue"), numeric=("original_requirement", "dispatch_requirement", "to_red", "to_yellow", "to_green", "to_blue")),
        "bor_oa": _rows(raw["bor_oa"], ("sku_code", "location_code", "supplier", "requirement", "dispatch_quantity", "req_black", "req_red", "req_yellow", "req_green", "req_blue", "dispatch_black", "dispatch_red", "dispatch_yellow", "dispatch_green", "dispatch_blue", "dispatch_colour"), numeric=("requirement", "dispatch_quantity", "req_black", "req_red", "req_yellow", "req_green", "req_blue", "dispatch_black", "dispatch_red", "dispatch_yellow", "dispatch_green", "dispatch_blue"), colours=("dispatch_colour",)),
        "logistic_pick": _rows(raw["logistic_pick"], _PICK_FIELDS, numeric=_PICK_NUMERIC),
    }

def normalize_master_checkpoints(checkpoints: dict, *, prefix="") -> dict:
    """Complete, typed source-state checkpoints; NULL is not a missing field."""
    numeric = {"norm", "min_norm", "rlt", "rcp", "gcp", "ocp", "min_order_count", "new_norm", "reason"}
    nullable = {"ocp", "min_order_count", "parent_location_code", "sku_intro_date"}
    result = {}
    for name, fields in _MASTER_CHECKPOINT_FIELDS.items():
        rows = checkpoints[prefix + name]  # A missing empty checkpoint must fail too.
        if not isinstance(rows, list):
            raise ValueError(f"Invalid R1 master checkpoint: {name}")
        result[name] = []
        for row in rows:
            if not isinstance(row, dict) or set(row) != set(fields):
                raise ValueError(f"Incomplete or unexpected R1 master checkpoint fields: {name}")
            item = {}
            for field in fields:
                value = row[field]
                if value is None:
                    if field not in nullable:
                        raise ValueError(f"Unexpected NULL in R1 master checkpoint: {field}")
                    item[field] = None
                elif field in numeric:
                    parsed = Decimal(number(value))
                    if not parsed.is_finite() or parsed != parsed.to_integral_value():
                        raise ValueError(f"Non-integer R1 master checkpoint: {field}")
                    item[field] = number(value)
                else:
                    if not isinstance(value, str) or not value:
                        raise ValueError(f"Invalid R1 master checkpoint identity/date: {field}")
                    item[field] = value
            result[name].append(item)
    return result

def compare(legacy_checkpoints: dict, modern_outputs: dict, *, master_state_required=False, importer_validation_required=False, supplier_required=False, daily_required=False, phase_required=False, accepted_required=False, order_input_required=False, order_parts_required=False, season_required=False, tags_required=False, diagnostics_required=False) -> dict:
    if daily_required:
        supplier_required = True
    if supplier_required:
        master_state_required = importer_validation_required = True
    legacy, modern = normalize_legacy(legacy_checkpoints), normalize_modern(modern_outputs)
    keys_by_checkpoint = dict(_CHECKPOINT_KEYS)
    if order_parts_required:
        for checkpoint, capability in (('routes', 'r1_order_route'), ('order_bpp', 'r1_order_bpp'),
                                       ('advance_stock', 'r1_advance_stock_allocation'),
                                       ('git_advance', 'r1_git_advance_allocation')):
            for target, source in ((legacy, legacy_checkpoints[checkpoint]), (modern, modern_outputs[capability])):
                if checkpoint == 'order_bpp':
                    source = [r for r in source if r['source_location_code'] != r['destination_location_code']]
                if len(source) != len(target[checkpoint]):
                    raise ValueError('Order part projection population mismatch')
                for projected, raw in zip(target[checkpoint], source, strict=True):
                    projected.update(order_key=number(raw['order_key']), part_id=number(raw['part_id']))
            keys_by_checkpoint[checkpoint] += ('order_key', 'part_id')
        fields = ('order_id', 'order_key', 'part_id', 'remaining_quantity')
        for target, rows in ((legacy, legacy_checkpoints['order_remaining']),
                             (modern, modern_outputs['r1_order_remaining'])):
            target['order_remaining'] = _rows(rows, fields, numeric=fields[1:])
        keys_by_checkpoint['order_remaining'] = ('order_id', 'order_key', 'part_id')
    if master_state_required or importer_validation_required:
        legacy.update(normalize_master_checkpoints(legacy_checkpoints))
        modern.update(normalize_master_checkpoints(modern_outputs, prefix="r1_"))
        keys_by_checkpoint.update(_MASTER_CHECKPOINT_KEYS)
    if season_required or 'season_control_state' in legacy_checkpoints or 'r1_season_control_state' in modern_outputs:
        from mta.application.r1_seasonality import STATE_FIELDS as SEASON_FIELDS
        for target,rows in ((legacy,legacy_checkpoints.get('season_control_state',[])),
                            (modern,modern_outputs.get('r1_season_control_state',[]))):
            if len(rows) != len(SEASON_FIELDS) or {r['table'] for r in rows} != set(SEASON_FIELDS):
                raise ValueError('Missing or duplicate seasonal state table')
            target['season_control_state'] = [dict(table=r['table'],rows=json.dumps(r['rows'],sort_keys=True)) for r in rows]
        keys_by_checkpoint['season_control_state'] = ('table',)
    if tags_required or 'transit_tag_state' in legacy_checkpoints or 'r1_transit_tag_state' in modern_outputs:
        for target,rows in ((legacy,legacy_checkpoints['transit_tag_state']), (modern,modern_outputs['r1_transit_tag_state'])):
            target['transit_tag_state'] = _rows(rows, ('SKUCode','WhCode','Tags'))
        keys_by_checkpoint['transit_tag_state'] = ('SKUCode','WhCode')
    for name in ('phase_diagnostic_state','force_diagnostic_state'):
        if diagnostics_required or name in legacy_checkpoints or 'r1_'+name in modern_outputs:
            for target,rows in ((legacy,legacy_checkpoints[name]),(modern,modern_outputs['r1_'+name])):
                if len(rows)!=1:
                    raise ValueError('Missing diagnostic report state')
                target[name] = [dict(table=r['table'],rows=json.dumps(r['rows'],sort_keys=True)) for r in rows]
            keys_by_checkpoint[name] = ('table',)
    if phase_required or 'phase_control_state' in legacy_checkpoints or 'r1_phase_control_state' in modern_outputs:
        # Table-keyed rows contain complete sorted multisets; serialize nested
        # values without numeric tolerances or dropping NULL/duplicate entries.
        for target, rows in ((legacy, legacy_checkpoints.get('phase_control_state', [])),
                             (modern, modern_outputs.get('r1_phase_control_state', []))):
            from mta.application.r1_phase_entry import STATE_FIELDS
            if len(rows) != len(STATE_FIELDS) or {r['table'] for r in rows} != set(STATE_FIELDS):
                raise ValueError('Missing or duplicate required phase state table')
            target['phase_control_state'] = [dict(table=r['table'], rows=json.dumps(r['rows'], sort_keys=True)) for r in rows]
        keys_by_checkpoint['phase_control_state'] = ('table',)
    if accepted_required or 'accepted_control_state' in legacy_checkpoints or 'r1_accepted_control_state' in modern_outputs:
        from mta.application.r1_parent_suggestions import ACCEPTED_STATE_FIELDS
        for target,rows in ((legacy,legacy_checkpoints.get('accepted_control_state',[])),
                            (modern,modern_outputs.get('r1_accepted_control_state',[]))):
            if len(rows) != len(ACCEPTED_STATE_FIELDS) or {r['table'] for r in rows} != set(ACCEPTED_STATE_FIELDS):
                raise ValueError('Missing or duplicate accepted-control state table')
            target['accepted_control_state'] = [dict(table=r['table'],rows=json.dumps(r['rows'],sort_keys=True)) for r in rows]
        keys_by_checkpoint['accepted_control_state'] = ('table',)
    if order_input_required or 'order_import_state' in legacy_checkpoints or 'r1_order_import_state' in modern_outputs:
        for target,rows in ((legacy,legacy_checkpoints.get('order_import_state',[])),
                            (modern,modern_outputs.get('r1_order_import_state',[]))):
            if len(rows) != 3 or {r['table'] for r in rows} != {'orders','new_spikes','closure_history'}:
                raise ValueError('Missing or duplicate order-import state table')
            target['order_import_state'] = [dict(table=r['table'],rows=json.dumps(sorted(r['rows'],key=lambda x:json.dumps(x,sort_keys=True)),sort_keys=True)) for r in rows]
        keys_by_checkpoint['order_import_state'] = ('table',)
    results = {}
    for checkpoint, keys in keys_by_checkpoint.items():
        result = compare_records(
            scenario_id="R1-CURRENT-DAY", output_policy=OutputPolicy(
                f"R1-{checkpoint.upper()}", ComparisonClass.TECHNICAL_NORMALIZATION,
                False, keys, (TECHNICAL_NORMALIZER,),
            ), rule_ids=("R1-CURRENT-DAY",), legacy_rows=legacy[checkpoint], new_rows=modern[checkpoint],
        )
        results[checkpoint] = {
            "status": result.status.value, "legacy_rows": len(legacy[checkpoint]),
            "modern_rows": len(modern[checkpoint]), "diffs": [dataclasses.asdict(diff) for diff in result.diffs],
        }
    if importer_validation_required:
        from parity.run_r1_master_validation import compare_master_validation
        rows = modern_outputs["r1_importer_validation"]
        if len(rows) != 1 or rows[0].get("stage") != "master_validation":
            raise ValueError("Missing/duplicate persisted Importer validation checkpoint")
        result = compare_master_validation(legacy_checkpoints["importer_validation"], rows[0])
        results.update({"importer_validation_" + k: v for k, v in result.items()})
    if supplier_required:
        from parity.run_r1_supplier_validation import compare_supplier_validation, compare_supplier_state
        rows = modern_outputs["r1_supplier_validation"]
        if len(rows) != len(SUPPLIER_STAGES) or {r.get("stage") for r in rows} != set(SUPPLIER_STAGES):
            raise ValueError("Missing/duplicate persisted supplier validation")
        modern_stages = {r["stage"]: {k: v for k, v in r.items() if k != "stage"} for r in rows}
        results.update({"supplier_validation_" + k: v for k, v in compare_supplier_validation(legacy_checkpoints["supplier_validation"], modern_stages).items()})
        rows = modern_outputs["r1_supplier_state"]
        if len(rows) != 4 or {r.get("table") for r in rows} != set(SUPPLIER_STATE_FIELDS):
            raise ValueError("Missing/duplicate persisted supplier state")
        results.update({"supplier_state_" + k: v for k, v in compare_supplier_state(legacy_checkpoints["supplier_state"], {r["table"]: r["rows"] for r in rows}).items()})
        a = normalize_legacy({**legacy_checkpoints, "supplier_bor": legacy_checkpoints["vendor_bor"]})["supplier_bor"]
        b = normalize_modern({**modern_outputs, "r1_bor": modern_outputs["r1_vendor_bor"]})["supplier_bor"]
        result = compare_records(scenario_id="R1-VENDOR-BOR", output_policy=OutputPolicy("R1-VENDOR-BOR", ComparisonClass.TECHNICAL_NORMALIZATION,
            False, _CHECKPOINT_KEYS["supplier_bor"], (TECHNICAL_NORMALIZER,)), rule_ids=("R1-CURRENT-DAY",), legacy_rows=a, new_rows=b)
        results["vendor_bor"] = {"status": result.status.value, "legacy_rows": len(a), "modern_rows": len(b), "diffs": [dataclasses.asdict(d) for d in result.diffs]}
    if daily_required:
        from parity.run_r1_daily_validation import compare_daily_validation
        rows = modern_outputs["r1_daily_validation"]
        if len(rows) != len(DAILY_STAGES) or {r.get("stage") for r in rows} != set(DAILY_STAGES):
            raise ValueError("Missing/duplicate persisted daily validation")
        modern_stages = {r["stage"]: {k: v for k, v in r.items() if k != "stage"} for r in rows}
        results.update({"daily_validation_" + k: v for k, v in compare_daily_validation(legacy_checkpoints["daily_validation"], modern_stages).items()})
        rows = modern_outputs["r1_daily_consumption"]
        if len(rows) != 1 or set(rows[0]) != {"table", "rows"} or rows[0]["table"] != "DailyConsumption":
            raise ValueError("Missing/duplicate persisted daily consumption")
        a, b = legacy_checkpoints["daily_consumption"], rows[0]["rows"]
        for side in (a, b):
            if not isinstance(side, list) or any(not isinstance(r, dict) or set(r) != set(DAILY_CONSUMPTION_FIELDS) for r in side):
                raise ValueError("Incomplete daily consumption fields")
        bag = lambda records: Counter(json.dumps(r, sort_keys=True) for r in records)
        x, y = bag(a), bag(b)
        results["daily_consumption"] = {"status": "PASS" if x == y else "FAIL", "legacy_rows": len(a), "modern_rows": len(b),
            "legacy_only": [json.loads(r) for r in (x - y).elements()], "modern_only": [json.loads(r) for r in (y - x).elements()]}
    return results
