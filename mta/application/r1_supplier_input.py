"""Selected Importer supplier validators and independent BPR state ownership.

SQL-shaped raw rows are input facts. Master/descriptions/rejections are passed
from the master producer, never supplied as current-day processed fixture data.
"""
from collections import Counter, defaultdict
from copy import deepcopy
from decimal import Decimal, InvalidOperation
import json
import math

from mta.application.r1_importer_master import TABLE_COLUMNS as MASTER_TABLES, _sql_key, _distinct

RAW_TABLES = {
    "SOBDataRaw": ("SKUCode", "WHCode", "SupplierCode", "SupplierDescription", "SOB"),
    "MOQDataRaw1": ("SKUCode", "SupplierCode", "SupplierDescription", "MOQ"),
    "MOQDataRaw2": ("SKUCode", "WHCode", "SupplierCode", "SupplierDescription", "MOQ"),
}
OPENING_TABLES = {"SOBData": ("SKUCode", "WHCode", "SupplierCode", "SOB"),
                  "MOQData": ("SKUCode", "WHCode", "SupplierCode", "MOQ")}
CHECKPOINT_TABLES = {**RAW_TABLES, "SiteDescriptionTbl": MASTER_TABLES["SiteDescriptionTbl"],
                     "RejectedMaster": MASTER_TABLES["RejectedMaster"], "ImporterSettingsTbl": ("Parameter", "Value")}
STAGES = ("ValidateSOBData.sql", "ValidateMOQDataRaw1.sql", "ValidateMOQDataRaw2.sql", "ResetFlags.sql")


def typed_supplier_tables(payload, columns=RAW_TABLES):
    """SQL type contract only; source business rejection belongs to the port."""
    if not isinstance(payload, dict) or set(payload) != set(columns):
        raise ValueError("Supplier inputs must explicitly include each independent table")
    tables = {}
    for table, fields in columns.items():
        if not isinstance(payload[table], list):
            raise ValueError("Supplier table must be a row list")
        rows = []
        for row in payload[table]:
            if not isinstance(row, dict) or set(row) - set(fields):
                raise ValueError("Unknown supplier source field")
            result = {}
            for field in fields:
                value = row.get(field)
                if value is None:
                    result[field] = None
                elif field in {"SOB", "MOQ"}:
                    try:
                        number = Decimal(str(value))
                    except (InvalidOperation, ValueError):
                        raise ValueError("Invalid supplier numeric source") from None
                    if isinstance(value, bool) or not number.is_finite():
                        raise ValueError("Invalid supplier numeric source")
                    if field == "MOQ":
                        if number != number.to_integral_value() or not -2147483648 <= number <= 2147483647:
                            raise ValueError("Supplier MOQ must fit SQL int")
                        result[field] = int(number)
                    else:
                        result[field] = float(number)
                        if not math.isfinite(result[field]):
                            raise ValueError("Supplier SOB must fit SQL float")
                else:
                    limit = 125 if field == "SupplierDescription" else 50
                    if not isinstance(value, str) or not value.isascii() or len(value) > limit:
                        raise ValueError("Supplier text requires bounded ASCII; wider collation unproven")
                    result[field] = value
            if table in OPENING_TABLES and any(v is None for v in result.values()):
                raise ValueError("Prior BPR supplier columns are NOT NULL")
            rows.append(result)
        tables[table] = rows
    return tables


def sorted_rows(rows):
    return sorted(deepcopy(rows), key=lambda r: json.dumps(r, sort_keys=True))


def process_supplier_validation(raw, master_validation, settings, now):
    tables = typed_supplier_tables(raw)
    master = master_validation["tables"]
    tables.update(SiteDescriptionTbl=deepcopy(master["SiteDescriptionTbl"]),
                  RejectedMaster=deepcopy(master["RejectedMaster"]), ImporterSettingsTbl=deepcopy(settings))
    # All three raw VARCHAR descriptions have ANSI_PADDING OFF in pinned DDL.
    for table in RAW_TABLES:
        for row in tables[table]:
            value = row["SupplierDescription"]
            if value is not None:
                row["SupplierDescription"] = value.rstrip(" ") or (" " if value else "")

    def reject(table, rows, code, message, *, missing="", blank_location=False):
        rejects = [{"SKUCode": r.get("SKUCode") if r.get("SKUCode") is not None else missing,
                    "WhCode": "" if blank_location else r.get("WHCode") if r.get("WHCode") is not None else missing,
                    "RejectionDate": now, "ReasonCode": code,
                    "ReasonDescription": message(r) if callable(message) else message} for r in rows]
        # SQL INSERT is statement-atomic; truncation error precedes raw clearing.
        if any(len(r["ReasonDescription"]) > 100 for r in rejects):
            return "SQL_ERROR"
        tables["RejectedMaster"].extend(rejects)
        tables[table].clear()
        return "EARLY_RETURN"

    def warning(table, code, message):
        return reject(table, [{"SKUCode": "-NA-", "WHCode": "-NA-"}], code, message)

    def validate(table):
        raw1, sob = table == "MOQDataRaw1", table == "SOBDataRaw"
        value = "SOB" if sob else "MOQ"
        base = 180 if sob else 210 if raw1 else 220
        rows = tables[table]
        if raw1 and rows:
            tables["MOQDataRaw2"].clear()  # Before any Raw1 rejection.
        if not raw1 and not rows:
            return warning(table, -base, f"Warning-{value} file/table is not available or unreadable")
        had_rows = bool(rows)
        rows[:] = [r for r in rows if r["SKUCode"] is not None or r["SupplierCode" if raw1 else "WHCode"] is not None]
        if had_rows and not rows:
            identity = "SupplierCode" if raw1 else "WHCode"
            return reject(table, [{"SKUCode": "" if raw1 else "-NA-", "WHCode": "" if raw1 else "-NA-"}], base,
                          f"Null SKUCode and {identity} for all records in {value} file/table")
        for row in rows:
            for field in RAW_TABLES[table]:
                if isinstance(row[field], str):
                    row[field] = row[field].strip(" ")
        rows[:] = _distinct(rows, RAW_TABLES[table])
        keys = ("SKUCode", "SupplierCode") if raw1 else ("SKUCode", "WHCode", "SupplierCode")
        invalid = [r for r in rows if any(r[f] is None for f in (*keys, value))]
        if invalid:
            if sob:
                message = "Null SKUCode/WhCode/SupplierCode/SOB in SOB File"
            else:
                prefix = "Null SKUCode/" + ("" if raw1 else "WhCode/") + "SupplierCode/MOQ in MOQ file/table"
                message = lambda r: prefix + ((" For Supplier " if raw1 else " for Supplier ") + r["SupplierCode"]
                    if r["SupplierCode"] is not None and _sql_key(r["SupplierCode"]) != "" else "")
            return reject(table, invalid, base + 1, message, missing="Invalid" if sob else "", blank_location=raw1)
        counts = Counter(tuple(_sql_key(r[f]) for f in keys) for r in rows)
        duplicates = _distinct([r for r in rows if counts[tuple(_sql_key(r[f]) for f in keys)] > 1], keys)
        if duplicates:
            prefix = "SKUCode-" + ("" if raw1 else "WHCode-") + f"Supplier combination repeated in {value} file/table"
            return reject(table, duplicates, base + 2, prefix if sob else lambda r: prefix + " for supplier " + r["SupplierCode"], blank_location=raw1)
        invalid = [r for r in rows if r[value] < 0]
        if invalid:
            message = "Negative SOB value in SOB file/table" if sob else lambda r: "MOQ value is negative in MOQ file/table for " + ("supplier " if raw1 else "Supplier ") + r["SupplierCode"]
            return reject(table, invalid, base + 3, message, blank_location=raw1)
        names = _distinct(rows, ("SupplierCode", "SupplierDescription"))
        # SOB fills Intermediate.LocNames (WHDescription NOT NULL) before its
        # name-conflict check. Existing SiteDescription does not avoid this.
        if sob and any(r["SupplierDescription"] is None for r in names):
            return "SQL_ERROR"
        counts = Counter(_sql_key(r["SupplierCode"]) for r in names)
        duplicates = _distinct([r for r in names if counts[_sql_key(r["SupplierCode"])] > 1], ("SupplierCode",))
        if duplicates:
            records = [{**r, "SKUCode": "-NA-" if sob else "", "WHCode": "-NA-" if sob else ""} for r in duplicates]
            message = (lambda r: "Supplier Code " + r["SupplierCode"] + " has multiple names in Supplier data") if sob else (
                lambda r: "SupplierCode " + r["SupplierCode"] + " with multiple names in MOQ " + ("File" if raw1 else "file") + "/table")
            return reject(table, records, base + 4, message)
        if not raw1:
            # Raw2 fills the same NOT NULL temporary table only after checking
            # conflicting names; Raw1 never fills it. Preserve that ordering.
            if any(r["SupplierDescription"] is None for r in names):
                return "SQL_ERROR"
            existing = {_sql_key(r["WHCode"]) for r in tables["SiteDescriptionTbl"]}
            additions = [{"WHCode": r["SupplierCode"], "WHDescription": r["SupplierDescription"]}
                         for r in names if _sql_key(r["SupplierCode"]) not in existing]
            tables["SiteDescriptionTbl"].extend(additions)
        return "APPLIED"

    stages = {}
    for stage, table in zip(STAGES[:3], RAW_TABLES):
        if table == "MOQDataRaw2" and tables["MOQDataRaw1"]:
            sob_keys = {(_sql_key(r["SKUCode"]), _sql_key(r["WHCode"])) for r in tables["SOBDataRaw"]}
            parents = [(r["SKUCode"], r["WhCode"], r["ParentWhCode"]) for r in master["MasterData"]
                       if (_sql_key(r["SKUCode"]), _sql_key(r["WhCode"])) not in sob_keys]
            parents.extend((r["SKUCode"], r["WHCode"], r["SupplierCode"]) for r in tables["SOBDataRaw"])
            tables[table] = [{**r, "WHCode": wh} for r in tables["MOQDataRaw1"] for sku, wh, parent in parents
                             if parent is not None and r["SupplierCode"] is not None and r["SKUCode"] is not None
                             and (_sql_key(r["SKUCode"]), _sql_key(r["SupplierCode"])) == (_sql_key(sku), _sql_key(parent))]
        outcome = validate(table)
        stages[stage] = {"outcome": outcome, "tables": {t: sorted_rows(rows) for t, rows in tables.items()}}
    # Selected shell ImportNoNormData=0. Do not test processed master presence.
    if master["MasterDataRaw"]:
        for row in tables["ImporterSettingsTbl"]:
            if row["Parameter"] == "UpdatePWh_RLT_RCP_GCP":
                row["Value"] = 0
    stages[STAGES[3]] = {"outcome": "APPLIED", "tables": {t: sorted_rows(rows) for t, rows in tables.items()}}
    return stages


def supplier_calculation_state(opening, validated, master, *, vendor_codes):
    """Preserve each BPR table independently at the later normal-BOR refresh."""
    # GenSupplierWiseReq reads VendorList even when the vendor module is disabled.
    # Require this independent source population; never infer it from master.
    if (not isinstance(vendor_codes, list)
            or any(not isinstance(code, str) or not code.isascii() or len(code) > 50 for code in vendor_codes)
            or len({_sql_key(code) for code in vendor_codes}) != len(vendor_codes)):
        raise ValueError("VendorList requires explicit bounded, SQL-key-unique source codes")
    vendors = {_sql_key(code) for code in vendor_codes}
    prior = typed_supplier_tables(opening, OPENING_TABLES)
    current = deepcopy(prior)
    for dest, source in (("SOBData", "SOBDataRaw"), ("MOQData", "MOQDataRaw2")):
        if validated[source]:
            current[dest] = [{f: r[f] for f in OPENING_TABLES[dest]} for r in validated[source]]

    def project(tables, *, normal_bor):
        by_table = {}
        key_fields = ("SKUCode", "WHCode", "SupplierCode")
        for table, rows in tables.items():
            by_table[table] = {}
            for r in rows:
                key = tuple(_sql_key(r[f]) for f in key_fields)
                if key in by_table[table]:
                    raise ValueError("UNPROVEN: duplicate prior supplier state grain")
                by_table[table][key] = r
        # SQL union is SOB, then MOQ-only, then topmost without any supplier.
        rows = [{**r, "MOQ": 0} for r in tables["SOBData"]]
        rows.extend({**r, "SOB": 100.0} for k, r in by_table["MOQData"].items() if k not in by_table["SOBData"])
        covered = {(_sql_key(r["SKUCode"]), _sql_key(r["WHCode"])) for r in rows}
        physical = {(_sql_key(r["SKUCode"]), _sql_key(r["WhCode"])) for r in master}
        for r in master:
            key = (_sql_key(r["SKUCode"]), _sql_key(r["WhCode"]))
            if key not in covered and (_sql_key(r["SKUCode"]), _sql_key(r["ParentWhCode"])) not in physical:
                rows.append({"SKUCode": r["SKUCode"], "WHCode": r["WhCode"], "SupplierCode": r["ParentWhCode"], "SOB": 100.0, "MOQ": 0})
                covered.add(key)
        # Only the later normal BOR includes uncovered vendor-parent children;
        # BOR-OA has no equivalent VendorList branch. Use the joined vendor's
        # spelling, as the source selects B.WhCode rather than A.ParentWhCode.
        if normal_bor:
            vendor_spelling = {_sql_key(code): code for code in vendor_codes}
            for r in master:
                key = (_sql_key(r["SKUCode"]), _sql_key(r["WhCode"]))
                parent = _sql_key(r["ParentWhCode"])
                if key not in covered and parent in vendors:
                    rows.append({"SKUCode": r["SKUCode"], "WHCode": r["WhCode"], "SupplierCode": vendor_spelling[parent], "SOB": 100.0, "MOQ": 0})
                    covered.add(key)
        for r in rows:
            key = tuple(_sql_key(r[f]) for f in key_fields)
            r["MOQ"] = by_table["MOQData"].get(key, {}).get("MOQ", 0)
        # Final report SQL inner joins physical requirement/master populations.
        return [{"sku_code": r["SKUCode"], "location_code": r["WHCode"], "supplier": r["SupplierCode"],
                 "sob": str(r["SOB"]), "moq": r["MOQ"]} for r in rows
                if (_sql_key(r["SKUCode"]), _sql_key(r["WHCode"])) in physical]

    return {"prior_sob": sorted_rows(prior["SOBData"]), "prior_moq": sorted_rows(prior["MOQData"]),
            "refreshed_sob": sorted_rows(current["SOBData"]), "refreshed_moq": sorted_rows(current["MOQData"])}, project(prior, normal_bor=False), project(current, normal_bor=True)
