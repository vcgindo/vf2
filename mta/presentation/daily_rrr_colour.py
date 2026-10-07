"""Pure Normal-MTA colour-band rows from the deployed RRR allocation SQL.

Authority: ``GenerateRRR_OrderAllocation.sql`` SHA256
``4f034a2fab598d87683d5ab0457cf6af49460de67dbf42ad856a1dc3cdd26e7b``.
The deployed BAT invokes that script only for MTO.  The retained 3006 smoke
exception permits its unchanged Norm formula at ``IsMTOEnvironment=0``.  This
module therefore rejects every non-empty or unproved order-allocation source.
It does not persist or serve the rows.
"""
from decimal import Decimal, InvalidOperation, ROUND_CEILING
from types import MappingProxyType

from mta.application.r1_importer_master import _sql_key


SOURCE_SQL_SHA256 = "4f034a2fab598d87683d5ab0457cf6af49460de67dbf42ad856a1dc3cdd26e7b"
APPROVED_SMOKE_RUN_IDS = frozenset({
    "63c71fa7-944d-4547-a80f-2316a580d3c7",
    "17f0eb84-7b6d-40e9-a288-9441a4d7a860",
})
SMOKE_EXCEPTION = MappingProxyType({
    "controller_turn": "01a114e7-a015-7cb2-917a-275fb398c6c8",
    "instance": "owned-localhost-3006",
    "catalogue": "retained-synthetic",
    "is_mto_environment": 0,
    "population": "Norm-only",
})

OUTPUT_FIELDS = (
    "SKUCode", "WhCode", "ParentWhCode", "AllocationFor", "Norm",
    "VirtualNorm", "Stock", "GIT", "LeftoverParentStock", "Requirement",
    "TOBlack_ReqQty", "TOR_ReqQty", "TOY_ReqQty", "TOGreen_ReqQty",
    "TOBlue_ReqQty", "RationedQty", "RationedCasePacks",
    "TOBlack_AllocQty", "TOR_AllocQty", "TOY_AllocQty",
    "TOGreen_AllocQty", "TOBlue_AllocQty", "DispatchColor", "AdvAllocDone",
)

_REPORT_FIELDS = (
    "SKUCode", "WhCode", "ParentWhCode", "Req", "Norm", "VirtualNorm",
    "Stock", "GIT", "LeftoverParentStock", "NormReq",
    "AllocatedForVirtualNormReq", "ParentPackSize", "DispatchColor",
)
_BAND_INPUT_FIELDS = (
    "sku_code", "location_code", "parent_location_code", "norm_req_black",
    "norm_req_red", "norm_req_yellow", "norm_req_green", "order_req_black",
    "order_req_red", "order_req_yellow", "order_req_green", "order_req_blue",
)
_BAND_MAP = dict(zip(_BAND_INPUT_FIELDS, (
    "SKUCode", "WhCode", "ParentWhCode", "NormReqBlack", "NormReqRed",
    "NormReqYellow", "NormReqGreen", "OrderReqBlack", "OrderReqRed",
    "OrderReqYellow", "OrderReqGreen", "OrderReqBlue",
)))
_INT_MIN, _INT_MAX = -(2 ** 31), 2 ** 31 - 1


def _complete(row, fields, owner):
    missing = [field for field in fields if field not in row]
    if missing:
        raise ValueError(f"{owner} row lacks canonical fields: {missing}")


def _int(value, field, nullable=True):
    if value is None and nullable:
        return None
    if isinstance(value, bool):
        raise ValueError(f"{field} is not a native int")
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValueError(f"{field} is not a native int") from None
    if not number.is_finite() or number != number.to_integral_value():
        raise ValueError(f"{field} is not a native int")
    result = int(number)
    if not _INT_MIN <= result <= _INT_MAX:
        raise ValueError(f"{field} exceeds native int range")
    return result


def _code(value, field):
    if not isinstance(value, str) or len(value) > 50:
        raise ValueError(f"{field} is not a native non-null nvarchar(50)")
    return value


def _key(*values):
    if any(value is None for value in values):
        return None
    return tuple(_sql_key(value) for value in values)


def _add(*values):
    return None if any(value is None for value in values) else sum(values)


def _sub(left, *rights):
    return None if left is None or any(value is None for value in rights) else left - sum(rights)


def _mul(factor, value):
    return None if value is None else factor * Decimal(value)


def _sql_true(comparison):
    return comparison is True


def _lt(left, right):
    return None if left is None or right is None else left < right


def _le(left, right):
    return None if left is None or right is None else left <= right


def _eq(left, right):
    return None if left is None or right is None else left == right


def _ceiling(value):
    return None if value is None else int(Decimal(value).to_integral_value(rounding=ROUND_CEILING))


def _sql_divide(left, right):
    if left is None or right is None:
        return None
    if right == 0:
        raise ValueError("ParentPackSize causes native divide by zero")
    return int(Decimal(left) / Decimal(right))  # SQL int division truncates toward zero.


def _join(rows, key):
    return [row for row in rows if row["_key"] == key] if key is not None else []


def validate_smoke_source(context, band_rows, order_capabilities):
    """Fail closed outside the exact approved Normal-MTA smoke boundary."""
    expected = {
        "run_id", "instance_port", "synthetic", "is_mto_environment",
        "order_capabilities_complete",
    }
    if not isinstance(context, dict) or not expected.issubset(context):
        raise ValueError("RRR colour source requires complete smoke gate metadata")
    if (str(context["run_id"]) not in APPROVED_SMOKE_RUN_IDS
            or context["instance_port"] != 3006
            or context["synthetic"] is not True
            or context["is_mto_environment"] != 0):
        raise ValueError("RRR colour source is outside the approved 3006 Normal-MTA smoke scope")
    if context["order_capabilities_complete"] is not True:
        raise ValueError("RRR colour source cannot prove the complete order capability boundary")
    if not isinstance(order_capabilities, dict) or not order_capabilities:
        raise ValueError("RRR colour source requires explicit complete order capabilities")
    required = {"r1_order_route", "r1_order_bpp", "AllocatedOrders"}
    if not required.issubset(order_capabilities):
        raise ValueError("RRR colour source lacks a required order capability")
    if any(rows is None or not isinstance(rows, (list, tuple))
           for rows in order_capabilities.values()):
        raise ValueError("RRR colour order capability is unavailable")
    if any(rows for rows in order_capabilities.values()):
        raise ValueError("RRR colour AllocatedOrders mapping is unavailable for non-empty order inputs")
    for row in band_rows:
        values = [_int(row[field], field) for field in _BAND_INPUT_FIELDS[7:]]
        if any(value is None or value != 0 for value in values):
            raise ValueError("RRR colour AllocatedOrders mapping is unavailable for order requirements")


def _tor(row):
    virtual, stock, git, allocated = (row[name] for name in
                                      ("VirtualNorm", "Stock", "GIT", "AllocatedForVirtualNormReq"))
    if _sql_true(_eq(virtual, 1)):
        return allocated
    expression = _sub(_mul(Decimal(1) / Decimal(3), virtual), stock, git)
    if _sql_true(_lt(expression, 0)):
        return 0
    return _ceiling(expression) if _sql_true(_le(expression, allocated)) else allocated


def _toy(row, tor):
    virtual, stock, git, allocated = (row[name] for name in
                                      ("VirtualNorm", "Stock", "GIT", "AllocatedForVirtualNormReq"))
    if _sql_true(_eq(virtual, 1)):
        return 0
    expression = _sub(_mul(Decimal(2) / Decimal(3), virtual), stock, git)
    if _sql_true(_lt(expression, 0)):
        return 0
    return _sub(_ceiling(expression), tor) if _sql_true(_le(expression, allocated)) else _sub(allocated, tor)


def _tog(row, tor, toy):
    virtual, stock, git, allocated = (row[name] for name in
                                      ("VirtualNorm", "Stock", "GIT", "AllocatedForVirtualNormReq"))
    if _sql_true(_eq(virtual, 1)):
        return 0
    expression = _sub(virtual, stock, git)
    if _sql_true(_lt(expression, 0)):
        return 0
    if _sql_true(_le(expression, allocated)):
        return _sub(_ceiling(expression), tor, toy)
    return _sub(allocated, tor, toy)


def _adjust_blue(row):
    """Exact lines 243-259; inert for canonical Norm rows (Blue requirement 0)."""
    blue_req = row["TOBlue_ReqQty"]
    if not (blue_req > 0 and row["TOBlue_AllocQty"] < blue_req):
        return row
    red, yellow, green = (row["TOR_AllocQty"], row["TOY_AllocQty"], row["TOGreen_AllocQty"])
    red_match = red == row["TOR_ReqQty"] + blue_req
    yellow_match = yellow == row["TOY_ReqQty"] + blue_req
    green_match = green == row["TOGreen_ReqQty"] + blue_req
    if not (red_match or yellow_match or green_match):
        return row
    before = red + yellow + green
    result = dict(row)
    if red_match:
        result["TOR_AllocQty"] = max(red - blue_req, 0)
    if yellow_match:
        result["TOY_AllocQty"] = max(yellow - blue_req, 0)
    if green_match:
        result["TOGreen_AllocQty"] = max(green - blue_req, 0)
    result["TOBlue_AllocQty"] = before + row["TOBlue_AllocQty"] if blue_req > before + row["TOBlue_AllocQty"] else blue_req
    return result


def norm_rrr_colour_rows(*, rationed_report, requirement_bands, bpr_master,
                         advance_stock_allocations, order_capabilities, context,
                         scope_validator=validate_smoke_source):
    """Return complete RRR_OrderAllocation Norm rows; row order is unspecified.

    Exact duplicate final rows collapse like the source ``UNION``. Unequal rows
    and all inner-join multiplicity remain. Inputs use their stage/native field
    names; values are validated as SQL ``int`` where the pinned DDL says int.
    """
    for row in rationed_report:
        _complete(row, _REPORT_FIELDS, "vf_RationedReqReport")
    for row in requirement_bands:
        _complete(row, _BAND_INPUT_FIELDS, "r1_requirement_band")
    for row in bpr_master:
        _complete(row, ("SKUCode", "WHCode"), "BPRMaster")
    scope_validator(context, requirement_bands, order_capabilities)

    bands = []
    for source in requirement_bands:
        row = {_BAND_MAP[field]: source[field] for field in _BAND_INPUT_FIELDS}
        for field in ("SKUCode", "WhCode", "ParentWhCode"):
            row[field] = _code(row[field], field)
        for field in tuple(_BAND_MAP.values())[3:]:
            row[field] = _int(row[field], field)
        row["_key"] = _key(row["SKUCode"], row["WhCode"])
        bands.append(row)

    masters = []
    for source in bpr_master:
        masters.append(_key(_code(source["SKUCode"], "SKUCode"),
                            _code(source["WHCode"], "WHCode")))

    # GenerateBifurcationOfRationedReq.sql lines 17-33. Each matching master
    # occurrence inserts a Pick occurrence; direct virtual rows are excluded by
    # the later WhCode != ParentWhCode predicate and cannot affect this output.
    picks = []
    for source in rationed_report:
        row = dict(source)
        for field in ("SKUCode", "WhCode", "ParentWhCode"):
            row[field] = _code(row[field], field)
        for field in _REPORT_FIELDS[3:-1]:
            row[field] = _int(row[field], field)
        if not _sql_true(_lt(0, row["Req"])):
            continue
        parent_key = _key(row["SKUCode"], row["ParentWhCode"])
        for master_key in masters:
            if parent_key is not None and parent_key == master_key:
                row_copy = dict(row)
                row_copy["_key"] = _key(row["SKUCode"], row["WhCode"], row["ParentWhCode"])
                picks.append(row_copy)

    tor_rows = [dict(row, TOR=_tor(row)) for row in picks]
    toy_rows = []
    for row in picks:
        for prior in _join(tor_rows, row["_key"]):
            toy_rows.append(dict(row, TOR=prior["TOR"], TOY=_toy(row, prior["TOR"])))
    tog_rows = []
    for row in picks:
        for prior in _join(toy_rows, row["_key"]):
            tog_rows.append(dict(row, TOR=prior["TOR"], TOY=prior["TOY"],
                                 TOG=_tog(row, prior["TOR"], prior["TOY"])))
    blue_rows = []
    for row in picks:
        for prior in _join(tog_rows, row["_key"]):
            stock_git = _add(row["Stock"], row["GIT"])
            tor_b = prior["TOR"] if _sql_true(_eq(stock_git, 0)) else 0
            tor_r = prior["TOR"] if _sql_true(_lt(0, stock_git)) else 0
            toy = 0 if _sql_true(_lt(prior["TOY"], 0)) else prior["TOY"]
            tog = 0 if _sql_true(_lt(prior["TOG"], 0)) else prior["TOG"]
            blue_rows.append(dict(row, TOR_B=tor_b, TOR_R=tor_r, TOY=toy, TOG=tog))

    advances = {}
    for allocation in advance_stock_allocations:
        _complete(allocation, ("sku_code", "source_location_code", "allocated_quantity",
                               "allocation_type"),
                  "r1_advance_stock_allocation")
        if allocation["allocation_type"] != "advance-stock":
            raise ValueError("r1_advance_stock_allocation contains a non-stock allocation")
        key = _key(_code(allocation["sku_code"], "sku_code"),
                   _code(allocation["source_location_code"], "source_location_code"))
        quantity = _int(allocation["allocated_quantity"], "allocated_quantity", nullable=False)
        advances[key] = advances.get(key, 0) + quantity
        _int(advances[key], "AdvAllocDone", nullable=False)

    output = []
    for pick in blue_rows:
        if _key(pick["WhCode"]) == _key(pick["ParentWhCode"]):
            continue
        for band in _join(bands, _key(pick["SKUCode"], pick["WhCode"])):
            requirement = _add(band["NormReqBlack"], band["NormReqRed"],
                               band["NormReqYellow"], band["NormReqGreen"])
            if not _sql_true(_lt(0, requirement)):
                continue
            remaining = _sub(pick["AllocatedForVirtualNormReq"], pick["TOR_B"],
                             pick["TOR_R"], pick["TOY"], pick["TOG"])
            to_blue = 0 if _sql_true(_lt(remaining, 0)) else remaining
            dispatch = ("Black" if _sql_true(_lt(0, band["NormReqBlack"])) else
                        "Red" if _sql_true(_lt(0, band["NormReqRed"])) else
                        "Yellow" if _sql_true(_lt(0, band["NormReqYellow"])) else
                        "Green" if _sql_true(_lt(0, band["NormReqGreen"])) else "White")
            row = {
                "SKUCode": pick["SKUCode"], "WhCode": pick["WhCode"],
                "ParentWhCode": pick["ParentWhCode"], "AllocationFor": "Norm",
                "Norm": pick["Norm"], "VirtualNorm": pick["VirtualNorm"],
                "Stock": pick["Stock"], "GIT": pick["GIT"],
                "LeftoverParentStock": pick["LeftoverParentStock"],
                "Requirement": requirement, "TOBlack_ReqQty": band["NormReqBlack"] or 0,
                "TOR_ReqQty": band["NormReqRed"] or 0,
                "TOY_ReqQty": band["NormReqYellow"] or 0,
                "TOGreen_ReqQty": band["NormReqGreen"] or 0,
                "TOBlue_ReqQty": 0, "RationedQty": pick["AllocatedForVirtualNormReq"],
                "RationedCasePacks": _sql_divide(pick["AllocatedForVirtualNormReq"],
                                                   pick["ParentPackSize"]),
                "TOBlack_AllocQty": pick["TOR_B"] or 0,
                "TOR_AllocQty": pick["TOR_R"] or 0,
                "TOY_AllocQty": pick["TOY"] or 0,
                "TOGreen_AllocQty": pick["TOG"] or 0,
                "TOBlue_AllocQty": to_blue or 0, "DispatchColor": dispatch,
                "AdvAllocDone": advances.get(_key(pick["SKUCode"], pick["WhCode"]), 0),
            }
            row = _adjust_blue(row)
            for field in OUTPUT_FIELDS[4:23]:
                if field != "DispatchColor":
                    row[field] = _int(row[field], field)
            output.append(row)

    # SQL UNION uses set semantics, including NULL-equal duplicate elimination.
    distinct = []
    seen = set()
    for row in output:
        signature = tuple(_sql_key(row[field]) if isinstance(row[field], str) else row[field]
                          for field in OUTPUT_FIELDS)
        if signature not in seen:
            seen.add(signature)
            distinct.append(row)
    return distinct
