"""R1-only level sequencing of the two CalculateReq.sql passes.

The shared Track A component remains a single-pass seam. This producer owns
the current-day order remainder and the first-pass CNR that the SQL retains
in its second pass. Its inputs are prepared raw facts, never legacy outputs.
"""
from copy import deepcopy
from dataclasses import asdict, replace
from datetime import date, timedelta
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR

from mta.application.track_a import calculate_track_a, json_value
from mta.domain.colours import all_colours
from mta.domain.demand import OrderDemand, ThresholdPolicy, calculate_requirement
from mta.domain.models import EffectiveNorm, InventoryPosition, RequirementInput
from mta.domain.validation import RuleBlocked
from mta.domain.virtual_norm import resolve_virtual_norm

ZERO = Decimal(0)


def calculate_r1_requirements(prepared, payload):
    """Return final Track A-shaped rows and a replayable source-state trace."""
    payload = prepared.calculation_payload or payload
    track = deepcopy(prepared.track_a)
    foundation = track["foundation"]
    today = date.fromisoformat(foundation["snapshot"]["business_date"])
    key = lambda row: (row["sku_code"], row["location_code"])
    templates = {key(row): row for row in calculate_track_a(track, allow_negative_stock_for_requirement=True)}
    nodes = {key(row): row for row in track["nodes"]}
    masters = {key(row): row for row in foundation["sku_locations"]}
    positions = {key(row): row for row in foundation["inventory_positions"]}
    parents = {(r["sku_code"], r["child_location_code"]): (r["sku_code"], r["parent_location_code"])
               for r in foundation["hierarchy"]}
    children = {k: [] for k in nodes}
    for child, parent in parents.items():
        children.setdefault(parent, []).append(child)
    depths = {key(row): row["wh_level"] for row in prepared.additional_master}
    levels = sorted(set(depths.values()), reverse=True)
    balances = {key(row): row for row in prepared.stock_balances}
    raw_orders = {row["order_id"]: row for row in payload["orders"]}
    orders = {order["order_id"]: order for node in nodes.values() for order in node["orders"]}
    remaining = {oid: Decimal(order["quantity"]) for oid, order in orders.items() if order["is_spike"]}
    norms = {k: EffectiveNorm(k[0], k[1], today, Decimal(row["effective_norm"]["value"]),
                             row["effective_norm"]["basis"], tuple(row["effective_norm"]["applied_control_ids"]))
             for k, row in templates.items()}
    policies = {k: ThresholdPolicy(**{name: None if value is None else Decimal(value)
                                     for name, value in node["policy"].items()}) for k, node in nodes.items()}
    demands = {k: OrderDemand(Decimal(row["requirement"]["pso"]), Decimal(row["requirement"]["due_spike"]),
                              Decimal(row["requirement"]["future_spike"])) for k, row in templates.items()}
    threshold = Decimal(payload["allocation"]["advance_stock_threshold_percent"]) / 100
    daily, stock_allocations, git_allocations = [], [], []
    first, frozen_cnr = {}, {}
    stock_at_source = {k: ZERO for k in nodes}
    routes_by_source, routes_by_destination = {}, {}
    for route in prepared.routes:
        routes_by_source.setdefault(key(route), []).append(route)
        destination = (route["sku_code"], route["child_location_code"])
        routes_by_destination.setdefault(destination, []).append(route)

    def req(k, previous, routed, *, cnr=None, direct=None):
        child_rows = [previous[c] for c in children[k]]
        position = positions[k]
        return calculate_requirement(
            RequirementInput(norms[k], InventoryPosition(*k, today, Decimal(position["stock_quantity"]),
                                                         Decimal(position["goods_in_transit_quantity"]))),
            demands[k] if direct is None else replace(demands[k], due_spike=direct), policies[k],
            cnr=sum((r.normal_gap for r in child_rows), ZERO) if cnr is None else cnr,
            residual_children=sum((r.residual_additional for r in child_rows), ZERO),
            routed_due_spike=routed, stock_for_requirement=Decimal(balances[k]["stock_for_requirement"]),
            allow_negative_stock_for_requirement=True,
            phase_out=(k in prepared.phase_out_membership
                       or any(c["type"] == "phase_out" for c in nodes[k]["controls"])),
        )

    def append_route(route, qty, kind):
        if qty <= 0:
            return
        oid = route["order_id"]
        daily.append({"order_id": oid, "sku_code": route["sku_code"],
                      "source_location_code": route["location_code"],
                      "destination_location_code": route["child_location_code"],
                      "allocated_quantity": format(qty, "f"), "allocation_type": kind})
        # SQL subtracts cumulative allocated packs, including an over-full last
        # pack, from original Qty; it does not clamp the remainder to zero.
        remaining[oid] -= qty
        if kind != "stock":
            due = date.fromisoformat(route["due_date"])
            raw_ced = raw_orders[oid]["customer_expected_date"]
            ced = date.fromisoformat(raw_ced) if raw_ced else None
            ced_at_node = None if ced is None else ced - timedelta(days=(date.fromisoformat(orders[oid]["due_date"]) - due).days)
            output = {**daily[-1], "route_due_date": due.isoformat(),
                      "customer_expected_at_node": ced_at_node.isoformat() if ced_at_node else None}
            (stock_allocations if kind == "advance-stock" else git_allocations).append(output)

    def candidates(routes):
        result = []
        for route in routes:
            oid = route["order_id"]
            due = date.fromisoformat(route["due_date"])
            if due <= today or remaining.get(oid, ZERO) <= 0:
                continue
            raw_ced = raw_orders[oid]["customer_expected_date"]
            ced = date.fromisoformat(raw_ced) if raw_ced else None
            ced_at_node = None if ced is None else ced - timedelta(days=(date.fromisoformat(orders[oid]["due_date"]) - due).days)
            # SQL deletes only ``CEDAtNode > @today``.  NULL CED is retained.
            if ced_at_node is None or ced_at_node <= today:
                result.append((due, ced_at_node, oid, route))
        # SQL's third sort column is the persisted OrderKey, never customer
        # ID or input position. ImportSpikeOrders retains it for established
        # Spikes but deletes/reinserts promoted PSOs, so a PSO opening key
        # cannot determine that promoted order's current allocation priority.
        def retained_key(oid):
            raw = raw_orders[oid]
            if raw["established_is_spike"] is True:
                return raw.get("established_order_key")
            # Separate-feed preparation owns this map only after it computes
            # the approved generated keys. Raw callers cannot seed that map.
            if raw['established_is_spike'] is None and prepared.order_part_identity is not None:
                return prepared.order_part_identity[oid]['order_key']
            return None

        groups = {}
        for row in result:
            groups.setdefault(row[:2], []).append(row)
        for tied in groups.values():
            if len(tied) > 1 and any(retained_key(row[2]) is None for row in tied):
                raise RuleBlocked("R1_ORDER_KEY_OPENING_REQUIRED", "Equal due/CED allocation needs the retained legacy OrderKey opening; customer-ID sorting is not canonical")
        # SQL ASC ordering puts a NULL CED before a dated CED.  Avoid Python's
        # undefined ``None``/``date`` comparison while retaining that order.
        return [r[3] for r in sorted(
            result,
            key=lambda r: (r[0], r[1] is not None, r[1] or date.min, retained_key(r[2]) or 0),
        )]

    for level in levels:
        current = sorted(k for k in nodes if depths[k] == level)
        current_keys = set(current)
        # Due routes are created at the source depth before advance allocation.
        for route in prepared.routes:
            src = (route["sku_code"], route["location_code"])
            if src in current_keys and date.fromisoformat(route["due_date"]) <= today:
                append_route(route, remaining.get(route["order_id"], ZERO), "stock")
        for k in current:
            need = sum((first[c].requirement for c in children[k]), ZERO) + demands[k].due_spike + demands[k].pso
            excess = max(Decimal(balances[k]["stock_for_rationing"]) - need
                         - (Decimal(masters[k]["base_norm"]) * threshold).to_integral_value(rounding=ROUND_FLOOR), ZERO)
            pack = Decimal(masters[k]["pack_size"])
            available = int(excess // pack)
            eligible = candidates(routes_by_source.get(k, ()))
            for route in eligible:
                requested = int((remaining[route["order_id"]] / pack).to_integral_value(rounding=ROUND_CEILING))
                qty = min(requested, available) * pack
                append_route(route, qty, "advance-stock")
                stock_at_source[k] += qty
                available -= int(qty // pack)
        # A child's first-pass routed demand sees only the still-unallocated
        # quantity on an already-due incoming route (parent executes later).
        for k in current:
            routed = sum((max(remaining.get(r["order_id"], ZERO), ZERO) for r in routes_by_destination.get(k, ())
                          if date.fromisoformat(r["due_date"]) <= today), ZERO)
            first[k] = req(k, first, routed)
            frozen_cnr[k] = first[k].cnr
        # Incoming GIT at this depth precedes parent stock at the next depth.
        groups = {}
        quotas = {}
        for k in current:
            git = Decimal(positions[k]["goods_in_transit_quantity"])
            eco = max(Decimal(balances[k]["stock_for_requirement"]) + git - stock_at_source[k]
                      - first[k].additional_demand - norms[k].value, ZERO)
            quotas[k] = int(min(git, eco) // Decimal(masters[k]["pack_size"]))
            if k in parents:
                groups.setdefault(parents[k], []).extend(r for r in routes_by_destination.get(k, ())
                    if (r["sku_code"], r["location_code"]) == parents[k])
        for parent, routes in sorted(groups.items()):
            cumulative = 0
            for route in candidates(routes):
                dest = (route["sku_code"], route["child_location_code"])
                pack = Decimal(masters[dest]["pack_size"])
                requested = int((remaining[route["order_id"]] / pack).to_integral_value(rounding=ROUND_CEILING))
                allocated = min(requested, max(quotas[dest] - cumulative, 0))
                cumulative += requested  # source partitions cumulative demand by parent, not destination
                append_route(route, allocated * pack, "git")
    for route in prepared.routes:
        src = (route["sku_code"], route["location_code"])
        dest = (route["sku_code"], route["child_location_code"])
        if src not in nodes and dest in nodes and depths[dest] == 1 and parents.get(dest) == src and date.fromisoformat(route["due_date"]) <= today:
            append_route(route, remaining.get(route["order_id"], ZERO), "stock")
    routed_totals, direct_totals = {}, {}
    for route in daily:
        dest = route["destination_location_code"]
        k = (route["sku_code"], dest if dest is not None else route["source_location_code"])
        totals = routed_totals if dest is not None else direct_totals
        totals[k] = totals.get(k, ZERO) + Decimal(route["allocated_quantity"])
    final = {}
    for level in levels:
        for k in sorted(k for k in nodes if depths[k] == level):
            # The SQL second update is an inner join. With no daily route it
            # retains the first-pass SpikeOverdueAtParent value.
            routed = routed_totals.get(k, first[k].routed_due_spike)
            final[k] = req(k, final, routed, cnr=frozen_cnr[k], direct=direct_totals.get(k, demands[k].due_spike))
            nodes[k]["routed_due_spike"] = format(routed, "f")
    output = []
    for k, template in sorted(templates.items()):
        result = final[k]
        parent = parents.get(k)
        peers = tuple(norms[c].value for c in children[parent]) if parent else ()
        pack = Decimal(masters[parent]["pack_size"]) if parent in masters else Decimal(1 if parent else masters[k]["pack_size"])
        # ConsolidateReq's uncapped top-node update tests for a physical
        # parent row, not whether a supplier/plant reference is present.
        virtual = resolve_virtual_norm(norms[k].value, result.additional_demand, kind="CHILD" if parent in masters else "TOP", peer_norms=peers, parent_pack_size=pack)
        position = positions[k]
        colours = all_colours(norms[k].value, Decimal(position["stock_quantity"]), Decimal(position["goods_in_transit_quantity"]), virtual)
        direct = None
        if children[k] and result.pso + result.due_spike > 0:
            vn = resolve_virtual_norm(ZERO, result.pso + result.due_spike, kind="DIRECT", peer_norms=tuple(norms[c].value for c in children[k]))
            direct = {"business_date": today.isoformat(), "parent_location_code": k[1], "virtual_norm": asdict(vn),
                      "dispatch": asdict(all_colours(ZERO, ZERO, ZERO, vn)["dispatch"])}
        output.append(json_value({**template, "requirement": asdict(result), "virtual_norm": asdict(virtual),
                                  "colours": {name: asdict(value) for name, value in colours.items()}, "direct_virtual_node": direct}))
    trace = {"schema": "r1-level-calculation-v1", "daily_routes": daily,
             "stock_configuration": prepared.stock_configuration,
             "additional_master": list(prepared.additional_master),
             "first_pass": [{"sku_code": k[0], "location_code": k[1], "depth": depths[k],
                             "requirement": json_value(asdict(first[k]))} for k in sorted(first)],
             "order_remainders": [{"order_id": oid, "remaining_quantity": format(qty, "f")} for oid, qty in sorted(remaining.items())]}
    if prepared.master_state is not None:
        trace["master_state"] = prepared.master_state
    if prepared.importer_validation is not None:
        trace["importer_validation"] = prepared.importer_validation
    if prepared.supplier_validation is not None:
        trace["supplier_validation"] = prepared.supplier_validation
        trace["supplier_state"] = prepared.supplier_state
        trace["vendor_codes"] = list(prepared.vendor_codes)
    if prepared.daily_validation is not None:
        trace["daily_validation"] = prepared.daily_validation
        trace["daily_consumption"] = prepared.daily_consumption
    if prepared.order_import_state is not None:
        trace['order_import_state'] = prepared.order_import_state
    if prepared.order_part_identity is not None:
        trace['order_part_identity'] = prepared.order_part_identity
    return track, output, stock_allocations, git_allocations, trace
