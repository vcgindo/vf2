"""Recovered normal-replenishment rationing (RRR) domain rules.

Source sequence: GetReqData.sql, GetReqDataForParent.sql,
GetStepwiseChildReq.sql and RationPacksize.sql. Work-table mechanics are not
reproduced; their business state transitions are explicit values here.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP, localcontext

from mta.domain.validation import ZERO, ceiling, number, signed_number


# Historical receipt identifiers only; the approved final location key now
# resolves this former denial. Retain imports for older diagnostic callers.
RRR_TIE_BLOCKER = "RRR-PACK-TIE-GAP09"
RRR_TIE_REASON = (
    "Recovered RationPacksize.sql has no unique final key after penetration, "
    "Norm, RLT and configured priority; allocating across the tied boundary is undefined."
)
# Compatibility names retained while the persisted Track A stage is upgraded.
RRR_BLOCKER = RRR_TIE_BLOCKER
RRR_REASON = RRR_TIE_REASON


@dataclass(frozen=True)
class RationChild:
    sku_code: str
    location_code: str
    parent_location_code: str
    virtual_norm: Decimal
    stock_for_requirement: Decimal
    goods_in_transit: Decimal
    replenishment_lead_time_days: int
    location_priority: int = 999999
    virtual: bool = False


@dataclass(frozen=True)
class RationAllocation:
    sku_code: str
    parent_location_code: str
    location_code: str
    virtual_norm: Decimal
    requirement: Decimal
    capping_percent: int
    pre_round_quantity: Decimal
    pack_size: Decimal
    pack_rounded_quantity: Decimal
    residual_allocation: Decimal
    final_quantity: Decimal
    post_round_penetration: Decimal
    remaining_parent_stock: Decimal


def _requirement(child: RationChild, *, allow_negative_stock_for_requirement: bool = False) -> Decimal:
    return max(
        number(child.virtual_norm, "Virtual Norm", integer=True)
        - (signed_number(child.stock_for_requirement, "requirement stock", integer=True)
           if allow_negative_stock_for_requirement else
           number(child.stock_for_requirement, "requirement stock", integer=True))
        - number(child.goods_in_transit, "GIT", integer=True),
        ZERO,
    )


def _at_step(child: RationChild, step: int) -> Decimal:
    with localcontext() as ctx:
        ctx.prec = 50
        return max(
            ceiling(child.virtual_norm * Decimal(step) / 100)
            - child.stock_for_requirement
            - child.goods_in_transit,
            ZERO,
        )


def allocate_rrr(*, parent_stock: Decimal, parent_pack_size: Decimal,
                 children: tuple[RationChild, ...],
                 allow_negative_stock_for_requirement: bool = False) -> tuple[RationAllocation, ...]:
    """Apply 1% equalisation, parent-pack rounding and one-pack residual allocation."""
    stock = number(parent_stock, "parent stock for rationing", integer=True)
    pack = number(parent_pack_size, "parent pack size", integer=True, positive=True)
    if not children:
        return ()
    identities = {(child.sku_code, child.location_code) for child in children}
    if len(identities) != len(children):
        raise ValueError("Duplicate RRR child")
    parents = {(child.sku_code, child.parent_location_code) for child in children}
    if len(parents) != 1:
        raise ValueError("One SKU-parent group required")
    for child in children:
        number(child.virtual_norm, "Virtual Norm", integer=True)
        if allow_negative_stock_for_requirement:
            signed_number(child.stock_for_requirement, "requirement stock", integer=True)
        else:
            number(child.stock_for_requirement, "requirement stock", integer=True)
        number(child.goods_in_transit, "GIT", integer=True)
        if type(child.replenishment_lead_time_days) is not int or child.replenishment_lead_time_days < 0:
            raise ValueError("Non-negative integral RLT required")
        if type(child.location_priority) is not int:
            raise ValueError("Integral priority required")

    requirements = [_requirement(child, allow_negative_stock_for_requirement=allow_negative_stock_for_requirement)
                    for child in children]
    total = sum(requirements, ZERO)
    capping = 0
    if total > 0:
        feasible = [
            step for step in range(1, 101)
            if sum((_at_step(child, step) for child in children), ZERO) <= stock
        ]
        capping = max(feasible, default=0)
    pre = [min(_at_step(child, capping), requirements[index]) if capping else ZERO
           for index, child in enumerate(children)]
    positive = [index for index, value in enumerate(requirements) if value > 0]
    if len(positive) == 1:
        index = positive[0]
        pre[index] = min(stock, total)
    leftover_step1 = max(stock - sum(pre, ZERO), ZERO)
    rounded = [(value // pack) * pack for value in pre]
    leftover = leftover_step1 + sum(
        (pre[index] - rounded[index] for index in range(len(children))), ZERO
    )
    with localcontext() as ctx:
        ctx.prec = 50
        penetration = [
            (child.virtual_norm - child.stock_for_requirement - child.goods_in_transit - rounded[index])
            / child.virtual_norm if child.virtual_norm else ZERO
            for index, child in enumerate(children)
        ]
    # Step2EcoPen.EcoPenAfterStep2 is numeric(15,7), and the SQL predicate
    # compares it with the decimal(8,6) result of 1/3.0.  Persisted precision
    # therefore owns both residual eligibility and ordering.
    penetration = [value.quantize(Decimal("0.0000001"), rounding=ROUND_HALF_UP) for value in penetration]
    # RationPacksize.sql inner-joins physical children to DBMMaster for residual
    # ranking. Generated direct-order virtual nodes participate in equalisation
    # but cannot receive the later one-pack residual.
    eligible = [index for index, value in enumerate(penetration)
                if value >= Decimal("0.333333") and not children[index].virtual]
    # Approved production policy: preserve penetration severity, prefer lower
    # rationing Norm, then RLT/priority and finally lexical location code.
    # This deliberately differs from legacy Norm DESC / unspecified final tie.
    eligible.sort(key=lambda index: (
        -penetration[index], children[index].virtual_norm,
        children[index].replenishment_lead_time_days, children[index].location_priority,
        children[index].location_code,
    ))
    packs_available = int(leftover // pack)
    residual = [ZERO for _ in children]
    for index in eligible[:packs_available]:
        residual[index] = pack
    final = [rounded[index] + residual[index] for index in range(len(children))]
    remaining = stock - sum(final, ZERO)
    return tuple(
        RationAllocation(
            child.sku_code, child.parent_location_code, child.location_code,
            child.virtual_norm, requirements[index], capping,
            pre[index], pack, rounded[index], residual[index], final[index],
            penetration[index], remaining,
        )
        for index, child in enumerate(children)
    )


def calculate_rrr(*args, **kwargs):
    return allocate_rrr(*args, **kwargs)
