"""Pure ports of the deployed daily goods-in-transit source processors.

Authority:
* ``Scripts/Importer/ValidateGoodsInTransit.sql``
  SHA256 ``6db973f9f72e28fcb6d22d8e9ce2e069708b6f656a7169573680afbd45e81257``
* ``Scripts/BPR/GoodsInTransitTransporterMaster.sql``
  SHA256 ``79a3a80bd45d989b37ae59d08259c7a39aeda8ef51e2261a722d241cc689a79d``

Callers supply full raw shipment facts.  This module never adapts aggregate GIT
or the retained seven-field shipment ledger into the wider native raw schema.
SQL output order is unspecified; input and join occurrence multiplicity remains.
"""
from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation

from mta.application.r1_importer_master import _sql_key


VALIDATE_SOURCE_SHA256 = "6db973f9f72e28fcb6d22d8e9ce2e069708b6f656a7169573680afbd45e81257"
TRANSPORTER_SOURCE_SHA256 = "79a3a80bd45d989b37ae59d08259c7a39aeda8ef51e2261a722d241cc689a79d"

RAW_FIELDS = (
    "SKUCode", "ToLocationCode", "FromLocationCode", "CurrentLocationCode",
    "LRCode", "OrderNo", "CreationDate", "GateOutDate", "InTransitQty",
    "TransporterCode", "Remark", "ReportDate",
)
TRANSIT_FIELDS = (
    "SKUCode", "WhCode", "ParentWhCode", "CurrentLocationCode", "LRCode",
    "OrderNo", "CreationDate", "GateOutDate", "InTransitQty",
    "TransporterCode", "Ageing", "ETA", "TLT", "SLT", "Remark", "ReportDate",
)
TRANSPORTER_FIELDS = (
    "Status", "OrderNo", "SKUCode", "WhCode", "ParentWhCode",
    "CurrentLocation", "TransporterCode", "TransporterName",
    "TransporterContact", "LRCode", "InTransitQty", "PhysicalInventoryPen",
    "PhysicalInventoryColor", "PipelineInventoryColor", "Price", "SLT",
    "Ageing", "ETA", "Remark", "CreationDate", "TruckStatus", "SKUStatus",
    "IsParent", "IsReceiving",
)


def _require_rows(rows, required, label):
    if not isinstance(rows, list):
        raise ValueError(label + " must be a list")
    for row in rows:
        if not isinstance(row, dict) or any(name not in row for name in required):
            raise ValueError(label + " requires complete fields: " + ",".join(required))


def _text(value, field, limit=None):
    if value is not None and not isinstance(value, str):
        raise ValueError(field + " must be text or NULL")
    if value is not None and limit is not None and len(value) > limit:
        raise ValueError(field + " exceeds native width")
    return value


def _integer(value, field):
    if value is not None and (type(value) is not int):
        raise ValueError(field + " must be an integer or NULL")
    if value is not None and not -(2 ** 31) <= value < 2 ** 31:
        raise ValueError(field + " exceeds native int range")
    return value


def _date(value, field):
    if value is not None and (not isinstance(value, date) or isinstance(value, datetime)):
        raise ValueError(field + " must be a date or NULL")
    return value


def _day_difference(start, end):
    return None if start is None else (end - start).days


def _raw_join_key(value):
    # The SQL applies LTRIM/RTRIM to the raw side before its CI_AS equality.
    return _sql_key(value.strip(' ')) if isinstance(value, str) else value


def _join_key(value):
    return _sql_key(value)


def validate_goods_in_transit(raw_rows, standards, business_date, run_timestamp):
    """Port ValidateGoodsInTransit.sql lines 23-97 as a relational bag.

    The disabled native NULL-rejection block remains disabled.  Only rows where
    SKU, destination and origin are all NULL are deleted.  Negative quantities
    emit the native -166 RejectedMaster diagnostic and remain eligible for the
    subsequent standard-attribute inner join.
    """
    _require_rows(raw_rows, RAW_FIELDS, "InTransitDataRaw")
    _require_rows(standards, ("SKUCode", "WhCode", "SLT"), "SKULocStandardAttributes")
    if not isinstance(business_date, date) or isinstance(business_date, datetime):
        raise ValueError("business_date must be a date")
    if not isinstance(run_timestamp, datetime):
        raise ValueError("run_timestamp must be a datetime")

    standard_index = defaultdict(list)
    for standard in standards:
        sku = _text(standard["SKUCode"], "standard.SKUCode", 50)
        wh = _text(standard["WhCode"], "standard.WhCode", 50)
        slt = _integer(standard["SLT"], "standard.SLT")
        if sku is not None and wh is not None:
            standard_index[(_join_key(sku), _join_key(wh))].append(slt)

    retained = []
    diagnostics = []
    for source in raw_rows:
        row = {name: source[name] for name in RAW_FIELDS}
        for name in ("SKUCode", "ToLocationCode", "FromLocationCode",
                     "CurrentLocationCode", "LRCode", "OrderNo",
                     "TransporterCode"):
            _text(row[name], "raw." + name, 50)
        _text(row["Remark"], "raw.Remark")
        for name in ("CreationDate", "GateOutDate", "ReportDate"):
            _date(row[name], "raw." + name)
        quantity = _integer(row["InTransitQty"], "raw.InTransitQty")
        if all(row[name] is None for name in
               ("SKUCode", "ToLocationCode", "FromLocationCode")):
            continue
        retained.append(row)
        if quantity is not None and quantity < 0:
            if row["SKUCode"] is None or row["ToLocationCode"] is None:
                # RejectedMaster declares both codes NOT NULL; the deployed TRY
                # would fail rather than silently manufacture a placeholder.
                raise ValueError("Negative GIT diagnostic requires non-NULL SKUCode/ToLocationCode")
            diagnostics.append({
                "SKUCode": row["SKUCode"], "WhCode": row["ToLocationCode"],
                "RejectionDate": run_timestamp, "ReasonCode": -166,
                "ReasonDescription": "negative Qty in GoodsInTransit Data file/table",
            })

    output = []
    for row in retained:
        key = (_raw_join_key(row["SKUCode"]), _raw_join_key(row["ToLocationCode"]))
        if None in key:
            continue
        for slt in standard_index.get(key, ()):
            creation = row["CreationDate"]
            gate_out = row["GateOutDate"]
            output.append({
                "SKUCode": row["SKUCode"], "WhCode": row["ToLocationCode"],
                "ParentWhCode": row["FromLocationCode"],
                "CurrentLocationCode": row["CurrentLocationCode"],
                "LRCode": row["LRCode"], "OrderNo": row["OrderNo"],
                "CreationDate": creation, "GateOutDate": gate_out,
                "InTransitQty": row["InTransitQty"],
                "TransporterCode": row["TransporterCode"],
                "Ageing": _day_difference(creation, business_date),
                "ETA": None if creation is None or slt is None else creation + timedelta(days=slt),
                "TLT": _day_difference(gate_out, business_date), "SLT": slt,
                "Remark": row["Remark"], "ReportDate": row["ReportDate"],
            })
    return {"rows": output, "diagnostics": diagnostics}


def _decimal(value, field):
    if value is None or isinstance(value, bool):
        raise ValueError(field + " must be a finite numeric value")
    try:
        result = Decimal(value)
    except (InvalidOperation, TypeError, ValueError) as error:
        raise ValueError(field + " must be a finite numeric value") from error
    if not result.is_finite():
        raise ValueError(field + " must be a finite numeric value")
    return result


def _nullable_decimal(value, field):
    return None if value is None else _decimal(value, field)


def _target_int(value, field):
    # SQL Server's implicit decimal-to-int conversion truncates toward zero.
    return None if value is None else _integer(int(_decimal(value, field)), field)


def transporter_master(transit, directory, rationed_report, standards, super_delay_factor):
    """Port GoodsInTransitTransporterMaster.sql's insert and overwrite passes."""
    _require_rows(transit, TRANSIT_FIELDS, "InTransitData")
    _require_rows(directory, ("TransporterCode", "TransporterName", "TransporterContact"),
                  "TransporterMaster")
    _require_rows(rationed_report, ("SKUCode", "WhCode", "ParentWhCode", "GIT",
                  "PhysicalInventoryPen", "PhysicalInventoryColor", "DispatchColor"),
                  "vf_RationedReqReport")
    _require_rows(standards, ("SKUCode", "WhCode", "Price"), "SKULocStandardAttributes")
    factor = _decimal(super_delay_factor, "SuperDelayFactor")

    transporters = defaultdict(list)
    for row in directory:
        code = _text(row["TransporterCode"], "directory.TransporterCode", 50)
        _text(row["TransporterName"], "directory.TransporterName", 125)
        _text(row["TransporterContact"], "directory.TransporterContact", 20)
        if code is not None:
            transporters[_join_key(code)].append(row)
    reports = defaultdict(list)
    for row in rationed_report:
        for name in ("SKUCode", "WhCode", "ParentWhCode",
                     "PhysicalInventoryColor", "DispatchColor"):
            _text(row[name], "report." + name, 50)
        git = _nullable_decimal(row["GIT"], "report.GIT")
        _nullable_decimal(row["PhysicalInventoryPen"], "report.PhysicalInventoryPen")
        key = tuple(_join_key(row[name]) for name in ("SKUCode", "WhCode", "ParentWhCode"))
        if None not in key and git is not None and git > 0:
            reports[key].append(row)
    standard_index = defaultdict(list)
    for row in standards:
        sku = _text(row["SKUCode"], "standard.SKUCode", 50)
        wh = _text(row["WhCode"], "standard.WhCode", 50)
        _target_int(row["Price"], "standard.Price")
        if sku is not None and wh is not None:
            standard_index[(_join_key(sku), _join_key(wh))].append(row)

    output = []
    for source in transit:
        for name in ("SKUCode", "WhCode", "ParentWhCode", "CurrentLocationCode",
                     "TransporterCode", "LRCode", "OrderNo"):
            _text(source[name], "transit." + name, 50)
        _text(source["Remark"], "transit.Remark")
        for name in ("CreationDate", "GateOutDate", "ETA", "ReportDate"):
            _date(source[name], "transit." + name)
        for name in ("InTransitQty", "Ageing", "TLT", "SLT"):
            _integer(source[name], "transit." + name)
        pair = (_join_key(source["SKUCode"]), _join_key(source["WhCode"]))
        report_key = (*pair, _join_key(source["ParentWhCode"]))
        if None in report_key or source["TransporterCode"] is None:
            continue
        for transporter in transporters.get(_join_key(source["TransporterCode"]), ()):
            for report in reports.get(report_key, ()):
                for standard in standard_index.get(pair, ()):
                    tlt, slt = source["TLT"], source["SLT"]
                    truck = None
                    if tlt is not None and slt is not None:
                        if Decimal(tlt) > factor * Decimal(slt):
                            truck = "SuperDelay"
                        elif tlt > slt:
                            truck = "Delay"
                    output.append({
                        "Status": "", "OrderNo": source["OrderNo"],
                        "SKUCode": source["SKUCode"], "WhCode": source["WhCode"],
                        "ParentWhCode": source["ParentWhCode"],
                        "CurrentLocation": source["CurrentLocationCode"],
                        "TransporterCode": source["TransporterCode"],
                        "TransporterName": transporter["TransporterName"],
                        "TransporterContact": transporter["TransporterContact"],
                        "LRCode": source["LRCode"], "InTransitQty": source["InTransitQty"],
                        "PhysicalInventoryPen": _nullable_decimal(
                            report["PhysicalInventoryPen"], "report.PhysicalInventoryPen"),
                        "PhysicalInventoryColor": report["PhysicalInventoryColor"],
                        "PipelineInventoryColor": report["DispatchColor"],
                        "Price": _target_int(standard["Price"], "standard.Price"),
                        "SLT": source["SLT"], "Ageing": source["Ageing"],
                        "ETA": source["ETA"], "Remark": source["Remark"],
                        "CreationDate": source["CreationDate"], "TruckStatus": truck,
                        "SKUStatus": None, "IsParent": False, "IsReceiving": True,
                    })

    # SQL UPDATE self-joins preserve a bag and set a flag; they do not add rows.
    parent_keys = {(_join_key(row["SKUCode"]), _join_key(row["ParentWhCode"]))
                   for row in output if row["SKUCode"] is not None and row["ParentWhCode"] is not None}
    for row in output:
        if (_join_key(row["SKUCode"]), _join_key(row["WhCode"])) in parent_keys:
            row["IsParent"] = True

    def overwrite(key_field, status_field):
        super_keys = {_join_key(row[key_field]) for row in output
                      if row[key_field] is not None and row[status_field] == "SuperDelay"}
        for row in output:
            if row[key_field] is not None and _join_key(row[key_field]) in super_keys:
                row[status_field] = "SuperDelay"
        delay_keys = {_join_key(row[key_field]) for row in output
                      if row[key_field] is not None and row[status_field] == "Delay"}
        for row in output:
            if row[key_field] is not None and _join_key(row[key_field]) in delay_keys:
                row[status_field] = "Delay"

    overwrite("LRCode", "TruckStatus")
    # SKUStatus starts NULL; its two passes source TruckStatus, not prior SKUStatus.
    super_skus = {_join_key(row["SKUCode"]) for row in output
                  if row["SKUCode"] is not None and row["TruckStatus"] == "SuperDelay"}
    delay_skus = {_join_key(row["SKUCode"]) for row in output
                  if row["SKUCode"] is not None and row["TruckStatus"] == "Delay"}
    for row in output:
        if _join_key(row["SKUCode"]) in super_skus:
            row["SKUStatus"] = "SuperDelay"
    # Preserve the deployed statement sequence exactly: unlike the comment in
    # the SQL, its later Delay UPDATE overwrites a SuperDelay SKUStatus when the
    # SKU has shipments in both status groups (TruckStatus itself is unchanged).
    for row in output:
        if _join_key(row["SKUCode"]) in delay_skus:
            row["SKUStatus"] = "Delay"
    return deepcopy(output)
