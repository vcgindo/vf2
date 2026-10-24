"""Explicit in-memory handoffs for the existing ordered daily producers.

These values are calculation state only: they do not assert persistence,
publication readiness, consumption, or run completion. Mutable producer tables
retain their existing owners; a handoff retains only later consumers' inputs.
"""
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass(slots=True)
class DayContext:
    prior: Any
    day: Any
    opening_date: str
    profile: Any
    identity: str
    execute_calculation: Callable[..., Any]
    report_exceptions: Any
    native_daily: bool
    master_snapshot: Any
    today: str
    now: str
    finalization: Any
    completion: Any
    master: Any
    master_reused: bool
    master_work: Any


@dataclass(slots=True)
class DayPhase:
    context: DayContext
    importer: Any
    control_final: Any
    control_aux: Any
    diagnostics: Any
    force_alert_capture: Any
    completed_boundaries: Any
    nms: Any
    delivery: Any
    supplier_sob: Any
    supplier_moq: Any
    pick_source_digests: Any = field(default=None, kw_only=True)


@dataclass(slots=True)
class PreparedDay(DayPhase):
    daily_input: Any
    supplier_final: Any
    daily: Any
    daily_final: Any
    old_sourcing: Any
    new_sourcing: Any
    standard_attributes: Any
    daily_consumption: Any = field(default=None, kw_only=True)

    @property
    def complete(self):
        return self.context.completion


@dataclass(slots=True)
class BprDay(DayPhase):
    daily_final: Any
    standard_attributes: Any
    bpr_master: Any
    order_state: Any
    calculated: Any
    report: Any
    late: Any
    complete: Any
    operational_input_tables: Any
    pick_state: Any
    pick_sources: Any


@dataclass(slots=True)
class DbmDay(DayPhase):
    bpr_master: Any
    order_state: Any
    calculated: Any
    report: Any
    late: Any
    complete: Any
    operational_input_tables: Any
    pick_state: Any
    pick_sources: Any
    final_dbm: Any
    reports: Any


@dataclass(frozen=True, slots=True)
class ScopedDayOutput:
    """Terminal producer state plus original finite calculation consumers.

    This is deliberately distinct from the Full result passed to finish_run.
    It cannot claim reconstruction of discarded CalculationOutputs diagnostics.
    """
    output: Any
    calculation_sources: Any
