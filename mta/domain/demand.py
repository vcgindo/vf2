"""MTA order/requirement rules from ImportSpikeOrders.sql and CalculateReq.sql.

Inputs are accepted outstanding orders and coherent post-route child balances.
This module does not invent promises, route orders, or allocate advance stock.
"""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation, localcontext

from mta.domain.models import RequirementInput
from mta.domain.validation import ZERO, ceiling, day, identity, number, signed_number


@dataclass(frozen=True)
class ThresholdPolicy:
    spike_high: Decimal
    spike_low: Decimal
    pso_high: Decimal
    pso_low: Decimal
    spike_override: Decimal | None = None
    pso_override: Decimal | None = None

    @classmethod
    def from_mapping(cls, value):
        fields = ('spike_high', 'spike_low', 'pso_high', 'pso_low',
                  'spike_override', 'pso_override')
        if not isinstance(value, dict) or set(value) != set(fields):
            raise ValueError('Complete Spike/PSO threshold policy required')
        parsed = {}
        for name in fields:
            item = value[name]
            if item is None and name.endswith('_override'):
                parsed[name] = None
            else:
                if type(item) not in (str, int):
                    raise ValueError('Exact threshold string or integer required: ' + name)
                try:
                    exact = Decimal(item)
                except InvalidOperation as error:
                    raise ValueError('Exact numeric threshold required: ' + name) from error
                parsed[name] = number(exact, name)
        return cls(**parsed)

    def thresholds(self, norm: Decimal) -> tuple[Decimal, Decimal]:
        number(norm, "Norm", integer=True)
        # These are demand multipliers (Norm * value / 100), not bounded shares.
        for value in (self.spike_high, self.spike_low, self.pso_high, self.pso_low):
            number(value, 'Spike/PSO threshold')
        for value in (self.spike_override, self.pso_override):
            if value is not None:
                number(value, 'Spike/PSO threshold override')
        spike = self.spike_high if norm >= 3 else self.spike_low
        pso = self.pso_high if norm >= 3 else self.pso_low
        return (spike if self.spike_override is None else self.spike_override,
                pso if self.pso_override is None else self.pso_override)


def classify_spike(quantity: Decimal, norm_at_acceptance: Decimal, policy: ThresholdPolicy) -> bool:
    quantity = number(quantity, "order quantity", integer=True)
    spike, _ = policy.thresholds(norm_at_acceptance)
    with localcontext() as ctx:
        ctx.prec = 50
        return quantity > ceiling(norm_at_acceptance * spike / 100)


@dataclass(frozen=True)
class AcceptedOrder:
    order_id: str
    sku_code: str
    location_code: str
    quantity: Decimal
    accepted_on: date
    due_date: date
    # Established classification survives Norm changes. Never retag cumulative PSO.
    is_spike: bool


@dataclass(frozen=True)
class OrderDemand:
    pso: Decimal = ZERO
    due_spike: Decimal = ZERO
    future_spike: Decimal = ZERO
    due_order_ids: tuple[str, ...] = ()


def collect_orders(orders: tuple[AcceptedOrder, ...], sku_code: str,
                   location_code: str, business_date: date) -> OrderDemand:
    identity(sku_code); identity(location_code); day(business_date)
    pso = due = future = ZERO
    ids, eligible = set(), []
    for order in orders:
        identity(order.order_id); day(order.accepted_on); day(order.due_date)
        if order.order_id in ids:
            raise ValueError("Duplicate accepted order")
        ids.add(order.order_id)
        if (order.sku_code, order.location_code) != (sku_code, location_code):
            raise ValueError("Order outside SKU-location closure")
        if type(order.is_spike) is not bool:
            raise ValueError("Established boolean order classification required")
        quantity = number(order.quantity, "outstanding quantity", integer=True)
        if order.accepted_on > business_date:
            raise ValueError("Order not accepted at snapshot business date")
        if not order.is_spike:
            pso += quantity  # legacy includes all outstanding PSO, not only due PSO
        elif order.due_date <= business_date:
            due += quantity
            eligible.append(order.order_id)
        else:
            future += quantity
    return OrderDemand(pso, due, future, tuple(sorted(eligible)))


@dataclass(frozen=True)
class RequirementBreakdown:
    normal_gap: Decimal
    pso: Decimal
    cnr: Decimal
    relevant_pso_cnr: Decimal
    due_spike: Decimal
    future_spike: Decimal
    residual_children: Decimal
    routed_due_spike: Decimal
    additional_demand: Decimal
    netted_additional: Decimal
    residual_additional: Decimal
    requirement: Decimal
    stock_for_requirement: Decimal
    spike_threshold: Decimal
    pso_threshold: Decimal


def calculate_requirement(data: RequirementInput, orders: OrderDemand, policy: ThresholdPolicy,
                          *, cnr: Decimal = ZERO, residual_children: Decimal = ZERO,
                          routed_due_spike: Decimal = ZERO,
                          stock_for_requirement: Decimal | None = None,
                          allow_negative_stock_for_requirement: bool = False,
                          phase_out: bool = False) -> RequirementBreakdown:
    norm, inventory = data.effective_norm, data.inventory_position
    if (norm.sku_code, norm.location_code, norm.business_date) != (
            inventory.sku_code, inventory.location_code, inventory.business_date):
        raise ValueError("Norm and inventory must have identical SKU/location/business date")
    day(norm.business_date); identity(norm.sku_code); identity(norm.location_code)
    n = number(norm.value, "Effective Norm", integer=True)
    stock = number(inventory.stock, "physical stock", integer=True)
    git = number(inventory.goods_in_transit, "GIT", integer=True)
    if stock_for_requirement is not None:
        stock = (signed_number(stock_for_requirement, "post-allocation stock for requirement", integer=True)
                 if allow_negative_stock_for_requirement else
                 number(stock_for_requirement, "post-allocation stock for requirement", integer=True))
    cnr = number(cnr, "CNR", integer=True)
    residual_children = number(residual_children, "child residual", integer=True)
    routed_due_spike = number(routed_due_spike, "post-route due Spike", integer=True)
    for value in (orders.pso, orders.due_spike, orders.future_spike):
        number(value, "order demand", integer=True)
    if type(phase_out) is not bool:
        raise ValueError("Explicit phase-out membership required")
    if phase_out:
        cnr = ZERO
    spike_pct, pso_pct = policy.thresholds(n)
    with localcontext() as ctx:
        ctx.prec = 50
        small_residual = residual_children < n * spike_pct / 100
        threshold_input = orders.pso + cnr + (residual_children if small_residual else ZERO)
        relevant = max(ceiling(threshold_input - n * pso_pct / 100), ZERO)
        additional = orders.due_spike + routed_due_spike + relevant + (ZERO if small_residual else residual_children)
        netted = min(additional, max(stock + git - n, ZERO))
        gap = max(n - (stock + git - netted), ZERO)
        residual = additional - netted
        total = gap + residual
    for quantity in (additional, netted, gap, residual, total):
        number(quantity, "calculated requirement", integer=True)
    return RequirementBreakdown(gap, orders.pso, cnr, relevant, orders.due_spike,
                                orders.future_spike, residual_children, routed_due_spike,
                                additional, netted, residual, total, stock, spike_pct, pso_pct)
