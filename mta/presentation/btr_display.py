"""Opt-in BTR rows prepared exactly as the retained browser mapper.

The selected BTR grid reader creates fresh string-valued row dictionaries.  The
presenter consumes those rows in place so an opted-in client does not repeat the
same full-row conversion and Availability scan in the browser.  Non-finite JS
numbers are represented as JSON ``null`` plus a sparse restoration descriptor.
"""
from __future__ import annotations

import math
import re
from typing import Any


STRING_FIELDS = frozenset(
    ("SKUCode", "SKUDescription", "Whcode", "WhCode", "LocationName", "pc", "pn")
)
BRANCHES = ("tech", "eco")

# ECMAScript WhiteSpace and LineTerminator code points accepted before parseFloat.
_JS_SPACE = "\\u0009-\\u000d\\u0020\\u00a0\\u1680\\u2000-\\u200a\\u2028\\u2029\\u202f\\u205f\\u3000\\ufeff"
_PARSE_FLOAT = re.compile(
    rf"^[{_JS_SPACE}]*([+-]?(?:Infinity|(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?))"
)


def display_horizon(payload: dict[str, Any]) -> int | None:
    """Return a validated opt-in horizon; absent/false markers retain raw output."""
    if payload.get("displayPrepared") is not True:
        return None
    value = payload.get("displayHorizon")
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 90:
        raise ValueError("displayHorizon_must_be_an_integer_from_1_to_90")
    return value


def _parse_float(value: str) -> float | None:
    match = _PARSE_FLOAT.match(value)
    if match is None:
        return None
    token = match.group(1)
    try:
        return float(token)
    except ValueError:  # Defensive: the grammar above admits only Python float tokens.
        return None


def _js_string(value: Any) -> str:
    """JS primitive String conversion needed by the seven retained text fields."""
    if isinstance(value, str):
        return value
    if value is None:
        return ""
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, float):
        if math.isnan(value):
            return "NaN"
        if math.isinf(value):
            return "Infinity" if value > 0 else "-Infinity"
        if value == 0:
            return "0"
    # BTR SQL rows are strings. This fallback covers ordinary integral test/input
    # primitives without pretending to reproduce JS object coercion.
    return str(value)


def _convert(key: str, value: Any) -> Any:
    if value is None:
        value = ""
    if key in STRING_FIELDS:
        return _js_string(value)
    if isinstance(value, str):
        parsed = _parse_float(value)
        if parsed is not None and not math.isnan(parsed):
            return parsed
    return value


def _parse_int_is_below_100(value: Any) -> bool:
    """The only observable use of JS parseInt in mapBTRRowData.

    Numeric strings have already passed through parseFloat.  JS renders finite
    numbers outside [1e-6, 1e21) in exponent form, so parseInt consumes only the
    one-digit mantissa integer and therefore reports a value below 100.
    """
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        number = float(value)
        if not math.isfinite(number):
            return False
        magnitude = abs(number)
        if magnitude != 0 and (magnitude < 1e-6 or magnitude >= 1e21):
            return True
        return math.trunc(number) < 100
    if isinstance(value, str):
        # Any string for which parseInt can succeed would already have been
        # converted by parseFloat. Empty and remaining nonnumeric strings fail.
        return False
    return False


def _availability(non_black: int, denominator: int) -> float:
    if denominator == 0:
        return float("nan")
    value = (non_black / denominator) * 100.0
    # ECMAScript toFixed(2) chooses the nearer decimal integer, choosing the
    # larger integer on an exact tie. Work from the exact binary float ratio.
    numerator, binary_denominator = value.as_integer_ratio()
    quotient, remainder = divmod(numerator * 100, binary_denominator)
    if remainder * 2 >= binary_denominator:
        quotient += 1
    # parseFloat is then applied to the fixed decimal string.
    return quotient / 100.0


def _token(value: float) -> str:
    if math.isnan(value):
        return "NaN"
    return "Infinity" if value > 0 else "-Infinity"


def prepare_display(result: dict[str, Any], horizon: int) -> dict[str, Any]:
    """Consume fresh BTR grid rows and add the opt-in display contract."""
    descriptors: list[list[Any]] = []
    for branch in BRANCHES:
        rows = result.get(branch)
        if rows is None:
            continue
        for row_index, row in enumerate(rows):
            for key in tuple(row):
                row[key] = _convert(key, row[key])

            non_black = 0
            empty = 0
            for index in range(90, 90 - horizon, -1):
                value = row.get(f"D{index}", _MISSING)
                if value != "" and _parse_int_is_below_100(value):
                    non_black += 1
                if value == "":
                    empty += 1
            row["Availability"] = _availability(non_black, horizon - empty)

            for field, value in tuple(row.items()):
                if isinstance(value, float) and not math.isfinite(value):
                    descriptors.append([branch, row_index, field, _token(value)])
                    row[field] = None

    result["displayPrepared"] = True
    result["displayNonFinite"] = descriptors
    return result


_MISSING = object()
