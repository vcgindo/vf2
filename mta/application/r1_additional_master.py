"""R1 producer for GenerateAddionalMasterData's physical hierarchy/thresholds.

The current raw closure represents matching DBM/BPR masters and complete SKU
and SKU-location attributes. File ingestion, pre-BPR Norm updates and Elephant
state remain separate entry obligations; none is synthesized by this module.
"""
from decimal import Decimal

from mta.domain.demand import ThresholdPolicy
from mta.domain.validation import RuleBlocked, number


def calculate_additional_master(foundation: dict, policies: list[dict]) -> tuple[dict, ...]:
    masters = {(r["sku_code"], r["location_code"]): r for r in foundation["sku_locations"]}
    if len(masters) != len(foundation["sku_locations"]):
        raise ValueError("Duplicate R1 additional-master physical grain")
    parents = {(r["sku_code"], r["child_location_code"]): (r["sku_code"], r["parent_location_code"])
               for r in foundation["hierarchy"]}
    if len(parents) != len(foundation["hierarchy"]) or set(parents) - set(masters):
        raise ValueError("Duplicate or nonphysical R1 additional-master child")
    configured = {(r["sku_code"], r["location_code"]): r["policy"] for r in policies}
    if len(configured) != len(policies) or set(configured) != set(masters):
        raise ValueError("R1 additional-master policy closure is incomplete")
    produced = {}
    pending = set(masters)
    while pending:
        ready = sorted(key for key in pending if parents.get(key) not in masters or parents[key] in produced)
        if not ready:
            raise ValueError("Cyclic R1 additional-master hierarchy")
        for key in ready:
            master = masters[key]
            norm = number(master["base_norm"], "Norm", integer=True)
            pack = number(master["pack_size"], "pack size", integer=True, positive=True)
            rlt = master["replenishment_lead_time_days"]
            if type(rlt) is not int or rlt < 0:
                raise ValueError("R1 additional-master RLT must be a nonnegative integer")
            parent = produced.get(parents.get(key))
            level = parent["wh_level"] + 1 if parent else 1
            # The selected SQL forces a stop after inserting level102. Do not
            # silently extend its result or publish an incomplete hierarchy.
            if level > 102:
                raise RuleBlocked("R1_MASTER_DEPTH_SOURCE_LIMIT", "Selected AdditionalMasterData stops at level102; deeper closure is not certified")
            policy = ThresholdPolicy(**{name: None if value is None else Decimal(value)
                                        for name, value in configured[key].items()})
            spike, pso = policy.thresholds(norm)
            produced[key] = {
                "sku_code": key[0], "location_code": key[1], "wh_level": level,
                "topmost_location_code": parent["topmost_location_code"] if parent else key[1],
                "topmost_norm": parent["topmost_norm"] if parent else str(norm),
                "topmost_pack_size": parent["topmost_pack_size"] if parent else str(pack),
                "cumulative_rlt_days": (parent["cumulative_rlt_days"] if parent else 0) + rlt,
                "spike_threshold_percent": str(spike), "pso_threshold_percent": str(pso),
            }
        pending.difference_update(ready)
    return tuple(produced[key] for key in sorted(produced))
