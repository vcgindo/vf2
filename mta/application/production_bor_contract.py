"""Approved production-only normal-BOR Black-band amendment.

The existing normal BOR calculation remains the owner of SOB/MOQ and the four
legacy requirement bands.  Its ``r1_bor`` result deliberately omits the
DispatchColor that it consumed.  Callers must therefore project
``r1_requirement[*].colours.dispatch.band`` into ``COLOUR_FIELDS`` from the
same calculation output.  This module does no calculation or state lookup.
"""
from copy import deepcopy
from decimal import Decimal

from mta.domain.complete_daily_scalars import ascii_equal
from mta.application.row_bag_lookup import AsciiBagLookup


POLICY = "fresh-production-normal-bor-black-v1"

INPUT_FIELDS = (
    "SKUCode", "WHCode", "SupplierCode", "OriginalReq", "DispatchReq",
    "ReqTopOfRed", "ReqTopOfYellow", "ReqTopOfGreen", "ReqTopOfBlue",
    *(f"SKULocAtt{i:02}" for i in range(1, 16)),
    "CumulativeTOR", "CumulativeTOY", "CumulativeTOG", "CumulativeTOB",
)
OUTPUT_FIELDS = (*INPUT_FIELDS, "ReqTopOfBlack", "CumulativeTOBlack")
COLOUR_FIELDS = ("SKUCode", "WHCode", "DispatchColor")
QUANTITY_FIELDS = (
    "OriginalReq", "DispatchReq", "ReqTopOfRed", "ReqTopOfYellow",
    "ReqTopOfGreen", "ReqTopOfBlue", "CumulativeTOR", "CumulativeTOY",
    "CumulativeTOG", "CumulativeTOB",
)
COLOURS = ("Black", "Red", "Yellow", "Green", "Blue", "White", "Grey")


def _int(value, field):
    if isinstance(value, bool) or not isinstance(value, (int, str, Decimal)):
        raise ValueError(f"Native BOR SQL int required: {field}")
    number = Decimal(value)
    if (not number.is_finite() or number != number.to_integral_value()
            or not -2147483648 <= number <= 2147483647):
        raise ValueError(f"Native BOR SQL int differs or overflows: {field}")
    return int(number)


def _text(value, field, *, nullable=False):
    if value is None and nullable:
        return None
    if not isinstance(value, str) or len(value) > 50:
        raise ValueError(f"Native BOR text(50) required: {field}")
    return value


def _same_pair(left, right):
    return (ascii_equal(left["SKUCode"], right["SKUCode"])
            and ascii_equal(left["WHCode"], right["WHCode"]))


def _validate_supplier(row):
    if not isinstance(row, dict) or set(row) != set(INPUT_FIELDS):
        raise ValueError("Full 28-field SupplierDispatchReq source required")
    for field in ("SKUCode", "WHCode", "SupplierCode"):
        _text(row[field], field)
    for field in QUANTITY_FIELDS:
        _int(row[field], field)
    for field in (f"SKULocAtt{i:02}" for i in range(1, 16)):
        _text(row[field], field, nullable=True)


def _validate_colour(row):
    if not isinstance(row, dict) or set(row) != set(COLOUR_FIELDS):
        raise ValueError("Exact same-run DispatchColor projection required")
    _text(row["SKUCode"], "SKUCode")
    _text(row["WHCode"], "WHCode")
    _text(row["DispatchColor"], "DispatchColor")
    if not any(ascii_equal(row["DispatchColor"], colour) for colour in COLOURS):
        raise ValueError("Canonical same-run DispatchColor required")


def produce(*, supplier_dispatch_rows, dispatch_colours, policy):
    """Return the complete 30-field production BOR source in retained order.

    ``dispatch_colours`` is a unique same-run SKU/location projection of
    ``r1_requirement[*].colours.dispatch.band``.  It may include non-top nodes
    because those calculated nodes do not all produce SupplierDispatchReq rows.
    """
    if policy != POLICY:
        raise ValueError("Approved production normal-BOR policy required")
    if not isinstance(supplier_dispatch_rows, list) or not isinstance(dispatch_colours, list):
        raise ValueError("Explicit same-run normal-BOR populations required")

    for row in supplier_dispatch_rows:
        _validate_supplier(row)
    for index, row in enumerate(dispatch_colours, 1):
        try:
            _validate_colour(row)
        except ValueError as error:
            context = {name: repr(row.get(name))[:120] for name in COLOUR_FIELDS} if isinstance(row, dict) else {}
            raise ValueError(f"{error}; colour ordinal={index}, context={context}") from error
    # Validate the complete population first, retaining error precedence.  The
    # ordered lookup only narrows candidates; the original SQL predicate still
    # owns equality and its denials for unqualified keys.
    seen = []
    colours = AsciiBagLookup(seen, ("SKUCode", "WHCode"), ascii_equal)
    for index, row in enumerate(dispatch_colours, 1):
        if any(_same_pair(row, prior) for prior in colours.candidates(row, ("SKUCode", "WHCode"))):
            raise ValueError(f"Ambiguous same-run DispatchColor for SKU/location; colour ordinal={index}, "
                             f"SKUCode={row['SKUCode']!r}, WHCode={row['WHCode']!r}")
        seen.append(row)
        colours.add(row)

    result = []
    for index, source in enumerate(supplier_dispatch_rows, 1):
        matches = [row for row in colours.candidates(source, ("SKUCode", "WHCode")) if _same_pair(source, row)]
        if len(matches) != 1:
            raise ValueError("Missing or ambiguous same-run DispatchColor for SupplierDispatchReq; "
                             f"supplier ordinal={index}, SKUCode={source['SKUCode']!r}, WHCode={source['WHCode']!r}")
        black = ascii_equal(matches[0]["DispatchColor"], "Black")
        values = {field: deepcopy(source[field]) for field in INPUT_FIELDS}
        for field in QUANTITY_FIELDS:
            values[field] = _int(values[field], field)
        red = _int(source["ReqTopOfRed"], "ReqTopOfRed")
        values["ReqTopOfBlack"] = red if black else 0
        values["ReqTopOfRed"] = 0 if black else red
        values["CumulativeTOBlack"] = values["ReqTopOfBlack"]
        cumulative = values["ReqTopOfBlack"] + values["ReqTopOfRed"]
        values["CumulativeTOR"] = _int(cumulative, "CumulativeTOR")
        for output, field in (("CumulativeTOY", "ReqTopOfYellow"),
                              ("CumulativeTOG", "ReqTopOfGreen"),
                              ("CumulativeTOB", "ReqTopOfBlue")):
            cumulative = _int(cumulative + _int(values[field], field), output)
            values[output] = cumulative
        result.append({field: values[field] for field in OUTPUT_FIELDS})
    return result
