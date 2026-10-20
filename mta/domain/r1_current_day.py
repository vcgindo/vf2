"""Pure current-day MTA primitives recovered for the R1 spine.

The existing Track A boundary accepts an adjusted stock balance and a routed
Spike quantity.  That is useful for the historical Stage 6 seam, but it is
not an acceptable entry point for R1.  This module ports the source-shaped
pieces that create those values, without depending on a database or on a
legacy SQL runtime.

Sources:
* ``StockCalculation.sql`` -- stock-for-requirement/rationing reservation;
* ``CalculateDD.sql`` and ``CalculateRoute.sql`` -- first-service and route;
* ``GenerateBifurcationOfRationedReq.sql`` -- Pick-list colour buckets.

The functions intentionally expose an explicit, small contract.  A caller
must supply the opening facts used by the legacy scripts; it cannot smuggle in
post-calculation stock, bands, or rationed buckets.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, ROUND_CEILING

from mta.domain.validation import RuleBlocked


ZERO = Decimal("0")
NO_PERCENT_RESERVATION = 0
STOCK_PERCENT_RESERVATION = 1
NORM_PERCENT_RESERVATION = 2
ROUTE_SOURCE_LIMIT = 100  # CalculateRoute.sql stops after 100 iterations.


def _decimal(value: object, label: str, *, non_negative: bool = True) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (str, int, Decimal)):
        raise ValueError(f"{label} must be an exact integer or decimal")
    result = Decimal(value)
    if not result.is_finite() or (non_negative and result < ZERO):
        raise ValueError(f"{label} must be finite" + (" and non-negative" if non_negative else ""))
    return result


def _integer(value: object, label: str) -> Decimal:
    result = _decimal(value, label)
    if result != result.to_integral_value():
        raise ValueError(f"{label} must be an integer")
    return result


def _signed_integer(value: object, label: str) -> Decimal:
    result = _decimal(value, label, non_negative=False)
    if result != result.to_integral_value():
        raise ValueError(f"{label} must be an integer")
    return result


def _text(value: Decimal) -> str:
    return format(value, "f")


def _ceil(value: Decimal) -> Decimal:
    return value.to_integral_value(rounding=ROUND_CEILING)


@dataclass(frozen=True, slots=True)
class StockOpening:
    """Raw stock and reservation facts for one SKU/location/day.

    ``stock_for_requirement_override`` and ``stock_for_rationing_override``
    are source facts from the two importer input tables, not calculations made
    by another MTA stage.  The names deliberately retain their legacy meaning.
    """

    sku_code: str
    location_code: str
    stock: Decimal
    norm: Decimal
    utilized_stock: Decimal | None = ZERO
    stock_for_requirement_override: Decimal | None = None
    stock_for_rationing_override: Decimal | None = None
    stock_percent_reservation: Decimal = ZERO
    norm_percent_reservation: Decimal = ZERO


@dataclass(frozen=True, slots=True)
class StockBalances:
    sku_code: str
    location_code: str
    stock_for_requirement: Decimal
    stock_for_rationing: Decimal
    reserved_stock: Decimal


def calculate_stock_balances(
    openings: tuple[StockOpening, ...],
    *,
    reservation_type: int,
    reservation_for_rationing_only: bool,
) -> tuple[StockBalances, ...]:
    """Port ``StockCalculation.sql`` for a closed set of opening facts.

    This preserves source ordering: importer requirement override, absolute
    utilized-stock deduction, percentage reservation, then optional rationing
    override.  Requirement stock is deliberately not clamped—the source only
    clamps the provisional rationing balance.
    """
    if type(reservation_type) is not int or reservation_type not in {
        NO_PERCENT_RESERVATION, STOCK_PERCENT_RESERVATION, NORM_PERCENT_RESERVATION,
    }:
        raise ValueError("Unknown legacy stock reservation type")
    if type(reservation_for_rationing_only) is not bool:
        raise ValueError("reservation_for_rationing_only must be boolean")
    seen: set[tuple[str, str]] = set()
    output: list[StockBalances] = []
    for opening in openings:
        if not opening.sku_code or not opening.location_code:
            raise ValueError("SKU and location are required")
        key = (opening.sku_code, opening.location_code)
        if key in seen:
            raise ValueError("Duplicate stock opening grain")
        seen.add(key)
        stock = _integer(opening.stock, "stock")
        norm = _integer(opening.norm, "norm")
        # StockCalculation.sql applies ISNULL(UtilizedStock, 0) in both the
        # rationing deduction and the optional requirement-stock deduction.
        utilized = (ZERO if opening.utilized_stock is None
                    else _integer(opening.utilized_stock, "utilized stock"))
        requirement = stock if opening.stock_for_requirement_override is None else _signed_integer(
            opening.stock_for_requirement_override, "stock-for-requirement override"
        )
        if not reservation_for_rationing_only:
            requirement -= utilized
        provisional_rationing = max(stock - utilized, ZERO)
        if reservation_type == NORM_PERCENT_RESERVATION:
            reserve = min(
                provisional_rationing,
                norm * _decimal(opening.norm_percent_reservation, "norm percent reservation") / 100,
            )
        elif reservation_type == STOCK_PERCENT_RESERVATION:
            reserve = provisional_rationing * (
                100 - _decimal(opening.stock_percent_reservation, "stock percent reservation")
            ) / 100
        else:
            # R1-04 selected GulfOil setting0: canonical StockCalculation.sql
            # initializes ReservedStock=0; neither percentage IF executes.
            reserve = ZERO
        # Intermediate.ReservedStock is SQL int: the assignment truncates the
        # percentage result toward zero before subtraction (not after it).
        reserve = Decimal(int(reserve))
        rationing = provisional_rationing - reserve
        if opening.stock_for_rationing_override is not None:
            # AdditionalDailyData.StockForRationing is a nullable SQL int.
            # The unchanged SQL applies this override after its provisional
            # non-negative clamp, so a negative source override stays negative.
            rationing = _signed_integer(opening.stock_for_rationing_override, "stock-for-rationing override")
        output.append(StockBalances(*key, requirement, rationing, reserve))
    return tuple(output)


@dataclass(frozen=True, slots=True)
class RouteNode:
    """One raw hierarchy node required by ``CalculateDD``/``CalculateRoute``.

    A node without a BPR master is the source's plant/supplier stop condition.
    ``rlt_to_parent_days`` belongs to the edge from this node to its parent.
    """

    location_code: str
    has_bpr_master: bool
    norm: Decimal | None
    spike_threshold_percent: Decimal | None
    parent_location_code: str | None
    rlt_to_parent_days: int | None


@dataclass(frozen=True, slots=True)
class RoutedSpikeOrder:
    order_id: str
    sku_code: str
    source_location_code: str
    first_servicing_location_code: str
    due_date: date
    route: tuple[dict[str, str | None], ...]


def route_new_spike_order(
    *,
    business_date: date,
    order_id: str,
    sku_code: str,
    source_location_code: str,
    quantity: Decimal,
    customer_expected_date: date | None,
    nodes: tuple[RouteNode, ...],
) -> RoutedSpikeOrder:
    """Port the first-service/DueDate and route construction for one new Spike.

    The route is ordered from customer/source towards first service.  Each
    entry uses the same backward date adjustment as ``CalculateRoute.sql``.
    Existing orders are intentionally out of scope: their established first
    service and due date are historical opening state and must be supplied as
    such by the later orchestration adapter.
    """
    if not isinstance(business_date, date) or (customer_expected_date is not None and not isinstance(customer_expected_date, date)):
        raise ValueError("business date and an optional customer-expected date are required")
    if not order_id or not sku_code or not source_location_code:
        raise ValueError("order, SKU and source location are required")
    quantity = _integer(quantity, "order quantity")
    if quantity <= ZERO:
        raise ValueError("order quantity must be positive")
    node_by_location = {node.location_code: node for node in nodes}
    if len(node_by_location) != len(nodes) or source_location_code not in node_by_location:
        raise ValueError("Route nodes must be unique and include the source location")
    chain: list[RouteNode] = []
    accumulated_rlt = 0
    current = source_location_code
    visited: set[str] = set()
    while True:
        if current in visited:
            raise ValueError("Cyclic Spike route")
        if len(chain) >= ROUTE_SOURCE_LIMIT:
            raise RuleBlocked("R1_ROUTE_SOURCE_LIMIT", "CalculateRoute.sql stops after 100 route nodes; deeper paths are not certified")
        visited.add(current)
        node = node_by_location[current]
        chain.append(node)
        stop = not node.has_bpr_master
        if node.has_bpr_master:
            if node.norm is None or node.spike_threshold_percent is None:
                raise ValueError("BPR route node requires Norm and Spike threshold")
            threshold = _ceil(
                _integer(node.norm, "route Norm")
                * _decimal(node.spike_threshold_percent, "Spike threshold")
                / 100
            )
            stop = quantity <= threshold
        if stop:
            break
        if node.parent_location_code is None or node.rlt_to_parent_days is None:
            raise ValueError("No evidence-backed parent/RLT exists before first service")
        if node.rlt_to_parent_days < 0:
            raise ValueError("Route RLT must be non-negative")
        if node.parent_location_code not in node_by_location:
            raise ValueError("Route parent is outside the declared hierarchy closure")
        accumulated_rlt += node.rlt_to_parent_days
        current = node.parent_location_code
    # The recovered CalculateDD.sql uses the RLT date when the legacy
    # OPEN_SALES_ORDER import leaves CustomerExpectedDate NULL.
    minimum_due_date = business_date + timedelta(days=accumulated_rlt)
    due_date = max(customer_expected_date, minimum_due_date) if customer_expected_date else minimum_due_date
    route: list[dict[str, str | None]] = []
    date_at_current = due_date
    for index, node in enumerate(chain):
        route.append({
            "location_code": node.location_code,
            "child_location_code": None if index == 0 else chain[index - 1].location_code,
            "due_date": date_at_current.isoformat(),
        })
        if index + 1 < len(chain):
            edge = node.rlt_to_parent_days
            assert edge is not None  # checked above before the parent was followed
            date_at_current -= timedelta(days=edge)
    return RoutedSpikeOrder(
        order_id, sku_code, source_location_code, chain[-1].location_code, due_date, tuple(route)
    )


def route_established_spike_order(
    *,
    order_id: str,
    sku_code: str,
    source_location_code: str,
    first_servicing_location_code: str,
    due_date: date,
    nodes: tuple[RouteNode, ...],
) -> RoutedSpikeOrder:
    """Port ``CalculateRoute.sql`` for an already-classified Spike order.

    ``CalculateDD.sql`` deliberately retains an established order's historical
    DueDate and first-service node.  ``CalculateRoute.sql`` still rebuilds the
    route from those source facts, moving the due date backwards by each RLT
    edge until that first-service node is reached.
    """
    if not isinstance(due_date, date):
        raise ValueError("Established Spike due date is required")
    if not all((order_id, sku_code, source_location_code, first_servicing_location_code)):
        raise ValueError("Established Spike identity and first service are required")
    node_by_location = {node.location_code: node for node in nodes}
    if len(node_by_location) != len(nodes) or source_location_code not in node_by_location:
        raise ValueError("Established Spike route lies outside the declared hierarchy closure")
    current, date_at_current = source_location_code, due_date
    child_location_code: str | None = None
    visited: set[str] = set()
    route: list[dict[str, str | None]] = []
    while True:
        if current in visited:
            raise ValueError("Cyclic established Spike route")
        if len(route) >= ROUTE_SOURCE_LIMIT:
            raise RuleBlocked("R1_ROUTE_SOURCE_LIMIT", "CalculateRoute.sql stops after 100 route nodes; deeper paths are not certified")
        visited.add(current)
        route.append({
            "location_code": current,
            "child_location_code": child_location_code,
            "due_date": date_at_current.isoformat(),
        })
        # Retained identifiers use the selected ASCII SQL collation: case and
        # trailing spaces do not turn an on-path historical node into a fallback.
        if current.rstrip(" ").upper() == first_servicing_location_code.rstrip(" ").upper():
            break
        node = node_by_location[current]
        # CalculateRoute.sql retains the historical first-service field when
        # hierarchy changes, but walks the current route to the supplier/plant.
        if not node.has_bpr_master and node.parent_location_code is None:
            break
        if node.parent_location_code is None or node.rlt_to_parent_days is None:
            raise ValueError("Established Spike reaches no declared first-service node")
        if node.rlt_to_parent_days < 0 or node.parent_location_code not in node_by_location:
            raise ValueError("Established Spike route has invalid parent/RLT")
        child_location_code, current = current, node.parent_location_code
        date_at_current -= timedelta(days=node.rlt_to_parent_days)
    return RoutedSpikeOrder(
        order_id, sku_code, source_location_code, first_servicing_location_code, due_date, tuple(route)
    )


@dataclass(frozen=True, slots=True)
class RationedRequirement:
    """The exact source fields used by the legacy ration-bifurcation SQL."""

    sku_code: str
    location_code: str
    parent_location_code: str
    virtual_norm: Decimal
    stock: Decimal
    goods_in_transit: Decimal
    rationed_quantity: Decimal


def bifurcate_rationed_requirement(row: RationedRequirement) -> dict[str, str]:
    """Port ``GenerateBifurcationOfRationedReq.sql`` for one report row."""
    if not row.sku_code or not row.location_code or not row.parent_location_code:
        raise ValueError("SKU, location and parent location are required")
    virtual_norm = _integer(row.virtual_norm, "virtual Norm")
    stock = _integer(row.stock, "stock")
    git = _integer(row.goods_in_transit, "GIT")
    rationed = _integer(row.rationed_quantity, "rationed quantity")
    inventory = stock + git
    if virtual_norm == 1:
        tor = rationed
        toy = tog = ZERO
    else:
        red_boundary = virtual_norm / 3 - inventory
        tor = ZERO if red_boundary < ZERO else min(_ceil(red_boundary), rationed)
        yellow_boundary = virtual_norm * 2 / 3 - inventory
        toy = ZERO if yellow_boundary < ZERO else min(_ceil(yellow_boundary) - tor, rationed - tor)
        green_boundary = virtual_norm - inventory
        tog = ZERO if green_boundary < ZERO else min(_ceil(green_boundary) - tor - toy, rationed - tor - toy)
    # SQL clamps the two intermediate bands at the final update, before BLUE.
    toy, tog = max(toy, ZERO), max(tog, ZERO)
    black = tor if inventory == ZERO else ZERO
    red = tor if inventory > ZERO else ZERO
    blue = max(rationed - black - red - toy - tog, ZERO)
    return {
        "sku_code": row.sku_code,
        "location_code": row.location_code,
        "parent_location_code": row.parent_location_code,
        "to_black": _text(black),
        "to_red": _text(red),
        "to_yellow": _text(toy),
        "to_green": _text(tog),
        "to_blue": _text(blue),
    }


@dataclass(frozen=True, slots=True)
class PsoRationInput:
    """Raw/current-stage facts consumed by ``PSORationing.sql`` for one child.

    ``norm_requirement`` and ``normal_rationed_quantity`` are named outputs of
    the preceding normal-ration stage, not caller-selected final allocations.
    The R1 orchestrator must obtain them from its persisted normal-ration
    checkpoint.  Keeping the interface explicit prevents the old Stage 6
    aggregate RRR seam from being silently used as PSO rationing.
    """

    sku_code: str
    location_code: str
    parent_location_code: str
    residual_spike_pso: Decimal
    spike_pso_to_net_off: Decimal
    norm_requirement: Decimal
    total_requirement: Decimal
    normal_rationed_quantity: Decimal
    parent_stock: Decimal
    parent_pack_size: Decimal
    excluded_from_replenishment: bool = False
    normal_row_present: bool = True
    is_virtual: bool = False


@dataclass(frozen=True, slots=True)
class PsoRationAllocation:
    sku_code: str
    location_code: str
    parent_location_code: str
    starting_requirement: Decimal
    remaining_requirement: Decimal
    proportion_percent: Decimal
    proportional_allocation: Decimal
    pack_allocation: Decimal
    last_casepack_allocation: Decimal
    total_allocation: Decimal
    parent_leftover: Decimal


def allocate_spike_pso(
    rows: tuple[PsoRationInput, ...],
) -> tuple[PsoRationAllocation, ...]:
    """Port normal-MTA child allocation from ``PSORationing.sql``.

    This is the PSO/Spike allocation *after* normal rationing.  It follows the
    SQL's raw-proportion, floor, pack-rounding and final-casepack ordering.
    The recovered SQL resolves equal proportions with ``SKUCode, WhCode``;
    this port retains that deterministic source ordering.
    """
    prepared: list[dict[str, Decimal | str]] = []
    seen: set[tuple[str, str, str]] = set()
    for row in rows:
        if row.excluded_from_replenishment:
            continue
        if not row.sku_code or not row.location_code or not row.parent_location_code:
            raise ValueError("PSO rationing requires SKU, child and parent")
        key = (row.sku_code, row.location_code, row.parent_location_code)
        if key in seen:
            raise ValueError("Duplicate PSO rationing child grain")
        seen.add(key)
        residual = _integer(row.residual_spike_pso, "residual Spike/PSO")
        to_net_off = _integer(row.spike_pso_to_net_off, "Spike/PSO net-off")
        norm_requirement = _integer(row.norm_requirement, "norm requirement")
        total_requirement = _integer(row.total_requirement, "total requirement")
        normal_rationed = _integer(row.normal_rationed_quantity, "normal rationed quantity")
        # CollectDataForPSORationing retains signed adjusted stock unless a
        # normal-ration leftover replaces it. PSORationing only assigns a
        # positive proportional amount to RawAllocation; negative stock is
        # carried into the leftover, not an invalid order/demand quantity.
        parent_stock = _signed_integer(row.parent_stock, "parent stock")
        pack = _integer(row.parent_pack_size, "parent pack size")
        if pack <= ZERO:
            raise ValueError("Parent pack size must be positive")
        if row.is_virtual:
            starting, remaining = residual, max(residual - normal_rationed, ZERO)
        else:
            starting = residual if to_net_off == ZERO or not row.normal_row_present else max(norm_requirement + residual - normal_rationed, ZERO)
            remaining = max(starting - max(normal_rationed - total_requirement, ZERO), ZERO) if row.normal_row_present else starting
        remaining = _ceil(remaining / pack) * pack
        prepared.append({
            "sku_code": row.sku_code, "location_code": row.location_code,
            "parent_location_code": row.parent_location_code, "starting": starting,
            "remaining": remaining, "parent_stock": parent_stock, "pack": pack,
        })
    groups: dict[tuple[str, str], list[dict[str, Decimal | str]]] = {}
    for row in prepared:
        groups.setdefault((str(row["sku_code"]), str(row["parent_location_code"])), []).append(row)
    output: list[PsoRationAllocation] = []
    for (_, _), members in sorted(groups.items()):
        stocks = {Decimal(member["parent_stock"]) for member in members}
        packs = {Decimal(member["pack"]) for member in members}
        if len(stocks) != 1 or len(packs) != 1:
            raise ValueError("Parent stock and pack size must agree within a PSO group")
        parent_stock, pack = stocks.pop(), packs.pop()
        total_remaining = sum((Decimal(member["remaining"]) for member in members), ZERO)
        for member in members:
            remaining = Decimal(member["remaining"])
            proportion = ZERO if total_remaining == ZERO else remaining * 100 / total_remaining
            proportional = min(remaining, parent_stock * proportion / 100)
            raw = proportional.to_integral_value(rounding="ROUND_FLOOR") if proportional > ZERO else ZERO
            member["proportion"] = proportion
            member["proportional"] = proportional
            member["pack_allocation"] = (raw // pack) * pack
        allocated = sum((Decimal(member["pack_allocation"]) for member in members), ZERO)
        remaining_casepacks = (parent_stock - allocated) // pack
        candidates = [member for member in members if Decimal(member["remaining"]) > Decimal(member["pack_allocation"])]
        candidates.sort(key=lambda item: (
            -(Decimal(item["remaining"]) - Decimal(item["pack_allocation"])) / Decimal(item["remaining"]),
            str(item["sku_code"]), str(item["location_code"]),
        ))
        for priority, member in enumerate(candidates, 1):
            member["last_casepack"] = pack if priority <= remaining_casepacks else ZERO
        for member in members:
            member.setdefault("last_casepack", ZERO)
        group_total = sum((Decimal(member["pack_allocation"]) + Decimal(member["last_casepack"]) for member in members), ZERO)
        leftover = parent_stock - group_total
        for member in sorted(members, key=lambda item: (str(item["sku_code"]), str(item["location_code"]))):
            pack_allocation, last_casepack = Decimal(member["pack_allocation"]), Decimal(member["last_casepack"])
            output.append(PsoRationAllocation(
                str(member["sku_code"]), str(member["location_code"]), str(member["parent_location_code"]),
                Decimal(member["starting"]), Decimal(member["remaining"]), Decimal(member["proportion"]),
                Decimal(member["proportional"]), pack_allocation, last_casepack,
                pack_allocation + last_casepack, leftover,
            ))
    return tuple(output)
