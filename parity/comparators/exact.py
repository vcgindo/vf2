"""Lossless, dependency-free comparison primitives for future captured records."""
from __future__ import annotations
import json
from collections import Counter
from typing import Any, Iterable, Mapping
from parity.models import ComparisonClass, ComparisonResult, ComparisonStatus, FieldDiff, OutputPolicy


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _key(record: Mapping[str, Any], fields: tuple[str, ...]) -> tuple[tuple[str, Any], ...]:
    missing = [field for field in fields if field not in record]
    if missing:
        raise ValueError(f"record missing key field(s): {', '.join(missing)}")
    return tuple((field, record[field]) for field in fields)


def compare_records(*, scenario_id: str, output_policy: OutputPolicy, legacy_rows: Iterable[Mapping[str, Any]], new_rows: Iterable[Mapping[str, Any]], rule_ids: tuple[str, ...]) -> ComparisonResult:
    if output_policy.comparison_class in {ComparisonClass.TECHNICAL_NORMALIZATION, ComparisonClass.APPROVED_INTENTIONAL_CHANGE} and not output_policy.approved_normalizers and not output_policy.approved_change_ids:
        raise ValueError("Class C/D requires an explicit approved normalizer or change record")
    legacy, new = list(legacy_rows), list(new_rows)
    for row in legacy + new:
        _key(row, output_policy.key_fields)
    legacy_values, new_values = (legacy, new) if output_policy.ordered else (sorted(legacy, key=_canonical), sorted(new, key=_canonical))
    if _canonical(legacy_values) == _canonical(new_values):
        return ComparisonResult(scenario_id, ComparisonStatus.PASS, (), "exact records match")
    diffs: list[FieldDiff] = []
    for index in range(max(len(legacy_values), len(new_values))):
        left = legacy_values[index] if index < len(legacy_values) else None
        right = new_values[index] if index < len(new_values) else None
        if _canonical(left) == _canonical(right):
            continue
        if left is None or right is None:
            record = left or right or {}
            diffs.append(FieldDiff(output_policy.output_id, _key(record, output_policy.key_fields), "__row__", left, right, output_policy.comparison_class, rule_ids))
            continue
        for field in sorted(set(left) | set(right)):
            if field not in left or field not in right or _canonical(left[field]) != _canonical(right[field]):
                diffs.append(FieldDiff(output_policy.output_id, _key(left, output_policy.key_fields), field, left.get(field, {"__missing__": True}), right.get(field, {"__missing__": True}), output_policy.comparison_class, rule_ids))
    return ComparisonResult(scenario_id, ComparisonStatus.FAIL, tuple(diffs), "typed record difference")


def multiset_signature(rows: Iterable[Mapping[str, Any]]) -> Counter[str]:
    """Diagnostic helper that retains duplicate occurrences rather than applying DISTINCT."""
    return Counter(_canonical(row) for row in rows)
