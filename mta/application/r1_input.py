"""Validation boundary for the raw, synthetic R1 current-day input contract.

This deliberately does *not* turn the old ``track-a-v1`` seam into a claimed
full input pipeline.  It gives the R1 orchestrator a closed source-fact entry
point and rejects values which a legacy current-day batch must create itself.
"""
from __future__ import annotations

from mta.application.r1_importer_master import _sql_key

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass, replace
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import hashlib

from mta.application.r1_additional_master import calculate_additional_master
from mta.application.r1_master_state import MASTER_SCHEMA, source_calculation_view, reconcile_master_state
from mta.application.r1_raw_master_entry import RAW_MASTER_SCHEMA, validate_raw_master_run, generated_master_view
from mta.application.r1_importer_master import process_importer_master
from mta.application.r1_supplier_entry import RAW_SUPPLIER_SCHEMA, validate_supplier_run, master_input_skeleton
from mta.application.r1_supplier_input import process_supplier_validation, supplier_calculation_state, STAGES, OPENING_TABLES
from mta.application.r1_daily_entry import RAW_DAILY_SCHEMA, validate_daily_run, generated_daily_view, generated_bpr_daily_state
from mta.application.r1_daily_input import process_daily_validation


RAW_SCHEMA = "r1-current-day-input-v2"
LEGACY_RAW_SCHEMA = "r1-current-day-input-v1"
CONFIGURED_RAW_SCHEMA = "r1-current-day-input-v3"
EXCLUSION_RAW_SCHEMA = "r1-current-day-input-v4"

# These are current-day products, never source facts in an R1 fixture.  Keep
# the list narrow and explicit: input fields such as StockForRationing from the
# importer remain allowed under their source-fact names/locations.
DERIVED_SEED_FIELDS = frozenset({
    "stock_for_requirement",
    "routed_due_spike",
    "bands",
    "rationed_quantity",
    "buckets",
    "to_black",
    "to_red",
    "to_yellow",
    "to_green",
    "to_blue",
})


def _reject_derived(value: object, path: str = "payload") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if key in DERIVED_SEED_FIELDS:
                raise ValueError(f"R1 raw input must not seed derived field {path}.{key}")
            _reject_derived(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_derived(child, f"{path}[{index}]")


def _source_number(value: object, field: str) -> Decimal:
    if isinstance(value, bool):
        raise ValueError(f"R1 sourcing {field} must be numeric")
    try:
        parsed = Decimal(value)
    except (InvalidOperation, TypeError, ValueError) as error:
        raise ValueError(f"R1 sourcing {field} must be numeric") from error
    if not parsed.is_finite() or parsed < 0:
        raise ValueError(f"R1 sourcing {field} must be non-negative")
    return parsed


class R1EntryFailure(ValueError):
    """Source failure carries its exact stage; no successful partial entry."""
    def __init__(self, message, *, stage, evidence):
        super().__init__(message)
        self.stage = stage
        self.evidence = evidence


def resolve_r1_vehicle_mappings(logistics):
    """Selected parent join; never choose among multiple applicable vehicles."""
    # Parent queues are independent. Stable traversal makes checkpoint row
    # sequence reproducible without choosing an order within any queue.
    parents = sorted({r['from_location'] for r in logistics['items']})
    if 'vehicles' not in logistics and 'location_vehicles' not in logistics:
        return {parent: logistics['vehicle'] for parent in parents}
    if 'vehicle' in logistics or not {'vehicles', 'location_vehicles'} <= logistics.keys():
        raise ValueError('Explicit vehicle master and location mappings must have one owner')
    vehicles = {}
    for row in logistics['vehicles']:
        if set(row) != {'vehicle_id','name','weight_capacity','volume_capacity'}:
            raise ValueError('Invalid vehicle master fields')
        identity = row['vehicle_id']
        if type(identity) is not int or identity <= 0 or identity in vehicles:
            raise ValueError('Vehicle master requires unique positive integer identity')
        if not isinstance(row['name'], str) or not row['name'].strip():
            raise ValueError('Vehicle name is required')
        if any(not Decimal(str(row[f])).is_finite() or Decimal(str(row[f])) <= 0
               for f in ('weight_capacity','volume_capacity')):
            raise ValueError('Selected vehicle capacities must be positive finite numbers')
        vehicles[identity] = row
    result = {}
    for parent in parents:
        ids = set()
        for mapping in logistics['location_vehicles']:
            if set(mapping) != {'location_code','vehicle_id'} or type(mapping['vehicle_id']) is not int:
                raise ValueError('Invalid parent vehicle mapping')
            if _sql_key(mapping['location_code']) == _sql_key(parent) and mapping['vehicle_id'] in vehicles:
                ids.add(mapping['vehicle_id'])
        if len(ids) > 1:
            raise ValueError('Multiple applicable vehicles duplicate canonical queue rows; source selection remains ambiguous')
        if ids:
            result[parent] = vehicles[next(iter(ids))]
    return result


def resolve_r1_stock_configuration(payload, *, reservation_type=None, reservation_for_rationing_only=None):
    """Resolve one source-owned profile; explicit callers may not override v3.

    The v1/v2 compatibility oracle profile was type=1 / rationing-only=true.
    v3 requires these settings as raw facts shared by both engines.
    """
    supplied = {"reservation_type": reservation_type,
                "reservation_for_rationing_only": reservation_for_rationing_only}
    if reservation_type is not None and type(reservation_type) is not int:
        raise ValueError("R1 reservation_type caller setting must be an integer")
    if reservation_for_rationing_only is not None and type(reservation_for_rationing_only) is not bool:
        raise ValueError("R1 reservation_for_rationing_only caller setting must be boolean")
    if payload.get("schema") in {CONFIGURED_RAW_SCHEMA, EXCLUSION_RAW_SCHEMA, MASTER_SCHEMA}:
        config = payload.get("stock_configuration")
        if not isinstance(config, dict) or set(config) != set(supplied):
            raise ValueError("R1 v3 requires a complete stock_configuration")
        if any(value is not None and value != config[name] for name, value in supplied.items()):
            raise ValueError("R1 stock configuration conflicts with explicit caller settings")
        config = dict(config)
    else:
        config = {"reservation_type": 1 if reservation_type is None else reservation_type,
                  "reservation_for_rationing_only": True if reservation_for_rationing_only is None else reservation_for_rationing_only}
    if type(config["reservation_type"]) is not int or config["reservation_type"] not in {0, 1, 2}:
        raise ValueError("R1 reservation_type must be source option 0, 1 or 2")
    if type(config["reservation_for_rationing_only"]) is not bool:
        raise ValueError("R1 reservation_for_rationing_only must be boolean")
    return config


def resolve_r1_replenishment_exclusions(payload: dict) -> tuple[str, ...]:
    """Importer WhCode exclusions, never inferred from calculated demand.

    v1-v3 retain their recorded root-exclusion profile. v4 owns the exact
    list, including an explicit empty list. A physical parent exclusion does
    not imply exclusion of its generated direct-order virtual WhCode.
    """
    if payload.get("schema") in {EXCLUSION_RAW_SCHEMA, MASTER_SCHEMA}:
        codes = payload.get("replenishment_exclusions")
        if (not isinstance(codes, list)
                or any(not isinstance(code, str) or not code.strip() or code != code.strip() for code in codes)
                or len(set(codes)) != len(codes)):
            raise ValueError("R1 replenishment_exclusions must be unique nonblank WhCodes")
        return tuple(sorted(codes))
    parents = {(row["sku_code"], row["child_location_code"]) for row in payload["foundation"]["hierarchy"]}
    return tuple(sorted({row["location_code"] for row in payload["foundation"]["sku_locations"]
                         if (row["sku_code"], row["location_code"]) not in parents}))


def validate_r1_raw_input(payload: dict, *, _order_types_reconciled=False) -> None:
    """Validate the R1 entry contract before source-shaped adaptation.

    It is intentionally stricter than the Stage 6 integrated contract: order
    classification/history, routing context, stock adjustment source facts,
    sourcing and transport facts must be owned by one immutable payload.
    """
    if isinstance(payload, dict) and 'order_input' in payload:
        from mta.application.r1_order_input import validate_order_input
        if payload.get('orders') != []:
            raise ValueError('Separate order input cannot also supply projected orders')
        validate_order_input(payload['order_input'], payload['foundation']['snapshot']['business_date'])
        if 'sku_attributes' in payload['order_input'] and 'raw_master_entry' in payload:
            raise ValueError('Raw master owns SKU attributes; order input cannot override its producer')
        skeleton = {k:v for k,v in payload.items() if k != 'order_input'}
        validate_r1_raw_input(skeleton)
        return
    if isinstance(payload, dict) and payload.get("schema") == RAW_DAILY_SCHEMA:
        _reject_derived(payload)
        validate_daily_run(payload)
        return
    if isinstance(payload, dict) and payload.get("schema") == RAW_SUPPLIER_SCHEMA:
        _reject_derived(payload)
        validate_supplier_run(payload)
        return
    if isinstance(payload, dict) and payload.get("schema") == RAW_MASTER_SCHEMA:
        _reject_derived(payload)
        validate_raw_master_run(payload)
        return
    required = {
        "schema", "foundation", "orders", "policies", "stock_openings",
        "routing", "allocation", "sourcing", "logistics",
    }
    v2_required = required | {"supplier_openings"}
    v3_required = v2_required | {"stock_configuration"}
    v4_required = v3_required | {"replenishment_exclusions"}
    if isinstance(payload, dict) and payload.get("schema") == MASTER_SCHEMA:
        if set(payload) != (v4_required - {"routing"}) | {"master_state"}:
            raise ValueError("Invalid R1 v5 master-state input contract")
        _reject_derived(payload)
        validate_r1_raw_input(source_calculation_view(payload,
            _order_types_reconciled=_order_types_reconciled))
        return
    if not isinstance(payload, dict) or set(payload) not in (required, v2_required, v3_required, v4_required):
        raise ValueError("Invalid R1 raw input contract")
    if payload["schema"] not in {RAW_SCHEMA, LEGACY_RAW_SCHEMA, CONFIGURED_RAW_SCHEMA, EXCLUSION_RAW_SCHEMA}:
        raise ValueError("Unsupported R1 raw input schema")
    if payload["schema"] == RAW_SCHEMA and set(payload) != v2_required:
        raise ValueError("R1 v2 requires supplier_openings")
    if payload["schema"] == LEGACY_RAW_SCHEMA and set(payload) != required:
        raise ValueError("R1 v1 contract has unexpected fields")
    if payload["schema"] == CONFIGURED_RAW_SCHEMA:
        if set(payload) != v3_required:
            raise ValueError("R1 v3 requires supplier_openings and stock_configuration")
        resolve_r1_stock_configuration(payload)
    if payload["schema"] == EXCLUSION_RAW_SCHEMA:
        if set(payload) != v4_required:
            raise ValueError("R1 v4 requires stock_configuration and replenishment_exclusions")
        resolve_r1_stock_configuration(payload)
        resolve_r1_replenishment_exclusions(payload)
    if not isinstance(payload["foundation"], dict):
        raise ValueError("R1 foundation must be an object")
    for field in ("orders", "policies", "stock_openings", "routing", "sourcing"):
        if not isinstance(payload[field], list):
            raise ValueError(f"R1 {field} must be a list")
    if payload["schema"] != LEGACY_RAW_SCHEMA and not isinstance(payload["supplier_openings"], list):
        raise ValueError("R1 supplier_openings must be a list")
    if not isinstance(payload["logistics"], dict):
        raise ValueError("R1 logistics must be an object")
    allocation = payload["allocation"]
    if (not isinstance(allocation, dict)
            or set(allocation) != {"advance_stock_threshold_percent"}):
        raise ValueError("R1 allocation controls are invalid")
    threshold = Decimal(allocation["advance_stock_threshold_percent"])
    if not threshold.is_finite() or threshold < 0 or threshold > 100:
        raise ValueError("R1 advance-stock threshold must be between 0 and 100")
    _reject_derived(payload)
    snapshot = payload["foundation"].get("snapshot")
    if not isinstance(snapshot, dict) or not all(snapshot.get(key) for key in (
        "snapshot_id", "business_date", "configuration_version", "site_code",
    )):
        raise ValueError("R1 foundation snapshot identity is incomplete")
    if not payload["stock_openings"]:
        raise ValueError("R1 requires at least one raw stock opening")
    for opening in payload["stock_openings"]:
        if not isinstance(opening, dict):
            raise ValueError("Invalid R1 raw stock opening")
        for field in ("stock_percent_reservation", "norm_percent_reservation"):
            if field in opening:
                value = _source_number(opening[field], field)
                if value != value.to_integral_value() or value > 2147483647:
                    raise ValueError(f"R1 {field} must fit the source SQL integer column")
    def validate_supplier_rows(rows: list[dict], label: str) -> None:
        source_keys: set[tuple[str, str, str]] = set()
        for index, source in enumerate(rows):
            required_source = {"sku_code", "location_code", "supplier", "sob", "moq", "pack_size"}
            allowed_source = required_source | {"case"}
            if not isinstance(source, dict) or set(source) - allowed_source or not required_source.issubset(source):
                raise ValueError(f"Invalid R1 {label} row at index {index}")
            identity = tuple(source[field] for field in ("sku_code", "location_code", "supplier"))
            if not all(isinstance(value, str) and value.strip() for value in identity):
                raise ValueError(f"R1 {label} identity is incomplete")
            if identity in source_keys:
                raise ValueError(f"R1 {label} SKU/location/supplier combination repeats")
            source_keys.add(identity)
            _source_number(source["sob"], "SOB")
            moq, pack_size = _source_number(source["moq"], "MOQ"), _source_number(source["pack_size"], "pack size")
            if moq != moq.to_integral_value():
                raise ValueError(f"R1 {label} MOQ must be an integer")
            if pack_size != pack_size.to_integral_value() or pack_size <= 0:
                raise ValueError(f"R1 {label} pack size must be a positive integer")

    validate_supplier_rows(payload["sourcing"], "sourcing")
    if payload["schema"] != LEGACY_RAW_SCHEMA:
        validate_supplier_rows(payload["supplier_openings"], "supplier opening")
    established_keys = set()
    for index, order in enumerate(payload["orders"]):
        required_order = {
            "order_id", "sku_code", "location_code", "outstanding_quantity",
            "accepted_on", "customer_expected_date", "established_is_spike",
            "established_due_date", "first_servicing_location_code",
        }
        if (not isinstance(order, dict) or not required_order.issubset(order)
                or set(order) - required_order - {"established_order_key"}):
            raise ValueError(f"Invalid raw order at index {index}")
        if order["customer_expected_date"] is not None and not isinstance(order["customer_expected_date"], str):
            raise ValueError("Customer expected date must be an ISO date or null when the legacy source omitted it")
        if order["established_is_spike"] is not None and type(order["established_is_spike"]) is not bool:
            raise ValueError("Established order classification must be boolean or null for a new order")
        if order["established_is_spike"] is True and (
            not order["established_due_date"] or not order["first_servicing_location_code"]
        ):
            raise ValueError("Established Spike order requires historical due date and first service")
        if "established_order_key" in order:
            order_key = order["established_order_key"]
            if (type(order_key) is not int or not 0 < order_key <= 2147483647
                    or order["established_is_spike"] is None):
                raise ValueError("Established OrderKey must be a positive SQL int belonging to an existing order")
            if order_key in established_keys:
                raise ValueError("Established OrderKey repeats across raw orders")
            established_keys.add(order_key)


def raw_stock_opening_records(payload: dict):
    """Convert only raw stock facts to the pure R1 source primitive."""
    validate_r1_raw_input(payload)
    if payload["schema"] == MASTER_SCHEMA:
        payload = source_calculation_view(payload)
    from mta.domain.r1_current_day import StockOpening

    result = []
    for row in payload["stock_openings"]:
        allowed = {
            "sku_code", "location_code", "stock", "norm", "utilized_stock",
            "stock_for_requirement_override", "stock_for_rationing_override",
            "stock_percent_reservation", "norm_percent_reservation",
        }
        if not isinstance(row, dict) or set(row) - allowed or not {"sku_code", "location_code", "stock", "norm"}.issubset(row):
            raise ValueError("Invalid R1 raw stock opening")
        result.append(StockOpening(**{"stock_percent_reservation": 100, **row}))
    return tuple(result)


def validate_r1_source_consistency(payload: dict) -> None:
    """Reject duplicated source facts with conflicting owners before either run.

    This checks only raw values/relationships, never calculates oracle outputs.
    Legacy RLT/Norm live in DBMMaster and physical stock in DailyConsumption;
    the modern routing/stock sections must describe those same facts.
    """
    if payload.get("schema") == MASTER_SCHEMA:
        payload = source_calculation_view(payload)
    foundation = payload["foundation"]
    masters = {(row["sku_code"], row["location_code"]): row for row in foundation["sku_locations"]}
    inventory = {(row["sku_code"], row["location_code"]): row for row in foundation["inventory_positions"]}
    parents = {(row["sku_code"], row["child_location_code"]): row["parent_location_code"] for row in foundation["hierarchy"]}
    if payload["schema"] == EXCLUSION_RAW_SCHEMA and any(key not in parents or not parents[key] for key in masters):
        raise ValueError("R1 v4 requires an explicit parent for every physical master")
    policies = {(row["sku_code"], row["location_code"]): row["policy"] for row in payload["policies"]}
    for row in payload["stock_openings"]:
        key = (row["sku_code"], row["location_code"])
        if key not in masters or key not in inventory:
            raise ValueError("R1 stock opening outside source closure")
        if Decimal(row["stock"]) != Decimal(inventory[key]["stock_quantity"]) or Decimal(row["norm"]) != Decimal(masters[key]["base_norm"]):
            raise ValueError("R1 stock/Norm source facts disagree")
    for row in payload["routing"]:
        key = (row["sku_code"], row["location_code"])
        if key not in masters:
            if row["has_bpr_master"]:
                raise ValueError("R1 route claims an absent BPR master")
            continue
        if not row["has_bpr_master"] or Decimal(row["norm"]) != Decimal(masters[key]["base_norm"]):
            raise ValueError("R1 route Norm/master facts disagree")
        if row["parent_location_code"] != parents.get(key):
            raise ValueError("R1 route parent differs from source hierarchy")
        if key in parents and row["rlt_to_parent_days"] != masters[key]["replenishment_lead_time_days"]:
            raise ValueError("R1 route RLT differs from source master")
        policy = policies[key]
        threshold = policy["spike_high"] if Decimal(masters[key]["base_norm"]) >= 3 else policy["spike_low"]
        if policy.get("spike_override") is not None:
            threshold = policy["spike_override"]
        if Decimal(row["spike_threshold_percent"]) != Decimal(threshold):
            raise ValueError("R1 route threshold differs from source policy")
    for field in ("spike_high", "spike_low", "pso_high", "pso_low"):
        if len({Decimal(row["policy"][field]) for row in payload["policies"]}) != 1:
            raise ValueError(f"Legacy {field} is global; use explicit per-item overrides")


@dataclass(frozen=True, slots=True)
class PreparedR1CurrentDay:
    """Internal R1 input produced solely from the immutable raw closure."""

    track_a: dict
    stock_balances: tuple[dict, ...]
    routes: tuple[dict, ...]
    stock_configuration: dict
    replenishment_exclusions: tuple[str, ...]
    additional_master: tuple[dict, ...]
    phase_out_membership: tuple[tuple[str, str], ...] = ()
    master_state: dict | None = None
    importer_validation: dict | None = None
    supplier_validation: dict | None = None
    supplier_state: dict | None = None
    daily_validation: dict | None = None
    daily_consumption: list | None = None
    vendor_codes: tuple[str, ...] | None = None
    calculation_payload: dict | None = None
    order_import_state: dict | None = None
    order_part_identity: dict | None = None
    _order_dependencies: _R1OrderDependencies | None = None


@dataclass(frozen=True, slots=True)
class _R1OrderDependencies:
    business_date: date
    master_keys: frozenset[tuple[str, str]]
    master_by_key: dict
    resolved_policies: dict
    route_nodes_by_sku: dict


@dataclass(frozen=True, slots=True)
class _PreparedR1OperationContext:
    """Opaque, operation-owned reuse of the validated order-free preparation."""

    prepared: PreparedR1CurrentDay
    _source_identity: int
    _dependency_fingerprint: bytes


def _fingerprint_value(checksum, value):
    """Type- and order-sensitive fingerprint without retaining a second graph."""
    kind = type(value)
    checksum.update(f'{kind.__module__}.{kind.__qualname__}:'.encode())
    if value is None:
        return
    if kind is bool:
        checksum.update(b'1' if value else b'0')
    elif kind is int:
        checksum.update(str(value).encode())
    elif kind is float:
        checksum.update(value.hex().encode())
    elif kind is str:
        raw = value.encode('utf-8')
        checksum.update(str(len(raw)).encode() + b':' + raw)
    elif kind is bytes:
        checksum.update(str(len(value)).encode() + b':' + value)
    elif kind is Decimal:
        checksum.update(str(value).encode())
    elif kind in (date, datetime):
        checksum.update(value.isoformat().encode())
    elif kind is dict:
        checksum.update(str(len(value)).encode() + b'{')
        for key, child in value.items():
            _fingerprint_value(checksum, key)
            _fingerprint_value(checksum, child)
        checksum.update(b'}')
    elif kind in (list, tuple):
        checksum.update(str(len(value)).encode() + b'[')
        for child in value:
            _fingerprint_value(checksum, child)
        checksum.update(b']')
    else:
        raise TypeError(f'Unsupported R1 operation dependency type: {kind.__name__}')


def _dependency_fingerprint(payload):
    checksum = hashlib.sha256()
    checksum.update(str(len(payload) - ('orders' in payload)).encode() + b'{')
    for key, value in payload.items():
        if key != 'orders':
            _fingerprint_value(checksum, key)
            _fingerprint_value(checksum, value)
    checksum.update(b'}')
    return checksum.digest()


def _prepare_r1_operation_context(payload):
    """Prepare an order-free operation source once for its connected order owner."""
    if payload.get('orders') != []:
        raise ValueError('R1 operation context requires its order-free timeline source')
    prepared = prepare_r1_current_day(payload)
    if prepared._order_dependencies is None:
        raise ValueError('R1 operation context requires standard prepared dependencies')
    return _PreparedR1OperationContext(
        prepared=prepared,
        _source_identity=id(payload),
        _dependency_fingerprint=_dependency_fingerprint(payload),
    )


def calculation_order_rows(closing):
    """Project the actual order owner; repeated customer IDs remain distinct parts."""
    rows = closing['SpikeOrderData']
    ids = [r['CustomerOrderId'] for r in rows]
    multipart = len(ids) != len(set(ids))
    return [dict(order_id=str(r['OrderKey']) if multipart else r['CustomerOrderId'],
        sku_code=r['SKUCode'],location_code=r['WhCode'],outstanding_quantity=r['Qty'],
        accepted_on=r['IntroDate'],customer_expected_date=r['CustomerExpectedDate'],
        established_is_spike=r['IsSpike'],established_due_date=r['DueDate'],
        first_servicing_location_code=r['FirstServicingWhCode'],established_order_key=r['OrderKey'])
        for r in rows]


def prepare_owned_order_current_day(payload, closing):
    """Internal daily producer connection; this metadata is never a raw input field."""
    if 'order_input' in payload or payload['orders'] != calculation_order_rows(closing):
        raise ValueError('Owned order calculation projection drift')
    rows = closing['SpikeOrderData']
    keys = [r['OrderKey'] for r in rows]
    if len(keys) != len(set(keys)):
        raise ValueError('Duplicate owned order keys')
    prepared = prepare_r1_current_day(payload, _order_types_reconciled=True)
    ids = [r['CustomerOrderId'] for r in rows]
    if len(ids) == len(set(ids)):
        return prepared
    identity = {str(r['OrderKey']): dict(order_id=r['CustomerOrderId'],
                order_key=r['OrderKey'],part_id=r['PartId']) for r in rows}
    return replace(prepared, order_part_identity=identity)


def _consume_r1_operation_context(context, payload, closing):
    """Consume an opaque preparation after the connected order stage completes."""
    if type(context) is not _PreparedR1OperationContext or context._source_identity != id(payload):
        raise ValueError('Owned R1 preparation context does not belong to this operation source')
    if context._dependency_fingerprint != _dependency_fingerprint(payload):
        raise ValueError('Owned R1 preparation dependency drift')
    projected = calculation_order_rows(closing)
    if 'order_input' in payload or payload['orders'] != projected:
        raise ValueError('Owned order calculation projection drift')
    rows = closing['SpikeOrderData']
    keys = [row['OrderKey'] for row in rows]
    if len(keys) != len(set(keys)):
        raise ValueError('Duplicate owned order keys')
    dependencies = context.prepared._order_dependencies
    orders_by_key, routed_due, routes = _prepare_r1_orders(
        payload['orders'], dependencies, order_types_reconciled=True)
    nodes = []
    for node in context.prepared.track_a['nodes']:
        key = (node['sku_code'], node['location_code'])
        nodes.append({**node, 'orders': orders_by_key[key],
                      'routed_due_spike': format(routed_due[key], 'f')})
    prepared = replace(
        context.prepared,
        track_a={**context.prepared.track_a, 'nodes': nodes},
        routes=tuple(routes),
    )
    ids = [row['CustomerOrderId'] for row in rows]
    if len(ids) == len(set(ids)):
        return prepared
    identity = {str(row['OrderKey']): dict(order_id=row['CustomerOrderId'],
                order_key=row['OrderKey'], part_id=row['PartId']) for row in rows}
    return replace(prepared, order_part_identity=identity)


def _prepare_r1_orders(orders, dependencies, *, order_types_reconciled):
    """Calculate only fields whose real source is the current owned order state."""
    from mta.domain.demand import ThresholdPolicy, classify_spike
    from mta.domain.r1_current_day import _RouteLookup, route_established_spike_order, route_new_spike_order

    business_date = dependencies.business_date
    master_keys = dependencies.master_keys
    master_by_key = dependencies.master_by_key
    resolved_policies = dependencies.resolved_policies
    route_nodes_by_sku = dependencies.route_nodes_by_sku
    orders_by_key = {key: [] for key in master_keys}
    routed_due = {key: Decimal('0') for key in master_keys}
    routes = []
    seen_orders = set()
    route_indexes, route_nodes = {}, {}
    for order in orders:
        key = (order['sku_code'], order['location_code'])
        if key not in master_keys or order['order_id'] in seen_orders:
            raise ValueError('Raw order lies outside R1 closure or duplicates an order ID')
        seen_orders.add(order['order_id'])
        accepted = date.fromisoformat(order['accepted_on'])
        expected = (date.fromisoformat(order['customer_expected_date'])
                    if order['customer_expected_date'] is not None else None)
        if accepted > business_date:
            raise ValueError('Raw order is accepted after the R1 business date')
        established = order['established_is_spike']
        if established is None and accepted != business_date:
            raise ValueError('Existing raw order must retain its established Spike classification')
        policy = resolved_policies[key]
        threshold_policy = ThresholdPolicy(**{
            name: None if value is None and name.endswith('_override') else Decimal(value)
            for name, value in policy.items()
        })
        is_spike = (established is True if order_types_reconciled and established is not None
                    else established is True or classify_spike(
                        Decimal(order['outstanding_quantity']),
                        Decimal(master_by_key[key]['base_norm']), threshold_policy))
        routed = None
        due = expected or business_date
        if is_spike and key[0] not in route_nodes:
            route_nodes[key[0]] = tuple(route_nodes_by_sku[key[0]])
            route_indexes[key[0]] = _RouteLookup(route_nodes[key[0]])
        if is_spike and established is not True:
            routed = route_new_spike_order(
                business_date=business_date, order_id=order['order_id'], sku_code=key[0],
                source_location_code=key[1], quantity=Decimal(order['outstanding_quantity']),
                customer_expected_date=expected, nodes=route_nodes[key[0]], _route_lookup=route_indexes[key[0]],
            )
            due = routed.due_date
        elif is_spike:
            due = date.fromisoformat(order['established_due_date'])
            routed = route_established_spike_order(
                order_id=order['order_id'], sku_code=key[0], source_location_code=key[1],
                first_servicing_location_code=order['first_servicing_location_code'],
                due_date=due, nodes=route_nodes[key[0]], _route_lookup=route_indexes[key[0]],
            )
        if routed is not None:
            for route_row in routed.route:
                routes.append({
                    'order_id': routed.order_id, 'sku_code': routed.sku_code,
                    'source_location_code': routed.source_location_code,
                    'first_servicing_location_code': routed.first_servicing_location_code,
                    **route_row,
                })
            for route_row in routed.route:
                if date.fromisoformat(str(route_row['due_date'])) <= business_date:
                    destination = route_row['child_location_code']
                    route_key = (key[0], destination) if destination is not None else None
                    if route_key in routed_due:
                        routed_due[route_key] += Decimal(order['outstanding_quantity'])
                    break
        orders_by_key[key].append({
            'order_id': order['order_id'], 'quantity': order['outstanding_quantity'],
            'accepted_on': order['accepted_on'], 'due_date': due.isoformat(), 'is_spike': is_spike,
        })
    return orders_by_key, routed_due, routes


def prepare_r1_current_day(
    payload: dict,
    *,
    reservation_type: int | None = None,
    reservation_for_rationing_only: bool | None = None,
    _order_types_reconciled: bool = False,
) -> PreparedR1CurrentDay:
    """Construct Track A's historical seam input from source-shaped R1 facts.

    This is deliberately an adapter, not an alternate demand calculation.
    It derives adjusted stock and new-Spike routes before Track A sees any
    values, retaining raw payload ownership and stable checkpoint rows for the
    later persisted R1 run.
    """
    validate_r1_raw_input(payload, _order_types_reconciled=_order_types_reconciled)
    if 'order_input' in payload:
        from mta.application.r1_order_input import reconcile_order_feed
        skeleton = deepcopy({k:v for k,v in payload.items() if k != 'order_input'})
        base = prepare_r1_current_day(skeleton, reservation_type=reservation_type,
                                     reservation_for_rationing_only=reservation_for_rationing_only)
        day = payload['foundation']['snapshot']['business_date']
        thresholds = {(r['sku_code'],r['location_code']):r['spike_threshold_percent']
                      for r in base.additional_master}
        attributes = (base.importer_validation['tables']['SkuAttributeData'] if base.importer_validation is not None
                      else payload['order_input'].get('sku_attributes', []))
        caps = {r['SKUCode']:r['ElephantOrderCapping'] for r in attributes}
        masters = [dict(SKUCode=r['sku_code'],WhCode=r['location_code'],Norm=r['base_norm'],
                        SpikeThreshold=thresholds[(r['sku_code'],r['location_code'])],
                        **({'ElephantOrderCapping':caps[r['sku_code']]} if r['sku_code'] in caps else {}))
                   for r in base.track_a['foundation']['sku_locations']]
        imported = reconcile_order_feed(payload['order_input'], masters, day)
        if any(r['OrderKey'] is None for r in imported['orders']):
            raise ValueError('New order identity connection remains unverified in separate-feed entry')
        ids = [r['CustomerOrderId'] for r in payload['order_input']['opening_orders']]
        multipart = len(ids) != len(set(ids)) or "identity_last_value" in payload["order_input"]
        generated_spike_keys = []
        if multipart and imported['new_spikes']:
            if 'identity_last_value' not in payload['order_input']:
                raise ValueError('Generated Spike identities require an explicit owned counter')
            from mta.domain.order_identity import next_keys
            # The approved production contract assigns the filtered Spike
            # subset in feed order, after the newly inserted ordinary subset.
            last = max([payload['order_input']['identity_last_value']] +
                       [r['OrderKey'] for r in imported['orders']])
            generated_spike_keys = list(next_keys(last, len(imported['new_spikes'])))
        elif len(imported['new_spikes']) > 1:
            raise ValueError('Multiple generated Spike identities require an explicit owned counter')
        # Canonical routes and quantity remainders belong to OrderKey, not to
        # CustomerOrderId. Internal keys never replace customer identity at the
        # persisted consumer boundary. Preserve the existing single-order seam.
        identity = {str(r['OrderKey']): dict(order_id=r['CustomerOrderId'],
                    order_key=r['OrderKey'], part_id=r['PartId'])
                    for r in imported['orders']} if multipart else None
        for generated_key, row in zip(generated_spike_keys, imported['new_spikes']):
            identity[str(generated_key)] = dict(order_id=row['CustomerOrderId'],order_key=generated_key,part_id=1)
        effective = deepcopy(base.calculation_payload or skeleton)
        effective['orders'] = [dict(order_id=str(r['OrderKey']) if multipart else r['CustomerOrderId'],sku_code=r['SKUCode'],location_code=r['WhCode'],
            outstanding_quantity=r['Qty'],accepted_on=r['IntroDate'],customer_expected_date=r['CustomerExpectedDate'],
            established_is_spike=bool(r['IsSpike']),established_due_date=r['DueDate'],
            first_servicing_location_code=r['FirstServicingWhCode'],established_order_key=r['OrderKey'])
            for r in imported['orders']]
        effective['orders'].extend(dict(order_id=str(generated_spike_keys[index]) if generated_spike_keys else r['CustomerOrderId'],sku_code=r['SKUCode'],location_code=r['WhCode'],
            outstanding_quantity=r['Qty'],accepted_on=day,customer_expected_date=r['CustomerExpectedDate'],
            established_is_spike=None,established_due_date=None,first_servicing_location_code=None)
            for index,r in enumerate(imported['new_spikes']))
        calculated = prepare_r1_current_day(effective, reservation_type=reservation_type,
                                           reservation_for_rationing_only=reservation_for_rationing_only,
                                           _order_types_reconciled=True)
        if base.daily_consumption is not None:
            # The calculation view contains master nodes only. Keep the validated
            # daily population outside that master when composing the order feed,
            # just as the ordinary daily entry does; never fabricate master rows.
            from mta.application.r1_daily_entry import auxiliary_stock_balances
            auxiliary = auxiliary_stock_balances(base.daily_consumption, calculated.stock_balances,
                base.importer_validation['tables']['SkuLocAttributeData'], day)
            calculated = replace(calculated, stock_balances=calculated.stock_balances + auxiliary)
        return replace(calculated, calculation_payload=effective, order_import_state=imported,
                       order_part_identity=identity,
                       importer_validation=base.importer_validation,supplier_validation=base.supplier_validation,
                       supplier_state=base.supplier_state,daily_validation=base.daily_validation,
                       daily_consumption=base.daily_consumption,vendor_codes=base.vendor_codes)
    if payload["schema"] in {RAW_SUPPLIER_SCHEMA, RAW_DAILY_SCHEMA}:
        entry = payload["raw_master_entry"]
        validation = process_importer_master(entry)
        suppliers = process_supplier_validation(payload["raw_supplier_entry"], validation, entry["settings"], entry["run_timestamp"])
        failed = next((name for name, result in suppliers.items() if result['outcome'] == 'SQL_ERROR'), None)
        if failed is not None:
            raise R1EntryFailure('R1 supplier SQL_ERROR: ' + failed,
                                 stage='supplier_validation:' + failed, evidence=suppliers)
        daily, daily_consumption = None, None
        if payload["schema"] == RAW_DAILY_SCHEMA:
            daily_master = deepcopy(validation)
            for table in ("SiteDescriptionTbl", "RejectedMaster"):
                daily_master["tables"][table] = suppliers[STAGES[-1]]["tables"][table]
            daily = process_daily_validation(payload["raw_daily_entry"], daily_master, entry["business_date"], entry["run_timestamp"])
            daily_consumption = generated_bpr_daily_state(payload, daily)
            payload = generated_daily_view(payload, validation, daily)
        state, prior, refreshed = supplier_calculation_state(
            {k: payload["supplier_state"][k] for k in OPENING_TABLES}, suppliers[STAGES[-1]]["tables"],
            validation["tables"]["MasterData"], vendor_codes=payload["vendor_codes"])
        skeleton = master_input_skeleton(payload)
        skeleton.update(sourcing=refreshed, supplier_openings=prior)
        view = generated_master_view(skeleton, validation)
        prepared = prepare_r1_current_day(view, reservation_type=reservation_type,
                                         reservation_for_rationing_only=reservation_for_rationing_only)
        if daily_consumption is not None:
            from mta.application.r1_daily_entry import auxiliary_stock_balances
            auxiliary = auxiliary_stock_balances(daily_consumption, prepared.stock_balances,
                validation['tables']['SkuLocAttributeData'], entry['business_date'])
            prepared = replace(prepared, stock_balances=prepared.stock_balances + auxiliary)
        return replace(prepared, importer_validation=validation, supplier_validation=suppliers,
                       supplier_state=state, daily_validation=daily, daily_consumption=daily_consumption,
                       vendor_codes=tuple(payload["vendor_codes"]), calculation_payload=view)
    if payload["schema"] == RAW_MASTER_SCHEMA:
        validation = process_importer_master(payload["raw_master_entry"])
        view = generated_master_view(payload, validation)
        prepared = prepare_r1_current_day(view, reservation_type=reservation_type,
                                         reservation_for_rationing_only=reservation_for_rationing_only)
        return replace(prepared, importer_validation=validation, calculation_payload=view)
    master_state = None
    phase_out_membership = ()
    if payload["schema"] == MASTER_SCHEMA:
        phase_out_membership = tuple((row['SKUCode'], row['WhCode'])
                                     for row in payload['master_state'].get('phase_out_membership', []))
        master_state = reconcile_master_state(payload, _order_types_reconciled=_order_types_reconciled)
        # Modern calculations consume the exported importer state. The oracle
        # still projects/seeds original source facts independently.
        effective = deepcopy(payload)
        changed = {(r['sku_code'], r['location_code']): r for r in master_state['importer_master']}
        for row in effective['master_state']['importer_master']:
            row.update(norm=changed[(row['sku_code'], row['location_code'])]['norm'],
                       min_norm=changed[(row['sku_code'], row['location_code'])]['min_norm'])
        payload = source_calculation_view(effective, _order_types_reconciled=_order_types_reconciled)
    stock_configuration = resolve_r1_stock_configuration(
        payload, reservation_type=reservation_type,
        reservation_for_rationing_only=reservation_for_rationing_only,
    )
    from mta.domain.r1_current_day import RouteNode, calculate_stock_balances

    foundation = payload["foundation"]
    required_foundation = {
        "snapshot", "skus", "locations", "sku_locations", "hierarchy",
        "inventory_positions", "orders", "norm_controls",
    }
    if not isinstance(foundation, dict) or set(foundation) != required_foundation:
        raise ValueError("R1 foundation must be the canonical order-free closure")
    if foundation["orders"] or foundation["norm_controls"]:
        raise ValueError("R1 raw orders and controls must have one owner outside foundation")
    validate_r1_source_consistency(payload)
    business_date = date.fromisoformat(foundation["snapshot"]["business_date"])
    master_keys = {(row["sku_code"], row["location_code"]) for row in foundation["sku_locations"]}
    if not master_keys or master_keys != {
        (row["sku_code"], row["location_code"]) for row in foundation["inventory_positions"]
    }:
        raise ValueError("R1 master/inventory closure is incomplete")
    if any((source["sku_code"], source["location_code"]) not in master_keys
           for source in payload["sourcing"]):
        raise ValueError("R1 sourcing lies outside the master closure")
    stock_openings = raw_stock_opening_records(payload)
    opening_keys = {(row.sku_code, row.location_code) for row in stock_openings}
    if opening_keys != master_keys:
        raise ValueError("R1 raw stock-opening closure must match master grain")
    balances = calculate_stock_balances(
        stock_openings,
        **stock_configuration,
    )
    balance_by_key = {(row.sku_code, row.location_code): row for row in balances}
    master_by_key = {(row["sku_code"], row["location_code"]): row for row in foundation["sku_locations"]}
    policy_by_key: dict[tuple[str, str], dict] = {}
    for row in payload["policies"]:
        if not isinstance(row, dict) or set(row) - {"sku_code", "location_code", "policy", "controls", "rationing_priority"}:
            raise ValueError("Invalid R1 policy row")
        key = (row.get("sku_code"), row.get("location_code"))
        if key not in master_keys or key in policy_by_key or not isinstance(row.get("policy"), dict):
            raise ValueError("R1 policy coverage is invalid")
        policy_by_key[key] = row
    if set(policy_by_key) != master_keys:
        raise ValueError("R1 requires exactly one policy row per SKU/location")
    dbm_foundation = foundation
    if master_state is not None:
        dbm_foundation = deepcopy(foundation)
        dbm_norms = {(r["sku_code"], r["location_code"]): r["norm"] for r in master_state["dbm_master"]}
        for row in dbm_foundation["sku_locations"]:
            row["base_norm"] = dbm_norms[(row["sku_code"], row["location_code"])]
    additional_master = calculate_additional_master(dbm_foundation, payload["policies"])
    additional_by_key = {(row["sku_code"], row["location_code"]): row for row in additional_master}
    parents = {(row["sku_code"], row["child_location_code"]): row["parent_location_code"] for row in foundation["hierarchy"]}
    resolved_policies = {
        key: {**policy_by_key[key]["policy"],
              "spike_override": additional_by_key[key]["spike_threshold_percent"],
              "pso_override": additional_by_key[key]["pso_threshold_percent"]}
        for key in master_keys
    }
    route_nodes_by_sku: dict[str, list[RouteNode]] = {}
    for row in payload["routing"]:
        required = {
            "sku_code", "location_code", "has_bpr_master", "norm",
            "spike_threshold_percent", "parent_location_code", "rlt_to_parent_days",
        }
        if not isinstance(row, dict) or set(row) != required or type(row["has_bpr_master"]) is not bool:
            raise ValueError("Invalid R1 routing row")
        key = (row["sku_code"], row["location_code"])
        physical = key in master_by_key
        route_nodes_by_sku.setdefault(row["sku_code"], []).append(RouteNode(
            location_code=row["location_code"], has_bpr_master=row["has_bpr_master"],
            norm=Decimal(master_by_key[key]["base_norm"]) if physical else None,
            spike_threshold_percent=Decimal(additional_by_key[key]["spike_threshold_percent"]) if physical else None,
            parent_location_code=parents.get(key) if physical else row["parent_location_code"],
            rlt_to_parent_days=master_by_key[key]["replenishment_lead_time_days"] if physical and key in parents else row["rlt_to_parent_days"],
        ))
    route_locations_by_sku = {sku: {node.location_code for node in nodes}
                              for sku, nodes in route_nodes_by_sku.items()}
    for sku, location in master_keys:
        if sku not in route_locations_by_sku or location not in route_locations_by_sku[sku]:
            raise ValueError("R1 routing must cover every master SKU/location")
    order_dependencies = _R1OrderDependencies(
        business_date=business_date,
        master_keys=frozenset(master_keys),
        master_by_key=master_by_key,
        resolved_policies=resolved_policies,
        route_nodes_by_sku=route_nodes_by_sku,
    )
    orders_by_key, routed_due, routes = _prepare_r1_orders(
        payload['orders'], order_dependencies,
        order_types_reconciled=_order_types_reconciled)
    nodes = []
    for key in sorted(master_keys):
        policy_row, balance = policy_by_key[key], balance_by_key[key]
        nodes.append({
            "sku_code": key[0], "location_code": key[1], "policy": resolved_policies[key],
            "controls": policy_row.get("controls", []), "orders": orders_by_key[key],
            "stock_for_requirement": format(balance.stock_for_requirement, "f"),
            "routed_due_spike": format(routed_due[key], "f"),
            "rationing_priority": policy_row.get("rationing_priority", 999999),
        })
    return PreparedR1CurrentDay(
        master_state=master_state,
        stock_configuration=stock_configuration,
        replenishment_exclusions=resolve_r1_replenishment_exclusions(payload),
        additional_master=additional_master,
        phase_out_membership=phase_out_membership,
        track_a={"schema": "track-a-v1", "mode": 0, "foundation": foundation, "nodes": nodes, "rationing": {"enabled": True}},
        stock_balances=tuple({
            "sku_code": row.sku_code, "location_code": row.location_code,
            "stock_for_requirement": format(row.stock_for_requirement, "f"),
            "stock_for_rationing": format(row.stock_for_rationing, "f"),
            "reserved_stock": format(row.reserved_stock, "f"),
        } for row in balances),
        routes=tuple(routes),
        _order_dependencies=order_dependencies,
    )
