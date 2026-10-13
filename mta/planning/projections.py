"""Current-day projections extracted from pinned R1 functions.

Only ORM reads were replaced with explicit produced-row arguments. See
baseline/calculation-reuse.json. No copied persistence/audit framework.
"""
from datetime import date
from decimal import Decimal, ROUND_CEILING
from mta.application.r1_input import resolve_r1_vehicle_mappings
from mta.application.r1_importer_master import _sql_key
from mta.domain.r1_current_day import PsoRationInput, RationedRequirement, bifurcate_rationed_requirement
from mta.domain.r1_requirement_bands import RequirementBandInput, calculate_requirement_bands
from mta.domain.remaining_capabilities import calculate_bor, calculate_bor_oa, calculate_pick_list

def _as_json(value):
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, tuple):
        return [_as_json(row) for row in value]
    if isinstance(value, dict):
        return {key: _as_json(item) for key, item in value.items()}
    if hasattr(value, "__dataclass_fields__"):
        return _as_json({key: getattr(value, key) for key in value.__dataclass_fields__})
    return value


def _pso_inputs(prepared, requirement_rows: list[dict], normal_rows) -> tuple[PsoRationInput, ...]:
    result_by_key = {(row["sku_code"], row["location_code"]): row for row in requirement_rows}
    masters = {(row["sku_code"], row["location_code"]): row for row in prepared.track_a["foundation"]["sku_locations"]}
    parents = {(row["sku_code"], row["child_location_code"]): row["parent_location_code"]
               for row in prepared.track_a["foundation"]["hierarchy"]}
    rrr_rows = sorted(normal_rows, key=lambda r: (r.sku_id, r.parent_location_id, r.location_code))
    normal = {(row.sku_id, row.location_code): row for row in rrr_rows}
    # CollectDataForPSORationing starts with adjusted stock, then overwrites
    # only parents represented by surviving normal-replenishment rows.
    parent_stock = {(row["sku_code"], row["location_code"]): Decimal(row["stock_for_rationing"])
                    for row in prepared.stock_balances}
    parent_stock.update({(row.sku_id, row.parent_location_id): row.remaining_parent_stock for row in rrr_rows})
    source = []
    # Physical PSO population is BPRMaster, not the normal-ration result.
    for key in sorted(masters):
        if key[1] in prepared.replenishment_exclusions:
            continue
        result = result_by_key[key]
        requirement = result["requirement"]
        parent = (key[0], parents[key])
        rrr = normal.get(key)
        normal_present = Decimal(result["virtual_norm"]["value"]) != 0
        source.append(PsoRationInput(
            sku_code=key[0], location_code=key[1], parent_location_code=parent[1],
            residual_spike_pso=Decimal(requirement["residual_additional"]),
            spike_pso_to_net_off=Decimal(requirement["additional_demand"]),
            norm_requirement=Decimal(requirement["normal_gap"]),
            total_requirement=rrr.requirement_quantity if rrr else Decimal(0),
            normal_rationed_quantity=rrr.final_quantity if rrr else Decimal(0),
            parent_stock=parent_stock.get(parent, Decimal(0)),
            parent_pack_size=Decimal(masters[parent]["pack_size"]) if parent in masters else Decimal(1),
            normal_row_present=normal_present,
        ))
    # Virtual PSO rows are inserted AFTER physical exclusion, but inner-join
    # the already-filtered normal table. No physical-to-virtual inheritance.
    for rrr in rrr_rows:
        if not rrr.is_virtual:
            continue
        parent = (rrr.sku_id, rrr.parent_location_id)
        requirement = result_by_key[parent]["requirement"]
        source.append(PsoRationInput(
            sku_code=rrr.sku_id, location_code=rrr.location_code, parent_location_code=parent[1],
            residual_spike_pso=Decimal(requirement["pso"]) + Decimal(requirement["due_spike"]),
            spike_pso_to_net_off=Decimal(0), norm_requirement=Decimal(0), total_requirement=rrr.requirement_quantity,
            normal_rationed_quantity=rrr.final_quantity, parent_stock=parent_stock[parent],
            parent_pack_size=Decimal(masters[parent]["pack_size"]), is_virtual=True,
        ))
    return tuple(source)


def _bifurcation_rows(prepared, requirement_rows: list[dict], normal_rows, pso_rows) -> list[dict]:
    result_by_key = {(row["sku_code"], row["location_code"]): row for row in requirement_rows}
    pso_by_key = {(row.sku_code, row.location_code, row.parent_location_code): row for row in pso_rows}
    inventory = {(row["sku_code"], row["location_code"]): row for row in prepared.track_a["foundation"]["inventory_positions"]}
    parents = {(row["sku_code"], row["child_location_code"]): row["parent_location_code"]
               for row in prepared.track_a["foundation"]["hierarchy"]}
    normal = {(row.sku_id, row.location_code): row for row in normal_rows}
    output = []
    for key, result in sorted(result_by_key.items()):
        parent = parents.get(key)
        if (key[0], parent) not in inventory:
            continue
        position = inventory[key]
        # The first legacy report population is ``vf_RationedReqReport`` rows
        # with ``Req > 0``.  Do not invent a zero-ration Pick producer merely
        # because the persisted normal-ration seam has a zero child record.
        if Decimal(result["requirement"]["requirement"]) <= 0:
            continue
        pso, rrr = pso_by_key.get((*key, parent)), normal.get(key)
        rationed = (rrr.final_quantity if rrr else Decimal(0)) + (pso.total_allocation if pso else Decimal(0))
        output.append(bifurcate_rationed_requirement(RationedRequirement(
            sku_code=key[0], location_code=key[1], parent_location_code=parent,
            virtual_norm=Decimal(result["virtual_norm"]["value"]), stock=Decimal(position["stock_quantity"]),
            goods_in_transit=Decimal(position["goods_in_transit_quantity"]), rationed_quantity=rationed,
        )))
    # Source's second population retains every direct virtual parent, even
    # when its virtual allocation row was excluded. It explicitly seeds
    # RationedReq=0; direct allocation is a separate report field, not bands.
    for key, result in sorted(result_by_key.items()):
        if result["direct_virtual_node"]:
            output.append(bifurcate_rationed_requirement(RationedRequirement(
                sku_code=key[0], location_code=key[1], parent_location_code=key[1],
                virtual_norm=Decimal(result["virtual_norm"]["value"]),
                stock=Decimal(inventory[key]["stock_quantity"]),
                goods_in_transit=Decimal(inventory[key]["goods_in_transit_quantity"]), rationed_quantity=Decimal(0),
            )))
    return output


def _bpp_order_rows(prepared, payload: dict) -> list[dict]:
    """Port source route BPP/order colour before requirement-band allocation.

    ``UpdateBPPAndColorForOrder.sql`` assigns a BPP to the upstream route
    from the destination node's RLT and its downstream DueDate.  Only routes
    already due today, coloured Red/Yellow/Green, feed the requirement-band
    order buckets; Black direct Spike demand remains the separate source
    field consumed by ``ReqInColorBand.sql``.
    """
    masters = {(row["sku_code"], row["location_code"]): row
               for row in prepared.track_a["foundation"]["sku_locations"]}
    business_date = date.fromisoformat(prepared.track_a["foundation"]["snapshot"]["business_date"])
    order_quantity = {row["order_id"]: Decimal(row["outstanding_quantity"]) for row in payload["orders"]}
    routes_by_order: dict[str, list[dict]] = {}
    for route in prepared.routes:
        routes_by_order.setdefault(route["order_id"], []).append(route)
    output = []
    for order_id, routes in sorted(routes_by_order.items()):
        by_location = {route["location_code"]: route for route in routes}
        for route in sorted(routes, key=lambda item: (item["due_date"], item["location_code"])):
            destination = route["child_location_code"]
            if destination is None:
                continue
            destination_route = by_location.get(destination)
            if destination_route is None:
                raise ValueError("BPP route is missing its destination DueDate")
            rlt = Decimal(masters[(route["sku_code"], destination)]["replenishment_lead_time_days"])
            if rlt <= 0:
                raise ValueError("BPP route requires a positive destination RLT")
            due_at_destination = date.fromisoformat(destination_route["due_date"])
            elapsed_to_due = max((due_at_destination - business_date).days, 0)
            # Source CEILING wraps the complete ratio; e.g. RLT=3, two
            # days remaining yields 34/Yellow, verified by full SQL replay.
            bpp = (Decimal("100") * (rlt - elapsed_to_due) / rlt).to_integral_value(rounding=ROUND_CEILING)
            colour = ("white" if bpp < 0 else "green" if bpp < 34 else "yellow" if bpp < 67
                      else "red" if bpp < 100 else "black")
            output.append({
                "order_id": order_id, "sku_code": route["sku_code"],
                "source_location_code": route["location_code"],
                "destination_location_code": destination,
                "route_due_date": route["due_date"],
                "due_date_at_destination": destination_route["due_date"],
                "bpp": format(bpp.normalize(), "f"), "colour": colour,
                "quantity": format(Decimal("0") if due_at_destination <= business_date else order_quantity[order_id], "f"),
                "eligible_for_requirement_band": date.fromisoformat(route["due_date"]) <= business_date
                and colour in {"red", "yellow", "green"},
            })
    return output


def _requirement_band_rows(prepared, payload: dict, requirement_rows: list[dict], bpp_rows: list[dict], advance_allocations: list[dict], *, source_rows=None) -> list[dict]:
    parent_by_key = {
        (row["sku_code"], row["child_location_code"]): row["parent_location_code"]
        for row in prepared.track_a["foundation"]["hierarchy"]
    }
    route_colours: dict[tuple[str, str], list[tuple[str, Decimal]]] = {}
    allocated_by_order: dict[str, Decimal] = {}
    stock_allocated_at_source: dict[tuple[str, str], Decimal] = {}
    blue_allocations = []
    for allocation in advance_allocations:
        source = (allocation["sku_code"], allocation["source_location_code"])
        if allocation["allocation_type"] == "advance-stock":
            stock_allocated_at_source[source] = stock_allocated_at_source.get(source, Decimal("0")) + Decimal(allocation["allocated_quantity"])
        # ReqInColorBand always includes routed advances; a direct (NULL
        # destination) advance is Blue only when its upstream BPP is White.
        if allocation["destination_location_code"] is not None or any(
            row["order_id"] == allocation["order_id"] and row["destination_location_code"] == source[1]
            and row["colour"] == "white" for row in bpp_rows
        ):
            blue_allocations.append(allocation)
            key = allocation["order_id"]
            allocated_by_order[key] = allocated_by_order.get(key, Decimal("0")) + Decimal(allocation["allocated_quantity"])
    for row in bpp_rows:
        if not row["eligible_for_requirement_band"]:
            continue
        quantity = max(Decimal(row["quantity"]) - allocated_by_order.get(row["order_id"], Decimal("0")), Decimal("0"))
        route_colours.setdefault((row["sku_code"], row["destination_location_code"]), []).append(
            (row["colour"], quantity)
        )
    advance_blue: dict[tuple[str, str], Decimal] = {}
    for allocation in blue_allocations:
        key = (allocation["sku_code"], allocation["destination_location_code"] or allocation["source_location_code"])
        advance_blue[key] = advance_blue.get(key, Decimal("0")) + Decimal(allocation["allocated_quantity"])
    inputs = []
    phase_out_keys = set(prepared.phase_out_membership) | {
        (policy["sku_code"], policy["location_code"]) for policy in payload["policies"]
        if any(control["type"] == "phase_out" for control in policy.get("controls", []))
    }
    for row in requirement_rows:
        requirement = row["requirement"]
        inputs.append(RequirementBandInput(
            sku_code=row["sku_code"], location_code=row["location_code"],
            parent_location_code=parent_by_key.get((row["sku_code"], row["location_code"])),
            norm=Decimal(row["effective_norm"]["value"]),
            stock=Decimal(next(position["stock_quantity"] for position in prepared.track_a["foundation"]["inventory_positions"]
                               if (position["sku_code"], position["location_code"]) == (row["sku_code"], row["location_code"]))),
            goods_in_transit=Decimal(next(position["goods_in_transit_quantity"] for position in prepared.track_a["foundation"]["inventory_positions"]
                                          if (position["sku_code"], position["location_code"]) == (row["sku_code"], row["location_code"]))),
            pso=Decimal(requirement["pso"]), pso_threshold_percent=Decimal(requirement["pso_threshold"]),
            due_direct_spike=max(Decimal(requirement["due_spike"]) - stock_allocated_at_source.get((row["sku_code"], row["location_code"]), Decimal("0")), Decimal("0")),
            due_routed_spike=Decimal(requirement["routed_due_spike"]),
            routed_order_colours=tuple(route_colours.get((row["sku_code"], row["location_code"]), [])),
            advance_order_blue=advance_blue.get((row["sku_code"], row["location_code"]), Decimal("0")),
            excluded_from_parent_rollup=(row["sku_code"], row["location_code"]) in phase_out_keys,
        ))
    physical_keys = {(row["sku_code"], row["location_code"]) for row in requirement_rows}
    references = frozenset((sku, parent) for (sku, _), parent in parent_by_key.items()
                           if (sku, parent) not in physical_keys)
    return calculate_requirement_bands(tuple(inputs), reference_parent_keys=references, source_rows=source_rows)


def _source_bor_rows(prepared, payload: dict, requirement_rows: list[dict], band_rows) -> tuple[list[dict], list[dict]]:
    requirements = {(row["sku_code"], row["location_code"]): row for row in requirement_rows}
    balances = {(row["sku_code"], row["location_code"]): row for row in prepared.stock_balances}
    positions = {(row["sku_code"], row["location_code"]): row for row in prepared.track_a["foundation"]["inventory_positions"]}
    bands = {
        (row["sku_code"], row["location_code"]): row
        for row in band_rows
    }
    bor_items, oa_items = [], []
    for index, source in enumerate(payload["sourcing"], 1):
        key = (source["sku_code"], source["location_code"])
        if key not in requirements or key not in bands:
            raise ValueError("R1 supplier input has no computed requirement/band source")
        result, position, balance = requirements[key], positions[key], balances[key]
        bor_items.append({
            "case": source.get("case", f"r1_bor_{index}"), "sku": key[0], "location": key[1],
            "supplier": source["supplier"], "norm": result["effective_norm"]["value"],
            "virtual_norm": result["virtual_norm"]["value"], "stock": position["stock_quantity"],
            "git": position["goods_in_transit_quantity"], "stock_for_requirement": balance["stock_for_requirement"],
            "requirement": result["requirement"]["requirement"],
            "dispatch_color": result["colours"]["dispatch"]["band"], "sob": source["sob"],
            "moq": source["moq"], "pack_size": source["pack_size"],
        })
    # BOR-OA reads the BPR supplier opening before GenSupplierWiseReq refreshes
    # BPR from the raw importer feed.  v1 fixtures retain their historical
    # fallback only as regression evidence; v2 fixtures must make this input
    # source explicit.
    for index, source in enumerate(payload.get("supplier_openings", payload["sourcing"]), 1):
        key = (source["sku_code"], source["location_code"])
        if key not in requirements or key not in bands:
            raise ValueError("R1 supplier opening has no computed requirement/band source")
        result, position, balance = requirements[key], positions[key], balances[key]
        band = bands[key]
        oa_items.append({
            "case": source.get("case", f"r1_bor_oa_{index}"), "sku": key[0], "location": key[1],
            "supplier": source["supplier"], "norm": result["effective_norm"]["value"],
            "virtual_norm": result["virtual_norm"]["value"], "stock": position["stock_quantity"],
            "git": position["goods_in_transit_quantity"], "sob": source["sob"], "moq": source["moq"],
            "dispatch_pen": result["colours"]["dispatch"]["penetration"],
            "bands": {
                "order_black": band["order_req_black"], "order_red": band["order_req_red"],
                "order_yellow": band["order_req_yellow"], "order_green": band["order_req_green"],
                "order_blue": band["order_req_blue"], "norm_black": band["norm_req_black"],
                "norm_red": band["norm_req_red"], "norm_yellow": band["norm_req_yellow"],
                "norm_green": band["norm_req_green"], "order_black_band": band["order_black_band"],
                "order_red_band": band["order_red_band"], "order_yellow_band": band["order_yellow_band"],
                "order_green_band": band["order_green_band"],
            },
        })
    return calculate_bor({"items": bor_items}, allow_negative_stock_for_requirement=True), calculate_bor_oa({"items": oa_items})


def _pick_rows(bifurcation_rows, logistics: dict, *, remaining=False) -> list[dict]:
    buckets_by_key = {
        (row["sku_code"], row["location_code"], row["parent_location_code"]): row
        for row in bifurcation_rows
    }
    # The selected importer lands destination/logistics-location pairs as a
    # shared master, not as a SKU-specific relation. The canonical Pick join
    # retains every distinct matching location row, including multiple groups
    # for a destination appearing under different SKU parents.
    locations = {}
    for source in logistics['items']:
        locations.setdefault(_sql_key(source['to_location']), set()).add(source['logistics_location'])
    items = []
    for index, item in enumerate(logistics["items"], 1):
        # A parent may also have a direct-order/self report row. Keep the
        # source ParentWhCode grain so that row cannot shadow its inbound
        # physical replenishment bands.
        key = (item["sku_code"], item["location_code"], item["from_location"])
        if key not in buckets_by_key:
            # Logistics master data is source-shaped and can contain a node
            # that has no ``vf_PickListReport`` row this day (Req <= 0).
            # It therefore produces no dispatch row, rather than an error or
            # a synthetic all-zero Pick row.
            continue
        buckets = buckets_by_key[key]
        for logistics_location in sorted(locations[_sql_key(item['to_location'])], key=lambda value: (value is not None, str(value))):
            items.append({
                "case": item.get("case", f"r1_pick_{index}"), "sku": item["sku_code"],
                "from_location": item["from_location"], "to_location": item["to_location"],
                "logistics_location": item['to_location'] if logistics_location is None else logistics_location,
                "weight": item["weight"],
                "volume": item["volume"], "pack_size": item["pack_size"],
                "buckets": {name: buckets[name] for name in ("to_black", "to_red", "to_yellow", "to_green", "to_blue")},
            })
    # The legacy ``LogisticPickList`` table receives only formed-truck rows.
    # Its residual queue remains in ``PickListDataForTruckFormation``; exposing
    # that queue as a completed R1 Pick row would create a false dispatch.
    vehicles = resolve_r1_vehicle_mappings(logistics)
    result = []
    for parent, vehicle in vehicles.items():
        selected = [row for row in items if row['from_location'] == parent]
        result.extend({**row, 'vehicle': vehicle['name']}
                      for row in calculate_pick_list({'vehicle': vehicle, 'items': selected})
                      if (row['truck'] is None) == remaining)
    return result
