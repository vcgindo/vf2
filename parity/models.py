from __future__ import annotations
from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class ComparisonClass(StrEnum):
    EXACT = "A"
    MULTISET = "B"
    TECHNICAL_NORMALIZATION = "C"
    APPROVED_INTENTIONAL_CHANGE = "D"


class ComparisonStatus(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    INCOMPARABLE_INPUT = "INCOMPARABLE_INPUT"
    LEGACY_EXECUTION_ERROR = "LEGACY_EXECUTION_ERROR"
    LEGACY_NONDETERMINISTIC = "LEGACY_NONDETERMINISTIC"
    NOT_RUN = "NOT_RUN"


@dataclass(frozen=True, slots=True)
class OutputPolicy:
    output_id: str
    comparison_class: ComparisonClass
    ordered: bool
    key_fields: tuple[str, ...]
    approved_normalizers: tuple[str, ...] = ()
    approved_change_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class FieldDiff:
    output_id: str
    key: tuple[tuple[str, Any], ...]
    field: str
    legacy_value: Any
    new_value: Any
    comparison_class: ComparisonClass
    rule_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ComparisonResult:
    scenario_id: str
    status: ComparisonStatus
    diffs: tuple[FieldDiff, ...]
    message: str

