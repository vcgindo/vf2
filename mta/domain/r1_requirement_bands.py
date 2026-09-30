"""Normal-MTA requirement colour-band allocation for the R1 spine.

This is the current-day, non-MTO path recovered from
``ReqInColorBand.sql``.  It retains the source order in which physical stock
is consumed: Order Black, Norm Black, Order Red, Norm Red, Order Yellow,
Norm Yellow, Order Green, Norm Green, then Order Blue.

Advance stock/GIT allocations are deliberately an input to neither this module
nor R1's public contract.  They belong to the preceding reservation port; R1
does not pretend that an absent allocation is zero in a scenario that needs it.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_CEILING


ZERO = Decimal("0")


def _integer(value: Decimal, label: str) -> Decimal:
    if not isinstance(value, Decimal) or not value.is_finite() or value < ZERO or value != value.to_integral_value():
        raise ValueError(f"{label} must be a non-negative integer Decimal")
    return value


def _ceil(value: Decimal) -> Decimal:
    return value.to_integral_value(rounding=ROUND_CEILING)


def _text(value: Decimal) -> str:
    return format(value, "f")


@dataclass(frozen=True, slots=True)
class RequirementBandInput:
    sku_code: str
    location_code: str
    parent_location_code: str | None
    norm: Decimal
    stock: Decimal
    goods_in_transit: Decimal
    pso: Decimal
    pso_threshold_percent: Decimal
    due_direct_spike: Decimal
    due_routed_spike: Decimal
    advance_order_blue: Decimal = ZERO
    # ``None`` means the legacy BPP producer is absent (primitive-only
    # callers retain the historical routed-Black fallback).  An empty tuple
    # means BPP ran but no Red/Yellow/Green source rows were eligible.
    routed_order_colours: tuple[tuple[str, Decimal], ...] | None = None
    excluded_from_parent_rollup: bool = False


def calculate_requirement_bands(
    rows: tuple[RequirementBandInput, ...], *,
    reference_parent_keys: frozenset[tuple[str, str]] = frozenset(),
) -> list[dict]:
    """Calculate persisted band populations from requirement/route facts.

    Child Norm and order requirements are folded into the parent's CNR and
    residual-order populations before the parent consumes its own inventory.
    ReqInColorBand excludes phase-out children from parent CNR and residual
    order rollup, while retaining the child's own output row.
    """
    by_key: dict[tuple[str, str], RequirementBandInput] = {}
    children: dict[tuple[str, str], list[tuple[str, str]]] = {}
    for row in rows:
        if not row.sku_code or not row.location_code:
            raise ValueError("Requirement band SKU and location are required")
        key = (row.sku_code, row.location_code)
        if key in by_key:
            raise ValueError("Duplicate requirement-band grain")
        for value, label in (
            (row.norm, "norm"), (row.stock, "stock"), (row.goods_in_transit, "GIT"),
            (row.pso, "PSO"), (row.due_direct_spike, "direct Spike"),
            (row.due_routed_spike, "routed Spike"),
        ):
            _integer(value, label)
        colours = row.routed_order_colours or ()
        if any(colour not in {"red", "yellow", "green"} or not isinstance(quantity, Decimal)
               for colour, quantity in colours):
            raise ValueError("Routed order colours must be Red, Yellow or Green integer quantities")
        for _, quantity in colours:
            _integer(quantity, "routed order colour quantity")
        _integer(row.advance_order_blue, "advance order Blue quantity")
        if not row.pso_threshold_percent.is_finite() or row.pso_threshold_percent < ZERO:
            raise ValueError("PSO threshold must be non-negative")
        by_key[key] = row
        if row.parent_location_code is not None:
            parent = (row.sku_code, row.parent_location_code)
            children.setdefault(parent, []).append(key)
    for parent in children:
        if parent not in by_key and parent not in reference_parent_keys:
            raise ValueError("Requirement-band parent lies outside closure")
    resolved: dict[tuple[str, str], dict] = {}
    visiting: set[tuple[str, str]] = set()

    def resolve(key: tuple[str, str]) -> dict:
        if key in resolved:
            return resolved[key]
        if key in visiting:
            raise ValueError("Cyclic requirement-band hierarchy")
        visiting.add(key)
        row = by_key[key]
        child_rows = [resolve(child) for child in sorted(children.get(key, []))
                      if not by_key[child].excluded_from_parent_rollup]
        inventory = row.stock + row.goods_in_transit
        third = _ceil(row.norm / 3)
        norm_black = third if inventory == ZERO else ZERO
        norm_red = third if inventory > ZERO else ZERO
        norm_yellow = _ceil(row.norm * 2 / 3) - norm_red - norm_black
        norm_green = row.norm - norm_yellow - norm_red - norm_black
        threshold_qty = row.norm * row.pso_threshold_percent / 100
        remaining_pso_threshold = max(threshold_qty - row.pso, ZERO)
        rel_pso = max(row.pso - threshold_qty, ZERO)
        cnr_green = sum((Decimal(child["norm_req_green"]) for child in child_rows), ZERO)
        cnr_yellow = sum((Decimal(child["norm_req_yellow"]) for child in child_rows), ZERO)
        cnr_red = sum((Decimal(child["norm_req_red"]) for child in child_rows), ZERO)
        cnr_black = sum((Decimal(child["norm_req_black"]) for child in child_rows), ZERO)
        residual_child_orders = sum((
            Decimal(child["order_req_black"]) + Decimal(child["order_req_red"]) +
            Decimal(child["order_req_yellow"]) + Decimal(child["order_req_green"]) +
            Decimal(child["order_req_blue"])
            for child in child_rows
        ), ZERO)

        def relevant(quantity: Decimal) -> Decimal:
            nonlocal remaining_pso_threshold
            result = max(_ceil(quantity - remaining_pso_threshold), ZERO)
            remaining_pso_threshold = max(remaining_pso_threshold - quantity, ZERO)
            return result

        rel_cnr_green, rel_cnr_yellow = relevant(cnr_green), relevant(cnr_yellow)
        rel_cnr_red, rel_cnr_black = relevant(cnr_red), relevant(cnr_black)
        routed_by_colour = {colour: sum((quantity for value, quantity in (row.routed_order_colours or ())
                                         if value == colour), ZERO)
                            for colour in ("red", "yellow", "green")}
        # The BPP producer classifies every eligible parent-to-child route.
        # Retain the historical black fallback only for callers that have not
        # supplied that producer (the standalone primitive contract).
        routed_black = row.due_routed_spike if row.routed_order_colours is None else ZERO
        order_bands = {
            "black": row.due_direct_spike + routed_black + residual_child_orders,
            "red": routed_by_colour["red"], "yellow": routed_by_colour["yellow"],
            "green": routed_by_colour["green"], "blue": row.advance_order_blue,
        }
        norm_bands = {
            "black": norm_black + rel_cnr_black + rel_pso,
            "red": norm_red + rel_cnr_red,
            "yellow": norm_yellow + rel_cnr_yellow,
            "green": norm_green + rel_cnr_green,
        }
        remaining = inventory
        requirements: dict[str, Decimal] = {}
        for kind, colour in (
            ("order", "black"), ("norm", "black"), ("order", "red"), ("norm", "red"),
            ("order", "yellow"), ("norm", "yellow"), ("order", "green"), ("norm", "green"),
            ("order", "blue"),
        ):
            band = order_bands[colour] if kind == "order" else norm_bands[colour]
            requirements[f"{kind}_{colour}"] = max(band - remaining, ZERO)
            remaining = max(remaining - band, ZERO)
        output = {
            "sku_code": row.sku_code, "location_code": row.location_code,
            "parent_location_code": row.parent_location_code,
            "norm_black_band": _text(norm_bands["black"]), "norm_red_band": _text(norm_bands["red"]),
            "norm_yellow_band": _text(norm_bands["yellow"]), "norm_green_band": _text(norm_bands["green"]),
            "order_black_band": _text(order_bands["black"]), "order_red_band": _text(order_bands["red"]),
            "order_yellow_band": _text(order_bands["yellow"]), "order_green_band": _text(order_bands["green"]),
            "order_blue_band": _text(order_bands["blue"]),
            "norm_req_black": _text(requirements["norm_black"]), "norm_req_red": _text(requirements["norm_red"]),
            "norm_req_yellow": _text(requirements["norm_yellow"]), "norm_req_green": _text(requirements["norm_green"]),
            "order_req_black": _text(requirements["order_black"]), "order_req_red": _text(requirements["order_red"]),
            "order_req_yellow": _text(requirements["order_yellow"]), "order_req_green": _text(requirements["order_green"]),
            "order_req_blue": _text(requirements["order_blue"]),
            "remaining_stock": _text(remaining), "rel_pso": _text(rel_pso),
            "rel_cnr_green": _text(rel_cnr_green), "rel_cnr_yellow": _text(rel_cnr_yellow),
            "rel_cnr_red": _text(rel_cnr_red), "rel_cnr_black": _text(rel_cnr_black),
        }
        resolved[key] = output
        visiting.remove(key)
        return output

    return [resolve(key) for key in sorted(by_key)]
