"""Pure ports of the canonical BOR/RRR order-allocation operational SQL.

The functions consume explicit source-shaped row populations.  They do not read
runtime state and they do not claim an order where the source INSERT/SELECT has
none.  Python list order is retained as the source-bag order for later native
qualification.
"""
from mta.row_sequences import is_record_rows
from copy import deepcopy
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import math


SOURCES = {
    "collect": (
        "Scripts/BPR/OrderAllocationReports/CollectBOR_OrderAllocationData.sql",
        "e06d22c31b0b51b6ba375c4bdf8ddeac52806d6e0b5b1c362a77dd8d3b4b18da",
    ),
    "report": (
        "Scripts/BPR/OrderAllocationReports/GenerateBOR_OrderAllocation.sql",
        "9a063498e99060a119f5c82655de61074f2a4cb895beb444ce2cbb8714ef5d9c",
    ),
    "bor_history": (
        "Scripts/BPR/OrderAllocationReports/CollectBOR_OrderAllocationHistory.sql",
        "4a58bb30a2b94c48693297852cafe0f48748f62f76c09178c0c2996e83298340",
    ),
    "rrr_history": (
        "Scripts/BPR/OrderAllocationReports/CollectRRR_OrderAllocationHistory.sql",
        "266ec95240ef468b94ad1e433235723e8cbb04115fbbb35083c7825b24c2ca5b",
    ),
}


def _columns(*definitions):
    return tuple(dict(name=name, sql_type=sql_type, nullable=nullable)
                 for name, sql_type, nullable in definitions)


BOR_COLUMNS = (
    "SKUCode", "WhCode", "SupplierCode", "Norm", "VirtualNorm", "Stock", "GIT",
    "ParentLeftoverStock", "Requirement", "Req_TOB", "Req_TOR", "Req_TOY", "Req_TOG",
    "Req_TOBlue", "DispatchQty", "Dispatch_TOB", "Dispatch_TOR", "Dispatch_TOY",
    "Dispatch_TOG", "Dispatch_ToBlue", "DispatchColor", "OrderBlackUnsatisfiedPercentage",
    "OrderRedUnsatisfiedPercentage", "OrderYellowUnsatisfiedPercentage",
    "OrderGreenUnsatisfiedPercentage", "DispatchPen",
)
RRR_COLUMNS = (
    "SKUCode", "WhCode", "ParentWhCode", "AllocationFor", "Norm", "VirtualNorm", "Stock",
    "GIT", "LeftoverParentStock", "Requirement", "TOBlack_ReqQty", "TOR_ReqQty",
    "TOY_ReqQty", "TOGreen_ReqQty", "TOBlue_ReqQty", "RationedQty", "RationedCasePacks",
    "TOBlack_AllocQty", "TOR_AllocQty", "TOY_AllocQty", "TOGreen_AllocQty",
    "TOBlue_AllocQty", "DispatchColor", "AdvAllocDone",
)

NATIVE_SCHEMAS = {
    "BORWithOrderAllocation": _columns(
        *((name, "nvarchar(50)", False) for name in BOR_COLUMNS[:3]),
        *((name, "int", False) for name in BOR_COLUMNS[3:20]),
        ("DispatchColor", "nvarchar(10)", False),
        *((name, "decimal(10,2)", False) for name in BOR_COLUMNS[21:]),
    ),
    "BOR_OrderAllocationHistory": _columns(
        *((name, "nvarchar(50)", False) for name in BOR_COLUMNS[:3]),
        *((name, "int", False) for name in BOR_COLUMNS[3:20]),
        ("DispatchColor", "nvarchar(10)", False),
        *((name, "decimal(10,2)", False) for name in BOR_COLUMNS[21:]),
        ("ReportDate", "date", False),
    ),
    "RRR_OrderAllocation": _columns(
        ("SKUCode", "nvarchar(50)", False), ("WhCode", "nvarchar(50)", False),
        ("ParentWhCode", "nvarchar(50)", False), ("AllocationFor", "nvarchar(10)", True),
        *((name, "int", True) for name in RRR_COLUMNS[4:10]),
        *((name, "int", False) for name in RRR_COLUMNS[10:15]),
        *((name, "int", True) for name in RRR_COLUMNS[15:17]),
        *((name, "int", False) for name in RRR_COLUMNS[17:22]),
        ("DispatchColor", "nvarchar(10)", True), ("AdvAllocDone", "int", False),
    ),
    "RRR_OrderAllocationHistory": _columns(
        ("SKUCode", "nvarchar(50)", False), ("WhCode", "nvarchar(50)", False),
        ("ParentWhCode", "nvarchar(50)", False), ("AllocationFor", "nvarchar(10)", True),
        *((name, "int", True) for name in RRR_COLUMNS[4:10]),
        *((name, "int", False) for name in RRR_COLUMNS[10:15]),
        *((name, "int", True) for name in RRR_COLUMNS[15:17]),
        *((name, "int", False) for name in RRR_COLUMNS[17:22]),
        ("DispatchColor", "nvarchar(10)", True), ("AdvAllocDone", "int", False),
        ("ReportDate", "date", False),
    ),
}

ORDER_QUALIFICATION = {
    "BORWithOrderAllocation": "INSERT has no ORDER BY; source-bag order retained pending native qualification",
    "BOR report non-MTO": "ORDER BY ColorSequence.SequenceNo, DispatchPen DESC; ties retain source-bag order pending native qualification",
    "BOR report MTO": "ORDER BY colour and four unsatisfied percentages then DispatchPen; ties retain source-bag order pending native qualification",
    "BOR history": "DELETE/INSERT has no ORDER BY; surviving predecessor then current source-bag order retained pending native qualification",
    "RRR history": "DELETE/INSERT has no ORDER BY; surviving predecessor then current source-bag order retained pending native qualification",
}

BPR_MASTER_FIELDS = ("SKUCode", "WHCode", "ParentWhCode")
SOB_FIELDS = ("SKUCode", "WHCode", "SupplierCode", "SOB")
MOQ_FIELDS = ("SKUCode", "WHCode", "SupplierCode", "MOQ")
REQUIREMENT_FIELDS = (
    "SKUCode", "WhCode", "ParentWhCode", "OrderReqBlack", "OrderReqRed", "OrderReqYellow",
    "OrderReqGreen", "OrderReqBlue", "NormReqBlack", "NormReqRed", "NormReqYellow",
    "NormReqGreen", "OrderBlackBand", "OrderRedBand", "OrderYellowBand", "OrderGreenBand",
)
RATIONED_FIELDS = (
    "SKUCode", "WhCode", "Norm", "VirtualNorm", "Stock", "GIT", "LeftOverParentStock",
    "DispatchPen",
)
BPR_TABLE_FIELDS = ("SKUCode", "WhCode")
COLOR_FIELDS = ("Color", "SequenceNo")
SKU_DESCRIPTION_FIELDS = ("SKUCode", "SKUDescription")
SITE_DESCRIPTION_FIELDS = ("WHCode", "WHDescription")
REQ_REPORT_FIELDS = ("SKUCode", "WhCode", "AdvAllocDone")

BOR_REPORT_HEADER = (
    "SKU Code", "SKU Description", "Loc Code", "Loc Description", "Supplier Code",
    "Supplier Description", "Norm", "Virtual Norm", "Stock", "GIT", "Parent Leftover stock",
    "Requirement", "Req_TOB", "Req_TOR", "Req_TOY", "Req_TOG", "Req_ToBlue",
    "Dispatch Qty", "Dispatch_TOB", "Dispatch_TOR", "Dispatch_TOY", "Dispatch_TOG",
    "Dispatch_ToBlue", "Dispatch Color", "Adv Allocation",
)


class LegacyBorAmbiguity(ValueError):
    """A source UPDATE has multiple different eligible winners."""


def _require_rows(name, rows, fields):
    if not is_record_rows(rows):
        raise ValueError(f"{name} must be an explicit row list")
    expected = set(fields)
    for row in rows:
        if not isinstance(row, dict) or set(row) != expected:
            raise ValueError(f"{name} row fields differ from its typed source projection")


def _text(value, limit, *, nullable=False):
    if value is None and nullable:
        return
    if not isinstance(value, str) or len(value) > limit:
        raise ValueError("Native SQL text value required")


def _validate_collect_inputs(bpr_master, sob_data, moq_data, requirements,
                             rationed_report, bpr_table):
    for row in bpr_master:
        _text(row["SKUCode"], 50); _text(row["WHCode"], 50)
        _text(row["ParentWhCode"], 50, nullable=True)
    for row in sob_data:
        for field in ("SKUCode", "WHCode", "SupplierCode"):
            _text(row[field], 50)
        try:
            sob = float(row["SOB"])
        except (TypeError, ValueError):
            raise ValueError("Native SQL float value required") from None
        if not math.isfinite(sob):
            raise ValueError("Native SQL float value required")
    for row in moq_data:
        for field in ("SKUCode", "WHCode", "SupplierCode"):
            _text(row[field], 50)
        _int(row["MOQ"])
    for row in requirements:
        for field in ("SKUCode", "WhCode", "ParentWhCode"):
            _text(row[field], 50)
        for field in REQUIREMENT_FIELDS[3:]:
            if row[field] is not None:
                _int(row[field])
    for row in rationed_report:
        _text(row["SKUCode"], 50); _text(row["WhCode"], 50)
        for field in ("Norm", "VirtualNorm"):
            if row[field] is not None:
                _int(row[field])
        for field in ("Stock", "GIT", "LeftOverParentStock"):
            _int(row[field])
        if row["DispatchPen"] is not None and Decimal(str(row["DispatchPen"])) != _decimal_10_2(row["DispatchPen"]):
            raise ValueError("vf_RationedReqReport.DispatchPen exceeds native scale")
    for row in bpr_table:
        _text(row["SKUCode"], 50); _text(row["WhCode"], 50)


def _join(left, right, pairs, equal):
    return all(left[a] is not None and right[b] is not None and equal(left[a], right[b])
               for a, b in pairs)


def _sql_add(*values):
    if any(value is None for value in values):
        return None
    result = sum(_int(value) for value in values)
    return _int(result)


def _int(value):
    if isinstance(value, bool):
        raise ValueError("Native SQL int required")
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValueError("Native SQL int required") from None
    if not number.is_finite() or number != number.to_integral_value() or not -2147483648 <= number <= 2147483647:
        raise ValueError("Native SQL int required")
    return int(number)


def _ceiling_share(total, sob):
    if total is None or sob is None:
        return None
    # SOB is native SQL FLOAT, and the expression explicitly introduces 100.0.
    value = math.ceil(float(total) * float(sob) / 100.0)
    return _int(value)


def _decimal_10_2(value):
    try:
        number = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError):
        raise ValueError("Native decimal(10,2) required") from None
    if not number.is_finite() or abs(number) >= Decimal("100000000"):
        raise ValueError("Native decimal(10,2) required")
    return number


def _one_update(values, message):
    """Allow repeated identical writes; reject a source UPDATE with different winners."""
    if not values:
        return None
    first = values[0]
    if any(value != first for value in values[1:]):
        raise LegacyBorAmbiguity(message)
    return first


def _validate_native(rows, table):
    schema = NATIVE_SCHEMAS[table]
    fields = tuple(column["name"] for column in schema)
    _require_rows(table, rows, fields)
    for row in rows:
        for column in schema:
            value = row[column["name"]]
            if value is None:
                if not column["nullable"]:
                    raise ValueError(f"{table}.{column['name']} is NOT NULL")
                continue
            sql_type = column["sql_type"]
            if sql_type == "int":
                _int(value)
            elif sql_type == "decimal(10,2)":
                if Decimal(str(value)) != _decimal_10_2(value):
                    raise ValueError(f"{table}.{column['name']} exceeds native scale")
            elif sql_type == "date":
                date.fromisoformat(value)
            elif sql_type.startswith("nvarchar"):
                limit = int(sql_type.removeprefix("nvarchar(").removesuffix(")"))
                if not isinstance(value, str) or len(value) > limit:
                    raise ValueError(f"{table}.{column['name']} exceeds native text type")


def collect_bor_order_allocation(*, bpr_master, sob_data, moq_data, requirements,
                                 rationed_report, bpr_table, equal):
    """Port ``CollectBOR_OrderAllocationData.sql`` through its final table image."""
    for name, rows, fields in (
        ("BPRMaster", bpr_master, BPR_MASTER_FIELDS), ("SOBData", sob_data, SOB_FIELDS),
        ("MOQData", moq_data, MOQ_FIELDS), ("RequirementInColorBand", requirements, REQUIREMENT_FIELDS),
        ("vf_RationedReqReport", rationed_report, RATIONED_FIELDS),
        ("BPR_Table", bpr_table, BPR_TABLE_FIELDS),
    ):
        _require_rows(name, rows, fields)
    _validate_collect_inputs(bpr_master, sob_data, moq_data, requirements,
                             rationed_report, bpr_table)
    if not callable(equal):
        raise ValueError("Explicit SQL equality adapter required")

    from mta.application.row_bag_lookup import AsciiBagLookup
    masters = AsciiBagLookup(bpr_master, ('SKUCode', 'WHCode'), equal)
    moqs_by_supplier = AsciiBagLookup(moq_data, ('SKUCode', 'WHCode', 'SupplierCode'), equal)
    reqs_by_pair = AsciiBagLookup(requirements, ('SKUCode', 'WhCode'), equal)
    reqs_by_parent = AsciiBagLookup(requirements, ('SKUCode', 'WhCode', 'ParentWhCode'), equal)
    reports_by_pair = AsciiBagLookup(rationed_report, ('SKUCode', 'WhCode'), equal)
    topmost = [row for row in bpr_master if not any(_join(
        row, parent, (("SKUCode", "SKUCode"), ("ParentWhCode", "WHCode")), equal)
        for parent in masters.candidates(row, ("SKUCode", "ParentWhCode")))]
    temp = [dict(SKUCode=r["SKUCode"], WhCode=r["WHCode"], SupplierCode=r["SupplierCode"],
                 SOB=r["SOB"], MOQ=0) for r in sob_data]
    temp_pairs = AsciiBagLookup(temp, ('SKUCode', 'WhCode'), equal)
    temp_suppliers = AsciiBagLookup(temp, ('SKUCode', 'WhCode', 'SupplierCode'), equal)
    def append_temp(row):
        temp.append(row)
        temp_pairs.add(row); temp_suppliers.add(row)
    for row in moq_data:
        if not any(_join(row, prior, (("SKUCode", "SKUCode"), ("WHCode", "WhCode"),
                                      ("SupplierCode", "SupplierCode")), equal) for prior in temp_suppliers.candidates(row, ("SKUCode", "WHCode", "SupplierCode"))):
            append_temp(dict(SKUCode=row["SKUCode"], WhCode=row["WHCode"],
                             SupplierCode=row["SupplierCode"], SOB=100, MOQ=0))
    for row in topmost:
        if not any(_join(row, prior, (("SKUCode", "SKUCode"), ("WHCode", "WhCode")), equal)
                   for prior in temp_pairs.candidates(row, ("SKUCode", "WHCode"))):
            append_temp(dict(SKUCode=row["SKUCode"], WhCode=row["WHCode"],
                             SupplierCode=row["ParentWhCode"], SOB=100, MOQ=0))

    req_fields = ("OrderReqBlack", "OrderReqRed", "OrderReqYellow", "OrderReqGreen",
                  "OrderReqBlue", "NormReqBlack", "NormReqRed", "NormReqYellow", "NormReqGreen")
    for row in temp:
        moqs = [m["MOQ"] for m in moqs_by_supplier.candidates(row, ("SKUCode", "WhCode", "SupplierCode")) if _join(row, m, (("SKUCode", "SKUCode"),
            ("WhCode", "WHCode"), ("SupplierCode", "SupplierCode")), equal)]
        selected = _one_update(moqs, "Legacy MOQ UPDATE has different matching winners")
        if selected is not None:
            row["MOQ"] = _int(selected)
        matches = [r for r in reqs_by_pair.candidates(row, ("SKUCode", "WhCode")) if _join(row, r, (("SKUCode", "SKUCode"),
                                                              ("WhCode", "WhCode")), equal)]
        updates = []
        for req in matches:
            total = _sql_add(*(req[name] for name in req_fields))
            colour = "White"
            for colour_name, order_name, norm_name in (
                ("Black", "OrderReqBlack", "NormReqBlack"),
                ("Red", "OrderReqRed", "NormReqRed"),
                ("Yellow", "OrderReqYellow", "NormReqYellow"),
                ("Green", "OrderReqGreen", "NormReqGreen"),
            ):
                amount = _sql_add(req[order_name], req[norm_name])
                if amount is not None and amount > 0:
                    colour = colour_name
                    break
            else:
                if req["OrderReqBlue"] is not None and _int(req["OrderReqBlue"]) > 0:
                    colour = "Blue"
            value = _ceiling_share(total, row["SOB"])
            updates.append((value, value, colour))
        selected = _one_update(updates, "Legacy requirement UPDATE has different matching winners")
        if selected is None:
            row.update(OriginalReq=None, DispatchReq=None, DispatchColor=None)
        else:
            row.update(OriginalReq=selected[0], DispatchReq=selected[1], DispatchColor=selected[2])

        reports = [report for report in reports_by_pair.candidates(row, ("SKUCode", "WhCode")) if _join(row, report,
            (("SKUCode", "SKUCode"), ("WhCode", "WhCode")), equal)]
        norm_zero = any(report["Norm"] is not None and _int(report["Norm"]) == 0 for report in reports)
        if (row["DispatchReq"] is not None and row["DispatchReq"] > 0
                and row["DispatchReq"] < row["MOQ"]
                and (row["DispatchColor"] in ("Black", "Red", "Yellow") or norm_zero)):
            row["DispatchReq"] = row["MOQ"]
        if row["DispatchReq"] is not None and row["DispatchReq"] < row["MOQ"]:
            # The source LEFT JOIN to BPR_Table contributes no selected/predicate field.
            row["DispatchReq"] = 0

    output = []
    for source in temp:
        reports = [row for row in reports_by_pair.candidates(source, ("SKUCode", "WhCode")) if _join(source, row,
            (("SKUCode", "SKUCode"), ("WhCode", "WhCode")), equal)]
        reqs = [row for row in reqs_by_pair.candidates(source, ("SKUCode", "WhCode")) if _join(source, row,
            (("SKUCode", "SKUCode"), ("WhCode", "WhCode")), equal)]
        for report in reports:
            for req in reqs:
                bands = {}
                for target, order_name, norm_name in (
                    ("Req_TOB", "OrderReqBlack", "NormReqBlack"),
                    ("Req_TOR", "OrderReqRed", "NormReqRed"),
                    ("Req_TOY", "OrderReqYellow", "NormReqYellow"),
                    ("Req_TOG", "OrderReqGreen", "NormReqGreen"),
                ):
                    bands[target] = _ceiling_share(_sql_add(req[order_name], req[norm_name]), source["SOB"])
                bands["Req_TOBlue"] = _ceiling_share(req["OrderReqBlue"], source["SOB"])
                dispatched = source["DispatchReq"] is not None and source["DispatchReq"] > 0
                output.append(dict(
                    SKUCode=deepcopy(source["SKUCode"]), WhCode=deepcopy(source["WhCode"]),
                    SupplierCode=deepcopy(source["SupplierCode"]), Norm=report["Norm"],
                    VirtualNorm=report["VirtualNorm"], Stock=report["Stock"], GIT=report["GIT"],
                    ParentLeftoverStock=report["LeftOverParentStock"], Requirement=source["OriginalReq"],
                    **bands, DispatchQty=source["DispatchReq"],
                    Dispatch_TOB=bands["Req_TOB"] if dispatched else 0,
                    Dispatch_TOR=bands["Req_TOR"] if dispatched else 0,
                    Dispatch_TOY=bands["Req_TOY"] if dispatched else 0,
                    Dispatch_TOG=bands["Req_TOG"] if dispatched else 0,
                    Dispatch_ToBlue=bands["Req_TOBlue"] if dispatched else 0,
                    DispatchColor=source["DispatchColor"],
                    OrderBlackUnsatisfiedPercentage=Decimal("0.00"),
                    OrderRedUnsatisfiedPercentage=Decimal("0.00"),
                    OrderYellowUnsatisfiedPercentage=Decimal("0.00"),
                    OrderGreenUnsatisfiedPercentage=Decimal("0.00"),
                    DispatchPen=report["DispatchPen"],
                ))

    for row in output:
        matching = [source for source in temp_suppliers.candidates(row, ("SKUCode", "WhCode", "SupplierCode")) if _join(row, source, (("SKUCode", "SKUCode"),
            ("WhCode", "WhCode"), ("SupplierCode", "SupplierCode")), equal)]
        deltas = [source["DispatchReq"] - row["Requirement"] for source in matching
                  if source["DispatchReq"] is not None and row["Requirement"] is not None
                  and source["DispatchReq"] > row["Requirement"]]
        delta = _one_update(deltas, "Legacy additional-blue UPDATE has different matching winners")
        if delta is not None:
            row["Dispatch_ToBlue"] = _int(row["Dispatch_ToBlue"] + delta)

        percentages = []
        for req in reqs_by_parent.candidates(row, ("SKUCode", "WhCode", "SupplierCode")):
            if not _join(row, req, (("SKUCode", "SKUCode"), ("WhCode", "WhCode"),
                                    ("SupplierCode", "ParentWhCode")), equal):
                continue
            values = []
            for request, band in (("OrderReqBlack", "OrderBlackBand"),
                                  ("OrderReqRed", "OrderRedBand"),
                                  ("OrderReqYellow", "OrderYellowBand"),
                                  ("OrderReqGreen", "OrderGreenBand")):
                denominator = _int(req[band])
                raw = Decimal(0) if denominator == 0 else Decimal(_int(req[request])) * 100 / Decimal(denominator)
                values.append(_decimal_10_2(raw))
            percentages.append(tuple(values))
        selected = _one_update(percentages, "Legacy unsatisfied-percentage UPDATE has different matching winners")
        if selected is not None:
            for name, value in zip(("OrderBlackUnsatisfiedPercentage", "OrderRedUnsatisfiedPercentage",
                                    "OrderYellowUnsatisfiedPercentage", "OrderGreenUnsatisfiedPercentage"), selected):
                row[name] = value

    _validate_native(output, "BORWithOrderAllocation")
    return output


def _quoted(value):
    return None if value is None else '"' + value + '"'


def generate_bor_order_allocation(*, bor_rows, color_sequence, sku_descriptions,
                                  site_descriptions, requirement_rows, is_mto_environment, equal):
    """Return the two resultsets emitted by ``GenerateBOR_OrderAllocation.sql``."""
    _validate_native(bor_rows, "BORWithOrderAllocation")
    for name, rows, fields in (
        ("ColorSequence", color_sequence, COLOR_FIELDS),
        ("SKUDescriptionTbl", sku_descriptions, SKU_DESCRIPTION_FIELDS),
        ("SiteDescriptionTbl", site_descriptions, SITE_DESCRIPTION_FIELDS),
        ("vf_ReqCalculation", requirement_rows, REQ_REPORT_FIELDS),
    ):
        _require_rows(name, rows, fields)
    for row in color_sequence:
        _text(row["Color"], 10); _int(row["SequenceNo"])
    for row in sku_descriptions:
        _text(row["SKUCode"], 50); _text(row["SKUDescription"], 125)
    for row in site_descriptions:
        _text(row["WHCode"], 50); _text(row["WHDescription"], 125)
    for row in requirement_rows:
        _text(row["SKUCode"], 50); _text(row["WhCode"], 50); _int(row["AdvAllocDone"])
    if type(is_mto_environment) not in (bool, int) or is_mto_environment not in (0, 1) or not callable(equal):
        raise ValueError("Explicit IsMTOEnvironment bit and SQL equality adapter required")

    expanded = []
    ordinal = 0
    for bor in bor_rows:
        colours = [row for row in color_sequence if _join(bor, row, (("DispatchColor", "Color"),), equal)]
        skus = [row for row in sku_descriptions if _join(bor, row, (("SKUCode", "SKUCode"),), equal)] or [None]
        locs = [row for row in site_descriptions if _join(bor, row, (("WhCode", "WHCode"),), equal)] or [None]
        suppliers = [row for row in site_descriptions if _join(bor, row, (("SupplierCode", "WHCode"),), equal)] or [None]
        reqs = [row for row in requirement_rows if _join(bor, row,
            (("SKUCode", "SKUCode"), ("WhCode", "WhCode")), equal)] or [None]
        for colour in colours:
            for sku in skus:
                for loc in locs:
                    for supplier in suppliers:
                        for req in reqs:
                            result = (
                                bor["SKUCode"], _quoted(None if sku is None else sku["SKUDescription"]),
                                bor["WhCode"], _quoted(None if loc is None else loc["WHDescription"]),
                                bor["SupplierCode"], _quoted(None if supplier is None else supplier["WHDescription"]),
                                *(bor[name] for name in BOR_COLUMNS[3:21]),
                                None if req is None else req["AdvAllocDone"],
                            )
                            if len(result) != len(BOR_REPORT_HEADER):
                                raise AssertionError("BOR report projection differs from canonical header")
                            if bool(is_mto_environment):
                                key = (colour["SequenceNo"], -Decimal(bor["OrderBlackUnsatisfiedPercentage"]),
                                    -Decimal(bor["OrderRedUnsatisfiedPercentage"]),
                                    -Decimal(bor["OrderYellowUnsatisfiedPercentage"]),
                                    -Decimal(bor["OrderGreenUnsatisfiedPercentage"]),
                                    -Decimal(bor["DispatchPen"]), ordinal)
                            else:
                                key = (colour["SequenceNo"], -Decimal(bor["DispatchPen"]), ordinal)
                            expanded.append((key, result)); ordinal += 1
    expanded.sort(key=lambda item: item[0])
    return {"header_resultset": [BOR_REPORT_HEADER],
            "data_resultset": [row for _, row in expanded],
            "order_qualification": ORDER_QUALIFICATION[
                "BOR report MTO" if bool(is_mto_environment) else "BOR report non-MTO"]}


def _history(*, opening, current, business_date, horizon, current_table, history_table):
    _validate_native(opening, history_table)
    _validate_native(current, current_table)
    today = date.fromisoformat(business_date)
    days = _int(horizon)
    cutoff = today - timedelta(days=days)
    result = [deepcopy(row) for row in opening
              if date.fromisoformat(row["ReportDate"]) != today
              and date.fromisoformat(row["ReportDate"]) > cutoff]
    for row in current:
        result.append({**deepcopy(row), "ReportDate": business_date})
    _validate_native(result, history_table)
    return result


def collect_bor_order_allocation_history(*, opening_history, current_bor, business_date, horizon):
    return _history(opening=opening_history, current=current_bor, business_date=business_date,
                    horizon=horizon, current_table="BORWithOrderAllocation",
                    history_table="BOR_OrderAllocationHistory")


def collect_rrr_order_allocation_history(*, opening_history, current_rrr, business_date, horizon):
    return _history(opening=opening_history, current=current_rrr, business_date=business_date,
                    horizon=horizon, current_table="RRR_OrderAllocation",
                    history_table="RRR_OrderAllocationHistory")
