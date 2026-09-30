"""Canonical orchestration for recovered RRR allocation groups."""
from decimal import Decimal

from mta.domain.rrr import RationChild, allocate_rrr


def calculate_rrr_groups(
    payload: dict,
    rows: list[dict],
    *,
    parent_stock_for_rationing: dict[tuple[str, str], Decimal] | None = None,
    replenishment_exclusions: tuple[str, ...] | None = None,
    allow_negative_stock_for_requirement: bool = False,
) -> list[dict]:
    """Calculate normal RRR groups.

    Stage 6 callers retain the historical default of physical parent stock.
    R1 supplies the persisted output of ``StockCalculation.sql`` so source
    reservation semantics, rather than raw inventory, govern parent rationing.
    """
    by_key = {(row["sku_code"], row["location_code"]): row for row in rows}
    masters = {(row["sku_code"], row["location_code"]): row for row in payload["foundation"]["sku_locations"]}
    inventory = {(row["sku_code"], row["location_code"]): row for row in payload["foundation"]["inventory_positions"]}
    parents = {(row["sku_code"], row["child_location_code"]): row["parent_location_code"]
               for row in payload["foundation"]["hierarchy"]}
    nodes = {(row["sku_code"], row["location_code"]): row for row in payload["nodes"]}
    groups = {}
    for child, parent in parents.items():
        groups.setdefault((child[0], parent), []).append(child)
    output = []
    for (sku, parent), child_keys in sorted(groups.items()):
        # GetReqDataForParent deletes the aggregate group, NOT its child
        # vf_ReplReq rows. R1 retains those children with zero allocation.
        # Shared Track A keeps its historical physical-group-only boundary.
        physical_parent = (sku, parent) in masters and (sku, parent) in inventory
        if not physical_parent and replenishment_exclusions is None:
            continue
        participants = []
        for key in sorted(child_keys):
            row, node, master, position = by_key[key], nodes[key], masters[key], inventory[key]
            # R1 mirrors GetReqData then ExcludeReplenishment. None retains
            # the historical shared Track A participant population.
            if replenishment_exclusions is not None and (
                key[1] in replenishment_exclusions or Decimal(row["virtual_norm"]["value"]) == 0
            ):
                continue
            participants.append(RationChild(sku, key[1], parent, Decimal(row["virtual_norm"]["value"]),
                Decimal(node["stock_for_requirement"]), Decimal(position["goods_in_transit_quantity"]),
                master["replenishment_lead_time_days"], node.get("rationing_priority", 999999), False))
        parent_row = by_key.get((sku, parent))
        if (parent_row and parent_row["direct_virtual_node"]
                and (replenishment_exclusions is None or parent + "_SYNTH" not in replenishment_exclusions)):
            direct = parent_row["direct_virtual_node"]
            participants.append(RationChild(sku, parent + "_SYNTH", parent,
                Decimal(direct["virtual_norm"]["value"]), Decimal(0), Decimal(0), 0, 999999, True))
        parent_stock = (parent_stock_for_rationing or {}).get(
            (sku, parent), Decimal(inventory[(sku, parent)]["stock_quantity"])
        ) if physical_parent else Decimal(0)
        # GetReqDataForParent deletes the parent aggregation row when its
        # StockForRationing is negative. GetReqData's child rows remain, with
        # their initialized zero ration quantity/leftover. Keep this behavior
        # exclusive to the R1 source-backed call; the shared Track A contract
        # continues to reject negative parent stock.
        deleted_negative_parent_group = replenishment_exclusions is not None and parent_stock < 0
        allocation_stock = Decimal(0) if deleted_negative_parent_group else parent_stock
        allocations = allocate_rrr(parent_stock=allocation_stock,
                                   parent_pack_size=Decimal(masters[(sku, parent)]["pack_size"]) if physical_parent else Decimal(1),
                                   children=tuple(participants),
                                   allow_negative_stock_for_requirement=allow_negative_stock_for_requirement)
        children_by_code = {child.location_code: child for child in participants}
        step1_leftover = allocation_stock - sum((row.pre_round_quantity for row in allocations), Decimal(0))
        for allocation in allocations:
            child = children_by_code[allocation.location_code]
            # Retain the producer's actual inputs and first-pass balance.
            # These are not reconstructed from downstream PSO/report totals.
            checkpoint = {} if replenishment_exclusions is None else {
                "virtual_norm": str(child.virtual_norm),
                "stock_for_requirement": str(child.stock_for_requirement),
                "goods_in_transit": str(child.goods_in_transit),
                "step1_parent_leftover": str(step1_leftover),
            }
            output.append({
                "sku_code": allocation.sku_code, "parent_location_code": allocation.parent_location_code,
                "location_code": allocation.location_code, "virtual": next(c.virtual for c in participants if c.location_code == allocation.location_code),
                "requirement": str(allocation.requirement),
                # No parent row means source StepwiseChildReq/RationPacksize
                # never set these child fields; their initialized values stay 0.
                "capping_percent": 0 if deleted_negative_parent_group else allocation.capping_percent,
                "pre_round_quantity": str(allocation.pre_round_quantity), "pack_size": str(allocation.pack_size),
                "pack_rounded_quantity": str(allocation.pack_rounded_quantity),
                "residual_allocation": str(allocation.residual_allocation), "final_quantity": str(allocation.final_quantity),
                "post_round_penetration": str(Decimal(0) if deleted_negative_parent_group else allocation.post_round_penetration),
                "remaining_parent_stock": str(allocation.remaining_parent_stock),
                **checkpoint,
            })
    return output
